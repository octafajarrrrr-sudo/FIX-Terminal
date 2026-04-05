require('dotenv').config();
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const io = socketIo(server, { cors: { origin: '*' } });

// Import services
const binance = require('./services/binance');
const ffBot = require('./services/fundingFeeBot');

// ============ Funding Fee Bot Endpoints ============

// Get full bot status
app.get('/api/ff/status', (req, res) => {
  res.json(ffBot.getStatus());
});

// Start the bot
app.post('/api/ff/start', (req, res) => {
  try {
    const result = ffBot.startBot(req.body || {});
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Stop the bot
app.post('/api/ff/stop', (req, res) => {
  try {
    const result = ffBot.stopBot();
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update bot config
app.post('/api/ff/config', (req, res) => {
  try {
    const result = ffBot.updateConfig(req.body);
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Manual funding rate scan
app.get('/api/ff/scan', async (req, res) => {
  try {
    const data = await ffBot.scanFundingRates();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get opportunities above threshold
app.get('/api/ff/opportunities', async (req, res) => {
  try {
    const data = await ffBot.getOpportunities();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Manually open a hedged position
app.post('/api/ff/open', async (req, res) => {
  try {
    const { symbol } = req.body;
    if (!symbol) return res.status(400).json({ error: 'symbol is required' });

    // Get current funding rate for the symbol
    const rate = await binance.getFundingRate(symbol);
    const fundingRate = parseFloat(rate.lastFundingRate);

    const result = await ffBot.openHedgedPosition(symbol, fundingRate);
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Close a specific position
app.post('/api/ff/close', async (req, res) => {
  try {
    const { positionId } = req.body;
    if (!positionId) return res.status(400).json({ error: 'positionId is required' });
    const result = await ffBot.closeHedgedPosition(positionId);
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Close all active positions
app.post('/api/ff/close-all', async (req, res) => {
  try {
    const results = await ffBot.closeAllPositions();
    res.json(results);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ============ Binance Direct Endpoints ============

// Futures balance
app.get('/api/binance/balance', async (req, res) => {
  try {
    const data = await binance.getFuturesBalance();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Current futures positions
app.get('/api/binance/positions', async (req, res) => {
  try {
    const data = await binance.getFuturesPositions();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Funding rate history
app.get('/api/binance/funding-history/:symbol', async (req, res) => {
  try {
    const data = await binance.getFundingRateHistory(req.params.symbol);
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ============ Socket.IO for real-time updates ============

io.on('connection', (socket) => {
  console.log('Client connected');

  // Send bot status every 5 seconds to connected clients
  const statusInterval = setInterval(() => {
    socket.emit('ff:status', ffBot.getStatus());
  }, 5000);

  socket.on('ff:scan', async () => {
    try {
      const data = await ffBot.scanFundingRates();
      socket.emit('ff:scanResult', data);
    } catch (err) {
      socket.emit('ff:error', { message: err.message });
    }
  });

  socket.on('disconnect', () => {
    clearInterval(statusInterval);
    console.log('Client disconnected');
  });
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => console.log(`FF Bot server running on port ${PORT}`));
