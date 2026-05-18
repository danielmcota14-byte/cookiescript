from cookiescript_vm import CookieScriptVM
import traceback

orig_exec = CookieScriptVM._executar_comando
orig_chamar = CookieScriptVM._chamar_funcao

def exec_wrapped(self, comando):
    print('EXEC_CMD:', repr(comando))
    return orig_exec(self, comando)

def chamar_wrapped(self, nome_func, args):
    print('CALL FUNC', nome_func, 'ARGS', args)
    return orig_chamar(self, nome_func, args)

CookieScriptVM._executar_comando = exec_wrapped
CookieScriptVM._chamar_funcao = chamar_wrapped

cs = CookieScriptVM(modo='debug')
cs.registrar_funcao('notificar_telegram', lambda mensagem='': print('NOTIFICAR:', mensagem))
cs.registrar_funcao('ler_entrada', lambda prompt='': 'sair')
cs.registrar_funcao('para_inteiro', lambda valor='': int(valor) if str(valor).isdigit() else 0)
with open('jogo.cookiescript','r',encoding='utf-8') as f:
    codigo = f.read()
try:
    cs.executar(codigo)
except Exception as e:
    print('ERROR', e)
    traceback.print_exc()
