# cookiescript/time.py
import time
import datetime
from typing import Dict, Any

class TimeOps:
    """Operações de data e hora"""

    def timestamp_atual(self) -> float:
        """Retorna timestamp atual em segundos"""
        return time.time()

    def data_hora_atual(self) -> str:
        """Retorna data e hora atual formatada"""
        return datetime.datetime.now().isoformat()

    def formatar_data(self, timestamp: float, formato: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Formata timestamp para string"""
        return datetime.datetime.fromtimestamp(timestamp).strftime(formato)

    def parse_data(self, data_str: str, formato: str = "%Y-%m-%d %H:%M:%S") -> float:
        """Converte string de data para timestamp"""
        dt = datetime.datetime.strptime(data_str, formato)
        return dt.timestamp()

    def diferenca_datas(self, timestamp1: float, timestamp2: float) -> Dict[str, Any]:
        """Calcula diferença entre duas datas"""
        dt1 = datetime.datetime.fromtimestamp(timestamp1)
        dt2 = datetime.datetime.fromtimestamp(timestamp2)
        diff = dt2 - dt1

        return {
            "dias": diff.days,
            "segundos": diff.seconds,
            "total_segundos": diff.total_seconds()
        }

    def adicionar_dias(self, timestamp: float, dias: int) -> float:
        """Adiciona dias a um timestamp"""
        dt = datetime.datetime.fromtimestamp(timestamp)
        nova_data = dt + datetime.timedelta(days=dias)
        return nova_data.timestamp()

    def dia_da_semana(self, timestamp: float) -> str:
        """Retorna o dia da semana"""
        dt = datetime.datetime.fromtimestamp(timestamp)
        dias = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
        return dias[dt.weekday()]

    def dormir(self, segundos: float) -> str:
        """Pausa execução por N segundos"""
        time.sleep(segundos)
        return f"Dormiu por {segundos} segundos"

    def cronometro(self) -> Dict[str, Any]:
        """Retorna informações de performance"""
        return {
            "cpu_time": time.process_time(),
            "wall_time": time.time()
        }