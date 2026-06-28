#!/bin/bash
echo "===================================="
echo "  Instalando Claude Code para CookieScript IDE"
echo "===================================="
echo ""

if ! command -v node >/dev/null 2>&1; then
  echo "⚠ Node.js não encontrado. Instale o Node.js antes de continuar:"
  echo "  https://nodejs.org/"
  exit 1
fi

echo "1. Instalando o CLI do Claude Code (requer Node.js)..."
npm install -g @anthropic-ai/claude-code

echo ""
echo "2. Autenticando (abra o navegador quando solicitado)..."
echo "   Rode 'claude' manualmente se este passo não abrir automaticamente:"
claude --version || true
echo ""
echo "   >>> Se ainda não autenticou, rode: claude   (login único)"
echo ""
echo "3. Iniciando IDE..."
python3 cookie_ide_app.py
