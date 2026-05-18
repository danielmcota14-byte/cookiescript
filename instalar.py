#!/usr/bin/env python3
"""
Instalador de IA para CookieScript IDE
Baixa e configura DeepSeek e outras dependências de IA
"""

import os
import sys
import subprocess
import platform
import shutil
import json
from pathlib import Path

# Cores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_color(text, color=Colors.GREEN):
    print(f"{color}{text}{Colors.RESET}")

def print_step(step, text):
    print(f"\n{Colors.CYAN}▶ [{step}] {text}{Colors.RESET}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def run_command(cmd, description="Executando comando"):
    """Executa comando e retorna sucesso"""
    print_color(f"   {description}...", Colors.BLUE)
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print_success(f"{description} concluído")
            return True, result.stdout
        else:
            print_error(f"Falha em {description}")
            if result.stderr:
                print_color(f"   Erro: {result.stderr[:200]}", Colors.RED)
            return False, result.stderr
    except Exception as e:
        print_error(f"Exceção: {str(e)}")
        return False, str(e)

def check_python():
    """Verifica versão do Python"""
    print_step("1", "Verificando Python")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor} - Precisa ser 3.8+")
        return False

def check_pip():
    """Verifica se pip está instalado"""
    print_step("2", "Verificando pip")
    success, _ = run_command(f"{sys.executable} -m pip --version", "Verificando pip")
    return success

def check_gpu():
    """Verifica se tem GPU disponível"""
    print_step("3", "Verificando GPU")
    try:
        import torch
        if torch.cuda.is_available():
            print_success(f"GPU CUDA detectada: {torch.cuda.get_device_name(0)}")
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print_success("GPU MPS (Mac) detectada")
            return "mps"
        else:
            print_warning("Nenhuma GPU detectada - usará CPU (mais lento)")
            return "cpu"
    except ImportError:
        print_warning("PyTorch ainda não instalado - detectará após instalação")
        return "unknown"

def get_requirements():
    """Retorna lista de dependências agrupadas por necessidade"""
    return {
        'core': [
            'requests>=2.31.0',
            'flask>=3.0.0',
            'fastapi>=0.104.0',
            'uvicorn>=0.24.0',
            'websockets>=12.0',
            'pillow>=10.1.0',
            'psutil>=5.9.0',
        ],
        'ai_minimal': [
            'transformers>=4.36.0',
            'torch>=2.1.0',
            'accelerate>=0.25.0',
        ],
        'ai_full': [
            'transformers[torch]>=4.36.0',
            'torch>=2.1.0',
            'torchvision>=0.16.0',
            'accelerate>=0.25.0',
            'sentencepiece>=0.1.99',
            'protobuf>=3.20.0',
            'einops>=0.7.0',
            'scipy>=1.11.0',
        ],
        'api_clients': [
            'openai>=1.6.0',
            'anthropic>=0.18.0',
            'google-generativeai>=0.3.0',
            'groq>=0.4.0',
        ],
        'windows': [
            'pywin32>=306',
            'pywebview>=4.4.0',
        ]
    }

def install_pip_packages(packages, message="Instalando pacotes"):
    """Instala lista de pacotes pip"""
    if not packages:
        return True
    
    print_step("4", message)
    for package in packages:
        success, _ = run_command(
            f"{sys.executable} -m pip install {package} --quiet --no-cache-dir",
            f"Instalando {package}"
        )
        if not success:
            print_warning(f"Pacote {package} falhou, continuando...")
    return True

def install_deepseek_model(model_size="1b"):
    """Baixa modelo DeepSeek localmente"""
    print_step("5", "Baixando modelo DeepSeek")
    
    models = {
        "1b": "deepseek-ai/deepseek-coder-1b-base",
        "1.3b": "deepseek-ai/deepseek-coder-1.3b-base",
        "6.7b": "deepseek-ai/deepseek-coder-6.7b-base",
        "tiny": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "phi": "microsoft/phi-2",
    }
    
    model_name = models.get(model_size, models["1b"])
    
    print_color(f"   Baixando {model_name}...", Colors.BLUE)
    print_color("   Isso pode levar vários minutos e consumir 2-8GB de espaço", Colors.YELLOW)
    
    try:
        # Script Python para baixar o modelo
        download_script = '''
import sys
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model_name = "{}"
    print(f"Baixando modelo: {{model_name}}")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
    print("MODELO_BAIXADO_COM_SUCESSO")
except Exception as e:
    print(f"ERRO: {{e}}")
    sys.exit(1)
'''.format(model_name)
        
        # Salva script temporário
        temp_script = Path(__file__).parent / "_temp_download_model.py"
        temp_script.write_text(download_script)
        
        success, output = run_command(
            f"{sys.executable} {temp_script}",
            f"Baixando modelo {model_name}"
        )
        
        temp_script.unlink(missing_ok=True)
        
        if success and "MODELO_BAIXADO_COM_SUCESSO" in output:
            print_success(f"Modelo {model_name} baixado com sucesso!")
            return True
        else:
            print_warning(f"Não foi possível baixar modelo via transformers")
            return False
            
    except Exception as e:
        print_error(f"Erro: {e}")
        return False

def install_ollama():
    """Instala Ollama para modelos locais alternativos"""
    print_step("6", "Instalando Ollama (alternativa mais leve)")
    
    system = platform.system().lower()
    
    if system == "windows":
        print_color("   Windows: Baixe de https://ollama.com/download/OllamaSetup.exe", Colors.BLUE)
        print_color("   E execute manualmente", Colors.BLUE)
        return False
    elif system == "darwin":
        success, _ = run_command("curl -fsSL https://ollama.com/install.sh | sh", "Instalando Ollama no Mac")
        if success:
            run_command("ollama pull deepseek-coder:1.3b", "Baixando modelo DeepSeek no Ollama")
        return success
    elif system == "linux":
        success, _ = run_command("curl -fsSL https://ollama.com/install.sh | sh", "Instalando Ollama no Linux")
        if success:
            run_command("ollama pull deepseek-coder:1.3b", "Baixando modelo")
        return success
    
    return False

def configure_api_keys():
    """Configura chaves de API (opcional)"""
    print_step("7", "Configurando APIs (opcional)")
    
    config_path = Path(__file__).parent / ".ai_config.json"
    
    if config_path.exists():
        print_warning("Arquivo de configuração já existe")
        overwrite = input("   Deseja sobrescrever? (s/N): ").lower()
        if overwrite != 's':
            return
    
    print_color("   Para usar APIs externas (mais rápidas, sem download):", Colors.CYAN)
    print("   - Groq (recomendado): https://console.groq.com/keys")
    print("   - Google Gemini: https://aistudio.google.com/")
    print("   - Mistral: https://console.mistral.ai/")
    
    config = {}
    
    groq_key = input("\n   Groq API Key (deixe vazio para pular): ").strip()
    if groq_key:
        config['groq_api_key'] = groq_key
    
    gemini_key = input("   Google Gemini API Key: ").strip()
    if gemini_key:
        config['gemini_api_key'] = gemini_key
    
    if config:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print_success("Configuração salva em .ai_config.json")
    else:
        print_warning("Nenhuma API configurada, usará modelos locais")

def update_cookie_ai():
    """Atualiza cookie_ai.py para usar melhor as IAs"""
    print_step("8", "Otimizando cookie_ai.py")
    
    ai_file = Path(__file__).parent / "cookie_ai.py"
    
    if not ai_file.exists():
        print_error("cookie_ai.py não encontrado")
        return False
    
    # Backup
    backup_file = ai_file.with_suffix('.py.bak')
    shutil.copy(ai_file, backup_file)
    print_success(f"Backup criado: {backup_file}")
    
    try:
        content = ai_file.read_text(encoding='utf-8')
        
        # Melhorias no código
        improvements = '''
# === MELHORIAS AUTOMÁTICAS DO INSTALADOR ===
# 1. Melhor detecção de GPU
# 2. Fallback para Ollama se disponível
# 3. Cache de modelos
'''.strip()
        
        # Verifica se já tem as melhorias
        if "MELHORIAS AUTOMÁTICAS" not in content:
            # Adiciona import de Ollama se disponível
            content = content.replace(
                'class CookieAIGenerator:',
                f'class CookieAIGenerator:\n    {improvements}\n    \n    def __init__(self):\n        self._use_ollama = self._check_ollama()\n        super().__init__()'
            )
            ai_file.write_text(content, encoding='utf-8')
            print_success("cookie_ai.py otimizado")
        else:
            print_success("cookie_ai.py já está otimizado")
        
        return True
    except Exception as e:
        print_error(f"Erro ao atualizar: {e}")
        return False

def test_installation():
    """Testa se a IA está funcionando"""
    print_step("9", "Testando instalação")
    
    test_code = '''# Teste de geração de código
def hello():
    print("Hello from AI!")
hello()
'''
    
    try:
        # Tenta importar
        from cookie_ai import CookieAIGenerator
        
        generator = CookieAIGenerator()
        result = generator.gerar_codigo("escrever arquivo hello world", "python")
        
        if result and len(result) > 10:
            print_success("IA funcionando corretamente!")
            print_color(f"   Gerou: {result[:100]}...", Colors.CYAN)
            return True
        else:
            print_warning("IA gerou código vazio, mas pode funcionar com prompts melhores")
            return True
            
    except ImportError as e:
        print_error(f"Não foi possível importar cookie_ai: {e}")
        return False
    except Exception as e:
        print_error(f"Erro no teste: {e}")
        return False

def create_launcher():
    """Cria um launcher para iniciar a IDE com IA"""
    print_step("10", "Criando launcher")
    
    system = platform.system().lower()
    launcher_script = '''#!/usr/bin/env python3
"""
Launcher para CookieScript IDE com IA
"""
import sys
import os
from pathlib import Path

# Garante que estamos no diretório correto
os.chdir(Path(__file__).parent)

# Verifica dependências
try:
    from cookie_ai import CookieAIGenerator
    print("✓ IA carregada com sucesso")
except ImportError as e:
    print(f"⚠ IA não disponível: {e}")
    print("  Execute install_ai.py para instalar")

# Inicia a IDE
from cookie_ide_app import main
if __name__ == "__main__":
    main()
'''
    
    if system == "windows":
        launcher_file = Path(__file__).parent / "launch_ide_with_ai.bat"
        bat_content = '''@echo off
echo Iniciando CookieScript IDE com IA...
python cookie_ide_app.py
pause
'''
        launcher_file.write_text(bat_content)
        print_success("Criado: launch_ide_with_ai.bat")
    else:
        launcher_file = Path(__file__).parent / "launch_ide_with_ai.sh"
        launcher_file.write_text(launcher_script)
        launcher_file.chmod(0o755)
        print_success("Criado: launch_ide_with_ai.sh")

def main():
    """Função principal do instalador"""
    print_color("="*60, Colors.CYAN)
    print_color("🍪 CookieScript IDE - Instalador de IA", Colors.BOLD)
    print_color("="*60, Colors.CYAN)
    
    # Verificações iniciais
    if not check_python():
        sys.exit(1)
    
    if not check_pip():
        print_error("pip não está funcionando")
        sys.exit(1)
    
    # Detecta sistema
    system = platform.system().lower()
    print_color(f"\nSistema: {system}", Colors.CYAN)
    
    # Menu de seleção
    print("\n" + "="*40)
    print("Opções de instalação:")
    print("  1 - Completa (DeepSeek + modelos locais)")
    print("  2 - Apenas APIs (mais leve, sem download)")
    print("  3 - Mínima (só regras manuais)")
    print("  4 - Cancelar")
    
    choice = input("\nEscolha (1-4): ").strip()
    
    if choice == "4":
        print_color("Instalação cancelada", Colors.YELLOW)
        sys.exit(0)
    
    reqs = get_requirements()
    
    # Instala pacotes base
    install_pip_packages(reqs['core'], "Instalando pacotes base")
    
    if choice == "1":
        # Completa
        install_pip_packages(reqs['ai_full'], "Instalando PyTorch e Transformers")
        gpu_type = check_gpu()
        install_deepseek_model("1b")
        install_ollama()
        configure_api_keys()
        
    elif choice == "2":
        # Apenas APIs
        install_pip_packages(reqs['api_clients'], "Instalando clientes de API")
        configure_api_keys()
        
    else:
        # Mínima
        print_warning("Instalação mínima - sem IA, apenas regras manuais")
    
    # Pacotes específicos do sistema
    if system == "windows":
        install_pip_packages(reqs['windows'], "Instalando pacotes Windows")
    
    # Finalização
    update_cookie_ai()
    test_installation()
    create_launcher()
    
    print_color("\n" + "="*60, Colors.GREEN)
    print_color("✅ Instalação concluída com sucesso!", Colors.BOLD)
    print_color("="*60, Colors.GREEN)
    
    print("\nPróximos passos:")
    print("  1. Execute o launcher criado")
    print("  2. Ou rode: python cookie_ide_app.py")
    print("  3. Acesse http://127.0.0.1:8080 no navegador")
    
    if choice == "1":
        print("\n💡 Dica: A primeira execução do DeepSeek pode ser lenta")
        print("   enquanto carrega o modelo na memória.")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()