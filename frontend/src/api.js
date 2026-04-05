const API_BASE = 'http://localhost:5000/api';

// ============ Funding Fee Bot ============

export const fetchBotStatus = async () => {
  const res = await fetch(`${API_BASE}/ff/status`);
  return res.json();
};

export const startBot = async (config = {}) => {
  const res = await fetch(`${API_BASE}/ff/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return res.json();
};

export const stopBot = async () => {
  const res = await fetch(`${API_BASE}/ff/stop`, { method: 'POST' });
  return res.json();
};

export const updateBotConfig = async (config) => {
  const res = await fetch(`${API_BASE}/ff/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return res.json();
};

export const scanFundingRates = async () => {
  const res = await fetch(`${API_BASE}/ff/scan`);
  return res.json();
};

export const fetchOpportunities = async () => {
  const res = await fetch(`${API_BASE}/ff/opportunities`);
  return res.json();
};

export const openPosition = async (symbol) => {
  const res = await fetch(`${API_BASE}/ff/open`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol }),
  });
  return res.json();
};

export const closePosition = async (positionId) => {
  const res = await fetch(`${API_BASE}/ff/close`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ positionId }),
  });
  return res.json();
};

export const closeAllPositions = async () => {
  const res = await fetch(`${API_BASE}/ff/close-all`, { method: 'POST' });
  return res.json();
};

// ============ Binance Direct ============

export const fetchBalance = async () => {
  const res = await fetch(`${API_BASE}/binance/balance`);
  return res.json();
};

export const fetchPositions = async () => {
  const res = await fetch(`${API_BASE}/binance/positions`);
  return res.json();
};

export const fetchFundingHistory = async (symbol) => {
  const res = await fetch(`${API_BASE}/binance/funding-history/${symbol}`);
  return res.json();
};
