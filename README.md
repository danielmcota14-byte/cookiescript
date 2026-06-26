# CookieScript IDE

Uma IDE web completa para a linguagem **CookieScript**, com suporte a Python, JavaScript e Lua, e IA local via Ollama.

## Como Rodar

```bash
pip install requests
python cookie_ide_app.py
```

Acesse: http://localhost:8080

## Configurar IA Local (sem API, sem internet)

A IA usa **Ollama** — roda modelos localmente, de graça, sem precisar de conta.

### Windows
```
Execute: instalar_ollama.bat
```

### Linux / Mac
```bash
chmod +x instalar_ollama.sh
./instalar_ollama.sh
```

### Manual
```bash
# 1. Instalar Ollama
# Windows: baixe em https://ollama.com/download
# Linux/Mac:
curl -fsSL https://ollama.com/install.sh | sh

# 2. Baixar modelo leve (recomendado para 4GB RAM)
ollama pull phi3

# 3. Rodar IDE
python cookie_ide_app.py
```

Abra `index1.html` → selecione **"Cookie AI Local (Ollama)"** → pronto!

## Modelos recomendados por RAM

| RAM   | Modelo recomendado       | Comando               |
|-------|--------------------------|-----------------------|
| 4GB   | phi3 (2.3GB)             | `ollama pull phi3`    |
| 8GB   | llama3.2 (2GB)           | `ollama pull llama3.2`|
| 16GB+ | llama3.1:8b (4.7GB)      | `ollama pull llama3.1`|

## Estrutura

```
cookiescript/
├── cookie_ide_app.py      # Servidor backend
├── cookie_ai.py           # Templates de código (fallback)
├── cookiescript_vm.py     # Máquina virtual CookieScript
├── index.html             # IDE principal
├── index1.html            # Cookie AI (chat com IA)
├── index2.html            # Wiki / Documentação
└── instalar_ollama.bat/.sh  # Scripts de instalação
```

## Variáveis de Ambiente

| Variável       | Descrição                    | Padrão                  |
|----------------|------------------------------|-------------------------|
| `PORT`         | Porta do servidor            | `8080`                  |
| `OLLAMA_URL`   | URL do Ollama                | `http://localhost:11434`|
| `OLLAMA_MODEL` | Modelo padrão                | `phi3`                  |
