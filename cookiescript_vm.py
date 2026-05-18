import os
import subprocess
import sys
import hashlib
import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
import re
from typing import Any, Callable, Dict, List

# Importar novos módulos
from cookiescript4 import DatabaseOps
from cookiescript5 import MathOps
from cookiescript6 import TimeOps
from cookiescript8 import StringOps, JsonOps, EncodingOps
from cookiescript9 import XMLOps
from cookiescript10 import LoggingOps
from cookiescript11 import SystemOps
from cookiescript12 import HTMLOps
from cookiescript13 import WebServiceOps

class FileSystemOps:
    def escrever_arquivo(self, caminho: str, conteudo: str = '', modo: str = 'w') -> str:
        """Escreve conteúdo em um arquivo
        modo: 'w' para sobrescrever, 'a' para adicionar ao final
        """
        caminho = os.path.expandvars(caminho)
        pasta = os.path.dirname(caminho)
        if pasta and not os.path.exists(pasta):
            os.makedirs(pasta, exist_ok=True)

        # Validar modo
        if modo not in ['w', 'a']:
            modo = 'w'

        with open(caminho, modo, encoding='utf-8') as f:
            f.write(str(conteudo))
        return caminho

    def ler_arquivo(self, caminho: str) -> str:
        caminho = os.path.expandvars(caminho)
        with open(caminho, 'r', encoding='utf-8') as f:
            return f.read()

    def deletar_arquivo(self, caminho: str) -> bool:
        caminho = os.path.expandvars(caminho)
        if os.path.exists(caminho):
            os.remove(caminho)
            return True
        return False

class ProcessOps:
    def criar_processo_oculto(self, comando: str) -> str:
        try:
            if os.name == 'nt':
                creationflags = subprocess.CREATE_NO_WINDOW
            else:
                creationflags = 0
            subprocess.Popen(comando, shell=True, creationflags=creationflags)
            return f'processo iniciado: {comando}'
        except Exception as e:
            return str(e)

class RegistryPersistence:
    def persistir_run(self, nome: str, caminho: str) -> str:
        return f'persistir_run: {nome} => {caminho}'

    def deletar_registro(self, hive: str, subkey: str, nome_valor: str) -> str:
        return f'deletar_registro: {hive}\\{subkey}::{nome_valor}'

class NetworkWebOps:
    def http_request(self, url: str, metodo: str = 'GET', dados: Any = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
        metodo = metodo.upper()
        data = None
        if dados is not None:
            data = json.dumps(dados).encode('utf-8')
        headers = headers or {}
        if data is not None:
            headers.setdefault('Content-Type', 'application/json')

        request = urllib.request.Request(url, data=data, headers=headers, method=metodo)
        context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(request, context=context, timeout=15) as response:
                body = response.read().decode('utf-8', errors='ignore')
                return {
                    'status': response.status,
                    'headers': dict(response.getheaders()),
                    'body': body
                }
        except urllib.error.HTTPError as err:
            return {'status': err.code, 'error': err.reason}
        except Exception as err:
            return {'error': str(err)}

    def websocket_client(self, url: str, on_message_callback: str = None) -> str:
        return f'websocket_client não implementado neste demo: {url}'

class CryptoOps:
    def hash_sha256(self, dados: str) -> str:
        return hashlib.sha256(dados.encode('utf-8')).hexdigest()

class PythonProxyModule:
    """Proxy de módulo Python carregado dinamicamente."""

    def __init__(self, module: Any):
        self._module = module

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._module, name, None)
        if callable(attr):
            def wrapper(*args, **kwargs):
                return attr(*args, **kwargs)
            return wrapper
        return attr

class PythonPackageOps:
    """Operações para instalar e verificar pacotes Python via pip."""

    def __init__(self, vm: 'CookieScriptVM' = None):
        self.vm = vm

    def instalar_pacote(self, nome: str, versao: str = '', atualizar: bool = False) -> Dict[str, Any]:
        pacote = f"{nome}=={versao}" if versao else nome
        comando = [sys.executable, '-m', 'pip', 'install', pacote]
        if atualizar:
            comando.append('--upgrade')
        try:
            resultado = subprocess.run(comando, capture_output=True, text=True, timeout=600)
            saida = resultado.stdout + resultado.stderr
            if resultado.returncode == 0:
                return {'sucesso': True, 'pacote': pacote, 'saida': saida}
            return {'sucesso': False, 'pacote': pacote, 'erro': saida}
        except Exception as e:
            return {'sucesso': False, 'pacote': pacote, 'erro': str(e)}

    def instalar_pacotes(self, pacotes: list) -> Dict[str, Any]:
        if not isinstance(pacotes, list):
            return {'sucesso': False, 'erro': 'Lista de pacotes esperada'}
        resultados = []
        for item in pacotes:
            if isinstance(item, dict):
                nome = item.get('nome')
                versao = item.get('versao', '')
                atualizar = item.get('atualizar', False)
            else:
                nome = str(item)
                versao = ''
                atualizar = False
            resultados.append(self.instalar_pacote(nome, versao, atualizar))
        return {'sucesso': True, 'resultados': resultados}

    def verificar_pacote(self, nome: str) -> bool:
        try:
            import importlib.util
            spec = importlib.util.find_spec(nome)
            return spec is not None
        except Exception:
            return False

    def importar_modulo(self, nome: str, alias: str = None) -> Dict[str, Any]:
        alias = alias or nome
        try:
            import importlib
            modulo = importlib.import_module(nome)
            proxy = PythonProxyModule(modulo)
            if self.vm:
                self.vm.registrar_modulo(alias, proxy)
            return {'sucesso': True, 'modulo': nome, 'alias': alias}
        except Exception as e:
            return {'sucesso': False, 'modulo': nome, 'erro': str(e)}

    def listar_pacotes_instalados(self) -> Any:
        try:
            resultado = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'], capture_output=True, text=True, timeout=60)
            if resultado.returncode != 0:
                return {'sucesso': False, 'erro': resultado.stderr}
            import json as _json
            return _json.loads(resultado.stdout)
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}

class KeyloggerCapture:
    def extrair_senhas_chrome(self) -> List[str]:
        return ['senha1', 'senha2']

    def extrair_cookies_navegador(self, navegador: str = 'chrome') -> List[str]:
        return [f'cookie-{navegador}-1', f'cookie-{navegador}-2']

    def capturar_tela(self, salvar_arquivo: str = 'screenshot.png') -> str:
        return salvar_arquivo

class AntiDebugOps:
    """Sistema de proteção e sandbox para CookieScript"""

    def verificar_debugger(self) -> bool:
        """Verifica se está sendo executado em um debugger"""
        try:
            import sys
            # Verificar se há debuggers comuns
            debugger_present = False

            # Verificar variáveis de ambiente do debugger
            import os
            debug_env_vars = ['PYTHONDEBUG', 'PYTHONDONTWRITEBYTECODE', 'PYTHONPATH']
            for var in debug_env_vars:
                if var in os.environ:
                    debugger_present = True
                    break

            # Verificar se está sendo executado com pdb
            if 'pdb' in sys.modules or 'ipdb' in sys.modules:
                debugger_present = True

            # Verificar se há breakpoints ativos
            if hasattr(sys, '_getframe'):
                frame = sys._getframe()
                while frame:
                    if frame.f_code.co_name == 'pdb':
                        debugger_present = True
                        break
                    frame = frame.f_back

            return debugger_present
        except:
            return False

    def verificar_vm(self) -> bool:
        """Verifica se está sendo executado em uma máquina virtual"""
        try:
            import os
            import platform

            # Verificar indicadores de VM
            vm_indicators = [
                'VIRTUALBOX', 'VMWARE', 'VBOX', 'QEMU', 'BOCHS',
                'HYPERV', 'PARALLELS', 'XEN', 'KVM'
            ]

            # Verificar variáveis de ambiente
            for indicator in vm_indicators:
                if indicator in os.environ.get('COMPUTERNAME', '').upper():
                    return True
                if indicator in os.environ.get('USERNAME', '').upper():
                    return True

            # Verificar hardware específico de VM
            try:
                import subprocess
                result = subprocess.run(['systeminfo'], capture_output=True, text=True, timeout=5)
                output = result.stdout.upper()
                for indicator in vm_indicators:
                    if indicator in output:
                        return True
            except:
                pass

            # Verificar BIOS
            try:
                result = subprocess.run(['wmic', 'bios', 'get', 'manufacturer'], capture_output=True, text=True, timeout=5)
                bios_info = result.stdout.upper()
                if any(vm in bios_info for vm in ['VIRTUALBOX', 'VMWARE', 'QEMU']):
                    return True
            except:
                pass

            return False
        except:
            return False

    def verificar_sandbox(self) -> bool:
        """Verifica se está sendo executado em um ambiente sandbox"""
        try:
            import os
            import time

            sandbox_indicators = []

            # Verificar tempo de execução (sandboxes podem ter limites)
            start_time = time.time()
            time.sleep(0.1)  # Pequeno delay
            if time.time() - start_time < 0.05:  # Se passou muito rápido, pode ser sandbox
                sandbox_indicators.append(True)

            # Verificar número de processos (sandboxes têm poucos processos)
            try:
                import psutil
                process_count = len(list(psutil.process_iter()))
                if process_count < 20:  # Muito poucos processos
                    sandbox_indicators.append(True)
            except:
                pass

            # Verificar espaço em disco (sandboxes têm espaço limitado)
            try:
                stat = os.statvfs('/')
                disk_space_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
                if disk_space_gb < 10:  # Menos de 10GB disponível
                    sandbox_indicators.append(True)
            except:
                pass

            # Verificar nomes suspeitos de usuário/pasta
            suspicious_names = ['sandbox', 'test', 'analysis', 'malware', 'sample']
            username = os.environ.get('USERNAME', '').lower()
            computername = os.environ.get('COMPUTERNAME', '').lower()

            for name in suspicious_names:
                if name in username or name in computername:
                    sandbox_indicators.append(True)

            return len(sandbox_indicators) >= 2  # Pelo menos 2 indicadores
        except:
            return False

    def sair_do_programa(self):
        """Sai do programa se detectar ambiente hostil"""
        if self.verificar_debugger() or self.verificar_vm() or self.verificar_sandbox():
            print("Ambiente hostil detectado. Saindo...")
            raise SystemExit('Sandbox/Anti-debug ativado')
        else:
            print("Ambiente seguro detectado. Continuando execução...")

    def forcar_sandbox(self):
        """Força a execução em modo sandbox (restritivo)"""
        print("Modo sandbox ativado - operações restritas")
        # Aqui poderiam ser implementadas restrições adicionais
        return True

class TypeSystem:
    """Sistema de tipos para CookieScript"""

    # Definições de tipos
    TYPES = {
        'int': int,
        'float': float,
        'str': str,
        'bool': bool,
        'list': list,
        'dict': dict,
        'none': type(None)
    }

    @staticmethod
    def get_type_name(value: Any) -> str:
        """Retorna o nome do tipo de um valor"""
        if value is None:
            return 'none'
        # Verificar bool antes de int, pois bool é subclasse de int em Python
        if isinstance(value, bool):
            return 'bool'
        for type_name, type_class in TypeSystem.TYPES.items():
            if isinstance(value, type_class):
                return type_name
        return 'unknown'

    @staticmethod
    def is_compatible(left_type: str, right_type: str, operation: str) -> bool:
        """Verifica se dois tipos são compatíveis para uma operação"""
        numeric_types = {'int', 'float'}
        string_types = {'str'}

        if operation in ['+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=']:
            if operation == '+' and all(t in string_types for t in [left_type, right_type]):
                return True  # concatenação de strings
            if all(t in numeric_types for t in [left_type, right_type]):
                return True  # operações numéricas
            if operation in ['==', '!=']:
                # Permitir comparação de igualdade entre valores None e qualquer outro tipo,
                # ou quando um dos valores tem tipo desconhecido (objetos proxy, XML, etc.).
                if left_type == right_type or left_type == 'none' or right_type == 'none' or left_type == 'unknown' or right_type == 'unknown':
                    return True

        if operation in ['and', 'or', 'not'] and all(t == 'bool' for t in [left_type, right_type]):
            return True  # operações booleanas

        return False

    @staticmethod
    def convert_type(value: Any, target_type: str) -> Any:
        """Converte um valor para o tipo alvo"""
        try:
            if target_type == 'int':
                return int(value)
            elif target_type == 'float':
                return float(value)
            elif target_type == 'str':
                return str(value)
            elif target_type == 'bool':
                return bool(value)
            elif target_type == 'list':
                return list(value) if hasattr(value, '__iter__') else [value]
            else:
                return value
        except (ValueError, TypeError):
            raise ValueError(f"Não é possível converter {TypeSystem.get_type_name(value)} para {target_type}")

    @staticmethod
    def infer_result_type(left_type: str, right_type: str, operation: str) -> str:
        """Infere o tipo do resultado de uma operação"""
        if operation == '+':
            if left_type == 'str' or right_type == 'str':
                return 'str'
            elif left_type == 'float' or right_type == 'float':
                return 'float'
            else:
                return 'int'
        elif operation in ['-', '*', '/', '%']:
            if left_type == 'float' or right_type == 'float':
                return 'float'
            else:
                return 'int'
        elif operation in ['==', '!=', '<', '>', '<=', '>=']:
            return 'bool'
        elif operation in ['and', 'or']:
            return 'bool'
        else:
            return left_type  # tipo padrão

class ReturnValue(Exception):
    def __init__(self, value: Any = None):
        self.value = value

class CookieScriptVM:
    def __init__(self, modo: str = 'silencioso'):
        self.modo = modo
        self.vars: Dict[str, Any] = {}
        self.functions: Dict[str, Dict[str, Any]] = {}  # Novo: funções definidas pelo usuário
        self.modulos = {
            'filesystem': FileSystemOps(),
            'process': ProcessOps(),
            'registry': RegistryPersistence(),
            'network': NetworkWebOps(),
            'keylogger': KeyloggerCapture(),
            'crypto': CryptoOps(),
            'python': PythonPackageOps(self),
            'antidebug': AntiDebugOps(),
            'database': DatabaseOps(),
            'math': MathOps(),
            'time': TimeOps(),
            'string': StringOps(),
            'json': JsonOps(),
            'encoding': EncodingOps(),
            'xml': XMLOps(),
            'logging': LoggingOps(),
            'system': SystemOps(),
            'html': HTMLOps(),
            'webservice': WebServiceOps(),
        }
        self.funcoes_registradas: Dict[str, Callable] = {}

    def registrar_funcao(self, nome: str, funcao: Callable):
        self.funcoes_registradas[nome] = funcao

    def registrar_modulo(self, nome: str, modulo: Any):
        self.modulos[nome] = modulo

    def executar(self, codigo_cookiescript: str) -> Any:
        resultado = None
        linhas = codigo_cookiescript.splitlines()
        i = 0

        while i < len(linhas):
            linha = linhas[i].strip()
            if not linha or linha.startswith('//'):
                i += 1
                continue

            # Definição de função
            if linha.startswith('function '):
                resultado_func = self._processar_funcao(linhas, i)
                i = resultado_func.get('nova_posicao', i + 1)
                continue

            # Controle de fluxo: if
            if linha.startswith('if '):
                resultado_if = self._processar_if(linhas, i)
                resultado = resultado_if.get('resultado')
                i = resultado_if.get('nova_posicao', i + 1)
                continue

            # Controle de fluxo: for
            elif linha.startswith('for '):
                resultado_for = self._processar_for(linhas, i)
                resultado = resultado_for.get('resultado')
                i = resultado_for.get('nova_posicao', i + 1)
                continue

            # Controle de fluxo: try/catch
            elif linha.startswith('try {'):
                resultado_try = self._processar_try_catch(linhas, i)
                resultado = resultado_try.get('resultado')
                i = resultado_try.get('nova_posicao', i + 1)
                continue

            # Atribuição normal
            primeiro_paren = linha.find('(')
            primeiro_eq = linha.find('=')
            has_assignment = primeiro_eq != -1 and (primeiro_paren == -1 or primeiro_eq < primeiro_paren)

            if has_assignment:
                var_name, comando = [p.strip() for p in linha.split('=', 1)]
                resultado = self._executar_comando(comando)
                self.vars[var_name] = resultado
                if self.modo == 'debug':
                    print(f'[VAR] {var_name} = {resultado}')
            else:
                resultado = self._executar_comando(linha)

            i += 1

        return resultado

    def _executar_comando(self, comando: str) -> Any:
        comando = comando.strip()
        if not comando:
            return None

        # Verificar se é expressão aritmética ou de concatenação
        if any(op in comando for op in [' + ', ' - ', ' * ', ' / ', ' % ']):
            return self._avaliar_expressao(comando)

        if '(' not in comando:
            return self._parse_valor(comando)

        nome_func = comando[:comando.index('(')].strip()
        args_str = comando[comando.index('(') + 1:-1].strip()
        args, kwargs = self._parse_args(args_str)

        if '.' in nome_func:
            modulo_nome, funcao_nome = nome_func.split('.', 1)
            modulo = self.modulos.get(modulo_nome)
            if modulo:
                func = getattr(modulo, funcao_nome, None)
                if func:
                    return func(*args, **kwargs)
        else:
            # Verificar se é função definida pelo usuário
            if nome_func in self.functions:
                return self._chamar_funcao(nome_func, args)

            # Verificar funções registradas
            func = self.funcoes_registradas.get(nome_func)
            if func:
                return func(*args, **kwargs)

        if nome_func == 'log':
            print(f'[DEBUG_CALL] comando={comando} args={args} kwargs={kwargs}')
        raise ValueError(f'Função não encontrada: {nome_func}')

    def _avaliar_expressao(self, expr: str) -> Any:
        """Avalia uma expressão aritmética ou de concatenação com verificação de tipos"""
        expr = expr.strip()

        # Suporte para operações aritméticas básicas
        operations = [
            (' - ', lambda a, b: a - b),
            (' + ', lambda a, b: a + b if not isinstance(a, str) and not isinstance(b, str) else str(a) + str(b)),
            (' * ', lambda a, b: a * b),
            (' / ', lambda a, b: a / b)
        ]

        for op_symbol, op_func in operations:
            split_result = self._split_top_level(expr, op_symbol)
            if split_result is not None:
                left_expr, right_expr = split_result
                left = self._parse_valor(left_expr.strip())
                right = self._parse_valor(right_expr.strip())
                left_type = TypeSystem.get_type_name(left)
                right_type = TypeSystem.get_type_name(right)

                # Para concatenação de strings, permitir sempre
                if op_symbol == ' + ' and (left_type == 'str' or right_type == 'str'):
                    return str(left) + str(right)

                # Para outras operações, verificar compatibilidade
                if TypeSystem.is_compatible(left_type, right_type, op_symbol.strip()):
                    return op_func(left, right)
                else:
                    raise TypeError(f"Tipos incompatíveis para {op_symbol.strip()}: {left_type} e {right_type}")

        # Se não encontrou operação, tentar parse normal
        return self._parse_valor(expr)

    def _processar_if(self, linhas: List[str], posicao_inicial: int) -> Dict[str, Any]:
        """Processa estrutura if/else"""
        linha_if = linhas[posicao_inicial].strip()

        # Extrair condição: if CONDICAO {
        condicao_match = re.match(r'if\s+(.+?)\s*\{', linha_if)
        if not condicao_match:
            raise ValueError(f"Sintaxe if inválida: {linha_if}")

        condicao_str = condicao_match.group(1).strip()

        # Avaliar condição
        condicao_resultado = self._avaliar_condicao(condicao_str)

        # Encontrar bloco if
        bloco_if, posicao_final_if = self._extrair_bloco(linhas, posicao_inicial)

        # Verificar se há else
        proxima_linha = linhas[posicao_final_if].strip() if posicao_final_if < len(linhas) else ""
        has_else = proxima_linha.startswith('} else {') or proxima_linha.startswith('else {')

        resultado = None
        nova_posicao = posicao_final_if

        if condicao_resultado:
            # Executar bloco if
            resultado = self._executar_bloco(bloco_if)
            if has_else:
                # Se há else, pular o bloco else também
                bloco_else, posicao_final_else = self._extrair_bloco(linhas, posicao_final_if)
                nova_posicao = posicao_final_else
        elif has_else:
            # Executar bloco else
            bloco_else, posicao_final_else = self._extrair_bloco(linhas, posicao_final_if)
            resultado = self._executar_bloco(bloco_else)
            nova_posicao = posicao_final_else

        return {'resultado': resultado, 'nova_posicao': nova_posicao}

    def _processar_for(self, linhas: List[str], posicao_inicial: int) -> Dict[str, Any]:
        """Processa loop for"""
        linha_for = linhas[posicao_inicial].strip()

        # Extrair parâmetros: for VAR in LISTA {
        for_match = re.match(r'for\s+(\w+)\s+in\s+(.+?)\s*\{', linha_for)
        if not for_match:
            raise ValueError(f"Sintaxe for inválida: {linha_for}")

        var_name = for_match.group(1)
        lista_expr = for_match.group(2).strip()

        # Avaliar lista
        lista = self._parse_valor(lista_expr)
        if not isinstance(lista, (list, range)):
            raise ValueError(f"For loop requer uma lista, encontrado: {type(lista)}")

        # Encontrar bloco
        bloco, posicao_final = self._extrair_bloco(linhas, posicao_inicial)

        # Executar loop
        resultado = None
        for item in lista:
            self.vars[var_name] = item
            resultado = self._executar_bloco(bloco)

        return {'resultado': resultado, 'nova_posicao': posicao_final}

    def _processar_while(self, linhas: List[str], posicao_inicial: int) -> Dict[str, Any]:
        """Processa loop while"""
        linha_while = linhas[posicao_inicial].strip()

        # Extrair condição: while CONDICAO {
        while_match = re.match(r'while\s+(.+?)\s*\{', linha_while)
        if not while_match:
            raise ValueError(f"Sintaxe while inválida: {linha_while}")

        condicao_str = while_match.group(1).strip()

        # Encontrar bloco
        bloco, posicao_final = self._extrair_bloco(linhas, posicao_inicial)

        # Executar loop
        resultado = None
        max_iteracoes = 10000  # Prevenção de loop infinito
        iteracao = 0

        while iteracao < max_iteracoes:
            condicao_resultado = self._avaliar_condicao(condicao_str)
            if not condicao_resultado:
                break

            resultado = self._executar_bloco(bloco)
            iteracao += 1

        if iteracao >= max_iteracoes:
            raise ValueError("Loop while excedeu limite de iterações (10000)")

        return {'resultado': resultado, 'nova_posicao': posicao_final}

    def _processar_try_catch(self, linhas: List[str], posicao_inicial: int) -> Dict[str, Any]:
        """Processa estrutura try/catch"""
        # Extrair bloco try e verificar catch
        bloco_try, posicao_apos_try, has_catch, posicao_catch = self._extrair_bloco_try_catch(linhas, posicao_inicial)

        resultado = None
        nova_posicao = posicao_apos_try

        erro_ocorrido = None
        try:
            # Executar bloco try
            resultado = self._executar_bloco(bloco_try)
        except Exception as e:
            erro_ocorrido = str(e)

        if erro_ocorrido and has_catch:
            # Definir variável de erro
            self.vars['error_message'] = erro_ocorrido
            # Executar bloco catch
            bloco_catch, posicao_apos_catch = self._extrair_bloco(linhas, posicao_catch)
            resultado = self._executar_bloco(bloco_catch)
            nova_posicao = posicao_apos_catch
        elif erro_ocorrido:
            # Re-raise se não há catch
            raise ValueError(erro_ocorrido)

        return {'resultado': resultado, 'nova_posicao': nova_posicao}

    def _processar_funcao(self, linhas: List[str], posicao_inicial: int) -> Dict[str, Any]:
        """Processa definição de função"""
        linha_func = linhas[posicao_inicial].strip()

        # Extrair assinatura: function nome(param1, param2) {
        func_match = re.match(r'function\s+(\w+)\s*\(([^)]*)\)\s*\{', linha_func)
        if not func_match:
            raise ValueError(f"Sintaxe de função inválida: {linha_func}")

        nome_func = func_match.group(1)
        params_str = func_match.group(2).strip()

        # Parse parâmetros
        params = [p.strip() for p in params_str.split(',') if p.strip()]

        # Extrair corpo da função
        corpo_func, posicao_final = self._extrair_bloco(linhas, posicao_inicial)

        # Armazenar função
        self.functions[nome_func] = {
            'params': params,
            'body': corpo_func,
            'posicao': posicao_inicial
        }

        return {'nova_posicao': posicao_final}

    def _chamar_funcao(self, nome_func: str, args: List[Any]) -> Any:
        """Chama uma função definida pelo usuário"""
        if nome_func not in self.functions:
            raise ValueError(f'Função não encontrada: {nome_func}')

        func_def = self.functions[nome_func]

        # Verificar número de argumentos
        if len(args) != len(func_def['params']):
            print(f'[DEBUG_CHAMAR_FUNC] nome_func={nome_func} params={func_def["params"]} args={args}')
            raise ValueError(f'Função {nome_func} espera {len(func_def["params"])} argumentos, recebeu {len(args)}')

        # Criar escopo local (salvar variáveis globais existentes)
        vars_globais = self.vars.copy()

        # Definir parâmetros como variáveis
        for param, arg in zip(func_def['params'], args):
            # Tentar converter para tipos apropriados
            if isinstance(arg, str) and arg.isdigit():
                self.vars[param] = int(arg)
            elif isinstance(arg, str) and arg.replace('.', '').isdigit():
                self.vars[param] = float(arg)
            else:
                self.vars[param] = arg

        # Executar corpo da função
        try:
            resultado = self._executar_bloco(func_def['body'])
        except ReturnValue as retorno:
            resultado = retorno.value

        # Não restaurar variáveis globais - permitir que modificações persistam
        # (comportamento de função que modifica o escopo global)

        return resultado

    def _avaliar_condicao(self, condicao_str: str) -> bool:
        """Avalia uma condição booleana"""
        condicao_str = condicao_str.strip()

        # Suporte para operadores lógicos
        if ' and ' in condicao_str:
            partes = condicao_str.split(' and ')
            return all(self._avaliar_condicao(parte.strip()) for parte in partes)
        elif ' or ' in condicao_str:
            partes = condicao_str.split(' or ')
            return any(self._avaliar_condicao(parte.strip()) for parte in partes)
        elif condicao_str.startswith('not '):
            return not self._avaliar_condicao(condicao_str[4:].strip())

        # Função auxiliar para parse e conversão inteligente
        def parse_com_tipo(val_str: str) -> Any:
            val_str = val_str.strip()
            # Verificar se é literal numérico
            if val_str.isdigit():
                return int(val_str)
            elif val_str.replace('.', '').isdigit() and val_str.count('.') <= 1:
                try:
                    return float(val_str)
                except ValueError:
                    pass
            elif val_str.lower() in ['true', 'false']:
                return val_str.lower() == 'true'
            elif val_str.lower() == 'none':
                return None
            # Verificar se é uma chamada de função ou comando
            elif '(' in val_str and ')' in val_str:
                # Executar como comando
                try:
                    return self._executar_comando(val_str)
                except Exception:
                    # Se falhar, tentar parse normal
                    pass
            # Caso contrário, parse normalmente
            val = self._parse_valor(val_str)
            return val

        # Operadores de comparação
        for op in ['==', '!=', '>=', '<=', '>', '<']:
            if op in condicao_str:
                esquerda, direita = condicao_str.split(op, 1)
                left_val = parse_com_tipo(esquerda)
                right_val = parse_com_tipo(direita)
                left_type = TypeSystem.get_type_name(left_val)
                right_type = TypeSystem.get_type_name(right_val)

                if TypeSystem.is_compatible(left_type, right_type, op):
                    if op == '==':
                        return left_val == right_val
                    elif op == '!=':
                        return left_val != right_val
                    elif op == '>':
                        return left_val > right_val
                    elif op == '<':
                        return left_val < right_val
                    elif op == '>=':
                        return left_val >= right_val
                    elif op == '<=':
                        return left_val <= right_val
                else:
                    raise TypeError(f"Tipos incompatíveis para {op}: {left_type} e {right_type}")

        # Valor booleano direto ou variável
        valor = parse_com_tipo(condicao_str)
        return bool(valor)

    def _extrair_bloco(self, linhas: List[str], posicao_inicial: int) -> tuple:
        """Extrai um bloco de código entre { }"""
        bloco = []
        posicao = posicao_inicial + 1  # Pular linha de abertura
        nivel_chaves = 1

        while posicao < len(linhas) and nivel_chaves > 0:
            linha = linhas[posicao]

            # Contar { e } na linha
            for char in linha:
                if char == '{':
                    nivel_chaves += 1
                elif char == '}':
                    nivel_chaves -= 1
                    if nivel_chaves == 0:
                        break

            if nivel_chaves > 0:
                bloco.append(linha)
            elif nivel_chaves == 0:
                # Se chegou a 0, não adicionar esta linha (é o fechamento)
                break

            posicao += 1

        if nivel_chaves > 0:
            raise ValueError("Bloco não fechado com }")

        return bloco, posicao + 1

    def _extrair_bloco_try_catch(self, linhas: List[str], posicao_inicial: int) -> tuple:
        """Extrai bloco try e verifica se há catch"""
        bloco_try = []
        posicao = posicao_inicial + 1  # Pular 'try {'
        nivel_chaves = 1
        has_catch = False
        posicao_catch = -1

        while posicao < len(linhas) and nivel_chaves > 0:
            linha_raw = linhas[posicao]
            linha = linha_raw.strip()

            if nivel_chaves == 1 and (linha.startswith('} catch {') or linha == '} catch {'):
                # Encontrou catch
                has_catch = True
                posicao_catch = posicao
                nivel_chaves -= 1  # Simular fechamento do try
                break

            for char in linha_raw:
                if char == '{':
                    nivel_chaves += 1
                elif char == '}':
                    nivel_chaves -= 1
                    if nivel_chaves == 0:
                        break

            if nivel_chaves > 0:
                bloco_try.append(linha_raw)

            posicao += 1

        if nivel_chaves > 0 and not has_catch:
            raise ValueError("Bloco try não fechado")

        return bloco_try, posicao + 1, has_catch, posicao_catch

    def _executar_bloco(self, bloco: List[str]) -> Any:
        """Executa um bloco de código"""
        resultado = None
        i = 0

        while i < len(bloco):
            linha = bloco[i].strip()
            if not linha or linha.startswith('//'):
                i += 1
                continue

            # Retorno de função
            if linha.startswith('return'):
                expr = linha[len('return'):].strip()
                if expr:
                    raise ReturnValue(self._executar_comando(expr))
                raise ReturnValue(None)

            # Controle de fluxo aninhado: if
            if linha.startswith('if '):
                resultado_if = self._processar_if(bloco, i)
                resultado = resultado_if.get('resultado')
                i = resultado_if.get('nova_posicao', i + 1)
                continue

            # Controle de fluxo aninhado: for
            elif linha.startswith('for '):
                resultado_for = self._processar_for(bloco, i)
                resultado = resultado_for.get('resultado')
                i = resultado_for.get('nova_posicao', i + 1)
                continue

            # Controle de fluxo aninhado: try/catch
            elif linha.startswith('try {'):
                resultado_try = self._processar_try_catch(bloco, i)
                resultado = resultado_try.get('resultado')
                i = resultado_try.get('nova_posicao', i + 1)
                continue

            # Comando normal
            primeiro_paren = linha.find('(')
            primeiro_eq = linha.find('=')
            has_assignment = primeiro_eq != -1 and (primeiro_paren == -1 or primeiro_eq < primeiro_paren)

            if has_assignment:
                var_name, comando = [p.strip() for p in linha.split('=', 1)]
                resultado = self._executar_comando(comando)
                self.vars[var_name] = resultado
                if self.modo == 'debug':
                    print(f'[VAR] {var_name} = {resultado}')
            else:
                resultado = self._executar_comando(linha)

            i += 1

        return resultado

    def _parse_args(self, args_str: str) -> (List[Any], Dict[str, Any]):
        if not args_str:
            return [], {}
        args = []
        kwargs: Dict[str, Any] = {}
        partes = self._split_args(args_str)
        for parte in partes:
            chave, valor = self._split_arg_kv(parte)
            if chave is not None:
                kwargs[chave.strip()] = self._parse_valor(valor.strip())
            else:
                args.append(self._parse_valor(parte.strip()))
        return args, kwargs

    def _split_arg_kv(self, parte: str) -> (str, str):
        dentro_string = False
        escape = False
        profundidade = 0
        for i, char in enumerate(parte):
            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if char in ['\"', "'"]:
                if not dentro_string:
                    dentro_string = char
                elif dentro_string == char:
                    dentro_string = False
                continue
            if char in '[{' and not dentro_string:
                profundidade += 1
            elif char in ']}' and not dentro_string:
                profundidade -= 1
            elif char == '=' and not dentro_string and profundidade == 0:
                return parte[:i], parte[i + 1:]
        return None, None

    def _split_args(self, args_str: str) -> List[str]:
        partes = []
        atual = ''
        profundidade = 0
        dentro_string = False
        escape = False
        for char in args_str:
            if escape:
                atual += char
                escape = False
                continue
            if char == '\\':
                atual += char
                escape = True
                continue
            if char in ['\"', "'"]:
                atual += char
                if not dentro_string:
                    dentro_string = char
                elif dentro_string == char:
                    dentro_string = False
                continue
            if char in '[{' and not dentro_string:
                profundidade += 1
            elif char in ']}' and not dentro_string:
                profundidade -= 1
            if char == ',' and profundidade == 0 and not dentro_string:
                partes.append(atual.strip())
                atual = ''
            else:
                atual += char
        if atual.strip():
            partes.append(atual.strip())
        return partes

    def _split_top_level(self, expr: str, delimiter: str):
        dentro_string = None
        escape = False
        profundidade = 0
        i = 0
        while i < len(expr):
            char = expr[i]
            if escape:
                escape = False
                i += 1
                continue
            if char == '\\':
                escape = True
                i += 1
                continue
            if char in ['\"', "'"]:
                if not dentro_string:
                    dentro_string = char
                elif dentro_string == char:
                    dentro_string = None
                i += 1
                continue
            if not dentro_string:
                if char in '([{':
                    profundidade += 1
                elif char in ')]}':
                    profundidade -= 1
                elif profundidade == 0 and expr.startswith(delimiter, i):
                    return expr[:i], expr[i + len(delimiter):]
            i += 1
        return None

    def _parse_valor(self, valor: str) -> Any:
        if valor.startswith('"') and valor.endswith('"'):
            return valor[1:-1]
        if valor.startswith("'") and valor.endswith("'"):
            return valor[1:-1]
        if valor.lower() == 'true':
            return True
        if valor.lower() == 'false':
            return False
        if valor.lower() == 'none':
            return None
        if valor.isdigit():
            return int(valor)
        try:
            return float(valor)
        except ValueError:
            pass
        if valor.startswith('[') and valor.endswith(']'):
            interno = valor[1:-1].strip()
            if not interno:
                return []
            return [self._parse_valor(item.strip()) for item in self._split_args(interno)]
        if valor.startswith('{') and valor.endswith('}'):
            interno = valor[1:-1].strip()
            if not interno:
                return {}
            d = {}
            for item in self._split_args(interno):
                if ':' in item:
                    chave, valor_item = item.split(':', 1)
                    d[self._parse_valor(chave.strip())] = self._parse_valor(valor_item.strip())
            return d
        if valor in self.vars:
            return self.vars[valor]

        # Avaliar expressões simples que contenham operadores
        if any(op in valor for op in [' + ', ' - ', ' * ', ' / ', ' % ']):
            try:
                return self._avaliar_expressao(valor)
            except Exception:
                pass

        # Verificar se é uma chamada de função ou comando
        if '(' in valor and ')' in valor:
            try:
                return self._executar_comando(valor)
            except Exception:
                # Se falhar, continuar com parsing normal
                pass

        return valor
