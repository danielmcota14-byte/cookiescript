@echo off
echo ====================================
echo   Instalando Claude Code para CookieScript IDE
echo ====================================
echo.

where node >nul 2>nul
if %errorlevel% neq 0 (
  echo Node.js nao encontrado. Instale em: https://nodejs.org/
  pause
  exit /b 1
)

echo 1. Instalando o CLI do Claude Code (requer Node.js)...
npm install -g @anthropic-ai/claude-code
echo.
echo 2. Verificando instalacao...
claude --version
echo.
echo    Se ainda nao autenticou, rode: claude   (login unico, abre o navegador)
echo.
echo 3. Iniciando IDE...
python cookie_ide_app.py
pause
