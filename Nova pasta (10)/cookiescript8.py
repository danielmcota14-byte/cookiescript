# cookiescript/utils.py
import re
import json
import base64
from typing import List, Dict, Any, Union

class StringOps:
    """Operações com strings"""

    def substituir(self, texto: str, padrao: str, substituicao: str) -> str:
        """Substitui ocorrências de um padrão em uma string"""
        return texto.replace(padrao, substituicao)

    def dividir(self, texto: str, separador: str = " ") -> List[str]:
        """Divide uma string em lista"""
        return texto.split(separador)

    def juntar(self, lista: List[str], separador: str = " ") -> str:
        """Junta lista de strings em uma string"""
        return separador.join(str(item) for item in lista)

    def maiusculo(self, texto: str) -> str:
        """Converte para maiúsculo"""
        return texto.upper()

    def minusculo(self, texto: str) -> str:
        """Converte para minúsculo"""
        return texto.lower()

    def capitalizar(self, texto: str) -> str:
        """Capitaliza primeira letra de cada palavra"""
        return texto.title()

    def comprimento(self, texto: str) -> int:
        """Retorna comprimento da string"""
        return len(texto)

    def contem(self, texto: str, substring: str) -> bool:
        """Verifica se string contém substring"""
        return substring in texto

    def regex_substituir(self, texto: str, padrao: str, substituicao: str) -> str:
        """Substitui usando regex"""
        return re.sub(padrao, substituicao, texto)

    def regex_encontrar(self, texto: str, padrao: str) -> List[str]:
        """Encontra todas as ocorrências de um padrão regex"""
        return re.findall(padrao, texto)

class JsonOps:
    """Operações com JSON"""

    def parse_json(self, texto: str) -> Union[Dict[str, Any], List[Any]]:
        """Converte string JSON para objeto"""
        return json.loads(texto)

    def stringify_json(self, objeto: Union[Dict[str, Any], List[Any]]) -> str:
        """Converte objeto para string JSON"""
        return json.dumps(objeto, indent=2, ensure_ascii=False)

class EncodingOps:
    """Operações de codificação"""

    def base64_encode(self, texto: str) -> str:
        """Codifica string em base64"""
        return base64.b64encode(texto.encode('utf-8')).decode('utf-8')

    def base64_decode(self, texto: str) -> str:
        """Decodifica string de base64"""
        return base64.b64decode(texto).decode('utf-8')

    def url_encode(self, texto: str) -> str:
        """Codifica para URL"""
        from urllib.parse import quote
        return quote(texto)

    def numero_para_texto(self, numero: Union[int, float]) -> str:
        """Converte número para string"""
        return str(numero)