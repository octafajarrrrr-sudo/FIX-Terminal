const API_BASE = 'http://localhost:5000/api';

export const fetchAccount = async () => {
  const res = await fetch(`${API_BASE}/account`);
  return res.json();
};

export const fetchPositions = async () => {
  const res = await fetch(`${API_BASE}/positions`);
  return res.json();
};

export const placeOrder = async (order) => {
  const res = await fetch(`${API_BASE}/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(order),
  });
  return res.json();
};

export const fetchOpenInterest = async (symbol) => {
  const res = await fetch(`${API_BASE}/coinglass/oi?symbol=${symbol}`);
  return res.json();
};

export const fetchFundingRate = async (symbol) => {
  const res = await fetch(`${API_BASE}/coinglass/funding?symbol=${symbol}`);
  return res.json();
};

export const fetchWhaleTracker = async () => {
  const res = await fetch(`${API_BASE}/coinglass/whale`);
  return res.json();
};

export const fetchWhaleAlert = async () => {
  const res = await fetch(`${API_BASE}/whalealert`);
  return res.json();
};

export const fetchSentiment = async (symbol) => {
  const res = await fetch(`${API_BASE}/sentiment/${symbol}`);
  return res.json();
};

export const fetchAI = async (symbol) => {
  const res = await fetch(`${API_BASE}/ai/${symbol}`);
  return res.json();
};
