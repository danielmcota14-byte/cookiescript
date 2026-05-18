#!/usr/bin/env python3
"""
Testes automatizados para CookieScript VM
Executa testes unitários e de integração
"""

import unittest
import sys
import os
from pathlib import Path

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cookiescript_vm import CookieScriptVM, TypeSystem

class TestCookieScriptVM(unittest.TestCase):
    """Testes para a VM do CookieScript"""

    def setUp(self):
        """Configura o ambiente de teste"""
        self.vm = CookieScriptVM()

    def test_tipo_sistema_basico(self):
        """Testa o sistema de tipos básico"""
        # Testes de tipos
        self.assertEqual(TypeSystem.get_type_name(42), 'int')
        self.assertEqual(TypeSystem.get_type_name(3.14), 'float')
        self.assertEqual(TypeSystem.get_type_name("hello"), 'str')
        self.assertEqual(TypeSystem.get_type_name(True), 'bool')
        self.assertEqual(TypeSystem.get_type_name([1, 2, 3]), 'list')
        self.assertEqual(TypeSystem.get_type_name({'a': 1}), 'dict')

    def test_compatibilidade_tipos(self):
        """Testa compatibilidade de tipos"""
        # Operações válidas
        self.assertTrue(TypeSystem.is_compatible('int', 'int', '+'))
        self.assertTrue(TypeSystem.is_compatible('float', 'float', '+'))
        self.assertTrue(TypeSystem.is_compatible('str', 'str', '+'))
        self.assertTrue(TypeSystem.is_compatible('int', 'float', '=='))

        # Operações inválidas
        self.assertFalse(TypeSystem.is_compatible('int', 'list', '+'))
        self.assertFalse(TypeSystem.is_compatible('str', 'dict', '-'))

    def test_parse_valor(self):
        """Testa parsing de valores"""
        vm = CookieScriptVM()

        # Literais
        self.assertEqual(vm._parse_valor('42'), 42)
        self.assertEqual(vm._parse_valor('3.14'), 3.14)
        self.assertEqual(vm._parse_valor('"hello"'), 'hello')
        self.assertEqual(vm._parse_valor('true'), True)
        self.assertEqual(vm._parse_valor('false'), False)

        # Listas
        self.assertEqual(vm._parse_valor('[1, 2, 3]'), [1, 2, 3])

        # Dicionários
        expected = {'a': 1, 'b': 2}
        self.assertEqual(vm._parse_valor('{"a": 1, "b": 2}'), expected)

    def test_execucao_comandos(self):
        """Testa execução de comandos básicos"""
        vm = CookieScriptVM()

        # Atribuição
        result = vm._executar_comando('42')
        self.assertEqual(result, 42)

        # Chamada de função
        result = vm._executar_comando('math.somar(2, 3)')
        self.assertEqual(result, 5)

    def test_condicoes(self):
        """Testa avaliação de condições"""
        vm = CookieScriptVM()

        # Condições simples
        self.assertTrue(vm._avaliar_condicao('5 > 3'))
        self.assertFalse(vm._avaliar_condicao('5 < 3'))
        self.assertTrue(vm._avaliar_condicao('"hello" == "hello"'))

        # Condições com funções
        vm.vars['num'] = 4
        self.assertTrue(vm._avaliar_condicao('math.modulo(num, 2) == 0'))

    def test_expressoes_aritmeticas(self):
        """Testa expressões aritméticas"""
        vm = CookieScriptVM()

        # Expressões básicas
        self.assertEqual(vm._avaliar_expressao('2 + 3'), 5)
        self.assertEqual(vm._avaliar_expressao('10 - 4'), 6)
        self.assertEqual(vm._avaliar_expressao('3 * 4'), 12)
        self.assertEqual(vm._avaliar_expressao('8 / 2'), 4.0)

        # Concatenação de strings
        self.assertEqual(vm._avaliar_expressao('"hello" + " world"'), 'hello world')

    def test_sistema_sandbox(self):
        """Testa o sistema de sandbox/anti-debug"""
        vm = CookieScriptVM()

        # Métodos devem retornar booleanos
        self.assertIsInstance(vm.modulos['antidebug'].verificar_debugger(), bool)
        self.assertIsInstance(vm.modulos['antidebug'].verificar_vm(), bool)
        self.assertIsInstance(vm.modulos['antidebug'].verificar_sandbox(), bool)

    def test_arquivos(self):
        """Testa operações com arquivos"""
        vm = CookieScriptVM()

        # Teste de escrita (modo write)
        result = vm._executar_comando('filesystem.escrever_arquivo("teste.txt", "conteudo", "w")')
        self.assertIsInstance(result, str)

        # Teste de leitura
        vm._executar_comando('filesystem.escrever_arquivo("teste_leitura.txt", "teste", "w")')
        result = vm._executar_comando('filesystem.ler_arquivo("teste_leitura.txt")')
        self.assertEqual(result, 'teste')

        # Limpeza
        vm._executar_comando('filesystem.deletar_arquivo("teste.txt")')
        vm._executar_comando('filesystem.deletar_arquivo("teste_leitura.txt")')

class TestIntegracao(unittest.TestCase):
    """Testes de integração"""

    def test_script_completo(self):
        """Testa execução de script completo"""
        vm = CookieScriptVM()

        script = '''
        numero = 42
        dobro = math.multiplicar(numero, 2)
        texto = "Resultado: " + encoding.numero_para_texto(dobro)
        '''

        resultado = vm.executar(script)
        self.assertIsNotNone(resultado)

        # Verificar se variáveis foram definidas
        self.assertEqual(vm.vars['numero'], 42)
        self.assertEqual(vm.vars['dobro'], 84)
        self.assertIn('Resultado: 84', vm.vars['texto'])

    def test_fluxo_controle(self):
        """Testa estruturas de controle"""
        vm = CookieScriptVM()

        script = '''
        x = 10
        if x > 5 {
            resultado = "maior"
        }
        else {
            resultado = "menor"
        }
        '''

        vm.executar(script)
        self.assertEqual(vm.vars['resultado'], 'maior')

    def test_funcoes_usuario(self):
        """Testa funções definidas pelo usuário"""
        vm = CookieScriptVM()

        script = '''
        function dobro(n) {
            resultado = math.multiplicar(n, 2)
        }

        dobro(5)
        '''

        vm.executar(script)
        self.assertEqual(vm.vars['resultado'], 10)

class TestPerformance(unittest.TestCase):
    """Testes de performance"""

    def test_performance_expressoes(self):
        """Testa performance de expressões"""
        import time

        vm = CookieScriptVM()

        # Teste de performance com muitas operações
        start_time = time.time()
        for i in range(1000):
            vm._avaliar_expressao('2 + 3 * 4')
        end_time = time.time()

        # Deve executar em menos de 1 segundo
        self.assertLess(end_time - start_time, 1.0)

def run_benchmark():
    """Executa benchmark de performance"""
    import time

    print("🚀 Executando benchmark de performance...")

    vm = CookieScriptVM()

    # Benchmark 1: Expressões aritméticas
    print("\n📊 Benchmark: Expressões aritméticas")
    start_time = time.time()
    for i in range(10000):
        vm._avaliar_expressao('2 + 3 * 4 - 1 / 2')
    end_time = time.time()
    print(".4f")

    # Benchmark 2: Chamadas de função
    print("\n📊 Benchmark: Chamadas de função")
    start_time = time.time()
    for i in range(5000):
        vm._executar_comando('math.somar(2, 3)')
    end_time = time.time()
    print(".4f")

    # Benchmark 3: Script completo
    print("\n📊 Benchmark: Execução de script")
    script = '''
    contador = 0
    while contador < 1000 {
        contador = math.somar(contador, 1)
    }
    '''
    start_time = time.time()
    vm.executar(script)
    end_time = time.time()
    print(".4f")

    print("\n✅ Benchmark concluído!")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'benchmark':
        run_benchmark()
    else:
        # Executar testes unitários
        unittest.main(verbosity=2)