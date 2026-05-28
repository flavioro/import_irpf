@echo off
setlocal

if "%IRPF_DIR%"=="" set "IRPF_DIR=C:\Arquivos de Programas RFB\IRPF2026"
if "%DADOS_DIR%"=="" set "DADOS_DIR=%IRPF_DIR%\aplicacao\dados"
if "%CPF%"=="" set "CPF=86320947187"
if "%XML_FILE%"=="" set "XML_FILE=%CPF%-0000000000.xml"

irpf-importer bens ^
  --mode dry-run ^
  --irpf-dir "%IRPF_DIR%" ^
  --xml "data\work\declaracoes\%CPF%\%XML_FILE%" ^
  --arquivo "data\input\bens\bens_2025.xlsx" ^
  --backup-dir "data\backup" ^
  --sem-recalcular-conf

endlocal
