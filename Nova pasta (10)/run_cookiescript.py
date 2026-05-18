import sys
from cookiescript_vm import CookieScriptVM


def notificar_telegram(mensagem: str = ''):
    print(f'[NOTIFICAÇÃO] {mensagem}')


def ler_entrada(prompt: str = '') -> str:
    try:
        return input(prompt)
    except EOFError:
        return ''


def para_inteiro(valor: str = '') -> int:
    try:
        return int(valor)
    except ValueError:
        return 0


def carregar_codigo_do_arquivo(caminho: str) -> str:
    with open(caminho, 'r', encoding='utf-8') as f:
        return f.read()


def localizar_arquivo_cookie(arquivo: str) -> str:
    caminhos_possiveis = [arquivo]
    if not arquivo.lower().endswith('.cookie') and not arquivo.lower().endswith('.cookiescript'):
        caminhos_possiveis.append(f'{arquivo}.cookie')
        caminhos_possiveis.append(f'{arquivo}.cookiescript')

    for caminho in caminhos_possiveis:
        try:
            with open(caminho, 'r', encoding='utf-8'):
                return caminho
        except FileNotFoundError:
            continue
    raise FileNotFoundError(f'Não foi possível encontrar o arquivo: {arquivo}')

if __name__ == '__main__':
    cs = CookieScriptVM(modo='debug')
    cs.registrar_funcao('notificar_telegram', notificar_telegram)
    cs.registrar_funcao('ler_entrada', ler_entrada)
    cs.registrar_funcao('para_inteiro', para_inteiro)

    if len(sys.argv) > 1:
        arquivo = sys.argv[1]
        arquivo = localizar_arquivo_cookie(arquivo)
        codigo = carregar_codigo_do_arquivo(arquivo)
        print(f'Executando CookieScript de: {arquivo}')
    else:
        arquivo = input('Digite o caminho do arquivo CookieScript (.cookie ou .cookiescript) ou ENTER para usar o exemplo: ').strip()
        if arquivo:
            arquivo = localizar_arquivo_cookie(arquivo)
            codigo = carregar_codigo_do_arquivo(arquivo)
            print(f'Executando CookieScript de: {arquivo}')
        else:
            codigo = '''
// Exemplo CookieScript funcional
filesystem.escrever_arquivo(caminho="output.txt", conteudo="CookieScript executado com sucesso")
notificar_telegram(mensagem="CookieScript rodou e escreveu output.txt")
resultado_http = network.http_request(url="https://httpbin.org/get", metodo="GET")
notificar_telegram(mensagem="HTTP request concluída")
'''
            print('Executando CookieScript embutido de exemplo...')

    cs.executar(codigo)
    print('Finalizado.')
