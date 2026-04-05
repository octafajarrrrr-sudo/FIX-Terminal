#!/bin/bash
# rotate_logs.sh - Rotate trades.log to prevent unbounded growth.
#
# Keeps the last 7 days of logs. Older entries are archived and compressed.
# Run via cron: 0 0 * * * /path/to/rotate_logs.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/../logs"
LOG_FILE="${LOG_DIR}/trades.log"
ARCHIVE_DIR="${LOG_DIR}/archive"

if [ ! -f "$LOG_FILE" ]; then
    echo "No trades.log found, nothing to rotate."
    exit 0
fi

mkdir -p "$ARCHIVE_DIR"

DATE=$(date +%Y%m%d_%H%M%S)
ARCHIVE_FILE="${ARCHIVE_DIR}/trades_${DATE}.log"

# Move current log to archive
cp "$LOG_FILE" "$ARCHIVE_FILE"
> "$LOG_FILE"

# Compress archived log
gzip "$ARCHIVE_FILE"

# Remove archives older than 30 days
find "$ARCHIVE_DIR" -name "trades_*.log.gz" -mtime +30 -delete

echo "Log rotated: ${ARCHIVE_FILE}.gz"
