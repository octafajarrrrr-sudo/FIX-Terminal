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
const bingxService = require('./services/bingx');
const coinglassService = require('./services/coinglass');
const whaleAlertService = require('./services/whalealert');
const sentimentService = require('./services/sentiment');
const aiService = require('./services/ai');

// REST endpoints
app.get('/api/account', async (req, res) => {
  try {
    const account = await bingxService.getAccount();
    res.json(account);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/positions', async (req, res) => {
  try {
    const positions = await bingxService.getPositions();
    res.json(positions);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/orders', async (req, res) => {
  try {
    const order = await bingxService.placeOrder(req.body);
    res.json(order);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/coinglass/oi', async (req, res) => {
  try {
    const { symbol } = req.query;
    const data = await coinglassService.getOpenInterest(symbol);
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/coinglass/funding', async (req, res) => {
  try {
    const { symbol } = req.query;
    const data = await coinglassService.getFundingRate(symbol);
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/coinglass/whale', async (req, res) => {
  try {
    const data = await coinglassService.getWhaleTracker();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/whalealert', async (req, res) => {
  try {
    const txs = await whaleAlertService.getRecentTransactions();
    res.json(txs);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/sentiment/:symbol', async (req, res) => {
  try {
    const data = await sentimentService.getSentiment(req.params.symbol);
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/ai/:symbol', async (req, res) => {
  try {
    const analysis = await aiService.analyze(req.params.symbol);
    res.json(analysis);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Socket.IO untuk real-time price
io.on('connection', (socket) => {
  console.log('Client connected');

  socket.on('subscribe', (symbol) => {
    // Panggil method subscribePrice dari bingxService dengan callback untuk mengirim ke client
    bingxService.subscribePrice(symbol, (price) => {
      socket.emit('price', { symbol, price });
    });
  });

  socket.on('disconnect', () => console.log('Client disconnected'));
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
