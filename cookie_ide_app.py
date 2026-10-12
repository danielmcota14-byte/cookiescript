import os
import json
import subprocess
import sys
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

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
        }

        handler = routes.get(path)
        if handler:
            try:
                handler(data)
            except Exception as e:
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
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response)

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
                                         headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    texto = json.loads(resp.read())['choices'][0]['message'].get('content') or ''
                    if not texto.strip():
                        raise RuntimeError(f'O modelo {m} devolveu resposta vazia.')
                    return texto, m
            except urllib.error.HTTPError as e:
                try:
                    msg = json.loads(e.read().decode()).get('error', {}).get('message') or f'HTTP {e.code}'
                except Exception:
                    msg = f'HTTP {e.code}'
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
        pergunta = data.get('pergunta', '').strip()
        provider = (data.get('provider') or '').strip().lower()
        if not pergunta:
            self.send_json({'error': 'Pergunta vazia'}); return

        # Provider explícito: o front-end pediu Claude Code Local especificamente.
        if provider == 'claude_code':
            if not ClaudeCodeAI:
                self.send_json({'success': False, 'error': 'Módulo claude_code_ai.py não encontrado.'})
                return
            cc = ClaudeCodeAI()
            if not cc.disponivel():
                self.send_json({
                    'success': False,
                    'error': (
                        'Claude Code CLI não encontrado nesta máquina. Instale com: '
                        'npm install -g @anthropic-ai/claude-code, depois rode "claude" '
                        'uma vez para autenticar.'
                    ),
                })
                return
            r = cc.responder(pergunta)
            if r.get('success'):
                self.send_json({'success': True, 'resposta': r['texto'], 'model': 'claude-code'})
            else:
                self.send_json({'success': False, 'error': r.get('error') or 'Erro ao consultar o Claude Code.'})
            return

        # 1. Claude Code local (prioridade quando disponível e nenhum provider foi forçado)
        if ClaudeCodeAI and os.getenv('DISABLE_CLAUDE_CODE', '').lower() not in ('1', 'true', 'yes'):
            try:
                cc = ClaudeCodeAI()
                if cc.disponivel():
                    r = cc.responder(pergunta)
                    if r.get('success') and r.get('texto'):
                        self.send_json({'success': True, 'resposta': r['texto'], 'model': 'claude-code'})
                        return
            except Exception as e:
                print(f'[ClaudeCode] {e}')

        # 2. DeepSeek local (se disponível e não em cloud)
        if CookieAIGenerator:
            try:
                gen = CookieAIGenerator()
                gen._load_deepseek_model()
                if gen._is_model_available():
                    resposta = gen.responder(pergunta)
                    self.send_json({'success': True, 'resposta': resposta, 'model': gen.DEEPSEEK_MODEL.split('/')[-1]})
                    return
            except Exception as e:
                print(f'[DeepSeek] {e}')

        # 3. Ollama local
        if self._ollama_running():
            try:
                resposta = self._ollama_request(pergunta)
                self.send_json({'success': True, 'resposta': resposta, 'model': 'ollama'})
                return
            except Exception as e:
                print(f'[Ollama] {e}')

        # 4. Fallback de templates
        if CookieAIGenerator:
            try:
                resposta = CookieAIGenerator()._fallback_resposta(pergunta)
                self.send_json({'success': True, 'resposta': resposta, 'model': 'fallback'})
                return
            except Exception as e:
                print(f'[Fallback] {e}')

        self.send_json({'success': False, 'error': 'Nenhum backend de IA disponível. Configure o Claude Code, Ollama ou uma API Key de Groq/Gemini.'})

    def api_ask_enhanced(self, data):
        import urllib.request, urllib.error
        pergunta = data.get('pergunta', '').strip()
        groq_model = data.get('groq_model') or self.GROQ_MODELOS[0]
        erro_groq = None
        groq_key = data.get('groq_api_key', '') or os.environ.get('GROQ_API_KEY', '')

        if not pergunta:
            self.send_json({'error': 'Pergunta vazia'}); return

        # Resposta base local
        resposta_local = None
        if CookieAIGenerator:
            try:
                gen = CookieAIGenerator()
                gen._load_deepseek_model()
                resposta_local = gen.responder(pergunta)
            except Exception as e:
                print(f'[Enhanced/local] {e}')

        # Groq refina
        if groq_key:
            try:
                if resposta_local:
                    system = 'Você é a Cookie AI Potencializada. Uma IA local já gerou uma resposta. Corrija erros, expanda e melhore. Responda em português.'
                    user = f'Pergunta: {pergunta}\n\nResposta local:\n{resposta_local}\n\nMelhore esta resposta.'
                else:
                    system = 'Você é a Cookie AI integrada ao CookieScript IDE. Responda em português de forma clara.'
                    user = pergunta

                texto, usado = self._groq_chat(system, user, groq_key, groq_model, temperature=0.7)
                self.send_json({'success': True, 'resposta': texto, 'model': f'Groq/{usado}'})
                return
            except Exception as e:
                erro_groq = str(e)
                print(f'[Groq] {e}')

        if resposta_local:
            self.send_json({'success': True, 'resposta': resposta_local, 'model': 'DeepSeek Local'})
            return

        self.send_json({'success': False, 'error': ('Groq: ' + erro_groq) if erro_groq else 'Configure GROQ_API_KEY ou instale torch+transformers para usar a IA Potencializada.'})


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
