# model-wordlist

Experimentos de geração de wordlists com modelos de linguagem de pequeno porte (SLMs)
quantizados para ataques de dicionário em ambientes com recursos limitados, replicando e
ampliando o método de Wright (2026).

Replica e amplia o método de Wright (2026), "Leveraging Generative AI for Password
Cracking Efficiency Under Resource Constraints" (SANS Institute), usando modelos de
linguagem de pequeno porte (SLMs) quantizados em GGUF Q4 para gerar wordlists, que são
então submetidas ao Hashcat contra hashes derivados de vazamentos públicos.

## Diferencial: três níveis de hardware pessoal

Em vez de um único equipamento, os experimentos rodam em três plataformas acessíveis,
para medir viabilidade e velocidade sob diferentes orçamentos de hardware:

| Tier | Plataforma | GPU | VRAM | SO |
|------|-----------|-----|------|----|
| tier1_rx7600 | VM | AMD Radeon RX 7600 (RDNA3, gfx1102) | 8 GB | Ubuntu 22.04 |
| tier2_gtx970 | Desktop | NVIDIA GeForce GTX 970 (Maxwell) | 4 GB | Windows 11 |
| tier3_vega7  | Desktop | AMD Radeon Vega 7 iGPU (Ryzen 5 5600G) | compartilhada | Windows 11 |

A inferência usa **llama.cpp com backend Vulkan** nas três plataformas (mesmo motor →
comparação de hardware justa). O cracking de referência usa **Hashcat com CUDA** na
GTX 970.

## Desenho experimental

- **Qualidade da wordlist** (senhas recuperadas) é medida uma única vez, pois independe
  do hardware que gerou a lista. Fonte das wordlists de qualidade: tier1_rx7600.
- **Velocidade** (tokens/s na geração e cracks/s no cracking) é medida por tier.
- Parâmetros de amostragem fixos: temperatura 0,7 e top-p 0,9 (Wright, 2026).
- Alvo de 2.000 candidatos por wordlist (desvio deliberado dos 10.000 de Wright, para
  viabilizar a matriz de três tiers no orçamento de tempo; o tamanho é idêntico entre
  todas as wordlists comparadas, preservando a comparabilidade).
- Prompts: os três níveis (simple, moderate, complex) de Wright, verbatim, em
  `config/prompts/`. Os três modelos-núcleo rodam os três prompts; os modelos adicionais
  rodam moderate e complex.

### Modelos

Núcleo (aprovados na proposta): Qwen2.5-7B-Instruct, Llama-3.1-8B-Instruct, Phi-3-mini-4k.
Extensões por tier (mais recentes, dimensionadas ao hardware): Qwen3-8B, Gemma-3-4B
(tier1); Llama-3.2-3B, Qwen3-4B (tier2); Qwen3-1.7B, Gemma-3-1B (tier3). Phi-3-mini roda
nos três tiers como modelo-âncora da comparação de velocidade. Todos em GGUF Q4.

### Baselines

- Amostras aleatórias da rockyou.txt (3 amostras, sementes fixas, truncadas ao mesmo
  tamanho das demais wordlists).
- PassGAN: o modelo pré-treinado oficial depende de TensorFlow 1.x, incompatível com o
  ambiente disponível, e não foi localizada uma wordlist pré-gerada com fonte citável por
  link direto; portanto o PassGAN é tratado como trabalho relacionado e fica como
  comparação para trabalhos futuros (limitação documentada).
- Conjunto de regras oneruletorulethemstill.rule (Hunt, 2023), comparado com "sem regra".

### Alvos (hashes)

Derivados de plaintexts de vazamentos públicos, re-hasheados de forma canônica para
garantir correspondência determinística no Hashcat e servir de ground truth:

- `linkedin_sha1` (SHA-1): plaintexts do vazamento do LinkedIn.
- `md5_target` (MD5): fatia disjunta dos mesmos plaintexts. Wright usou o vazamento da
  eHarmony (MD5); como não há fonte com link direto e citável para a eHarmony, o alvo MD5
  é derivado de uma partição disjunta do LinkedIn, sem sobreposição com o alvo SHA-1 nem
  com a rockyou (desvio documentado vs. Wright).

## Fontes de dados (links diretos)

- rockyou.txt — https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt
- LinkedIn (hash+plain) — https://github.com/brannondorsey/PassGAN/releases/download/data/68_linkedin_found_hash_plain.txt.zip
- oneruletorulethemstill.rule — https://raw.githubusercontent.com/stealthsploit/OneRuleToRuleThemStill/main/OneRuleToRuleThemStill.rule
- PassGAN (modelo/checkpoint) — https://github.com/brannondorsey/PassGAN
- Modelos GGUF — https://huggingface.co/ (bartowski, microsoft, Qwen, Google)
- llama.cpp — https://github.com/ggml-org/llama.cpp (build b10689, binários Vulkan)
- Hashcat 6.2.6 — https://hashcat.net/files/hashcat-6.2.6.7z

## Ética e escopo

Todos os alvos derivam de vazamentos já públicos e amplamente usados em pesquisa
acadêmica. Os experimentos ocorrem em ambiente isolado e controlado, com finalidade
estritamente defensiva e de pesquisa (avaliação de robustez de senhas e de políticas de
senha). Nenhum dado é inventado; toda métrica reportada vem da execução real dos scripts.

## Layout

```
config/   experiment.json, targets.json, rules.json, prompts/
src/      setup_*, generate.py, adherence.py, prepare_targets.py, crack.py, analyze.py, run_*
data/     modelos, hashes, alvos, wordlists (não versionado)
results/  raw/ (métricas cruas) e figuras/CSVs agregados
```

Execução passo a passo em `notes/EXECUTION.md`.
