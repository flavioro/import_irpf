param(
    [ValidateSet("add", "replace", "dry-run")]
    [string]$Mode = "dry-run",
    [string]$Cpf = "00000000000",
    [string]$IrpfDir = "C:\Arquivos de Programas RFB\IRPF2026",
    [string]$Arquivo = ""
)

$ErrorActionPreference = "Stop"
$ProjectDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$xml = Join-Path $IrpfDir "aplicacao\dados\$Cpf\$Cpf-0000000000.xml"
if (-not $Arquivo) { $Arquivo = Join-Path $ProjectDir "examples\proventos_exemplo.csv" }
$backupDir = Join-Path $ProjectDir "backup"

python -m irpf_importer proventos `
  --mode $Mode `
  --irpf-dir $IrpfDir `
  --xml $xml `
  --arquivo $Arquivo `
  --backup-dir $backupDir
