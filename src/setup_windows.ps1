$ErrorActionPreference = 'Stop'
$curl = "$env:SystemRoot\System32\curl.exe"
$base = (Resolve-Path "$PSScriptRoot\..").Path
$llamaBuild = "b10689"
New-Item -ItemType Directory -Force "$base\bin", "$base\data\models", "$base\data\hashes", "$base\data\rules" | Out-Null

if (-not (Test-Path "$base\bin\llama\llama-server.exe")) {
  & $curl -sL -o "$base\bin\llama-win.zip" "https://github.com/ggml-org/llama.cpp/releases/download/$llamaBuild/llama-$llamaBuild-bin-win-vulkan-x64.zip"
  Expand-Archive -Path "$base\bin\llama-win.zip" -DestinationPath "$base\bin\llama" -Force
}
if (-not (Test-Path "$base\bin\hashcat-6.2.6\hashcat.exe")) {
  & $curl -sL -o "$base\bin\7zr.exe" "https://www.7-zip.org/a/7zr.exe"
  & $curl -sL -o "$base\bin\hashcat.7z" "https://hashcat.net/files/hashcat-6.2.6.7z"
  & "$base\bin\7zr.exe" x "$base\bin\hashcat.7z" "-o$base\bin" -y | Out-Null
}

& $curl -sL -o "$base\data\rules\OneRuleToRuleThemStill.rule" "https://raw.githubusercontent.com/stealthsploit/OneRuleToRuleThemStill/main/OneRuleToRuleThemStill.rule"
& $curl -sL -o "$base\data\hashes\linkedin_found_hash_plain.zip" "https://github.com/brannondorsey/PassGAN/releases/download/data/68_linkedin_found_hash_plain.txt.zip"

function Fetch-Model($name, $url) {
  if (Test-Path "$base\data\models\$name") { Write-Output "skip $name"; return }
  & $curl -sL -C - -o "$base\data\models\$name" $url
  Write-Output "done $name"
}
Fetch-Model "phi3-mini.gguf"  "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
Fetch-Model "llama3.2-3b.gguf" "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

Write-Output "=== LOCAL ASSETS ==="
Get-ChildItem "$base\bin\llama\llama-server.exe","$base\bin\hashcat-6.2.6\hashcat.exe","$base\data\models","$base\data\hashes","$base\data\rules" -Recurse -File -ErrorAction SilentlyContinue |
  Select-Object @{n='MB';e={[math]::Round($_.Length/1MB,1)}}, FullName
Write-Output "LOCAL_SETUP_DONE"
