param(
    [Parameter(Mandatory=$true)][string]$SourceXml,
    [string]$TargetCpf = "00000000000",
    [string]$TargetName = "PESSOA TESTE",
    [ValidateSet("identidade", "template-limpo", "anonimo")]
    [string]$Mode = "template-limpo",
    [string]$IrpfDir = "C:\Arquivos de Programas RFB\IRPF2026"
)

$ErrorActionPreference = "Stop"
$ProjectDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$TargetDir = Join-Path $IrpfDir "aplicacao\dados"
$BackupDir = Join-Path $ProjectDir "backup"

python -m irpf_importer clone `
  --mode $Mode `
  --irpf-dir $IrpfDir `
  --source-xml $SourceXml `
  --target-dir $TargetDir `
  --target-cpf $TargetCpf `
  --target-name $TargetName `
  --backup-dir $BackupDir
