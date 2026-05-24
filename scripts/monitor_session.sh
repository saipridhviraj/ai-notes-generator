#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_KEY=$(grep '^APP_API_KEY=' "$ROOT/.env" | cut -d= -f2-)
SESSION="${1:?session id required}"
BASE="${2:-http://localhost:8000}"
LOG="$ROOT/data/monitor_${SESSION}.log"

echo "Monitoring $SESSION -> $LOG" | tee "$LOG"

while true; do
  STATUS_JSON=$(curl -s "$BASE/status/$SESSION" -H "X-API-Key: $API_KEY")
  TS=$(date -Iseconds)
  echo "$TS $STATUS_JSON" >> "$LOG"
  ST=$(echo "$STATUS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'), d.get('current_node',''), d.get('elapsed_seconds',0), d.get('progress_percent',0))")
  echo "$TS $ST"

  STATUS=$(echo "$STATUS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))")

  if [ "$STATUS" = "awaiting_tutor" ]; then
    echo "$TS Approving tutor plan..." | tee -a "$LOG"
    curl -s -X POST "$BASE/tutor/respond/$SESSION" \
      -H "Content-Type: application/json" \
      -H "X-API-Key: $API_KEY" \
      -d '{"approved":true,"feedback":""}' >> "$LOG"
    echo >> "$LOG"
  fi

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] || [ "$STATUS" = "max_retries_reached" ] || [ "$STATUS" = "rejected" ] || [ "$STATUS" = "cancelled" ]; then
    echo "$TS Final status: $STATUS" | tee -a "$LOG"
    curl -s "$BASE/result/$SESSION" -H "X-API-Key: $API_KEY" | python3 -m json.tool >> "$LOG" 2>&1 || true
    break
  fi

  sleep 20
done
