#!/bin/bash
echo "===================================="
echo "  Instalando Ollama para CookieScript IDE"
echo "===================================="
echo ""
echo "1. Instalando Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
echo ""
echo "2. Baixando modelo phi3 (2GB, pode demorar)..."
ollama pull phi3
echo ""
echo "3. Iniciando IDE..."
python3 cookie_ide_app.py
