# cookiescript/system.py
import platform
import socket
import getpass
from typing import Dict, Any

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class SystemOps:
    """Operações de informações do sistema"""

    def info_sistema(self) -> Dict[str, Any]:
        """Retorna informações gerais do sistema"""
        return {
            "sistema_operacional": platform.system(),
            "versao": platform.version(),
            "arquitetura": platform.architecture(),
            "processador": platform.processor(),
            "hostname": socket.gethostname(),
            "usuario": getpass.getuser()
        }

    def info_memoria(self) -> Dict[str, Any]:
        """Retorna informações de memória"""
        if not PSUTIL_AVAILABLE:
            return {"erro": "psutil não instalado"}
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "disponivel": mem.available,
            "usada": mem.used,
            "percentual": mem.percent
        }

    def info_cpu(self) -> Dict[str, Any]:
        """Retorna informações da CPU"""
        if not PSUTIL_AVAILABLE:
            return {"erro": "psutil não instalado"}
        return {
            "nucleos_fisicos": psutil.cpu_count(logical=False),
            "nucleos_logicos": psutil.cpu_count(logical=True),
            "frequencia": psutil.cpu_freq().current if psutil.cpu_freq() else None,
            "uso_percentual": psutil.cpu_percent(interval=1)
        }

    def info_disco(self) -> Dict[str, Any]:
        """Retorna informações do disco"""
        if not PSUTIL_AVAILABLE:
            return {"erro": "psutil não instalado"}
        disco = psutil.disk_usage('/')
        return {
            "total": disco.total,
            "usado": disco.used,
            "livre": disco.free,
            "percentual": disco.percent
        }

    def processos_ativos(self, limite: int = 10) -> list:
        """Retorna lista dos processos mais ativos"""
        if not PSUTIL_AVAILABLE:
            return [{"erro": "psutil não instalado"}]
        processos = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                processos.append({
                    "pid": info['pid'],
                    "nome": info['name'],
                    "cpu": info['cpu_percent'],
                    "memoria": info['memory_percent']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Ordena por uso de CPU
        processos.sort(key=lambda x: x['cpu'], reverse=True)
        return processos[:limite]

    def endereco_ip(self) -> str:
        """Retorna endereço IP local"""
        try:
            # Conecta a um servidor externo para obter IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def info_rede(self) -> Dict[str, Any]:
        """Retorna informações de rede"""
        if not PSUTIL_AVAILABLE:
            return {"erro": "psutil não instalado"}
        net = psutil.net_io_counters()
        return {
            "bytes_enviados": net.bytes_sent,
            "bytes_recebidos": net.bytes_recv,
            "pacotes_enviados": net.packets_sent,
            "pacotes_recebidos": net.packets_recv
        }