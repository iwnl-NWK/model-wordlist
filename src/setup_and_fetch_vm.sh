#!/usr/bin/env bash
set -e
ROOT="${MW_ROOT:-$HOME/model-wordlist}"
mkdir -p "$ROOT/bin" "$ROOT/models" "$ROOT/out" "$ROOT/logs"
cd "$ROOT"
LLAMA_BUILD="b10689"
if [ ! -x "bin/llama-server" ]; then
  curl -sL -o llama.tar.gz "https://github.com/ggml-org/llama.cpp/releases/download/${LLAMA_BUILD}/llama-${LLAMA_BUILD}-bin-ubuntu-vulkan-x64.tar.gz"
  rm -rf bin_extract && mkdir -p bin_extract
  tar xzf llama.tar.gz -C bin_extract
  SRV=$(find bin_extract -name llama-server | head -1)
  LIBDIR=$(dirname "$SRV")
  cp -a "$LIBDIR"/. bin/
  chmod +x bin/llama-* 2>/dev/null || true
fi
fetch() {
  if [ -s "models/$1" ]; then echo "skip $1"; else curl -sL -C - -o "models/$1" "$2"; echo "done $1"; fi
}
fetch phi3-mini.gguf "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
fetch qwen2.5-7b.gguf "https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
fetch llama3.1-8b.gguf "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
echo "=== VM ASSETS ==="
ls -lh bin/llama-server models/
echo "VM_SETUP_DONE"
