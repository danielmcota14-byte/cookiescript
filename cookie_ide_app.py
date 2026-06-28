import os
import json
import subprocess
import sys
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

try:
    from cookiescript_vm import CookieScriptVM
except ImportError:
    CookieScriptVM = None

try:
    from cookie_ai import CookieAIGenerator
except ImportError:
    CookieAIGenerator = None

BASE_DIR = Path(__file__).resolve().parent
PORT = int(os.environ.get('PORT', 8080))


class CookieIDEHandler(SimpleHTTPRequestHandler):
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

    def send_json(self, data, status=200):
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
        full = BASE_DIR / path
        if not full.exists():
            self.send_json({'error': f'Arquivo não encontrado: {path}'}); return
        try:
            self.send_json({'success': True, 'content': full.read_text('utf-8'), 'path': path})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_save(self, data):
        path = data.get('path', '') or 'untitled.cookiescript'
        content = data.get('content', '')
        full = BASE_DIR / path
        try:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, 'utf-8')
            self.send_json({'success': True, 'path': path})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_execute(self, data):
        code = data.get('code', '')
        language = data.get('language', 'cookiescript')
        if not code:
            self.send_json({'error': 'Código vazio'}); return
        output = []
        try:
            if language == 'cookiescript' and CookieScriptVM:
                vm = CookieScriptVM(modo='debug')
                output.append(str(vm.executar(code)))
            elif language == 'python':
                tmp = BASE_DIR / '_temp_exec.py'
                tmp.write_text(code, 'utf-8')
                r = subprocess.run([sys.executable, str(tmp)], capture_output=True, text=True, timeout=10)
                tmp.unlink(missing_ok=True)
                if r.stdout: output.append(r.stdout)
                if r.stderr: output.append(f'[ERRO] {r.stderr}')
            elif language == 'javascript':
                tmp = BASE_DIR / '_temp_exec.js'
                tmp.write_text(code, 'utf-8')
                if subprocess.run(['node', '-v'], capture_output=True).returncode == 0:
                    r = subprocess.run(['node', str(tmp)], capture_output=True, text=True, timeout=10)
                    tmp.unlink(missing_ok=True)
                    if r.stdout: output.append(r.stdout)
                    if r.stderr: output.append(f'[ERRO] {r.stderr}')
                else:
                    output.append('[ERRO] Node.js não encontrado')
            else:
                output.append(f'Execução simulada para {language}\n{code[:500]}')
            self.send_json({'success': True, 'output': '\n'.join(output)})
        except subprocess.TimeoutExpired:
            self.send_json({'success': False, 'error': 'Timeout na execução'})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)})

    def api_generate(self, data):
        prompt = data.get('prompt', '')
        language = data.get('language', 'cookiescript')
        if not prompt:
            self.send_json({'error': 'Prompt vazio'}); return
        code = ''
        if CookieAIGenerator:
            try:
                code = CookieAIGenerator().gerar_codigo(prompt, language) or ''
            except Exception:
                pass
        if not code:
            if language == 'python':
                code = f'# Gerado para: {prompt}\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n'
            elif language in ('javascript', 'js'):
                code = f'// Gerado para: {prompt}\nconsole.log("Hello, World!");\n'
            else:
                code = f'// Gerado para: {prompt}\nfilesystem.escrever_arquivo(caminho="saida.txt", conteudo="Hello, CookieScript!", modo="w")\n'
        self.send_json({'success': True, 'code': code})

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
        if CookieAIGenerator:
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
        if not pergunta:
            self.send_json({'error': 'Pergunta vazia'}); return

        # 1. DeepSeek local (se disponível e não em cloud)
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

        # 2. Ollama local
        if self._ollama_running():
            try:
                resposta = self._ollama_request(pergunta)
                self.send_json({'success': True, 'resposta': resposta, 'model': 'ollama'})
                return
            except Exception as e:
                print(f'[Ollama] {e}')

        # 3. Fallback de templates
        if CookieAIGenerator:
            try:
                resposta = CookieAIGenerator()._fallback_resposta(pergunta)
                self.send_json({'success': True, 'resposta': resposta, 'model': 'fallback'})
                return
            except Exception as e:
                print(f'[Fallback] {e}')

        self.send_json({'success': False, 'error': 'Nenhum backend de IA disponível. Configure Ollama ou uma API Key de Groq/Gemini.'})

    def api_ask_enhanced(self, data):
        import urllib.request, urllib.error
        pergunta = data.get('pergunta', '').strip()
        groq_model = data.get('groq_model', 'deepseek-r1-distill-llama-70b')
        groq_key = data.get('groq_api_key', '') or os.environ.get('GROQ_API_KEY', '') or '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'

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

                payload = json.dumps({
                    'model': groq_model,
                    'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
                    'max_tokens': 2048, 'temperature': 0.7
                }).encode()
                req = urllib.request.Request(
                    'https://api.groq.com/openai/v1/chat/completions', data=payload,
                    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {groq_key}'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                    self.send_json({'success': True, 'resposta': result['choices'][0]['message']['content'], 'model': f'Groq/{groq_model}'})
                    return
            except urllib.error.HTTPError as e:
                print(f'[Groq] HTTP {e.code}: {e.read().decode()}')
            except Exception as e:
                print(f'[Groq] {e}')

        if resposta_local:
            self.send_json({'success': True, 'resposta': resposta_local, 'model': 'DeepSeek Local'})
            return

        self.send_json({'success': False, 'error': 'Configure GROQ_API_KEY ou instale torch+transformers para usar a IA Potencializada.'})


# ── inicialização ─────────────────────────────────────────────────────────────

def main():
    os.chdir(BASE_DIR)
    httpd = HTTPServer(('0.0.0.0', PORT), CookieIDEHandler)
    print(f'\n{"="*50}')
    print(f'  CookieScript IDE — http://localhost:{PORT}/')
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
