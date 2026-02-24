const axios = require('axios');
const crypto = require('crypto');
const WebSocket = require('ws');

const BASE_URL = 'https://open-api.bingx.com';
const API_KEY = process.env.BINGX_API_KEY;
const SECRET_KEY = process.env.BINGX_SECRET_KEY;

function generateSignature(params) {
  const queryString = Object.keys(params).sort().map(key => `${key}=${params[key]}`).join('&');
  return crypto.createHmac('sha256', SECRET_KEY).update(queryString).digest('hex');
}

async function getAccount() {
  const timestamp = Date.now();
  const params = { timestamp };
  const signature = generateSignature(params);
  const url = `${BASE_URL}/openApi/spot/v1/account?timestamp=${timestamp}&signature=${signature}`;
  const res = await axios.get(url, { headers: { 'X-BX-APIKEY': API_KEY } });
  return res.data;
}

async function getPositions() {
  // Implementasi serupa untuk futures jika diperlukan
  // Untuk sementara return dummy
  return { message: 'Positions endpoint not fully implemented' };
}

async function placeOrder(order) {
  const { symbol, qty, side, type, time_in_force } = order;
  const timestamp = Date.now();
  const params = {
    symbol,
    side: side.toUpperCase(),
    type: type.toUpperCase(),
    quantity: qty,
    timeInForce: time_in_force.toUpperCase(),
    timestamp
  };
  const signature = generateSignature(params);
  params.signature = signature;
  const url = `${BASE_URL}/openApi/spot/v1/order`;
  const res = await axios.post(url, null, { 
    params,
    headers: { 'X-BX-APIKEY': API_KEY }
  });
  return res.data;
}

// WebSocket untuk harga real-time
const ws = new WebSocket('wss://open-api.bingx.com/ws');
const subscribers = {};

ws.on('open', () => {
  console.log('Connected to BingX WebSocket');
});

ws.on('message', (data) => {
  const message = JSON.parse(data);
  // Asumsikan format ticker: { stream: "btcusdt@ticker", data: { c: "45000" } }
  if (message.stream && message.stream.includes('@ticker')) {
    const symbol = message.stream.split('@')[0].toUpperCase();
    const price = message.data.c;
    if (subscribers[symbol]) {
      subscribers[symbol].forEach(cb => cb(price));
    }
  }
});

function subscribePrice(symbol, callback) {
  const stream = `${symbol.toLowerCase()}@ticker`;
  if (!subscribers[symbol]) {
    subscribers[symbol] = [];
    // Kirim subscription ke BingX
    ws.send(JSON.stringify({ method: 'SUBSCRIBE', params: [stream], id: 1 }));
  }
  subscribers[symbol].push(callback);
}

module.exports = { getAccount, getPositions, placeOrder, subscribePrice };
