const axios = require('axios');
const crypto = require('crypto');

const BASE_URL = 'https://fapi.binance.com';
const SPOT_BASE_URL = 'https://api.binance.com';
const API_KEY = process.env.BINANCE_API_KEY;
const SECRET_KEY = process.env.BINANCE_SECRET_KEY;

/**
 * Generate HMAC-SHA256 signature for Binance API requests.
 */
function generateSignature(queryString) {
  return crypto.createHmac('sha256', SECRET_KEY).update(queryString).digest('hex');
}

/**
 * Build query string from params object.
 */
function buildQueryString(params) {
  return Object.keys(params)
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');
}

/**
 * Make a signed request to Binance Futures API.
 */
async function signedRequest(method, endpoint, params = {}, isFutures = true) {
  const baseUrl = isFutures ? BASE_URL : SPOT_BASE_URL;
  params.timestamp = Date.now();
  params.recvWindow = 5000;
  const queryString = buildQueryString(params);
  const signature = generateSignature(queryString);
  const url = `${baseUrl}${endpoint}?${queryString}&signature=${signature}`;

  const config = {
    method,
    url,
    headers: { 'X-MBX-APIKEY': API_KEY },
  };

  const res = await axios(config);
  return res.data;
}

// --------------- Public Endpoints ---------------

/**
 * Get all funding rates from Binance Futures (public, no signature needed).
 */
async function getAllFundingRates() {
  const res = await axios.get(`${BASE_URL}/fapi/v1/premiumIndex`);
  return res.data;
}

/**
 * Get funding rate for a specific symbol.
 */
async function getFundingRate(symbol) {
  const res = await axios.get(`${BASE_URL}/fapi/v1/premiumIndex`, {
    params: { symbol },
  });
  return res.data;
}

/**
 * Get funding rate history for a symbol.
 */
async function getFundingRateHistory(symbol, limit = 100) {
  const res = await axios.get(`${BASE_URL}/fapi/v1/fundingRate`, {
    params: { symbol, limit },
  });
  return res.data;
}

/**
 * Get exchange info (all tradable symbols and their rules).
 */
async function getFuturesExchangeInfo() {
  const res = await axios.get(`${BASE_URL}/fapi/v1/exchangeInfo`);
  return res.data;
}

/**
 * Get current ticker price for a futures symbol.
 */
async function getFuturesTickerPrice(symbol) {
  const res = await axios.get(`${BASE_URL}/fapi/v1/ticker/price`, {
    params: { symbol },
  });
  return res.data;
}

/**
 * Get current ticker price for a spot symbol.
 */
async function getSpotTickerPrice(symbol) {
  const res = await axios.get(`${SPOT_BASE_URL}/api/v3/ticker/price`, {
    params: { symbol },
  });
  return res.data;
}

// --------------- Signed Endpoints (Account) ---------------

/**
 * Get futures account balance.
 */
async function getFuturesBalance() {
  return signedRequest('GET', '/fapi/v2/balance');
}

/**
 * Get futures account info (includes positions).
 */
async function getFuturesAccount() {
  return signedRequest('GET', '/fapi/v2/account');
}

/**
 * Get current open futures positions.
 */
async function getFuturesPositions() {
  const account = await getFuturesAccount();
  return account.positions.filter(
    (p) => parseFloat(p.positionAmt) !== 0
  );
}

/**
 * Get spot account balances.
 */
async function getSpotAccount() {
  return signedRequest('GET', '/api/v3/account', {}, false);
}

// --------------- Order Endpoints ---------------

/**
 * Place a futures order.
 * @param {Object} params - { symbol, side, type, quantity, price?, timeInForce?, reduceOnly? }
 */
async function placeFuturesOrder(params) {
  const orderParams = {
    symbol: params.symbol,
    side: params.side.toUpperCase(),
    type: params.type.toUpperCase(),
    quantity: params.quantity,
  };

  if (params.price) orderParams.price = params.price;
  if (params.timeInForce) orderParams.timeInForce = params.timeInForce;
  if (params.reduceOnly) orderParams.reduceOnly = params.reduceOnly;
  if (params.positionSide) orderParams.positionSide = params.positionSide;

  return signedRequest('POST', '/fapi/v1/order', orderParams);
}

/**
 * Place a spot order.
 * @param {Object} params - { symbol, side, type, quantity, price?, timeInForce? }
 */
async function placeSpotOrder(params) {
  const orderParams = {
    symbol: params.symbol,
    side: params.side.toUpperCase(),
    type: params.type.toUpperCase(),
    quantity: params.quantity,
  };

  if (params.price) orderParams.price = params.price;
  if (params.timeInForce) orderParams.timeInForce = params.timeInForce;
  if (params.quoteOrderQty) orderParams.quoteOrderQty = params.quoteOrderQty;

  return signedRequest('POST', '/api/v3/order', orderParams, false);
}

/**
 * Cancel a futures order.
 */
async function cancelFuturesOrder(symbol, orderId) {
  return signedRequest('DELETE', '/fapi/v1/order', { symbol, orderId });
}

/**
 * Set futures leverage for a symbol.
 */
async function setLeverage(symbol, leverage) {
  return signedRequest('POST', '/fapi/v1/leverage', { symbol, leverage });
}

/**
 * Set margin type (ISOLATED or CROSSED).
 */
async function setMarginType(symbol, marginType) {
  try {
    return await signedRequest('POST', '/fapi/v1/marginType', {
      symbol,
      marginType: marginType.toUpperCase(),
    });
  } catch (err) {
    // Binance returns error -4046 if margin type is already set
    if (err.response && err.response.data && err.response.data.code === -4046) {
      return { msg: 'No need to change margin type.' };
    }
    throw err;
  }
}

module.exports = {
  getAllFundingRates,
  getFundingRate,
  getFundingRateHistory,
  getFuturesExchangeInfo,
  getFuturesTickerPrice,
  getSpotTickerPrice,
  getFuturesBalance,
  getFuturesAccount,
  getFuturesPositions,
  getSpotAccount,
  placeFuturesOrder,
  placeSpotOrder,
  cancelFuturesOrder,
  setLeverage,
  setMarginType,
};
