"""
claude_code_ai.py
──────────────────
Integração da Cookie AI com o Claude Code CLI rodando localmente na máquina
do usuário (https://docs.claude.com/en/docs/claude-code/overview).

Em vez de baixar um modelo (Ollama) ou carregar pesos locais (DeepSeek/transformers),
este módulo chama o binário `claude` já instalado e autenticado na máquina,
em modo não-interativo (headless / "print mode"):

    claude --print --output-format json "minha pergunta"

Pré-requisitos na máquina do usuário:
  1. Node.js instalado
  2. Claude Code instalado:   npm install -g @anthropic-ai/claude-code
  3. Sessão autenticada:      claude        (login interativo uma única vez)
                              — ou —
     variável ANTHROPIC_API_KEY definida (uso com API key / CI)

Nada disso passa pela rede da Cookie AI: o subprocess fala direto com o
binário `claude` já configurado no computador local.
"""

import json
import os
import shutil
import subprocess
from typing import Optional


class ClaudeCodeAI:
    """Wrapper fino sobre o CLI `claude` em modo headless (--print)."""

    # Nome/caminho do binário. Permite apontar para um caminho customizado.
    BIN = os.getenv('CLAUDE_CODE_BIN', 'claude')

    # Modelo a usar (opcional). Se vazio, usa o padrão configurado no CLI.
    MODEL = os.getenv('CLAUDE_CODE_MODEL', '').strip()

    # Timeout por chamada, em segundos.
    TIMEOUT = int(os.getenv('CLAUDE_CODE_TIMEOUT', '120'))

    # Se "1"/"true", roda com --bare (sem CLAUDE.md, hooks, MCP, plugins do
    # diretório do projeto, sem auto-discovery). Útil para CI/Docker com
    # ANTHROPIC_API_KEY. Por padrão fica desligado para reaproveitar o login
    # interativo (assinatura Claude Pro/Max) já feito na máquina.
    BARE = os.getenv('CLAUDE_CODE_BARE', '').lower() in ('1', 'true', 'yes')

    # Argumentos extras livres, separados por espaço (ex: "--model opus").
    EXTRA_ARGS = os.getenv('CLAUDE_CODE_EXTRA_ARGS', '').split()

    # Diretório de trabalho onde o `claude` é executado (contexto do projeto).
    WORKDIR = os.getenv('CLAUDE_CODE_WORKDIR') or os.getcwd()

    def __init__(self):
        self._disponivel_cache: Optional[bool] = None

    # ── disponibilidade ──────────────────────────────────────────────────────

    def disponivel(self) -> bool:
        """Verifica se o CLI `claude` existe no PATH da máquina local."""
        if os.getenv('DISABLE_CLAUDE_CODE', '').lower() in ('1', 'true', 'yes'):
            return False
        if self._disponivel_cache is None:
            self._disponivel_cache = shutil.which(self.BIN) is not None
        return self._disponivel_cache

    def versao(self) -> Optional[str]:
        if not self.disponivel():
            return None
        try:
            r = subprocess.run(
                [self.BIN, '--version'], capture_output=True, text=True, timeout=10
            )
            return (r.stdout or r.stderr or '').strip() or None
        except Exception:
            return None

    # ── chamada principal ────────────────────────────────────────────────────

    def _montar_comando(self, prompt: str) -> list:
        cmd = [self.BIN, '--print', '--output-format', 'json']
        if self.BARE:
            cmd.append('--bare')
        if self.MODEL:
            cmd.extend(['--model', self.MODEL])
        cmd.extend(self.EXTRA_ARGS)
        cmd.append(prompt)
        return cmd

    def _executar(self, prompt: str) -> dict:
        """Roda `claude --print` e devolve {success, texto, error}."""
        if not self.disponivel():
            return {
                'success': False,
                'texto': '',
                'error': (
                    f"Claude Code CLI ('{self.BIN}') não encontrado no PATH. "
                    "Instale com: npm install -g @anthropic-ai/claude-code "
                    "e autentique com: claude"
                ),
            }
        try:
            r = subprocess.run(
                self._montar_comando(prompt),
                cwd=self.WORKDIR,
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return {'success': False, 'texto': '', 'error': f'Tempo limite de {self.TIMEOUT}s excedido ao chamar o Claude Code.'}
        except FileNotFoundError:
            return {'success': False, 'texto': '', 'error': f"Binário '{self.BIN}' não encontrado."}
        except Exception as e:
            return {'success': False, 'texto': '', 'error': f'Erro ao executar Claude Code: {e}'}

        saida = (r.stdout or '').strip()
        erro_stderr = (r.stderr or '').strip()

        if not saida:
            return {
                'success': False,
                'texto': '',
                'error': erro_stderr or f'Claude Code não retornou saída (exit code {r.returncode}).',
            }

        # --output-format json devolve um único objeto JSON com o resultado.
        try:
            payload = json.loads(saida)
        except json.JSONDecodeError:
            # Fallback: se por algum motivo vier texto puro, usa direto.
            return {'success': r.returncode == 0, 'texto': saida, 'error': None if r.returncode == 0 else erro_stderr}

        if payload.get('is_error'):
            return {'success': False, 'texto': '', 'error': payload.get('result') or erro_stderr or 'Erro desconhecido do Claude Code.'}

        texto = (payload.get('result') or '').strip()
        return {'success': True, 'texto': texto, 'error': None, 'raw': payload}

    # ── API pública (mesma "forma" do CookieAIGenerator) ────────────────────

    def responder(self, pergunta: str) -> dict:
        pergunta = (pergunta or '').strip()
        if not pergunta:
            return {'success': False, 'texto': '', 'error': 'Por favor, faça uma pergunta.'}
        instrucao = (
            'Você é a Cookie AI, assistente integrada ao CookieScript IDE, '
            'rodando localmente via Claude Code. Responda em português, '
            f'de forma direta e útil.\n\nPergunta: {pergunta}'
        )
        return self._executar(instrucao)

    def gerar_codigo(self, prompt: str, language: str = 'cookiescript') -> dict:
        prompt = (prompt or '').strip()
        if not prompt:
            return {'success': False, 'texto': '', 'error': 'Prompt vazio.'}
        lang_name = self._nome_linguagem(language)
        instrucao = (
            f'Gere apenas código {lang_name} válido para o seguinte pedido, '
            'sem explicações, sem markdown, apenas o código pronto para uso:\n\n'
            f'{prompt}'
        )
        resultado = self._executar(instrucao)
        if resultado.get('success'):
            resultado['texto'] = self._limpar_bloco_codigo(resultado['texto'])
        return resultado

    def pesquisar_codigo(self, query: str, language: str = 'cookiescript') -> dict:
        query = (query or '').strip()
        if not query:
            return {'success': False, 'texto': '', 'error': 'Consulta vazia.'}
        lang_name = self._nome_linguagem(language)
        instrucao = f'Forneça um exemplo de código {lang_name} para: {query}. Apenas o código, sem explicações.'
        resultado = self._executar(instrucao)
        if resultado.get('success'):
            resultado['texto'] = self._limpar_bloco_codigo(resultado['texto'])
        return resultado

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _nome_linguagem(language: str) -> str:
        language = (language or 'cookiescript').lower().strip()
        if language == 'cookiescript':
            return 'CookieScript'
        if language in ('js', 'javascript', 'node'):
            return 'JavaScript'
        return language.capitalize()

    @staticmethod
    def _limpar_bloco_codigo(texto: str) -> str:
        """Remove cercas de markdown (```lang ... ```) se o modelo as incluir."""
        texto = (texto or '').strip()
        if texto.startswith('```'):
            linhas = texto.split('\n')
            if linhas:
                linhas = linhas[1:]
            if linhas and linhas[-1].strip().startswith('```'):
                linhas = linhas[:-1]
            texto = '\n'.join(linhas).strip()
        return texto
