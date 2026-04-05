/**
 * PM2 Ecosystem Configuration
 *
 * Manages the executor bot and telegram approval bot as background services.
 * The analyst is run on a cron schedule (see setup.sh).
 */
module.exports = {
  apps: [
    {
      name: 'executor',
      script: 'agents/executor/main.py',
      interpreter: 'venv-executor/bin/python3',
      cwd: __dirname + '/..',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
      },
    },
    {
      name: 'telegram-approval',
      script: 'agents/approval/telegram_bot.py',
      interpreter: 'venv-approval/bin/python3',
      cwd: __dirname + '/..',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      env: {
        NODE_ENV: 'production',
      },
    },
  ],
};
