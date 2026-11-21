# CookieScript IDE

Uma IDE web completa para a linguagem **CookieScript**, com suporte a Python, JavaScript e Lua, e IA local via **Claude Code** (ou Ollama).

## Como Rodar

```bash
pip install requests
python cookie_ide_app.py
```

Acesse: http://localhost:8080

## Configurar IA Local — Claude Code (recomendado)

A IA usa o **Claude Code CLI** já instalado/autenticado no seu computador — roda local, sem precisar configurar nenhuma chave de API no app.

### Windows
```
Execute: instalar_claude_code.bat
```

### Linux / Mac
```bash
chmod +x instalar_claude_code.sh
./instalar_claude_code.sh
```

### Manual
```bash
# 1. Instalar Node.js (https://nodejs.org/) se ainda não tiver

# 2. Instalar o CLI do Claude Code
npm install -g @anthropic-ai/claude-code

# 3. Autenticar uma única vez (abre o navegador / pede login)
claude

# 4. Rodar a IDE
python cookie_ide_app.py
```

Abra `index1.html` → selecione **"🤖 Claude Code Local (CLI)"** → pronto!

> O backend chama `claude --print --output-format json "..."` (modo headless do
> Claude Code) via subprocess. Nenhum prompt passa pelos servidores da Cookie AI —
> a chamada é local, direto para o binário `claude` já configurado na máquina.

## Configurar IA Local — Ollama (alternativa, sem login)

Se preferir um modelo totalmente offline (sem login, sem assinatura Claude), pode
usar **Ollama** em vez do Claude Code.

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

Abra `index1.html` → selecione **"🧠 DeepSeek Local (sem API)"** (ou veja o status
do Ollama no endpoint `/api/ollama_status`) → pronto!

## Modelos recomendados por RAM (Ollama)

| RAM   | Modelo recomendado       | Comando               |
|-------|--------------------------|-----------------------|
| 4GB   | phi3 (2.3GB)             | `ollama pull phi3`    |
| 8GB   | llama3.2 (2GB)           | `ollama pull llama3.2`|
| 16GB+ | llama3.1:8b (4.7GB)      | `ollama pull llama3.1`|

## Estrutura

```
cookiescript/
├── cookie_ide_app.py      # Servidor backend
├── claude_code_ai.py      # Integração com o Claude Code CLI local
├── cookie_ai.py           # DeepSeek local / templates (fallback)
├── cookiescript_vm.py     # Máquina virtual CookieScript
├── index.html             # IDE principal
├── index1.html            # Cookie AI (chat com IA)
├── index2.html             # Wiki / Documentação
├── instalar_claude_code.bat/.sh  # Scripts de instalação do Claude Code
└── instalar_ollama.bat/.sh       # Scripts de instalação do Ollama
```

## Variáveis de Ambiente

| Variável               | Descrição                                  | Padrão                  |
|------------------------|---------------------------------------------|-------------------------|
| `PORT`                 | Porta do servidor                          | `8080`                  |
| `CLAUDE_CODE_BIN`      | Caminho/nome do binário do Claude Code     | `claude`                |
| `CLAUDE_CODE_MODEL`    | Modelo a usar no Claude Code (opcional)    | padrão do CLI           |
| `CLAUDE_CODE_TIMEOUT`  | Timeout por chamada (segundos)             | `120`                   |
| `CLAUDE_CODE_BARE`     | Usa `--bare` (requer `ANTHROPIC_API_KEY`)  | `0`                     |
| `DISABLE_CLAUDE_CODE`  | Desativa o backend Claude Code             | `0`                     |
| `OLLAMA_URL`           | URL do Ollama                              | `http://localhost:11434`|
| `OLLAMA_MODEL`         | Modelo padrão do Ollama                    | `phi3`                  |
| `GROQ_API_KEY`         | Chave da Groq para a Cookie Potencializada | —                       |

## ⚠️ Aviso de segurança

Durante a adaptação deste repositório, foi encontrada uma **chave de API da Groq
exposta diretamente no código-fonte** (em `cookie_ide_app.py` e `index1.html`).
Essa chave foi removida deste código atualizado, mas como ela já foi enviada a um
repositório Git (possivelmente público), **revogue/recrie essa chave em
https://console.groq.com/keys antes de publicar ou continuar usando o projeto**.
A partir de agora, configure sua chave via variável de ambiente `GROQ_API_KEY`
ou no campo de API Key da própria interface — nunca direto no código.


## Cookie AI 2.0 — OmniRoute + Grok + Memória + Arquivos

### Variáveis de ambiente (Render / Fly)

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `OMNIROUTE_URL` | Endpoint OmniRoute | `http://54.227.158.25:20128/v1` |
| `OMNIROUTE_API_KEY` | Chave OmniRoute | (dashboard OmniRoute) |
| `OMNIROUTE_MODEL` | Modelo padrão | `auto` |
| `GROK_API_KEY` | Chave xAI / Grok | `xai-...` |
| `GROK_URL` | Base Grok | `https://api.x.ai/v1` |
| `GROK_MODEL` | Modelo Grok | `grok-2-latest` |
| `GROQ_API_KEY` | Chave Groq (fallback) | `gsk_...` |
| `COOKIE_DATA_DIR` | Pasta da memória SQLite | `data` |

Ordem no modo **Auto**: OmniRoute → Grok → Groq.

### Funcionalidades

1. **Provedores**: OmniRoute, Grok (xAI), Groq, Claude Code local, DeepSeek local, Gemini.
2. **Criar arquivos**: a IA responde com blocos `<<<FILE path="...">>>...</<<<END_FILE>>>`; o servidor pode gravá-los automaticamente (códigos, CSV, scripts, etc.).
3. **Analisar arquivos**: envie fotos, PDF, planilhas, código, qualquer tipo — texto é extraído; imagens vão para modelos de visão quando suportados.
4. **Sem geração de imagens**: system prompt proíbe criar imagens.
5. **Memória obrigatória**:
   - Histórico de conversa por `session_id` (SQLite).
   - Memória de longo prazo / aprendizagem (fatos e preferências). Frases como "lembre que…", "prefiro…", "meu nome é…" são gravadas automaticamente.
6. Endpoints novos: `/api/chat`, `/api/upload_analyze`, `/api/memory/*`, `/api/sessions`, `/api/providers`, `/api/save_ai_files`.

### Deploy no Render

1. Defina no Environment:
   - `OMNIROUTE_URL=http://54.227.158.25:20128/v1`
   - `OMNIROUTE_API_KEY=sua_chave`
   - `GROK_API_KEY=sua_chave` (opcional)
   - `GROQ_API_KEY=sua_chave` (opcional)
2. Build: Dockerfile (já inclui `requests` e pastas `data/` / `uploads/`).
3. Disco persistente (recomendado): monte um volume em `/app/data` para a memória sobreviver a deploys.


## Conselho de IAs (modo padrão Auto)

No modo **Auto / Conselho**, várias IAs respondem à mesma pergunta e o **Grok** atua como coordenador central:

1. **OmniRoute** e **Groq** geram respostas independentes (membros do conselho).
2. **Grok** recebe todas as respostas, compara, corrige e funde numa resposta final potencializada.
3. A resposta final mantém as regras: sem imagens, com blocos `<<<FILE>>>` quando criar arquivos, e memória de longo prazo.

Providers isolados (`omniroute`, `grok`, `groq`) continuam disponíveis se quiser uma IA só.
Envie `"council": true` no body de `/api/chat` para forçar o conselho mesmo com provider isolado.
