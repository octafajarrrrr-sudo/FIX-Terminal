# Funding Fee (FF) Arbitrage Bot - Binance

Auto-trade bot that exploits funding rate differentials on Binance perpetual futures by opening delta-neutral (hedged) positions to collect funding fees.

---

## Strategy Overview

Funding fees are periodic payments between long and short holders on perpetual futures contracts. On Binance, funding is settled every **8 hours** (00:00, 08:00, 16:00 UTC). The bot earns profit by:

- **Positive funding rate**: Longs pay shorts. Bot opens SHORT futures + BUY spot (hedge).
- **Negative funding rate**: Shorts pay longs. Bot opens LONG futures + SELL spot (hedge).

The spot position neutralizes price risk while the futures position collects the funding fee.

---

## Flowchart

```
                    +---------------------------+
                    |       BOT STARTED         |
                    +---------------------------+
                                |
                                v
                    +---------------------------+
                    |  Scan All Funding Rates   |
                    |  (Every 60 seconds)       |
                    +---------------------------+
                                |
                                v
                    +---------------------------+
                    | Filter by min threshold   |
                    | (default >= 0.01%)        |
                    +---------------------------+
                                |
                                v
                   +----------------------------+
                   | Minutes until funding < 30 |
                   | AND > 5 minutes?           |
                   +----------------------------+
                      |                    |
                     YES                   NO
                      |                    |
                      v                    v
        +-------------------------+   (Wait for next cycle)
        | Select top opportunity  |
        +-------------------------+
                      |
                      v
        +-------------------------+
        | Funding Rate > 0?       |
        +-------+--------+-------+
                |                |
              YES               NO
                |                |
                v                v
    +-------------------+  +-------------------+
    | SHORT Futures     |  | LONG Futures      |
    | + BUY Spot        |  | + SELL Spot       |
    | (Collect from     |  | (Collect from     |
    |  longs)           |  |  shorts)          |
    +-------------------+  +-------------------+
                |                |
                +-------+--------+
                        |
                        v
            +---------------------------+
            | Wait for Funding          |
            | Settlement (8h cycle)     |
            +---------------------------+
                        |
                        v
            +---------------------------+
            | Funding Fee Collected!    |
            +---------------------------+
                        |
                        v
            +---------------------------+
            | Auto-close both          |
            | positions (futures +     |
            | spot) after delay        |
            +---------------------------+
                        |
                        v
            +---------------------------+
            | Log PnL & repeat cycle   |
            +---------------------------+
```

---

## Workflow

### 1. Setup Phase
```
User configures:
  - Binance API Key & Secret
  - Min funding rate threshold (default 0.01%)
  - Max position size in USDT (default 500)
  - Leverage (default 1x)
  - Margin type (ISOLATED)
  - Dry-run mode (default ON)
  - Specific symbols or scan all
```

### 2. Scanning Phase (runs every 60s when bot is active)
```
1. Fetch /fapi/v1/premiumIndex for all symbols
2. Sort by |fundingRate| descending
3. Filter above threshold
4. Check time until next funding settlement
5. Return ranked opportunities
```

### 3. Entry Phase (30 min before funding)
```
1. Pick top N opportunities (max 3 concurrent positions)
2. For each opportunity:
   a. Set leverage and margin type
   b. Place MARKET futures order (SHORT if FR>0, LONG if FR<0)
   c. Place MARKET spot order (opposite side as hedge)
   d. Record entry price, quantity, estimated fee
```

### 4. Collection Phase (at funding time)
```
- Funding fee is automatically credited/debited by Binance
- No action needed from the bot during settlement
```

### 5. Exit Phase (configurable delay after funding)
```
1. Close futures position (reduceOnly market order)
2. Close spot position (market order)
3. Calculate actual PnL (funding collected - trading fees - slippage)
4. Log trade to history
```

---

## Project Structure

```
FIX-Terminal/
  backend/
    .env.example          # Environment variables template
    package.json          # Node.js dependencies
    server.js             # Express + Socket.IO server with bot API
    services/
      binance.js          # Binance API wrapper (futures + spot)
      fundingFeeBot.js    # Core bot logic and state management
  frontend/
    package.json          # React dependencies
    public/
      index.html          # HTML entry point
    src/
      index.js            # React entry point
      api.js              # API client for backend
      App.js              # Main app with bot dashboard
      App.css             # Dashboard styling
      components/
        PanelFundingBot.js    # Bot control panel (start/stop/config)
        PanelOpportunities.js # Live funding rate opportunities
        PanelPositions.js     # Active & historical positions
```

---

## Quick Start

### 1. Backend

```bash
cd backend
cp .env.example .env
# Fill in your Binance API key and secret
npm install
npm start
```

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

### 3. Usage

1. Open the dashboard at `http://localhost:3000`
2. Configure bot parameters (threshold, max position size, etc.)
3. Enable **Dry Run** mode first to test without real orders
4. Click **Start Bot** to begin scanning
5. Monitor opportunities, active positions, and trade history
6. Click **Stop Bot** to halt operations

---

## Risk Warnings

- **This bot trades real money when dry-run mode is OFF.** Use at your own risk.
- Funding fee arbitrage is not risk-free: slippage, exchange fees, and execution delays can eat into profits.
- Always test with dry-run mode and small position sizes first.
- Ensure your Binance account has sufficient balance in both spot and futures wallets.
- The bot uses ISOLATED margin to limit downside risk per position.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ff/status` | Bot status, config, positions, history |
| POST | `/api/ff/start` | Start the bot (accepts config overrides in body) |
| POST | `/api/ff/stop` | Stop the bot |
| POST | `/api/ff/config` | Update bot configuration |
| GET | `/api/ff/scan` | Trigger manual funding rate scan |
| GET | `/api/ff/opportunities` | Get current opportunities above threshold |
| POST | `/api/ff/open` | Manually open a hedged position `{ symbol }` |
| POST | `/api/ff/close` | Close a specific position `{ positionId }` |
| POST | `/api/ff/close-all` | Close all active positions |
| GET | `/api/binance/balance` | Futures wallet balance |
| GET | `/api/binance/positions` | Current futures positions |
| GET | `/api/binance/funding-history/:symbol` | Funding rate history |

---

## License

MIT
