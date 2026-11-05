import os
import json
import subprocess
import sys
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse


def _carregar_dotenv():
    """Carrega o arquivo .env (se existir) sem sobrescrever variáveis já definidas.
    Roda ANTES de importar cookie_ai/claude_code_ai, que leem o ambiente ao importar."""
    arq = Path(__file__).resolve().parent / '.env'
    if not arq.is_file():
        return
    for linha in arq.read_text(encoding='utf-8').splitlines():
        linha = linha.strip()
        if not linha or linha.startswith('#') or '=' not in linha:
            continue
        k, v = linha.split('=', 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v != '' and k not in os.environ:
            os.environ[k] = v


_carregar_dotenv()

try:
    from cookiescript_vm import CookieScriptVM
except ImportError:
    CookieScriptVM = None

try:
    from cookie_ai import CookieAIGenerator
except ImportError:
    CookieAIGenerator = None

try:
    from claude_code_ai import ClaudeCodeAI
except ImportError:
    ClaudeCodeAI = None

try:
    from ai_client import (
        chat_completion,
        council_chat,
        build_messages,
        extract_file_blocks,
        strip_file_blocks,
        SYSTEM_BASE,
        AIClientError,
    )
except ImportError:
    chat_completion = None
    council_chat = None
    build_messages = None
    extract_file_blocks = None
    strip_file_blocks = None
    SYSTEM_BASE = ""
    AIClientError = RuntimeError

try:
    import memory_store
except ImportError:
    memory_store = None

try:
    from file_analyzer import prepare_for_ai, build_file_context, save_upload, MAX_FILE_BYTES
except ImportError:
    prepare_for_ai = None
    build_file_context = None
    save_upload = None
    MAX_FILE_BYTES = 15 * 1024 * 1024

BASE_DIR = Path(__file__).resolve().parent
PORT = int(os.environ.get('PORT', 8080))


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTPServer que atende cada requisição numa thread própria. Necessário
    porque /api/execute pode rodar CookieScript que chama ler_entrada()
    (input() bloqueante, ex.: jogo.cookiescript); com o HTTPServer padrão
    (single-threaded) isso travaria a IDE inteira para todo mundo até o
    timeout da requisição."""
    daemon_threads = True


class CookieIDEHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Evita o navegador reutilizar versões antigas das páginas
        self.send_header('Cache-Control', 'no-store, max-age=0')
        super().end_headers()

    def log_message(self, format, *args):
        print(f"[LOG] {format % args}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/health':
            self.send_json({'status': 'ok'})
            return
        if path in ('/', ''):
            self.path = '/index1.html' if (BASE_DIR / 'index1.html').exists() else '/cookie_ide.html'
        elif path.startswith('/api/'):
            self.send_json({'error': 'Método não suportado'}, 405)
            return
        return super().do_GET()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length else '{}'
        except Exception:
            body = '{}'
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        path = urlparse(self.path).path

        routes = {
            '/api/open':           self.api_open,
            '/api/save':           self.api_save,
            '/api/execute':        self.api_execute,
            '/api/generate':       self.api_generate,
            '/api/search':         self.api_search,
            '/api/files':          self.api_files,
            '/api/create_project': self.api_create_project,
            '/api/load_projects':  self.api_load_projects,
            '/api/load_project':   self.api_load_project,
            '/api/git_status':     self.api_git_status,
            '/api/git_commit':     self.api_git_commit,
            '/api/ollama_status':  self.api_ollama_status,
            '/api/claude_code_status': self.api_claude_code_status,
            '/api/ask':            self.api_ask,
            '/api/ask_enhanced':   self.api_ask_enhanced,
            # Novos endpoints Cookie AI 2.0
            '/api/chat':           self.api_chat,
            '/api/upload_analyze': self.api_upload_analyze,
            '/api/memory/list':    self.api_memory_list,
            '/api/memory/add':     self.api_memory_add,
            '/api/memory/delete':  self.api_memory_delete,
            '/api/memory/clear':   self.api_memory_clear,
            '/api/memory/block':   self.api_memory_block,
            '/api/sessions':       self.api_sessions,
            '/api/session/clear':  self.api_session_clear,
            '/api/save_ai_files':  self.api_save_ai_files,
            '/api/providers':      self.api_providers,
        }

        handler = routes.get(path)
        if handler:
            try:
                handler(data)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                import traceback; traceback.print_exc()
                self.send_json({'success': False, 'error': str(e)})
        else:
            self.send_json({'error': 'Rota não encontrada'}, 404)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _resolver_caminho_seguro(path: str):
        """Resolve 'path' relativo a BASE_DIR e garante que o resultado
        continua dentro de BASE_DIR. Sem isso, um 'path' como
        '../../etc/passwd' ou até um caminho absoluto tipo '/etc/passwd'
        (Path ignora a base quando o segundo operando é absoluto) permitiria
        ler ou sobrescrever qualquer arquivo da máquina — grave, já que este
        servidor roda exposto na web. Retorna None se o caminho escapar de
        BASE_DIR."""
        # Remover barra inicial para impedir que Path trate como absoluto e
        # descarte BASE_DIR por completo.
        candidato = (BASE_DIR / path.lstrip('/\\')).resolve()
        try:
            candidato.relative_to(BASE_DIR.resolve())
        except ValueError:
            return None
        return candidato

    def send_json(self, data, status=200):
        # Garante que 'error' seja sempre texto (nunca objeto) para o front-end
        if isinstance(data, dict) and data.get('error') is not None and not isinstance(data['error'], str):
            e = data['error']
            if isinstance(e, dict):
                e = e.get('message') or e.get('error') or json.dumps(e, ensure_ascii=False)
            data = dict(data, error=str(e))
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(response)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response)
        except (BrokenPipeError, ConnectionResetError):
            # O cliente/proxy fechou a conexão antes da resposta — nada a fazer.
            print('[HTTP] cliente desconectou antes da resposta')

    # ── endpoints ─────────────────────────────────────────────────────────────

    def api_open(self, data):
        path = data.get('path', '')
        if not path:
            self.send_json({'error': 'Caminho não informado'}); return
        full = self._resolver_caminho_seguro(path)
        if full is None:
            self.send_json({'error': 'Caminho inválido'}); return
        if not full.exists():
            self.send_json({'error': f'Arquivo não encontrado: {path}'}); return
        try:
            self.send_json({'success': True, 'content': full.read_text('utf-8'), 'path': path})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_save(self, data):
        path = data.get('path', '') or 'untitled.cookiescript'
        content = data.get('content', '')
        full = self._resolver_caminho_seguro(path)
        if full is None:
            self.send_json({'error': 'Caminho inválido'}); return
        try:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, 'utf-8')
            self.send_json({'success': True, 'path': path})
        except Exception as e:
            self.send_json({'error': str(e)})

    # ── execução de código ────────────────────────────────────────────────────

    # linguagem -> (executável, extensão). Só roda se o interpretador existir na máquina.
    _RUNNERS = {
        'python':     (None, '.py'),          # usa sys.executable
        'javascript': ('node', '.js'),
        'lua':        ('lua', '.lua'),
        'ruby':       ('ruby', '.rb'),
        'php':        ('php', '.php'),
    }

    def api_execute(self, data):
        import shutil, tempfile
        code = data.get('code', '')
        language = (data.get('language') or 'cookiescript').lower()
        if not code.strip():
            self.send_json({'success': False, 'error': 'Código vazio'}); return
        try:
            if language == 'cookiescript':
                if not CookieScriptVM:
                    self.send_json({'success': False, 'error': 'Interpretador CookieScript (cookiescript_vm.py) não encontrado.'}); return
                vm = CookieScriptVM(modo='debug')
                self.send_json({'success': True, 'output': str(vm.executar(code))}); return
            if language not in self._RUNNERS:
                self.send_json({'success': False, 'error': f'Linguagem "{language}" não é suportada.'}); return
            exe, ext = self._RUNNERS[language]
            exe = sys.executable if exe is None else shutil.which(exe)
            if not exe:
                self.send_json({'success': False, 'error': f'"{language}" não está instalado neste servidor, então não é possível executar.'}); return
            with tempfile.TemporaryDirectory() as tmpdir:
                f = Path(tmpdir) / f'main{ext}'
                f.write_text(code, 'utf-8')
                r = subprocess.run([exe, str(f)], capture_output=True, text=True, timeout=10, cwd=tmpdir)
            out = (r.stdout or '')
            if r.stderr:
                out += ('\n' if out else '') + '[ERRO] ' + r.stderr
            self.send_json({'success': r.returncode == 0, 'output': out.strip() or '(sem saída)',
                            **({} if r.returncode == 0 else {'error': f'O programa terminou com código {r.returncode}.'})})
        except subprocess.TimeoutExpired:
            self.send_json({'success': False, 'error': 'Timeout: a execução passou de 10 segundos.'})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)})

    # Modelos de produção da Groq (a Groq aposenta modelos com frequência;
    # confira https://console.groq.com/docs/deprecations). O primeiro é o padrão.
    GROQ_MODELOS = ['openai/gpt-oss-120b', 'openai/gpt-oss-20b']

    def _groq_chat(self, system, user, key, model=None, temperature=0.3):
        """Chama a Groq. Se o modelo pedido foi aposentado/não existe, tenta os modelos atuais.
        Retorna (texto, modelo_usado). Levanta RuntimeError com a mensagem real da Groq."""
        import urllib.request, urllib.error
        url = os.environ.get('GROQ_URL', 'https://api.groq.com/openai/v1/chat/completions')
        candidatos = []
        for m in [model] + self.GROQ_MODELOS:
            if m and m not in candidatos:
                candidatos.append(m)
        ultimo = 'Falha desconhecida na Groq.'
        for m in candidatos:
            corpo = {'model': m, 'temperature': temperature, 'max_tokens': 4096,
                     'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}
            if m.startswith('openai/gpt-oss'):
                corpo['reasoning_effort'] = 'low'   # evita gastar tokens só "pensando"
            req = urllib.request.Request(url, data=json.dumps(corpo).encode(), method='POST',
                                         headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                                                  'User-Agent': 'CookieScriptIDE/1.0 (+python)',
                                                  'Authorization': f'Bearer {key.strip()}'})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    texto = json.loads(resp.read())['choices'][0]['message'].get('content') or ''
                    if not texto.strip():
                        raise RuntimeError(f'O modelo {m} devolveu resposta vazia.')
                    return texto, m
            except urllib.error.HTTPError as e:
                corpo_erro = ''
                try:
                    corpo_erro = e.read().decode('utf-8', 'replace')
                    msg = json.loads(corpo_erro).get('error', {}).get('message') or f'HTTP {e.code}'
                except Exception:
                    msg = f'HTTP {e.code}' + (f' — {corpo_erro[:200]}' if corpo_erro else '')
                ultimo = msg
                baixo = msg.lower()
                if e.code in (400, 404) and any(t in baixo for t in ('decommission', 'does not exist', 'not found', 'no longer supported', 'access to it')):
                    print(f'[Groq] modelo {m} indisponível: {msg}')
                    continue   # tenta o próximo modelo
                raise RuntimeError(msg)
        raise RuntimeError(ultimo)

    @staticmethod
    def _so_codigo(texto):
        """Se a IA devolveu markdown com ```bloco```, extrai só o código."""
        import re
        m = re.search(r'```[\w+-]*\n(.*?)```', texto, re.S)
        return (m.group(1) if m else texto).strip()

    def api_generate(self, data):
        prompt = data.get('prompt', '')
        language = data.get('language', 'cookiescript')
        if not prompt:
            self.send_json({'success': False, 'error': 'Prompt vazio'}); return
        code = ''
        modelo_usado = None
        aviso = None
        # 1. Groq (IA de verdade) — chave enviada pela página ou GROQ_API_KEY do servidor
        key = data.get('groq_api_key') or os.environ.get('GROQ_API_KEY', '')
        model = data.get('groq_model') or self.GROQ_MODELOS[0]
        if key:
            try:
                extra = ''
                if language == 'cookiescript':
                    extra = (' CookieScript tem sintaxe própria: variáveis (x = 5), log("texto " + x), '
                             'filesystem.escrever_arquivo(caminho="a.txt", conteudo="..", modo="w"), '
                             'network.http_request(url=.., metodo="GET"), math.*, json.*, function nome(a) { resultado = ... }, '
                             'for i in [1,2,3] { }, if/else, ler_entrada(prompt="..").')
                system = (f'Você gera código {language}. Responda APENAS com o código, sem explicações, '
                          f'sem markdown.{extra}')
                texto, usado = self._groq_chat(system, prompt, key, model)
                code = self._so_codigo(texto)
                modelo_usado = f'Groq/{usado}'
            except Exception as e:
                aviso = f'Groq falhou: {e}'
                print(f'[Groq] {e}')
        # 2. Claude Code local (se instalado/autenticado na máquina)
        if not code and ClaudeCodeAI:
            try:
                cc = ClaudeCodeAI()
                if cc.disponivel():
                    r = cc.gerar_codigo(prompt, language)
                    if r.get('success') and r.get('texto'):
                        code = r['texto']
                        modelo_usado = 'claude-code'
            except Exception as e:
                print(f'[ClaudeCode] {e}')
        # 3. DeepSeek local / templates (fallback)
        if not code and CookieAIGenerator:
            try:
                code = CookieAIGenerator().gerar_codigo(prompt, language) or ''
            except Exception:
                pass
        if not code:
            code = f'// Gerado para: {prompt}\n'
        resp = {'success': True, 'code': code, 'model': modelo_usado or 'fallback'}
        if aviso:
            resp['aviso'] = aviso
        self.send_json(resp)

    def api_search(self, data):
        query = data.get('query', '')
        language = data.get('language', 'cookiescript')
        if not query:
            self.send_json({'error': 'Consulta vazia'}); return
        results = []
        for f in BASE_DIR.glob('*.cookiescript'):
            try:
                c = f.read_text('utf-8')
                if query.lower() in c.lower():
                    results.append({'file': f.name, 'preview': c[:200]})
            except Exception:
                pass
        generated = None
        if ClaudeCodeAI:
            try:
                cc = ClaudeCodeAI()
                if cc.disponivel():
                    r = cc.pesquisar_codigo(query, language)
                    if r.get('success') and r.get('texto'):
                        generated = r['texto']
            except Exception as e:
                print(f'[ClaudeCode] {e}')
        if generated is None and CookieAIGenerator:
            try:
                generated = CookieAIGenerator().pesquisar_codigo(query, language)
            except Exception:
                pass
        self.send_json({'success': True, 'results': results, 'generated': generated})

    def api_files(self, data):
        exts = ('.cookiescript', '.cookie', '.py', '.js', '.txt', '.md')
        files = sorted(f.name for f in BASE_DIR.iterdir() if f.is_file() and f.suffix in exts)
        self.send_json({'success': True, 'files': files})

    def api_create_project(self, data):
        name = data.get('name', '')
        if not name:
            self.send_json({'error': 'Nome não informado'}); return
        pf = BASE_DIR / '.projects.json'
        try:
            projects = json.loads(pf.read_text('utf-8')) if pf.exists() else {}
            pid = f'proj_{len(projects)+1}_{int(os.path.getmtime(BASE_DIR))}'
            projects[pid] = {'id': pid, 'name': name, 'description': data.get('description',''), 'files': {}}
            pf.write_text(json.dumps(projects, indent=2), 'utf-8')
            self.send_json({'success': True, 'project_id': pid})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_load_projects(self, data):
        pf = BASE_DIR / '.projects.json'
        try:
            projects = json.loads(pf.read_text('utf-8')) if pf.exists() else {}
            self.send_json({'success': True, 'projects': projects})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_load_project(self, data):
        pid = data.get('project_id', '')
        if not pid:
            self.send_json({'error': 'ID não informado'}); return
        pf = BASE_DIR / '.projects.json'
        try:
            projects = json.loads(pf.read_text('utf-8')) if pf.exists() else {}
            if pid in projects:
                self.send_json({'success': True, 'project': projects[pid]})
            else:
                self.send_json({'error': 'Projeto não encontrado'})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_git_status(self, data):
        try:
            r = subprocess.run(['git', 'status', '--porcelain'], cwd=str(BASE_DIR), capture_output=True, text=True)
            self.send_json({'success': True, 'status': r.stdout.strip() or 'Nenhuma alteração'})
        except Exception:
            self.send_json({'success': False, 'error': 'Git não encontrado'})

    def api_git_commit(self, data):
        msg = data.get('message', '')
        if not msg:
            self.send_json({'error': 'Mensagem não informada'}); return
        try:
            subprocess.run(['git', 'add', '-A'], cwd=str(BASE_DIR), capture_output=True)
            r = subprocess.run(['git', 'commit', '-m', msg], cwd=str(BASE_DIR), capture_output=True, text=True)
            self.send_json({'success': True, 'output': r.stdout or r.stderr})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_ollama_status(self, data):
        import urllib.request
        url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        try:
            with urllib.request.urlopen(f'{url}/api/tags', timeout=3) as resp:
                result = json.loads(resp.read())
                models = [m['name'] for m in result.get('models', [])]
                self.send_json({'online': True, 'models': models})
        except Exception as e:
            self.send_json({'online': False, 'error': str(e)})

    def api_claude_code_status(self, data):
        if not ClaudeCodeAI:
            self.send_json({'online': False, 'error': 'Módulo claude_code_ai.py não encontrado.'})
            return
        try:
            cc = ClaudeCodeAI()
            disponivel = cc.disponivel()
            self.send_json({
                'online': disponivel,
                'version': cc.versao() if disponivel else None,
                'error': None if disponivel else (
                    "Claude Code CLI não encontrado. Instale com: "
                    "npm install -g @anthropic-ai/claude-code e depois rode: claude"
                ),
            })
        except Exception as e:
            self.send_json({'online': False, 'error': str(e)})

    # ── IA local ──────────────────────────────────────────────────────────────

    def _ollama_running(self):
        import urllib.request
        try:
            with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def _ollama_request(self, pergunta, model=None):
        import urllib.request
        OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        if model is None:
            try:
                with urllib.request.urlopen(f'{OLLAMA_URL}/api/tags', timeout=5) as r:
                    data = json.loads(r.read())
                    models = [m['name'] for m in data.get('models', [])]
                    for pref in ['phi3', 'phi', 'llama3', 'gemma', 'mistral']:
                        match = next((m for m in models if pref in m.lower()), None)
                        if match:
                            model = match
                            break
                    if not model and models:
                        model = models[0]
            except Exception:
                pass
            if not model:
                model = 'phi3'
        payload = json.dumps({'model': model, 'prompt': pergunta, 'stream': False}).encode()
        req = urllib.request.Request(
            f'{OLLAMA_URL}/api/generate', data=payload,
            headers={'Content-Type': 'application/json'}, method='POST'
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read()).get('response', '').strip()

    def api_ask(self, data):
        """Compatibilidade: redireciona para o chat unificado."""
        data = dict(data or {})
        if 'message' not in data and 'pergunta' in data:
            data['message'] = data.get('pergunta')
        return self.api_chat(data)

    def api_ask_enhanced(self, data):
        data = dict(data or {})
        data['provider'] = data.get('provider') or 'auto'
        if 'message' not in data and 'pergunta' in data:
            data['message'] = data.get('pergunta')
        return self.api_chat(data)

    # ── Cookie AI 2.0: chat unificado + memória + arquivos ────────────────────

    def api_providers(self, data):
        """Status dos provedores configurados no servidor (env)."""
        import ai_client as ac
        self.send_json({
            'success': True,
            'providers': {
                'omniroute': {
                    'url': ac.OMNIROUTE_URL,
                    'configured': bool(ac.OMNIROUTE_KEY) or True,
                    'model': ac.DEFAULT_OMNIROUTE_MODEL,
                },
                'grok': {
                    'url': ac.GROK_URL,
                    'configured': bool(ac.GROK_KEY),
                    'model': ac.DEFAULT_GROK_MODEL,
                },
                'groq': {
                    'url': ac.GROQ_URL,
                    'configured': bool(ac.GROQ_KEY),
                    'model': ac.DEFAULT_GROQ_MODEL,
                },
            },
            'memory': memory_store is not None,
            'max_upload_mb': MAX_FILE_BYTES // (1024 * 1024),
            'no_image_generation': True,
        })

    def api_chat(self, data):
        """
        Endpoint principal de chat.
        Body JSON:
          message / pergunta: texto
          provider: auto | omniroute | grok | groq | claude_code | ollama
          model: opcional
          session_id: opcional (memória de conversa)
          api_key: opcional (sobrescreve env para o provider)
          files: lista de {name, content_base64}  (análise de qualquer tipo)
          save_files: bool — se true, grava automaticamente blocos <<<FILE>>> no disco
        """
        if chat_completion is None:
            self.send_json({'success': False, 'error': 'Módulo ai_client.py não encontrado.'})
            return

        message = (data.get('message') or data.get('pergunta') or '').strip()
        provider = (data.get('provider') or 'auto').strip().lower()
        model = data.get('model') or data.get('groq_model')
        session_id = data.get('session_id') or data.get('session') or None
        api_key = data.get('api_key') or data.get('groq_api_key') or data.get('omniroute_api_key') or data.get('grok_api_key')
        files_in = data.get('files') or []
        save_files = bool(data.get('save_files', True))
        scope = data.get('memory_scope') or 'global'

        if not message and not files_in:
            self.send_json({'success': False, 'error': 'Mensagem vazia.'})
            return

        # Claude Code / Ollama / local como atalhos legados
        if provider == 'claude_code':
            if not ClaudeCodeAI:
                self.send_json({'success': False, 'error': 'Claude Code não disponível.'})
                return
            cc = ClaudeCodeAI()
            if not cc.disponivel():
                self.send_json({'success': False, 'error': 'Claude Code CLI não encontrado nesta máquina.'})
                return
            r = cc.responder(message)
            if r.get('success'):
                self.send_json({'success': True, 'resposta': r['texto'], 'model': 'claude-code', 'files': []})
            else:
                self.send_json({'success': False, 'error': r.get('error') or 'Erro Claude Code'})
            return

        # Memória
        history = []
        mem_block = ''
        if memory_store:
            if session_id:
                session_id = memory_store.ensure_session(session_id)
                history = memory_store.get_history(session_id, limit=30)
            else:
                session_id = memory_store.ensure_session()
            mem_block = memory_store.memory_block_for_prompt(scope=scope, limit=25)
            # aprendizado automático se o usuário pedir para lembrar
            if message:
                memory_store.maybe_learn_from_user(message, scope=scope)

        # Arquivos enviados
        prepared = []
        file_parts = []
        file_text_ctx = ''
        if files_in and prepare_for_ai:
            import base64
            for f in files_in[:8]:  # max 8 arquivos por mensagem
                name = f.get('name') or 'arquivo'
                b64 = f.get('content_base64') or f.get('base64') or ''
                if not b64:
                    continue
                try:
                    raw = base64.b64decode(b64)
                except Exception:
                    continue
                try:
                    info = prepare_for_ai(name, raw)
                    prepared.append(info)
                except Exception as e:
                    prepared.append({'name': name, 'kind': 'error', 'text': str(e), 'size': 0})
            if prepared and build_file_context:
                file_text_ctx, image_parts = build_file_context(prepared)
                file_parts = image_parts or []

        user_content = message
        if file_text_ctx:
            user_content = (message + '\n\n' if message else '') + 'Arquivos enviados para análise:\n' + file_text_ctx

        # Mensagens
        messages = build_messages(
            user_content,
            memory_block=mem_block,
            history=history,
            file_parts=file_parts if file_parts else None,
            system_extra=(
                'Você NÃO gera imagens. Você cria códigos, planilhas (CSV/JSON), scripts e arquivos de texto. '
                'Quando criar arquivos use o formato <<<FILE path="...>>> ... <<<END_FILE>>>.'
            ),
        )

        council_members = []
        use_council = provider in ('auto', 'council', 'ensemble', 'conselho', '') or data.get('council')
        # provider isolado (omniroute/grok/groq) NÃO usa conselho, a menos que council=true
        if provider in ('omniroute', 'grok', 'groq') and not data.get('council'):
            use_council = False

        try:
            if use_council and council_chat is not None:
                texto, usado, council_members = council_chat(
                    messages,
                    temperature=float(data.get('temperature', 0.6)),
                    max_tokens=int(data.get('max_tokens', 8192)),
                    api_key=api_key,
                    include_providers=data.get('council_members') or ['omniroute', 'groq'],
                )
            else:
                texto, usado = chat_completion(
                    messages,
                    provider=provider if provider in ('omniroute', 'grok', 'groq', 'auto') else 'auto',
                    model=model,
                    temperature=float(data.get('temperature', 0.7)),
                    max_tokens=int(data.get('max_tokens', 8192)),
                    api_key=api_key,
                )
        except AIClientError as e:
            # fallbacks legados
            if CookieAIGenerator and os.getenv('ENABLE_LOCAL_AI', '').lower() in ('1', 'true', 'yes'):
                try:
                    gen = CookieAIGenerator()
                    texto = gen.responder(message)
                    usado = 'DeepSeek Local'
                except Exception:
                    self.send_json({'success': False, 'error': str(e)})
                    return
            elif self._ollama_running():
                try:
                    texto = self._ollama_request(message)
                    usado = 'ollama'
                except Exception:
                    self.send_json({'success': False, 'error': str(e)})
                    return
            else:
                self.send_json({'success': False, 'error': str(e)})
                return

        # Extrai arquivos gerados pela IA
        files_out = extract_file_blocks(texto) if extract_file_blocks else []
        visible = strip_file_blocks(texto) if strip_file_blocks else texto

        saved = []
        if save_files and files_out:
            for item in files_out:
                path = self._resolver_caminho_seguro(item['path'])
                if not path:
                    continue
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(item['content'], encoding='utf-8')
                    saved.append(str(path.relative_to(BASE_DIR)))
                except Exception as e:
                    print(f'[save_ai_file] {e}')

        # Persiste histórico
        if memory_store and session_id:
            memory_store.append_message(session_id, 'user', message or '[arquivos]')
            memory_store.append_message(session_id, 'assistant', visible[:20000])

        # Resumo do conselho (sem textos enormes no JSON — só labels + erros)
        council_summary = []
        for m in (council_members or []):
            council_summary.append({
                'provider': m.get('provider'),
                'label': m.get('label'),
                'ok': bool(m.get('text')),
                'error': m.get('error'),
                'chars': len(m.get('text') or ''),
            })

        self.send_json({
            'success': True,
            'resposta': visible or texto,
            'raw': texto,
            'model': usado,
            'session_id': session_id,
            'files': files_out,
            'saved_files': saved,
            'analyzed': [{'name': p.get('name'), 'kind': p.get('kind'), 'size': p.get('size')} for p in prepared],
            'council': council_summary,
            'mode': 'council' if council_summary else 'single',
        })

    def api_upload_analyze(self, data):
        """Analisa um ou mais arquivos sem chat completo (só extrai + opcionalmente pergunta curta)."""
        if not prepare_for_ai:
            self.send_json({'success': False, 'error': 'file_analyzer não disponível'})
            return
        import base64
        files_in = data.get('files') or []
        question = (data.get('question') or data.get('pergunta') or 'Resuma e analise estes arquivos.').strip()
        prepared = []
        for f in files_in[:8]:
            name = f.get('name') or 'arquivo'
            b64 = f.get('content_base64') or f.get('base64') or ''
            if not b64:
                continue
            try:
                raw = base64.b64decode(b64)
                prepared.append(prepare_for_ai(name, raw))
            except Exception as e:
                prepared.append({'name': name, 'kind': 'error', 'text': str(e), 'size': 0})
        if not prepared:
            self.send_json({'success': False, 'error': 'Nenhum arquivo válido'})
            return
        # reutiliza chat
        data2 = {
            'message': question,
            'files': files_in,
            'provider': data.get('provider') or 'auto',
            'model': data.get('model'),
            'session_id': data.get('session_id'),
            'api_key': data.get('api_key') or data.get('groq_api_key'),
            'save_files': data.get('save_files', False),
        }
        return self.api_chat(data2)

    def api_memory_list(self, data):
        if not memory_store:
            self.send_json({'success': False, 'error': 'Memória não disponível'})
            return
        scope = data.get('scope') or 'global'
        items = memory_store.list_memories(scope=scope, kind=data.get('kind'), limit=int(data.get('limit', 50)), search=data.get('search'))
        self.send_json({'success': True, 'memories': items})

    def api_memory_add(self, data):
        if not memory_store:
            self.send_json({'success': False, 'error': 'Memória não disponível'})
            return
        content = (data.get('content') or '').strip()
        if not content:
            self.send_json({'success': False, 'error': 'content vazio'})
            return
        mid = memory_store.add_memory(
            content,
            scope=data.get('scope') or 'global',
            kind=data.get('kind') or 'fact',
            importance=float(data.get('importance', 0.7)),
            metadata=data.get('metadata'),
        )
        self.send_json({'success': True, 'id': mid})

    def api_memory_delete(self, data):
        if not memory_store:
            self.send_json({'success': False, 'error': 'Memória não disponível'})
            return
        ok = memory_store.delete_memory(data.get('id') or '')
        self.send_json({'success': ok})

    def api_memory_clear(self, data):
        if not memory_store:
            self.send_json({'success': False, 'error': 'Memória não disponível'})
            return
        n = memory_store.clear_memories(scope=data.get('scope') or 'global')
        self.send_json({'success': True, 'deleted': n})

    def api_memory_block(self, data):
        if not memory_store:
            self.send_json({'success': True, 'block': '(memória desligada)'})
            return
        block = memory_store.memory_block_for_prompt(scope=data.get('scope') or 'global', limit=int(data.get('limit', 30)))
        self.send_json({'success': True, 'block': block})

    def api_sessions(self, data):
        if not memory_store:
            self.send_json({'success': True, 'sessions': []})
            return
        self.send_json({'success': True, 'sessions': memory_store.list_sessions(limit=int(data.get('limit', 20)))})

    def api_session_clear(self, data):
        if not memory_store:
            self.send_json({'success': False, 'error': 'Memória não disponível'})
            return
        sid = data.get('session_id')
        if not sid:
            self.send_json({'success': False, 'error': 'session_id obrigatório'})
            return
        memory_store.clear_session(sid)
        self.send_json({'success': True})

    def api_save_ai_files(self, data):
        """Salva explicitamente uma lista de {path, content} gerados pela IA."""
        files = data.get('files') or []
        saved = []
        for item in files:
            path = self._resolver_caminho_seguro(item.get('path') or '')
            if not path:
                continue
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(item.get('content') or '', encoding='utf-8')
                saved.append(str(path.relative_to(BASE_DIR)))
            except Exception as e:
                print(f'[save_ai_files] {e}')
        self.send_json({'success': True, 'saved': saved})


# ── inicialização ─────────────────────────────────────────────────────────────

def main():
    os.chdir(BASE_DIR)
    httpd = ThreadingHTTPServer(('0.0.0.0', PORT), CookieIDEHandler)
    print(f'\n{"="*50}')
    print(f'  CookieScript IDE — http://localhost:{PORT}/')
    print(f'  Pasta em uso: {BASE_DIR}')
    print(f'{"="*50}\n')
    if not os.environ.get('PORT'):
        try:
            webbrowser.open(f'http://localhost:{PORT}/')
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nEncerrando...')
        httpd.shutdown()


if __name__ == '__main__':
    main()
