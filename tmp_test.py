from cookiescript_vm import CookieScriptVM

cs = CookieScriptVM(modo='debug')
cs.registrar_funcao('notificar_telegram', lambda mensagem='': print('OUT:', repr(mensagem)))
cs.registrar_funcao('ler_entrada', lambda prompt='': 'sair')
cs.registrar_funcao('para_inteiro', lambda valor='': int(valor) if str(valor).isdigit() else 0)

codigo = '''python.importar_modulo(nome="os", alias="pyos")
newline = pyos.linesep
mapa_linhas = ["a", "b"]
xml_mapa = string.juntar(mapa_linhas, newline)
notificar_telegram(mensagem=xml_mapa)
'''

cs.executar(codigo)
