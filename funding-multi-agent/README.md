# Funding Fee Multi-Agent System

A multi-agent system for Binance Futures funding rate arbitrage with $30 capital. The system monitors negative funding rates across all USDT-M perpetual pairs, opens LONG positions before settlement to collect funding fees, and uses an LLM analyst with Telegram-based human approval for parameter tuning.

## Architecture

The system consists of three agents:

1. **Executor Bot** (Python/CCXT) - Monitors funding rates, opens/closes positions, manages risk
2. **LLM Analyst** (Qwen 3.6-Plus via OpenRouter) - Analyzes trade logs, recommends parameter adjustments
3. **Telegram Approval Bot** - Sends recommendations to user, processes yes/no approvals, updates config

Supporting infrastructure:
- **Grafana + Prometheus** for monitoring dashboard
- **PM2** for process management
- **Cron** for scheduled analyst runs and log rotation

## Prerequisites

- VPS with 2 vCPU, 4 GB RAM, Ubuntu 22.04+
- Binance account with Futures API enabled (testnet recommended for testing)
- OpenRouter account (free tier available for Qwen model)
- Telegram bot created via @BotFather with your chat ID

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/funding-multi-agent.git
cd funding-multi-agent
```

### 2. Configure environment variables

```bash
cp .env.template .env
```

Edit `.env` and fill in your credentials:

```
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_secret_here
OPENROUTER_API_KEY=your_openrouter_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
TESTNET=true
```

### 3. Run the setup script

```bash
chmod +x deploy/setup.sh
./deploy/setup.sh
```

This script will:
- Install Python 3, Node.js, Docker, PM2
- Create separate virtual environments for each agent
- Install all pip dependencies
- Start Docker services (Prometheus, Grafana, Node Exporter)
- Start PM2 processes (executor bot, Telegram bot)
- Set up cron jobs for the LLM analyst (every 6 hours) and log rotation (daily)

## Configuration

### config/config.yaml

The main configuration file controls all trading parameters:

```yaml
executor:
  binance:
    testnet: true            # Use testnet for testing
    futures_leverage: 10     # Leverage multiplier
    margin_mode: ISOLATED    # Margin mode
  strategy:
    min_funding_rate: -1.0   # Minimum funding rate threshold (%)
    max_concurrent_pairs: 3  # Max simultaneous positions
    margin_per_trade_usd: 10 # USD per trade ($30 / 3 pairs)
    entry_window_seconds: 10 # Enter T-10s before settlement
    exit_window_seconds: 5   # Exit T+5s after settlement
  risk:
    max_daily_loss_usd: 5    # Pause bot if daily loss exceeds this
    max_consecutive_losses: 3 # Pause after 3 consecutive losses
    stop_loss_percent: 2.0   # Close position if price drops >2%
    pause_on_error: true     # Pause on unexpected errors
```

### config/rules.txt

Rules and constraints for the LLM analyst (what it can and cannot recommend).

### config/prompts/

System and user prompt templates for the LLM analyst.

## Monitoring

### Grafana Dashboard

Access Grafana at `http://YOUR_IP:3000` (default credentials: admin/admin).

Add Prometheus as a data source:
- URL: `http://prometheus:9090`

Available metrics:
- `executor_total_profit_usd` - Cumulative profit
- `executor_win_rate` - Current win rate percentage
- `executor_open_positions` - Number of open positions
- `executor_daily_loss_usd` - Daily loss tracker
- `executor_trades_total` - Total trades count
- `executor_errors_total` - Error count

### Prometheus

Access Prometheus at `http://YOUR_IP:9090`.

### Trade Logs

Logs are stored in `shared/logs/trades.log` as JSON lines:

```json
{"timestamp": "2024-01-01T00:00:00+00:00", "symbol": "BTC/USDT:USDT", "funding_rate": -1.5, "profit_net": 0.15, "status": "SUCCESS"}
```

## PM2 Commands

```bash
pm2 status                  # Check process status
pm2 logs executor           # View executor bot logs
pm2 logs telegram-approval  # View Telegram bot logs
pm2 restart executor        # Restart executor
pm2 restart all             # Restart all processes
pm2 stop all                # Stop all processes
```

## Telegram Bot Commands

- `/start` - Show help
- `/status` - Check pending recommendations
- `/check` - Manually check for new recommendations
- Reply `yes` or `no` to approve/reject a recommendation

## How It Works

1. **Every 30 seconds**, the executor bot fetches funding rates for all USDT-M perpetual pairs
2. Filters pairs with funding rate <= -1.0% (configurable)
3. Sorts by most negative rate and selects top 3
4. **10 seconds before settlement**: Opens a LONG market order (collecting negative funding = profit)
5. **5 seconds after settlement**: Closes the position
6. Logs the trade result to `shared/logs/trades.log`
7. **Every 6 hours**: The LLM analyst reads the last 24h of trades, computes statistics, and calls Qwen to get parameter recommendations
8. **Every 30 minutes**: The Telegram bot checks for new recommendations and notifies the user
9. User approves or rejects via Telegram; approved changes are applied to `config.yaml` and the executor reloads

## Troubleshooting

### API Connection Issues

- Verify API keys in `.env` are correct
- For testnet, ensure `TESTNET=true` and use testnet API keys from [Binance Futures Testnet](https://testnet.binancefuture.com)
- Check rate limits: the bot uses CCXT's built-in rate limiter

### Telegram Bot Not Responding

- Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
- Get your chat ID by messaging @userinfobot on Telegram
- Check logs: `pm2 logs telegram-approval`

### No Trades Being Executed

- Check if funding rates meet the threshold: most pairs have rates between -0.01% and +0.01%
- Lower `min_funding_rate` in config (e.g., -0.5%) for more frequent trades
- Verify the executor is running: `pm2 status`

### Grafana Shows No Data

- Ensure Prometheus can reach the executor metrics: `curl http://localhost:8000/metrics`
- Check Docker networking: `docker compose logs prometheus`

## Project Structure

```
funding-multi-agent/
├── .env.template              # Environment variables template
├── config/
│   ├── config.yaml            # Main configuration
│   ├── rules.txt              # LLM analyst rules
│   └── prompts/               # LLM prompt templates
├── agents/
│   ├── executor/              # Funding rate trading bot
│   ├── analyst/               # LLM-based trade analyst
│   └── approval/              # Telegram approval bot
├── shared/
│   ├── logs/                  # Trade logs
│   ├── data/                  # Suggestions and state
│   └── scripts/               # Log rotation and backup
├── openclaw/                  # OpenClaw skill configuration
├── tests/                     # Unit tests
├── deploy/                    # Deployment scripts
├── docker/                    # Docker configuration
└── docker-compose.yml         # Prometheus + Grafana + Node Exporter
```

## License

MIT
