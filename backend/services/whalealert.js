const axios = require('axios');

const WHALE_API = 'https://api.whale-alert.io/v1';
const API_KEY = process.env.WHALEALERT_API_KEY;

async function getRecentTransactions(minValue = 500000) {
  const url = `${WHALE_API}/transactions?api_key=${API_KEY}&min_value=${minValue}`;
  const res = await axios.get(url);
  return res.data.transactions;
}

module.exports = { getRecentTransactions };
