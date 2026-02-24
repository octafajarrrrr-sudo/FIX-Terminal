const axios = require('axios');

const COINGLASS_API = 'https://open-api.coinglass.com/api/pro/v1';
const API_KEY = process.env.COINGLASS_API_KEY;

async function getOpenInterest(symbol) {
  const url = `${COINGLASS_API}/futures/openInterest/chart?symbol=${symbol}&interval=1d`;
  const res = await axios.get(url, { headers: { 'coinglassSecret': API_KEY } });
  return res.data.data;
}

async function getFundingRate(symbol) {
  const url = `${COINGLASS_API}/futures/fundingRate/chart?symbol=${symbol}&interval=8h`;
  const res = await axios.get(url, { headers: { 'coinglassSecret': API_KEY } });
  return res.data.data;
}

async function getWhaleTracker() {
  const url = `${COINGLASS_API}/futures/whalePosition/list`;
  const res = await axios.get(url, { headers: { 'coinglassSecret': API_KEY } });
  return res.data.data;
}

module.exports = { getOpenInterest, getFundingRate, getWhaleTracker };
