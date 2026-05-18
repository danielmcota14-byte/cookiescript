# cookiescript/logging.py
import logging
import os
from datetime import datetime
from typing import Optional

class LoggingOps:
    """Operações de logging"""

    def __init__(self):
        self.loggers = {}

    def criar_logger(self, nome: str, arquivo: Optional[str] = None, nivel: str = "INFO") -> str:
        """Cria um logger com arquivo opcional"""
        if nome in self.loggers:
            return f"Logger '{nome}' já existe"

        logger = logging.getLogger(nome)

        # Define nível
        niveis = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        logger.setLevel(niveis.get(nivel.upper(), logging.INFO))

        # Remove handlers existentes
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Handler para arquivo se especificado
        if arquivo:
            # Cria diretório se não existir
            dir_path = os.path.dirname(arquivo)
            if dir_path:  # Só cria se houver um diretório no caminho
                os.makedirs(dir_path, exist_ok=True)
            file_handler = logging.FileHandler(arquivo, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        self.loggers[nome] = logger
        return f"Logger '{nome}' criado com sucesso"

    def log_debug(self, nome_logger: str, mensagem: str) -> str:
        """Registra mensagem de debug"""
        if nome_logger in self.loggers:
            self.loggers[nome_logger].debug(mensagem)
            return "Debug logged"
        return f"Logger '{nome_logger}' não encontrado"

    def log_info(self, nome_logger: str, mensagem: str) -> str:
        """Registra mensagem de info"""
        if nome_logger in self.loggers:
            self.loggers[nome_logger].info(mensagem)
            return "Info logged"
        return f"Logger '{nome_logger}' não encontrado"

    def log_warning(self, nome_logger: str, mensagem: str) -> str:
        """Registra mensagem de warning"""
        if nome_logger in self.loggers:
            self.loggers[nome_logger].warning(mensagem)
            return "Warning logged"
        return f"Logger '{nome_logger}' não encontrado"

    def log_error(self, nome_logger: str, mensagem: str) -> str:
        """Registra mensagem de error"""
        if nome_logger in self.loggers:
            self.loggers[nome_logger].error(mensagem)
            return "Error logged"
        return f"Logger '{nome_logger}' não encontrado"

    def log_critical(self, nome_logger: str, mensagem: str) -> str:
        """Registra mensagem crítica"""
        if nome_logger in self.loggers:
            self.loggers[nome_logger].critical(mensagem)
            return "Critical logged"
        return f"Logger '{nome_logger}' não encontrado"

    def fechar_logger(self, nome: str) -> str:
        """Fecha um logger"""
        if nome in self.loggers:
            for handler in self.loggers[nome].handlers[:]:
                handler.close()
                self.loggers[nome].removeHandler(handler)
            del self.loggers[nome]
            return f"Logger '{nome}' fechado"
        return f"Logger '{nome}' não encontrado"