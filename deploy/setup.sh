#!/bin/bash
# setup.sh - One-click deployment script for the funding multi-agent system.
#
# Prerequisites:
#   - Ubuntu 22.04+ / Debian 12+
#   - Git, curl installed
#
# This script will:
#   1. Install system dependencies (Python 3, Node.js, Docker, PM2)
#   2. Create Python virtual environments for each agent
#   3. Install pip dependencies
#   4. Set up .env from template
#   5. Start Docker services (Prometheus, Grafana)
#   6. Start PM2 processes (executor, telegram bot)
#   7. Install cron jobs for analyst and log rotation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================="
echo " Funding Multi-Agent System Setup"
echo "=========================================="
echo "Project root: ${PROJECT_ROOT}"

cd "$PROJECT_ROOT"

# -------------------------------------------
# 1. System dependencies
# -------------------------------------------
echo ""
echo "[1/7] Installing system dependencies..."

sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip curl git

# Docker (skip if already installed)
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
fi

# Docker Compose plugin
if ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose plugin..."
    sudo apt-get install -y -qq docker-compose-plugin
fi

# Node.js (skip if already installed)
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y -qq nodejs
fi

# PM2
if ! command -v pm2 &> /dev/null; then
    echo "Installing PM2..."
    sudo npm install -g pm2
fi

echo "System dependencies OK."

# -------------------------------------------
# 2. Python virtual environments
# -------------------------------------------
echo ""
echo "[2/7] Setting up Python virtual environments..."

# Executor venv
if [ ! -d "venv-executor" ]; then
    python3 -m venv venv-executor
fi
venv-executor/bin/pip install --quiet --upgrade pip
venv-executor/bin/pip install --quiet -r agents/executor/requirements.txt

# Analyst venv
if [ ! -d "venv-analyst" ]; then
    python3 -m venv venv-analyst
fi
venv-analyst/bin/pip install --quiet --upgrade pip
venv-analyst/bin/pip install --quiet -r agents/analyst/requirements.txt

# Approval venv
if [ ! -d "venv-approval" ]; then
    python3 -m venv venv-approval
fi
venv-approval/bin/pip install --quiet --upgrade pip
venv-approval/bin/pip install --quiet -r agents/approval/requirements.txt

echo "Virtual environments OK."

# -------------------------------------------
# 3. Environment file
# -------------------------------------------
echo ""
echo "[3/7] Setting up .env file..."

if [ ! -f ".env" ]; then
    cp .env.template .env
    echo "Created .env from template."
    echo ">>> IMPORTANT: Edit .env and fill in your API keys before starting! <<<"
else
    echo ".env already exists, skipping."
fi

# -------------------------------------------
# 4. Create data directories
# -------------------------------------------
echo ""
echo "[4/7] Creating data directories..."

mkdir -p shared/logs shared/data docker
echo "Directories OK."

# -------------------------------------------
# 5. Docker services
# -------------------------------------------
echo ""
echo "[5/7] Starting Docker services (Prometheus, Grafana)..."

docker compose up -d
echo "Docker services started."

# -------------------------------------------
# 6. PM2 processes
# -------------------------------------------
echo ""
echo "[6/7] Starting PM2 processes..."

pm2 start deploy/pm2_ecosystem.config.js
pm2 save
pm2 startup -u "$USER" --hp "$HOME" 2>/dev/null || true

echo "PM2 processes started."

# -------------------------------------------
# 7. Cron jobs
# -------------------------------------------
echo ""
echo "[7/7] Installing cron jobs..."

CRON_ANALYST="0 */6 * * * cd ${PROJECT_ROOT} && venv-analyst/bin/python agents/analyst/openclaw_skill.py >> shared/logs/analyst.log 2>&1"
CRON_ROTATE="0 0 * * * ${PROJECT_ROOT}/shared/scripts/rotate_logs.sh >> /dev/null 2>&1"

# Add cron jobs (avoiding duplicates)
(crontab -l 2>/dev/null || true) | grep -v "openclaw_skill.py" | grep -v "rotate_logs.sh" > /tmp/crontab_tmp || true
echo "$CRON_ANALYST" >> /tmp/crontab_tmp
echo "$CRON_ROTATE" >> /tmp/crontab_tmp
crontab /tmp/crontab_tmp
rm -f /tmp/crontab_tmp

echo "Cron jobs installed."

# -------------------------------------------
# Done
# -------------------------------------------
echo ""
echo "=========================================="
echo " Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Check PM2 status: pm2 status"
echo "  3. View executor logs: pm2 logs executor"
echo "  4. Access Grafana: http://YOUR_IP:3000 (admin/admin)"
echo "  5. View Prometheus: http://YOUR_IP:9090"
echo ""
