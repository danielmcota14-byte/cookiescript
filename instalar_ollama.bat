@echo off
echo ====================================
echo   Instalando Ollama para CookieScript IDE
echo ====================================
echo.
echo 1. Baixando Ollama...
curl -L https://ollama.com/download/OllamaSetup.exe -o OllamaSetup.exe
echo.
echo 2. Instalando Ollama...
start /wait OllamaSetup.exe
echo.
echo 3. Baixando modelo phi3 (2GB, pode demorar)...
ollama pull phi3
echo.
echo 4. Iniciando IDE...
python cookie_ide_app.py
pause
