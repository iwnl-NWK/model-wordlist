# Notas de execução

Ordem de execução dos experimentos. Os caminhos são relativos à raiz do repositório.
Na VM Linux, o diretório de trabalho é definido por `MW_ROOT` (padrão `$HOME/model-wordlist`).
O acesso à VM usa SSH: `ssh -i <chave-ssh> <usuario>@<host-da-vm>`.

## 0. Pré-requisitos

- Máquina local (Windows, GPU dedicada + iGPU): Git, Python 3 (launcher `py`), drivers com
  Vulkan e OpenCL. Não é necessário toolchain de build (usam-se binários pré-compilados).
- VM (Ubuntu, GPU AMD): acesso SSH por chave; `mesa-vulkan-drivers`, `vulkan-tools`.

## 1. Setup + download de assets

- VM: enviar `src/setup_and_fetch_vm.sh` e executá-lo (`bash -s < src/setup_and_fetch_vm.sh`).
  Instala o llama.cpp Vulkan e baixa Qwen2.5-7B, Llama-3.1-8B e Phi-3-mini. Os extras do
  tier1 (Qwen3-8B, Gemma-3-4B) podem ser baixados para `$MW_ROOT/models` com `curl`.
- Local: `powershell -File src\setup_windows.ps1` (llama.cpp Vulkan, Hashcat 6.2.6, rockyou,
  LinkedIn, OneRule, Phi-3-mini, Llama-3.2-3B). Extras locais (Qwen3-4B, Qwen3-1.7B,
  Gemma-3-1B) em `data\models`.

## 2. Geração das wordlists

- VM (tier1): copiar `src/` e `config/` para `$MW_ROOT/`, depois executar
  `src/run_vm_tier1.sh`. Copiar de volta `$MW_ROOT/out/*.txt` e `gen_metrics.csv`.
- Local (tier2, GPU dedicada = Vulkan device 0):
  `powershell -File src\run_local_tier.ps1 -Tier tier2_gtx970 -VkDevice 0`
- Local (tier3, iGPU = Vulkan device 1):
  `powershell -File src\run_local_tier.ps1 -Tier tier3_vega7 -VkDevice 1`

Saídas: `results/raw/<tier>__<model>__<prompt>.txt` e `results/raw/gen_metrics.csv`.
Modo calibração (mede tok/s sem gravar wordlists): acrescentar `--calibrate` a `generate.py`.

## 3. Preparação dos alvos e baselines

```
py src\prepare_targets.py --linkedin-zip data\hashes\linkedin_found_hash_plain.zip ^
  --rockyou data\wordlists\rockyou.txt ^
  --targets-dir data\targets --wordlists-dir data\wordlists
```
Reunir as wordlists GenAI (`results\raw\*.txt`) e as amostras `rockyou_v*.txt` em
`data\crack_wordlists\`.

## 4. Cracking (referência, GPU dedicada via OpenCL)

```
py src\crack.py --hashcat bin\hashcat-6.2.6\hashcat.exe ^
  --wordlists-dir data\crack_wordlists ^
  --targets-json config\targets.json --rules-json config\rules.json ^
  --out results\raw\crack_metrics.csv --potdir results\potfiles ^
  --tag reference --device 1 --extra --backend-ignore-cuda --backend-ignore-hip
```
Descobrir o índice do dispositivo com `bin\hashcat-6.2.6\hashcat.exe -I`.

## 5. Análise

```
py -m pip install -r requirements.txt   # matplotlib, opcional (figuras)
py src\analyze.py --gen-glob "results\raw\gen_metrics_*.csv" ^
  --crack results\raw\crack_metrics.csv --results-dir results
```
Gera `results/gen_summary.csv`, `results/recovery_summary.csv` e, se o matplotlib estiver
disponível, as figuras `results/fig_*.png`.
