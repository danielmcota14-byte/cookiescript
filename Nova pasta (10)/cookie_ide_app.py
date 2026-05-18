import os

# Adicione isso DEPOIS dos imports
PORT = int(os.environ.get('PORT', 8080))  # Usa a porta do Render ou 8080 como fallback

import json
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

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
PORT = 8080

class CookieIDEHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[LOG] {format % args}")
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/' or parsed.path == '':
            self.path = '/cookie_ide.html'
        elif parsed.path == '/api/logs':
            self.send_logs()
            return
        elif parsed.path.startswith('/api/'):
            self.send_json({'error': 'Método não suportado'}, 405)
            return
        
        return super().do_GET()
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length else '{}'
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/open':
            self.api_open(data)
        elif parsed.path == '/api/save':
            self.api_save(data)
        elif parsed.path == '/api/execute':
            self.api_execute(data)
        elif parsed.path == '/api/generate':
            self.api_generate(data)
        elif parsed.path == '/api/search':
            self.api_search(data)
        elif parsed.path == '/api/files':
            self.api_files(data)
        elif parsed.path == '/api/create_project':
            self.api_create_project(data)
        elif parsed.path == '/api/load_projects':
            self.api_load_projects(data)
        elif parsed.path == '/api/load_project':
            self.api_load_project(data)
        elif parsed.path == '/api/git_status':
            self.api_git_status(data)
        elif parsed.path == '/api/git_commit':
            self.api_git_commit(data)
        else:
            self.send_json({'error': 'Rota não encontrada'}, 404)
    
    def send_json(self, data, status=200):
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)
    
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
                # Executar Python
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
                # Executar JavaScript
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
        
        # Fallback simples
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
        
        # Busca local nos arquivos .cookiescript
        results = []
        for file in BASE_DIR.glob('*.cookiescript'):
            if file.stat().st_size < 100000:  # Limite de 100KB
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
            # Primeiro adiciona tudo
            subprocess.run(['git', 'add', '-A'], cwd=str(BASE_DIR), capture_output=True)
            # Depois commita
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True
            )
            self.send_json({'success': True, 'output': result.stdout or result.stderr})
        except Exception as e:
            self.send_json({'error': str(e)})
    
    def send_logs(self):
        self.send_json({'logs': []})

def main():
    os.chdir(BASE_DIR)
    
    handler = CookieIDEHandler
    httpd = HTTPServer(('127.0.0.1', PORT), handler)
    
    url = f'http://127.0.0.1:{PORT}/'
    print(f"\n{'='*50}")
    print(f"CookieScript IDE iniciada!")
    print(f"Acesse: {url}")
    print(f"{'='*50}\n")
    
    # Abrir no navegador
    webbrowser.open(url)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
        httpd.shutdown()

if __name__ == '__main__':
    main()
