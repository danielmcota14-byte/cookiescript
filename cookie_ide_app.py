import os
import json
import subprocess
import sys
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Tentativa de importar módulos opcionais (não obrigatórios)
try:
    from cookiescript_vm import CookieScriptVM
except ImportError:
    print("AVISO: cookiescript_vm não encontrado. Usando modo simplificado.")
    CookieScriptVM = None

try:
    from cookie_ai import CookieAIGenerator
except ImportError:
    print("AVISO: cookie_ai não encontrado. Usando gerador simples.")
    CookieAIGenerator = None

BASE_DIR = Path(__file__).resolve().parent
PORT = int(os.environ.get('PORT', 8080))

class CookieIDEHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[LOG] {format % args}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Endpoint de saúde para o frontend
        if path == '/health':
            self.send_json({'status': 'ok'})
            return

        # Servir a página principal (cookie_ide.html ou index1.html)
        if path == '/' or path == '':
            # Tenta servir index1.html (Cookie AI) se existir, senão cookie_ide.html
            if (BASE_DIR / 'index1.html').exists():
                self.path = '/index1.html'
            else:
                self.path = '/cookie_ide.html'
        elif path == '/api/logs':
            self.send_logs()
            return
        elif path.startswith('/api/'):
            self.send_json({'error': 'Método não suportado'}, 405)
            return

        # Para arquivos estáticos (HTML, CSS, JS), usa o método padrão
        return super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length else '{}'
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/open':
            self.api_open(data)
        elif path == '/api/save':
            self.api_save(data)
        elif path == '/api/execute':
            self.api_execute(data)
        elif path == '/api/generate':
            self.api_generate(data)
        elif path == '/api/search':
            self.api_search(data)
        elif path == '/api/files':
            self.api_files(data)
        elif path == '/api/create_project':
            self.api_create_project(data)
        elif path == '/api/load_projects':
            self.api_load_projects(data)
        elif path == '/api/load_project':
            self.api_load_project(data)
        elif path == '/api/git_status':
            self.api_git_status(data)
        elif path == '/api/git_commit':
            self.api_git_commit(data)
        elif path == '/api/ollama_status':
            self.api_ollama_status(data)
        elif path == '/api/ask':                 # endpoint para IA local
            self.api_ask(data)
        elif path == '/api/ask_enhanced':        # endpoint para IA potencializada (Groq proxy)
            self.api_ask_enhanced(data)
        else:
            self.send_json({'error': 'Rota não encontrada'}, 404)

    # -------------------- Métodos auxiliares --------------------
    def send_json(self, data, status=200):
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    # -------------------- Endpoints originais --------------------
    def api_open(self, data):
        path = data.get('path', '')
        if not path:
            self.send_json({'error': 'Caminho não informado'})
            return
        full_path = BASE_DIR / path
        if not full_path.exists():
            self.send_json({'error': f'Arquivo não encontrado: {path}'})
            return
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_json({'success': True, 'content': content, 'path': path})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_save(self, data):
        path = data.get('path', '')
        content = data.get('content', '')
        if not path:
            path = 'untitled.cookiescript'
        full_path = BASE_DIR / path
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.send_json({'success': True, 'path': path})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_execute(self, data):
        code = data.get('code', '')
        language = data.get('language', 'cookiescript')
        if not code:
            self.send_json({'error': 'Código vazio'})
            return
        output_lines = []
        try:
            if language == 'cookiescript' and CookieScriptVM:
                vm = CookieScriptVM(modo='debug')
                result = vm.executar(code)
                output_lines.append(str(result))
            elif language == 'python':
                temp_file = BASE_DIR / '_temp_exec.py'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                result = subprocess.run(
                    [sys.executable, str(temp_file)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                temp_file.unlink(missing_ok=True)
                if result.stdout:
                    output_lines.append(result.stdout)
                if result.stderr:
                    output_lines.append(f"[ERRO] {result.stderr}")
            elif language == 'javascript':
                temp_file = BASE_DIR / '_temp_exec.js'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                node = subprocess.run(['node', '-v'], capture_output=True)
                if node.returncode == 0:
                    result = subprocess.run(
                        ['node', str(temp_file)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    temp_file.unlink(missing_ok=True)
                    if result.stdout:
                        output_lines.append(result.stdout)
                    if result.stderr:
                        output_lines.append(f"[ERRO] {result.stderr}")
                else:
                    output_lines.append("[ERRO] Node.js não encontrado")
            else:
                output_lines.append(f"Execução simulada para {language}")
                output_lines.append(f"Código:\n{code[:500]}")
            self.send_json({'success': True, 'output': '\n'.join(output_lines)})
        except subprocess.TimeoutExpired:
            self.send_json({'success': False, 'error': 'Timeout na execução'})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)})

    def api_generate(self, data):
        prompt = data.get('prompt', '')
        language = data.get('language', 'cookiescript')
        if not prompt:
            self.send_json({'error': 'Prompt vazio'})
            return
        code = f'// Código gerado para: {prompt}\n// Linguagem: {language}\n\n'
        if CookieAIGenerator:
            try:
                generator = CookieAIGenerator()
                generated = generator.gerar_codigo(prompt, language)
                if generated:
                    code = generated
            except Exception as e:
                code += f'// Erro ao usar IA: {e}\n'
        # Fallback
        if language == 'python':
            code += '''# Exemplo Python
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
        elif language == 'javascript':
            code += '''// Exemplo JavaScript
console.log("Hello, World!");
'''
        else:
            code += '''// Exemplo CookieScript
filesystem.escrever_arquivo("saida.txt", "Hello, World!")
'''
        self.send_json({'success': True, 'code': code})

    def api_search(self, data):
        query = data.get('query', '')
        language = data.get('language', 'cookiescript')
        if not query:
            self.send_json({'error': 'Consulta vazia'})
            return
        results = []
        for file in BASE_DIR.glob('*.cookiescript'):
            if file.stat().st_size < 100000:
                try:
                    content = file.read_text(encoding='utf-8')
                    if query.lower() in content.lower():
                        results.append({
                            'file': file.name,
                            'preview': content[:200] + '...' if len(content) > 200 else content
                        })
                except:
                    pass
        if CookieAIGenerator:
            try:
                generator = CookieAIGenerator()
                code = generator.pesquisar_codigo(query, language)
                self.send_json({'success': True, 'results': results, 'generated': code})
                return
            except:
                pass
        self.send_json({'success': True, 'results': results, 'generated': None})

    def api_files(self, data):
        files = []
        extensions = ('.cookiescript', '.cookie', '.py', '.js', '.txt', '.md')
        for file in BASE_DIR.iterdir():
            if file.is_file() and file.suffix in extensions:
                files.append(file.name)
        files.sort()
        self.send_json({'success': True, 'files': files})

    def api_create_project(self, data):
        name = data.get('name', '')
        description = data.get('description', '')
        if not name:
            self.send_json({'error': 'Nome do projeto não informado'})
            return
        projects_file = BASE_DIR / '.projects.json'
        try:
            if projects_file.exists():
                with open(projects_file, 'r', encoding='utf-8') as f:
                    projects = json.load(f)
            else:
                projects = {}
            project_id = f"proj_{len(projects) + 1}_{int(os.path.getmtime(BASE_DIR))}"
            projects[project_id] = {
                'id': project_id,
                'name': name,
                'description': description,
                'created': os.path.getmtime(BASE_DIR),
                'files': {}
            }
            with open(projects_file, 'w', encoding='utf-8') as f:
                json.dump(projects, f, indent=2)
            self.send_json({'success': True, 'project_id': project_id})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_load_projects(self, data):
        projects_file = BASE_DIR / '.projects.json'
        try:
            if projects_file.exists():
                with open(projects_file, 'r', encoding='utf-8') as f:
                    projects = json.load(f)
                self.send_json({'success': True, 'projects': projects})
            else:
                self.send_json({'success': True, 'projects': {}})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_load_project(self, data):
        project_id = data.get('project_id', '')
        if not project_id:
            self.send_json({'error': 'ID do projeto não informado'})
            return
        projects_file = BASE_DIR / '.projects.json'
        try:
            if projects_file.exists():
                with open(projects_file, 'r', encoding='utf-8') as f:
                    projects = json.load(f)
                if project_id in projects:
                    self.send_json({'success': True, 'project': projects[project_id]})
                else:
                    self.send_json({'error': 'Projeto não encontrado'})
            else:
                self.send_json({'error': 'Nenhum projeto encontrado'})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_git_status(self, data):
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True
            )
            status = result.stdout.strip() if result.stdout else "Nenhuma alteração"
            self.send_json({'success': True, 'status': status})
        except:
            self.send_json({'success': False, 'error': 'Git não encontrado'})

    def api_git_commit(self, data):
        message = data.get('message', '')
        if not message:
            self.send_json({'error': 'Mensagem não informada'})
            return
        try:
            subprocess.run(['git', 'add', '-A'], cwd=str(BASE_DIR), capture_output=True)
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True
            )
            self.send_json({'success': True, 'output': result.stdout or result.stderr})
        except Exception as e:
            self.send_json({'error': str(e)})

    def api_ollama_status(self, data):
        import urllib.request
        OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        try:
            with urllib.request.urlopen(f'{OLLAMA_URL}/api/tags', timeout=3) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                models = [m['name'] for m in result.get('models', [])]
                self.send_json({'online': True, 'models': models})
        except Exception as e:
            self.send_json({'online': False, 'error': str(e)})

    def send_logs(self):
        self.send_json({'logs': []})

    # -------------------- NOVO ENDPOINT para IA local (Cookie AI) --------------------
    def _ollama_list_models(self):
        """Retorna lista de modelos instalados no Ollama."""
        import urllib.request
        OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        try:
            with urllib.request.urlopen(f'{OLLAMA_URL}/api/tags', timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return [m['name'] for m in data.get('models', [])]
        except:
            return []

    def _ollama_pull(self, model):
        """Baixa um modelo do Ollama (bloqueante)."""
        import urllib.request
        OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        print(f'[Ollama] Baixando modelo {model}... (pode demorar alguns minutos)')
        payload = json.dumps({'name': model, 'stream': False}).encode('utf-8')
        req = urllib.request.Request(
            f'{OLLAMA_URL}/api/pull',
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print(f'[Ollama] Modelo {model} pronto: {result.get("status", "")}')

    def _ollama_request(self, pergunta, model=None):
        """Chama Ollama localmente na porta 11434."""
        import urllib.request, urllib.error
        OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        PREFERRED_MODEL = os.environ.get('OLLAMA_MODEL', 'phi3')

        # Se model não foi especificado, escolhe o melhor disponível
        if model is None:
            modelos = self._ollama_list_models()
            print(f'[Ollama] Modelos instalados: {modelos}')
            if modelos:
                # Prefere phi3, phi, llama, gemma nessa ordem
                for pref in [PREFERRED_MODEL, 'phi3', 'phi', 'llama3.2', 'llama3', 'gemma', 'mistral']:
                    match = next((m for m in modelos if pref in m.lower()), None)
                    if match:
                        model = match
                        break
                if not model:
                    model = modelos[0]  # qualquer um disponível
            else:
                # Nenhum modelo — baixa phi3 automaticamente
                print('[Ollama] Nenhum modelo encontrado. Baixando phi3...')
                try:
                    self._ollama_pull('phi3')
                    model = 'phi3'
                except Exception as e:
                    raise Exception(f'Ollama online mas sem modelos. Erro ao baixar phi3: {e}')

        print(f'[Ollama] Usando modelo: {model}')
        payload = json.dumps({'model': model, 'prompt': pergunta, 'stream': False}).encode('utf-8')
        req = urllib.request.Request(
            f'{OLLAMA_URL}/api/generate',
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result.get('response', '').strip()

    def api_ask(self, data):
        pergunta = data.get('pergunta', '')
        if not pergunta:
            self.send_json({'error': 'Pergunta vazia'})
            return

        # Usa DeepSeek local via torch + transformers
        if CookieAIGenerator:
            try:
                generator = CookieAIGenerator()
                # Carrega o modelo se ainda não carregou
                generator._load_deepseek_model()
                resposta = generator.responder(pergunta)
                model_name = generator.DEEPSEEK_MODEL.split('/')[-1]
                self.send_json({'success': True, 'resposta': resposta, 'model': model_name})
                return
            except Exception as e:
                print(f'[DeepSeek Local] Erro: {e}')
                self.send_json({'success': False, 'error': f'Erro no modelo local: {str(e)}'})
                return

        self.send_json({
            'success': False,
            'error': 'torch e transformers nao instalados. Verifique o Dockerfile.'
        })

    def api_ask_enhanced(self, data):
        """IA Potencializada: DeepSeek local gera resposta base, Groq refina e expande."""
        import urllib.request
        import urllib.error

        pergunta = data.get('pergunta', '')
        groq_model = data.get('groq_model', 'deepseek-r1-distill-llama-70b')
        groq_api_key = data.get('groq_api_key', '') or os.environ.get('GROQ_API_KEY', '')

        if not pergunta:
            self.send_json({'error': 'Pergunta vazia'})
            return

        # Passo 1: gera resposta base com DeepSeek local
        resposta_local = None
        if CookieAIGenerator:
            try:
                generator = CookieAIGenerator()
                generator._load_deepseek_model()
                resposta_local = generator.responder(pergunta)
                print(f'[Enhanced] Resposta local gerada ({len(resposta_local)} chars)')
            except Exception as e:
                print(f'[Enhanced] DeepSeek local falhou: {e}')

        # Passo 2: envia para Groq para refinar e potencializar
        if groq_api_key:
            try:
                if resposta_local:
                    system_prompt = (
                        "Você é a Cookie AI Potencializada, uma IA avançada integrada ao CookieScript IDE. "
                        "Uma IA local (DeepSeek) já gerou uma resposta inicial para a pergunta do usuário. "
                        "Sua tarefa é: 1) Analisar e corrigir erros na resposta local se houver. "
                        "2) Expandir e melhorar a resposta com mais detalhes e exemplos. "
                        "3) Manter o foco na pergunta original. "
                        "Responda sempre em português brasileiro."
                    )
                    user_content = (
                        f"Pergunta original: {pergunta}

"
                        f"Resposta da IA local (DeepSeek):
{resposta_local}

"
                        f"Por favor, analise, corrija se necessário e melhore esta resposta."
                    )
                else:
                    system_prompt = (
                        "Você é a Cookie AI Potencializada integrada ao CookieScript IDE. "
                        "Responda de forma clara, completa e em português brasileiro."
                    )
                    user_content = pergunta

                payload = json.dumps({
                    'model': groq_model,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_content}
                    ],
                    'max_tokens': 2048,
                    'temperature': 0.7
                }).encode('utf-8')

                req = urllib.request.Request(
                    'https://api.groq.com/openai/v1/chat/completions',
                    data=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {groq_api_key}'
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    resposta_final = result['choices'][0]['message']['content']
                    self.send_json({
                        'success': True,
                        'resposta': resposta_final,
                        'model': f'DeepSeek Local + {groq_model} (Groq)',
                        'resposta_local': resposta_local
                    })
                    return
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', errors='ignore')
                print(f'[Enhanced] Groq erro {e.code}: {body}')
            except Exception as e:
                print(f'[Enhanced] Groq falhou: {e}')

        # Fallback: retorna só a resposta local se Groq falhou ou sem chave
        if resposta_local:
            self.send_json({
                'success': True,
                'resposta': resposta_local,
                'model': 'DeepSeek Local (Groq indisponível)'
            })
            return

        self.send_json({
            'success': False,
            'error': 'Configure GROQ_API_KEY para usar a IA Potencializada.'
        })


# ============================================================
# AUTO-SETUP: instala Ollama e dependências automaticamente
# ============================================================

import platform
import threading
import time
import urllib.request
import urllib.error


def _print_step(msg):
    print(f"\n{'='*55}\n  {msg}\n{'='*55}")


def _cmd(args, **kwargs):
    """Roda comando e retorna (returncode, stdout+stderr)."""
    result = subprocess.run(
        args, capture_output=True, text=True,
        **kwargs
    )
    return result.returncode, result.stdout + result.stderr


def _is_ollama_installed():
    code, _ = _cmd(['ollama', '--version'])
    return code == 0


def _install_ollama():
    system = platform.system()
    _print_step(f"Instalando Ollama ({system})...")

    if system == 'Windows':
        installer = BASE_DIR / '_ollama_setup.exe'
        print("  Baixando instalador do Ollama...")
        try:
            urllib.request.urlretrieve(
                'https://ollama.com/download/OllamaSetup.exe',
                str(installer)
            )
            print("  Executando instalador (siga as instruções na tela)...")
            subprocess.run([str(installer)], check=True)
            installer.unlink(missing_ok=True)
            print("  Ollama instalado!")
            return True
        except Exception as e:
            print(f"  ERRO ao instalar Ollama: {e}")
            print("  Instale manualmente em: https://ollama.com/download")
            return False

    elif system in ('Linux', 'Darwin'):
        print("  Rodando instalador oficial do Ollama...")
        try:
            code, out = _cmd(
                'curl -fsSL https://ollama.com/install.sh | sh',
                shell=True
            )
            if code == 0:
                print("  Ollama instalado!")
                return True
            else:
                print(f"  ERRO: {out}")
                print("  Instale manualmente: https://ollama.com")
                return False
        except Exception as e:
            print(f"  ERRO: {e}")
            return False
    else:
        print(f"  Sistema {system} não suportado para instalação automática.")
        print("  Instale manualmente: https://ollama.com")
        return False


def _ollama_running():
    try:
        with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=3) as r:
            return r.status == 200
    except:
        return False


def _start_ollama_server():
    """Inicia ollama serve em background."""
    if _ollama_running():
        return
    print("  Iniciando servidor Ollama em background...")
    if platform.system() == 'Windows':
        subprocess.Popen(
            ['ollama', 'serve'],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        subprocess.Popen(
            ['ollama', 'serve'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    # Aguarda subir
    for _ in range(20):
        time.sleep(1)
        if _ollama_running():
            print("  Ollama online!")
            return
    print("  AVISO: Ollama demorou para iniciar. A IA pode não responder imediatamente.")


def _model_downloaded(model='phi3'):
    try:
        with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=5) as r:
            data = json.loads(r.read())
            names = [m['name'] for m in data.get('models', [])]
            return any(model in n for n in names)
    except:
        return False


def _pull_model(model='phi3'):
    _print_step(f"Baixando modelo de IA: {model} (~2GB, pode demorar...)")
    print("  Por favor aguarde. Isso só acontece uma vez.")
    code, out = _cmd(['ollama', 'pull', model])
    if code == 0:
        print(f"  Modelo {model} pronto!")
        return True
    else:
        print(f"  ERRO ao baixar modelo: {out}")
        return False


def _install_pip_deps():
    deps = ['requests']
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            print(f"  Instalando {dep}...")
            _cmd([sys.executable, '-m', 'pip', 'install', dep, '--quiet'])


def setup_auto():
    """Configura tudo automaticamente: pip deps, Ollama, modelo."""
    print("\n" + "="*55)
    print("  CookieScript IDE — Configuração Automática")
    print("="*55)

    # 1. Dependências Python
    print("\n[1/3] Verificando dependências Python...")
    _install_pip_deps()
    print("  OK")

    # 2. Ollama
    print("\n[2/3] Verificando Ollama...")
    if not _is_ollama_installed():
        ok = _install_ollama()
        if not ok:
            print("  AVISO: Ollama não instalado. IA local não estará disponível.")
            return
    else:
        print("  Ollama já instalado.")

    # Inicia servidor Ollama
    _start_ollama_server()

    # 3. Modelo
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'phi3')
    print(f"\n[3/3] Verificando modelo {OLLAMA_MODEL}...")
    if not _model_downloaded(OLLAMA_MODEL):
        _pull_model(OLLAMA_MODEL)
    else:
        print(f"  Modelo {OLLAMA_MODEL} já disponível.")

    print("\n  Tudo pronto! IA local funcionando.")


def main():
    os.chdir(BASE_DIR)

    # Auto-setup em thread separada para não travar o servidor
    setup_thread = threading.Thread(target=setup_auto, daemon=True)
    setup_thread.start()

    # Aguarda pelo menos as dependências básicas
    setup_thread.join(timeout=5)

    httpd = HTTPServer(('0.0.0.0', PORT), CookieIDEHandler)

    print(f"\n{'='*55}")
    print(f"  CookieScript IDE iniciada!")
    print(f"  Acesse: http://localhost:{PORT}/")
    print(f"  IA: configurando Ollama em background...")
    print(f"{'='*55}\n")

    # Abre navegador automaticamente
    if os.environ.get('RENDER') != 'true' and os.environ.get('PORT') is None:
        try:
            webbrowser.open(f'http://localhost:{PORT}/')
        except:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
        httpd.shutdown()


if __name__ == '__main__':
    main()