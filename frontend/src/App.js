import React, { useEffect, useState, useCallback } from 'react';
import io from 'socket.io-client';
import PanelFundingBot from './components/PanelFundingBot';
import PanelOpportunities from './components/PanelOpportunities';
import PanelPositions from './components/PanelPositions';
import { fetchBotStatus } from './api';
import './App.css';

const socket = io('http://localhost:5000');

function App() {
  const [status, setStatus] = useState(null);

  const refreshStatus = useCallback(async () => {
    try {
      const data = await fetchBotStatus();
      setStatus(data);
    } catch (err) {
      console.error('Failed to fetch status:', err);
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    refreshStatus();

    // Real-time updates via Socket.IO
    socket.on('ff:status', (data) => {
      setStatus(data);
    });

    return () => {
      socket.off('ff:status');
    };
  }, [refreshStatus]);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Funding Fee Arbitrage Bot</h1>
        <p className="subtitle">Binance Perpetual Futures - Delta Neutral Strategy</p>
        {status && (
          <div className="header-info">
            <span className={`bot-badge ${status.running ? 'running' : 'stopped'}`}>
              {status.running ? 'BOT ACTIVE' : 'BOT IDLE'}
            </span>
            <span className="next-funding">
              Next Funding: {new Date(status.nextFundingTime).toLocaleTimeString()} (
              {parseFloat(status.minutesUntilFunding).toFixed(0)} min)
            </span>
          </div>
        )}
      </header>

      <main className="dashboard">
        <div className="dashboard-left">
          <PanelFundingBot status={status} onRefresh={refreshStatus} />
        </div>
        <div className="dashboard-center">
          <PanelOpportunities
            scanResults={status?.scanResults}
            onRefresh={refreshStatus}
          />
          <PanelPositions
            activePositions={status?.activePositions}
            tradeHistory={status?.tradeHistory}
            onRefresh={refreshStatus}
          />
        </div>
      </main>

      <footer className="App-footer">
        <p>Funding times: 00:00 / 08:00 / 16:00 UTC | Strategy: Hedge spot + futures to collect funding fees</p>
      </footer>
    </div>
  );
}

export default App;
