#!/usr/bin/env bash
set -euo pipefail

export XAPI="${XAPI:-${XAI_API_KEY:-}}"
if [ -z "$XAPI" ]; then
  echo "ERROR: XAPI/XAI_API_KEY not set. Run: export XAPI=xai-..." >&2
  exit 1
fi

curl -s https://api.x.ai/v1/models \
  -H "Authorization: Bearer $XAPI" \
  | python3 -m json.tool