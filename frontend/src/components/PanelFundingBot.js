import React, { useState } from 'react';
import { startBot, stopBot, updateBotConfig } from '../api';

const PanelFundingBot = ({ status, onRefresh }) => {
  const [config, setConfig] = useState({
    minFundingRate: 0.01,
    maxPositionUSDT: 500,
    leverage: 1,
    dryRun: true,
    autoClose: true,
    closeDelayMinutes: 5,
  });

  const handleStart = async () => {
    await startBot(config);
    onRefresh();
  };

  const handleStop = async () => {
    await stopBot();
    onRefresh();
  };

  const handleConfigChange = (key, value) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleSaveConfig = async () => {
    await updateBotConfig(config);
    onRefresh();
  };

  return (
    <div className="panel panel-bot">
      <h3>Bot Control</h3>

      <div className="bot-status">
        <span className={`status-indicator ${status?.running ? 'active' : 'inactive'}`} />
        <strong>{status?.running ? 'RUNNING' : 'STOPPED'}</strong>
        {status?.running && (
          <span className="funding-timer">
            Next funding: {parseFloat(status.minutesUntilFunding).toFixed(0)} min
          </span>
        )}
      </div>

      {status?.totalEstimatedProfit && (
        <div className="profit-display">
          Total Est. Profit: <strong>${status.totalEstimatedProfit} USDT</strong>
        </div>
      )}

      <div className="config-form">
        <label>
          Min Funding Rate (%)
          <input
            type="number"
            step="0.001"
            value={config.minFundingRate}
            onChange={(e) => handleConfigChange('minFundingRate', parseFloat(e.target.value))}
          />
        </label>

        <label>
          Max Position (USDT)
          <input
            type="number"
            step="50"
            value={config.maxPositionUSDT}
            onChange={(e) => handleConfigChange('maxPositionUSDT', parseFloat(e.target.value))}
          />
        </label>

        <label>
          Leverage
          <input
            type="number"
            min="1"
            max="10"
            value={config.leverage}
            onChange={(e) => handleConfigChange('leverage', parseInt(e.target.value, 10))}
          />
        </label>

        <label>
          Close Delay (min)
          <input
            type="number"
            min="1"
            max="60"
            value={config.closeDelayMinutes}
            onChange={(e) => handleConfigChange('closeDelayMinutes', parseInt(e.target.value, 10))}
          />
        </label>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={config.dryRun}
            onChange={(e) => handleConfigChange('dryRun', e.target.checked)}
          />
          Dry Run (no real orders)
        </label>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={config.autoClose}
            onChange={(e) => handleConfigChange('autoClose', e.target.checked)}
          />
          Auto-close after funding
        </label>

        <button className="btn btn-secondary" onClick={handleSaveConfig}>
          Save Config
        </button>
      </div>

      <div className="bot-actions">
        {!status?.running ? (
          <button className="btn btn-start" onClick={handleStart}>
            Start Bot
          </button>
        ) : (
          <button className="btn btn-stop" onClick={handleStop}>
            Stop Bot
          </button>
        )}
      </div>

      {config.dryRun && (
        <div className="dry-run-notice">
          DRY RUN mode is ON - no real orders will be placed
        </div>
      )}
    </div>
  );
};

export default PanelFundingBot;
