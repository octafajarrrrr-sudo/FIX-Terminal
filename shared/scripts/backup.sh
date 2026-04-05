#!/bin/bash
# backup.sh - Backup critical configuration and data files.
#
# Creates a timestamped tarball of config, shared data, and logs.
# Run via cron: 0 */12 * * * /path/to/backup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/../.."
BACKUP_DIR="${PROJECT_ROOT}/backups"

mkdir -p "$BACKUP_DIR"

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${DATE}.tar.gz"

tar -czf "$BACKUP_FILE" \
    -C "$PROJECT_ROOT" \
    config/config.yaml \
    shared/logs/ \
    shared/data/ \
    .env 2>/dev/null || true

# Remove backups older than 7 days
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete

echo "Backup created: ${BACKUP_FILE}"
