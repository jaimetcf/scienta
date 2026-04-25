#!/usr/bin/env bash
# Restore a pg_dump -Fc archive to Neon using PostgreSQL 16 clients (matches docker postgres:16).
# Fixes: pg_restore: error: unsupported version (1.15) in file header (host pg_restore older than 16).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DUMP="${1:-$ROOT/scienta.dump}"
[[ -f "$DUMP" ]] || { echo "Dump not found: $DUMP" >&2; exit 1; }
[[ -f "$ROOT/.env" ]] || { echo "Missing $ROOT/.env (needs DATABASE_URL)." >&2; exit 1; }

DUMP_ABS="$(cd "$(dirname "$DUMP")" && pwd)/$(basename "$DUMP")"
case "$DUMP_ABS" in
"$ROOT"/*) REL="${DUMP_ABS#$ROOT/}" ;;
*)
  echo "Dump must be under project root so it can be mounted: $ROOT" >&2
  exit 1
  ;;
esac

docker run --rm --env-file "$ROOT/.env" \
  -v "$ROOT:/work" \
  -w /work \
  postgres:16-alpine \
  sh -c 'pg_restore --no-owner --no-privileges --verbose -d "$DATABASE_URL" "/work/'"${REL}"'"'
