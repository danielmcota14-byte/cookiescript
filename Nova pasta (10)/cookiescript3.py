# cookiescript/bridge.py
import ctypes
from typing import Any, Callable
import asyncio
import json

class CookieScriptVM:
    """Máquina virtual do CookieScript"""
    
    def __init__(self):
        # Carrega biblioteca C
        self.system = ctypes.CDLL('./system_layer.dll')
        
        # Inicializa V8 para JS
        import v8
        self.js_isolate = v8.Isolate()
        self.js_context = self.js_isolate.create_context()
        
        # Registra funções do sistema no JS
        self._expor_funcoes_sistema_para_js()
    
    def _expor_funcoes_sistema_para_js(self):
        """Expõe funções C/Python para JavaScript chamar"""
        self.js_context.register_callback('system_call', self._handler_system_call)
    
    def _handler_system_call(self, comando: str, args: dict):
        """Handler que recebe chamadas do JS e executa no sistema"""
        if comando == 'write_registry':
            return self.system.WriteRegistry(args['key'].encode(), args['value'].encode())
        elif comando == 'create_process':
            return self._criar_processo_oculto(args['cmd'])
        # ... mais comandos
    
    def executar_script(self, codigo_cookiescript: str):
        """Executa código CookieScript"""
        # Parseia e separa partes system/web
        partes = self._separar_partes(codigo_cookiescript)
        
        # Executa código system (Python/C)
        for system_code in partes['system']:
            self._executar_system(system_code)
        
        # Executa código web (JavaScript)
        for web_code in partes['web']:
            self.js_context.eval(web_code)