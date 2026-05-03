#!/usr/bin/env bash
set -euo pipefail
DB_NAME="${DB_NAME:-od_approval_db}"
DB_USER="${DB_USER:-postgres}"
OUT_DIR="database/backups"
mkdir -p "$OUT_DIR"
pg_dump -U "$DB_USER" -d "$DB_NAME" -f "$OUT_DIR/${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql"
