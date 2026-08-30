param(
  [Parameter(Mandatory=$true)][string]$Tier,
  [Parameter(Mandatory=$true)][int]$VkDevice,
  [int]$Ngl = 99
)
$base = (Resolve-Path "$PSScriptRoot\..").Path
$env:GGML_VK_VISIBLE_DEVICES = "$VkDevice"
py "$base\src\generate.py" `
  --tier $Tier `
  --llama-server "$base\bin\llama\llama-server.exe" `
  --models-dir "$base\data\models" `
  --out-dir "$base\results\raw" `
  --ngl $Ngl
