from cookiescript_vm import CookieScriptVM
from pathlib import Path
code = Path('jogo.cookiescript').read_text(encoding='utf-8')
lines = code.splitlines()
for i,line in enumerate(lines):
    if line.strip().startswith('try {'):
        print('try at', i, repr(line))
        cs = CookieScriptVM()
        bloco_try,pos_apos_try,has_catch,pos_catch = cs._extrair_bloco_try_catch(lines, i)
        print('pos_apos_try',pos_apos_try,'has_catch',has_catch,'pos_catch',pos_catch)
        print('bloco_try lines:', bloco_try)
        if has_catch:
            bloco_catch,pos_apos_catch = cs._extrair_bloco(lines,pos_catch)
            print('catch block lines:', bloco_catch)
        break
