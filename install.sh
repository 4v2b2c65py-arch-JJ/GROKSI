#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/4] write grok aspect header"
python3 grokheader.py grok-4 >/dev/null

echo "[2/4] partition local models into grok storage"
python3 storage.py >/dev/null

echo "[3/4] verify local weight class"
python3 weightclass.py llama3.2:latest >/dev/null

echo "[4/4] smoke test facade"
python3 grokfacade.py grok-4 "Say OK"

echo "install complete: pipeline ready (gguf backend, no heavy download)"