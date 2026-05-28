@echo off
setlocal
set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"

python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e .[dev]

echo.
echo Ambiente criado em %PROJECT_DIR%\.venv
endlocal
