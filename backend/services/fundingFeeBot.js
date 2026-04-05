const binance = require('./binance');

/**
 * Funding Fee (FF) Arbitrage Bot for Binance
 *
 * Strategy overview:
 *   1. Scan all perpetual futures for extreme funding rates
 *   2. When funding rate is highly positive (longs pay shorts):
 *      - Open SHORT futures position to *receive* funding
 *      - Simultaneously BUY equivalent amount on SPOT to hedge price risk
 *   3. When funding rate is highly negative (shorts pay longs):
 *      - Open LONG futures position to *receive* funding
 *      - Simultaneously SELL equivalent amount on SPOT to hedge price risk
 *   4. Hold through the funding settlement (every 8 hours on Binance)
 *   5. Close both positions after collecting the fee
 *
 * Funding times on Binance: 00:00 UTC, 08:00 UTC, 16:00 UTC
 */

// Bot state
const state = {
  running: false,
  config: {
    minFundingRate: 0.01,       // Minimum absolute funding rate to enter (1% annualized ~ 0.01% per 8h)
    maxPositionUSDT: 500,       // Max USDT per position
    leverage: 1,                // Keep leverage low for safety
    marginType: 'ISOLATED',     // ISOLATED margin to limit risk
    symbols: [],                // Empty = scan all; or specify e.g. ['BTCUSDT','ETHUSDT']
    autoClose: true,            // Auto-close after funding collection
    closeDelayMinutes: 5,       // Minutes after funding time to close positions
    dryRun: true,               // Dry-run mode (no real orders)
  },
  activePositions: [],          // Tracked hedged positions
  tradeHistory: [],             // Past trades log
  scanResults: [],              // Latest funding rate scan
  lastScanTime: null,
  intervalId: null,
};

/**
 * Get next Binance funding time (00:00, 08:00, 16:00 UTC).
 */
function getNextFundingTime() {
  const now = new Date();
  const hours = now.getUTCHours();
  let nextHour;

  if (hours < 8) nextHour = 8;
  else if (hours < 16) nextHour = 16;
  else nextHour = 24; // next day 00:00

  const next = new Date(now);
  next.setUTCHours(nextHour % 24, 0, 0, 0);
  if (nextHour === 24) next.setUTCDate(next.getUTCDate() + 1);

  return next;
}

/**
 * Get minutes until next funding time.
 */
function getMinutesUntilFunding() {
  const next = getNextFundingTime();
  return (next.getTime() - Date.now()) / (1000 * 60);
}

/**
 * Scan all symbols for high funding rates.
 */
async function scanFundingRates() {
  const allRates = await binance.getAllFundingRates();

  const processed = allRates
    .map((item) => ({
      symbol: item.symbol,
      fundingRate: parseFloat(item.lastFundingRate),
      fundingRatePercent: (parseFloat(item.lastFundingRate) * 100).toFixed(4),
      markPrice: parseFloat(item.markPrice),
      indexPrice: parseFloat(item.indexPrice),
      nextFundingTime: new Date(item.nextFundingTime).toISOString(),
      annualizedRate: (parseFloat(item.lastFundingRate) * 3 * 365 * 100).toFixed(2),
    }))
    .filter((item) => {
      // Filter by configured symbols if specified
      if (state.config.symbols.length > 0) {
        return state.config.symbols.includes(item.symbol);
      }
      return true;
    })
    .sort((a, b) => Math.abs(b.fundingRate) - Math.abs(a.fundingRate));

  state.scanResults = processed;
  state.lastScanTime = new Date().toISOString();

  return processed;
}

/**
 * Get top opportunities based on funding rate threshold.
 */
async function getOpportunities() {
  const rates = await scanFundingRates();
  const minRate = state.config.minFundingRate / 100; // Convert from percent to decimal

  return rates.filter((r) => Math.abs(r.fundingRate) >= minRate);
}

/**
 * Calculate the quantity to trade based on max USDT and current price.
 */
function calculateQuantity(price, maxUsdt) {
  const rawQty = maxUsdt / price;
  // Round down to reasonable precision (3 decimal places for most coins)
  return Math.floor(rawQty * 1000) / 1000;
}

/**
 * Open a hedged position (futures + spot).
 *
 * If funding rate is positive: SHORT futures + BUY spot (receive funding from longs)
 * If funding rate is negative: LONG futures + SELL spot (receive funding from shorts)
 */
async function openHedgedPosition(symbol, fundingRate) {
  const { maxPositionUSDT, leverage, marginType, dryRun } = state.config;

  // Get current price
  const ticker = await binance.getFuturesTickerPrice(symbol);
  const price = parseFloat(ticker.price);
  const quantity = calculateQuantity(price, maxPositionUSDT);

  if (quantity <= 0) {
    return { error: 'Calculated quantity is zero or negative' };
  }

  // Determine direction based on funding rate
  const futuresSide = fundingRate > 0 ? 'SELL' : 'BUY';   // Short if positive FR, Long if negative
  const spotSide = fundingRate > 0 ? 'BUY' : 'SELL';       // Hedge opposite on spot

  const position = {
    id: `ff-${Date.now()}`,
    symbol,
    fundingRate,
    fundingRatePercent: (fundingRate * 100).toFixed(4) + '%',
    direction: futuresSide === 'SELL' ? 'SHORT_FUTURES_LONG_SPOT' : 'LONG_FUTURES_SHORT_SPOT',
    quantity,
    entryPrice: price,
    notionalUSDT: (price * quantity).toFixed(2),
    openedAt: new Date().toISOString(),
    status: 'OPEN',
    futuresOrder: null,
    spotOrder: null,
    estimatedFeeUSDT: (Math.abs(fundingRate) * price * quantity).toFixed(4),
  };

  if (dryRun) {
    position.futuresOrder = { dryRun: true, side: futuresSide, symbol, quantity, type: 'MARKET' };
    position.spotOrder = { dryRun: true, side: spotSide, symbol, quantity, type: 'MARKET' };
    console.log(`[DRY RUN] Would open hedged position: ${JSON.stringify(position)}`);
  } else {
    try {
      // Set leverage and margin type first
      await binance.setLeverage(symbol, leverage);
      await binance.setMarginType(symbol, marginType);

      // Place futures order
      position.futuresOrder = await binance.placeFuturesOrder({
        symbol,
        side: futuresSide,
        type: 'MARKET',
        quantity: String(quantity),
      });

      // Place spot order as hedge
      position.spotOrder = await binance.placeSpotOrder({
        symbol,
        side: spotSide,
        type: 'MARKET',
        quantity: String(quantity),
      });
    } catch (err) {
      position.status = 'ERROR';
      position.error = err.message;
      console.error(`[FF Bot] Error opening position for ${symbol}:`, err.message);
    }
  }

  state.activePositions.push(position);
  return position;
}

/**
 * Close a hedged position (reverse both futures and spot).
 */
async function closeHedgedPosition(positionId) {
  const { dryRun } = state.config;
  const posIndex = state.activePositions.findIndex((p) => p.id === positionId);

  if (posIndex === -1) {
    return { error: 'Position not found' };
  }

  const position = state.activePositions[posIndex];
  const { symbol, quantity, direction } = position;

  // Reverse the sides
  const futuresSide = direction === 'SHORT_FUTURES_LONG_SPOT' ? 'BUY' : 'SELL';
  const spotSide = direction === 'SHORT_FUTURES_LONG_SPOT' ? 'SELL' : 'BUY';

  if (dryRun) {
    position.closeOrders = {
      futures: { dryRun: true, side: futuresSide, symbol, quantity, type: 'MARKET' },
      spot: { dryRun: true, side: spotSide, symbol, quantity, type: 'MARKET' },
    };
    console.log(`[DRY RUN] Would close hedged position: ${positionId}`);
  } else {
    try {
      position.closeOrders = {
        futures: await binance.placeFuturesOrder({
          symbol,
          side: futuresSide,
          type: 'MARKET',
          quantity: String(quantity),
          reduceOnly: 'true',
        }),
        spot: await binance.placeSpotOrder({
          symbol,
          side: spotSide,
          type: 'MARKET',
          quantity: String(quantity),
        }),
      };
    } catch (err) {
      position.closeError = err.message;
      console.error(`[FF Bot] Error closing position ${positionId}:`, err.message);
      return { error: err.message };
    }
  }

  // Get exit price for PnL calculation
  try {
    const ticker = await binance.getFuturesTickerPrice(symbol);
    position.exitPrice = parseFloat(ticker.price);
    const priceDiff = position.exitPrice - position.entryPrice;
    // For SHORT_FUTURES_LONG_SPOT: futures PnL is negative of price change, spot PnL is positive
    // Net PnL from price movement should be ~0 (hedged), profit comes from funding fee
    position.estimatedNetPnL = parseFloat(position.estimatedFeeUSDT);
  } catch (_) {
    position.exitPrice = null;
  }

  position.status = 'CLOSED';
  position.closedAt = new Date().toISOString();

  // Move to history
  state.tradeHistory.push(position);
  state.activePositions.splice(posIndex, 1);

  return position;
}

/**
 * Close all active positions.
 */
async function closeAllPositions() {
  const results = [];
  const positionIds = state.activePositions.map((p) => p.id);

  for (const id of positionIds) {
    const result = await closeHedgedPosition(id);
    results.push(result);
  }

  return results;
}

/**
 * Main bot loop: scan, open positions if opportunities exist, schedule closing.
 */
async function botCycle() {
  if (!state.running) return;

  console.log('[FF Bot] Running scan cycle...');
  const minutesUntilFunding = getMinutesUntilFunding();
  console.log(`[FF Bot] Minutes until next funding: ${minutesUntilFunding.toFixed(1)}`);

  try {
    const opportunities = await getOpportunities();
    console.log(`[FF Bot] Found ${opportunities.length} opportunities above threshold`);

    // Only open positions if we're within 30 minutes of funding time
    // and we don't already have too many positions open
    if (minutesUntilFunding <= 30 && minutesUntilFunding > 5) {
      const maxNewPositions = 3 - state.activePositions.length;

      for (let i = 0; i < Math.min(opportunities.length, maxNewPositions); i++) {
        const opp = opportunities[i];

        // Skip if we already have a position for this symbol
        if (state.activePositions.some((p) => p.symbol === opp.symbol)) {
          continue;
        }

        console.log(
          `[FF Bot] Opening hedged position for ${opp.symbol} (FR: ${opp.fundingRatePercent}%)`
        );
        await openHedgedPosition(opp.symbol, opp.fundingRate);
      }
    }

    // Auto-close positions after funding has been collected
    if (state.config.autoClose && state.activePositions.length > 0) {
      const recentFundingPassed = state.activePositions.some((p) => {
        const openedAt = new Date(p.openedAt).getTime();
        const now = Date.now();
        const eightHours = 8 * 60 * 60 * 1000;
        // If position has been open for more than the close delay after a funding period
        return (now - openedAt) > (eightHours + state.config.closeDelayMinutes * 60 * 1000);
      });

      if (recentFundingPassed) {
        console.log('[FF Bot] Auto-closing positions after funding collection');
        await closeAllPositions();
      }
    }
  } catch (err) {
    console.error('[FF Bot] Cycle error:', err.message);
  }
}

/**
 * Start the bot with given config overrides.
 */
function startBot(configOverrides = {}) {
  if (state.running) {
    return { status: 'already_running', config: state.config };
  }

  // Apply config overrides
  Object.assign(state.config, configOverrides);
  state.running = true;

  // Run immediately, then every 60 seconds
  botCycle();
  state.intervalId = setInterval(botCycle, 60 * 1000);

  console.log('[FF Bot] Started with config:', state.config);
  return { status: 'started', config: state.config };
}

/**
 * Stop the bot.
 */
function stopBot() {
  if (!state.running) {
    return { status: 'already_stopped' };
  }

  state.running = false;
  if (state.intervalId) {
    clearInterval(state.intervalId);
    state.intervalId = null;
  }

  console.log('[FF Bot] Stopped');
  return { status: 'stopped' };
}

/**
 * Update bot configuration (while running or stopped).
 */
function updateConfig(newConfig) {
  Object.assign(state.config, newConfig);
  return { config: state.config };
}

/**
 * Get full bot status.
 */
function getStatus() {
  return {
    running: state.running,
    config: state.config,
    activePositions: state.activePositions,
    tradeHistory: state.tradeHistory.slice(-20), // Last 20 trades
    scanResults: state.scanResults.slice(0, 20),  // Top 20 by funding rate
    lastScanTime: state.lastScanTime,
    nextFundingTime: getNextFundingTime().toISOString(),
    minutesUntilFunding: getMinutesUntilFunding().toFixed(1),
    totalEstimatedProfit: state.tradeHistory
      .reduce((sum, t) => sum + (parseFloat(t.estimatedNetPnL) || 0), 0)
      .toFixed(4),
  };
}

module.exports = {
  startBot,
  stopBot,
  updateConfig,
  getStatus,
  scanFundingRates,
  getOpportunities,
  openHedgedPosition,
  closeHedgedPosition,
  closeAllPositions,
  getNextFundingTime,
};
