const axios = require('axios');

const LUNARCRUSH_API = 'https://lunarcrush.com/api3';
const API_KEY = process.env.LUNARCRUSH_API_KEY;

async function getSentiment(symbol) {
  const url = `${LUNARCRUSH_API}/coins?symbol=${symbol}`;
  const res = await axios.get(url, { headers: { 'Authorization': `Bearer ${API_KEY}` } });
  return res.data.data[0]; // mengandung social volume, sentiment, dll
}

module.exports = { getSentiment };
