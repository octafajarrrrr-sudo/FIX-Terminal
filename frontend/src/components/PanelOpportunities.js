import React, { useState, useEffect } from 'react';
import { scanFundingRates, openPosition } from '../api';

const PanelOpportunities = ({ scanResults, onRefresh }) => {
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (scanResults && scanResults.length > 0) {
      setOpportunities(scanResults);
    }
  }, [scanResults]);

  const handleScan = async () => {
    setLoading(true);
    try {
      const data = await scanFundingRates();
      setOpportunities(data.slice(0, 30));
    } catch (err) {
      console.error('Scan error:', err);
    }
    setLoading(false);
  };

  const handleOpen = async (symbol) => {
    try {
      await openPosition(symbol);
      onRefresh();
    } catch (err) {
      console.error('Open position error:', err);
    }
  };

  const getFundingColor = (rate) => {
    if (rate > 0.0005) return '#ff4444';  // High positive - good for shorting
    if (rate > 0) return '#ff8844';
    if (rate < -0.0005) return '#44ff44'; // High negative - good for longing
    return '#44aa44';
  };

  return (
    <div className="panel panel-opportunities">
      <div className="panel-header">
        <h3>Funding Rate Opportunities</h3>
        <button className="btn btn-scan" onClick={handleScan} disabled={loading}>
          {loading ? 'Scanning...' : 'Scan Now'}
        </button>
      </div>

      <div className="opportunities-table">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Funding Rate</th>
              <th>Annualized</th>
              <th>Mark Price</th>
              <th>Next Funding</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {opportunities.length === 0 ? (
              <tr>
                <td colSpan="6" className="empty-state">
                  Click "Scan Now" to find opportunities
                </td>
              </tr>
            ) : (
              opportunities.map((opp) => (
                <tr key={opp.symbol}>
                  <td className="symbol-cell">{opp.symbol}</td>
                  <td style={{ color: getFundingColor(opp.fundingRate) }}>
                    {opp.fundingRatePercent}%
                  </td>
                  <td>{opp.annualizedRate}%</td>
                  <td>${parseFloat(opp.markPrice).toFixed(2)}</td>
                  <td>{new Date(opp.nextFundingTime).toLocaleTimeString()}</td>
                  <td>
                    <button
                      className="btn btn-small btn-open"
                      onClick={() => handleOpen(opp.symbol)}
                      title={
                        opp.fundingRate > 0
                          ? 'SHORT futures + BUY spot'
                          : 'LONG futures + SELL spot'
                      }
                    >
                      {opp.fundingRate > 0 ? 'Short+Buy' : 'Long+Sell'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PanelOpportunities;
