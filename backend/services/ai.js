const coinglass = require('./coinglass');
const whaleAlert = require('./whalealert');
const sentiment = require('./sentiment');

async function analyze(symbol) {
  // Ambil data secara paralel
  const [openInterest, fundingRate, whaleTxs, sentimentData] = await Promise.all([
    coinglass.getOpenInterest(symbol).catch(() => null),
    coinglass.getFundingRate(symbol).catch(() => null),
    whaleAlert.getRecentTransactions().catch(() => []),
    sentiment.getSentiment(symbol).catch(() => null),
  ]);

  let score = 50; // netral
  let signals = [];

  // Funding rate analysis
  if (fundingRate && fundingRate.length > 0) {
    const latest = fundingRate[0]; // asumsikan array terbaru
    const rate = latest.fundingRate;
    if (rate > 0.01) {
      score -= 10;
      signals.push('Funding rate tinggi (bearish)');
    } else if (rate < -0.01) {
      score += 10;
      signals.push('Funding rate rendah (bullish)');
    }
  }

  // Open Interest analysis (sederhana: bandingkan dengan rata-rata)
  if (openInterest && openInterest.length > 0) {
    const latestOI = openInterest[openInterest.length - 1].openInterest;
    const avgOI = openInterest.reduce((sum, o) => sum + o.openInterest, 0) / openInterest.length;
    if (latestOI > avgOI * 1.1) {
      score += 5;
      signals.push('Open Interest meningkat (bullish)');
    } else if (latestOI < avgOI * 0.9) {
      score -= 5;
      signals.push('Open Interest menurun (bearish)');
    }
  }

  // Whale transactions analysis (sederhana: jumlah transaksi besar)
  if (whaleTxs.length > 5) {
    score -= 5;
    signals.push('Banyak transaksi whale (potensi distribusi)');
  }

  // Sentiment analysis
  if (sentimentData) {
    const sentimentScore = sentimentData.sentiment; // asumsikan range -1 s/d 1
    if (sentimentScore > 0.3) {
      score += 10;
      signals.push('Sentimen positif');
    } else if (sentimentScore < -0.3) {
      score -= 10;
      signals.push('Sentimen negatif');
    }
  }

  // Tentukan rekomendasi
  let recommendation = 'NEUTRAL';
  if (score >= 60) recommendation = 'BULLISH';
  else if (score <= 40) recommendation = 'BEARISH';

  return { score, recommendation, signals };
}

module.exports = { analyze };
