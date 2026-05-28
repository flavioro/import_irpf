@echo off
set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
) else (
  echo Ambiente .venv nao encontrado. Rode scripts\criar_ambiente.cmd primeiro.
)
cmd /k
