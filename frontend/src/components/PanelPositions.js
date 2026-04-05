import React from 'react';
import { closePosition, closeAllPositions } from '../api';

const PanelPositions = ({ activePositions, tradeHistory, onRefresh }) => {
  const handleClose = async (positionId) => {
    try {
      await closePosition(positionId);
      onRefresh();
    } catch (err) {
      console.error('Close error:', err);
    }
  };

  const handleCloseAll = async () => {
    try {
      await closeAllPositions();
      onRefresh();
    } catch (err) {
      console.error('Close all error:', err);
    }
  };

  return (
    <div className="panel panel-positions">
      {/* Active Positions */}
      <div className="panel-header">
        <h3>Active Positions ({activePositions?.length || 0})</h3>
        {activePositions?.length > 0 && (
          <button className="btn btn-stop btn-small" onClick={handleCloseAll}>
            Close All
          </button>
        )}
      </div>

      <div className="positions-table">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Direction</th>
              <th>Qty</th>
              <th>Entry</th>
              <th>FR</th>
              <th>Est. Fee</th>
              <th>Opened</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {(!activePositions || activePositions.length === 0) ? (
              <tr>
                <td colSpan="8" className="empty-state">No active positions</td>
              </tr>
            ) : (
              activePositions.map((pos) => (
                <tr key={pos.id}>
                  <td className="symbol-cell">{pos.symbol}</td>
                  <td>
                    <span className={`direction ${pos.direction.includes('SHORT') ? 'short' : 'long'}`}>
                      {pos.direction.includes('SHORT') ? 'SHORT+BUY' : 'LONG+SELL'}
                    </span>
                  </td>
                  <td>{pos.quantity}</td>
                  <td>${pos.entryPrice?.toFixed(2)}</td>
                  <td>{pos.fundingRatePercent}</td>
                  <td>${pos.estimatedFeeUSDT}</td>
                  <td>{new Date(pos.openedAt).toLocaleTimeString()}</td>
                  <td>
                    <button
                      className="btn btn-small btn-close"
                      onClick={() => handleClose(pos.id)}
                    >
                      Close
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Trade History */}
      <h3 className="history-title">Trade History</h3>
      <div className="positions-table">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Direction</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>Est. PnL</th>
              <th>Opened</th>
              <th>Closed</th>
            </tr>
          </thead>
          <tbody>
            {(!tradeHistory || tradeHistory.length === 0) ? (
              <tr>
                <td colSpan="7" className="empty-state">No trade history yet</td>
              </tr>
            ) : (
              tradeHistory.map((trade, i) => (
                <tr key={trade.id || i}>
                  <td className="symbol-cell">{trade.symbol}</td>
                  <td>
                    <span className={`direction ${trade.direction.includes('SHORT') ? 'short' : 'long'}`}>
                      {trade.direction.includes('SHORT') ? 'SHORT+BUY' : 'LONG+SELL'}
                    </span>
                  </td>
                  <td>${trade.entryPrice?.toFixed(2)}</td>
                  <td>${trade.exitPrice?.toFixed(2) || '-'}</td>
                  <td className="pnl">
                    ${trade.estimatedNetPnL || '0.00'}
                  </td>
                  <td>{new Date(trade.openedAt).toLocaleTimeString()}</td>
                  <td>{trade.closedAt ? new Date(trade.closedAt).toLocaleTimeString() : '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PanelPositions;
