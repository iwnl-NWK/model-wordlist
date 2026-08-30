#!/usr/bin/env bash
set -e
ROOT="${MW_ROOT:-$HOME/model-wordlist}"
cd "$ROOT"
python3 src/generate.py \
  --tier tier1_rx7600 \
  --llama-server "$ROOT/bin/llama-server" \
  --models-dir "$ROOT/models" \
  --out-dir "$ROOT/out" \
  --ngl 99
