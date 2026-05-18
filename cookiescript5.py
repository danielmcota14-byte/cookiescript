# cookiescript/math.py
import math
import random
from typing import List, Union

class MathOps:
    """Operações matemáticas avançadas"""

    def seno(self, angulo: float) -> float:
        """Calcula seno de um ângulo em radianos"""
        return math.sin(angulo)

    def cosseno(self, angulo: float) -> float:
        """Calcula cosseno de um ângulo em radianos"""
        return math.cos(angulo)

    def tangente(self, angulo: float) -> float:
        """Calcula tangente de um ângulo em radianos"""
        return math.tan(angulo)

    def logaritmo(self, valor: float, base: float = math.e) -> float:
        """Calcula logaritmo de um valor"""
        return math.log(valor, base)

    def potencia(self, base: float, expoente: float) -> float:
        """Calcula potência"""
        return math.pow(base, expoente)

    def raiz_quadrada(self, valor: float) -> float:
        """Calcula raiz quadrada"""
        return math.sqrt(valor)

    def numero_aleatorio(self, minimo: float = 0.0, maximo: float = 1.0) -> float:
        """Gera número aleatório entre mínimo e máximo"""
        return random.uniform(minimo, maximo)

    def arredondar(self, valor: float, casas_decimais: int = 0) -> float:
        """Arredonda um número"""
        return round(valor, casas_decimais)

    def fatorial(self, n: int) -> int:
        """Calcula fatorial de n"""
        return math.factorial(n)

    def media(self, valores: List[Union[int, float]]) -> float:
        """Calcula média de uma lista de valores"""
        return sum(valores) / len(valores) if valores else 0.0

    def somar(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Soma dois números"""
        return a + b

    def subtrair(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Subtrai dois números"""
        return a - b

    def multiplicar(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Multiplica dois números"""
        return a * b

    def dividir(self, a: Union[int, float], b: Union[int, float]) -> float:
        """Divide dois números"""
        if b == 0:
            raise ValueError("Divisão por zero")
        return a / b

    def modulo(self, a: int, b: int) -> int:
        """Calcula o módulo (resto da divisão)"""
        return a % b