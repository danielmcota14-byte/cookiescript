import os
import re
from typing import Optional

TRANSFORMERS_AVAILABLE = False
torch = None
AutoModelForCausalLM = None
AutoTokenizer = None


def _try_import_transformers():
    global TRANSFORMERS_AVAILABLE, torch, AutoModelForCausalLM, AutoTokenizer
    if TRANSFORMERS_AVAILABLE:
        return True
    try:
        import torch as _torch
        from transformers import AutoModelForCausalLM as _AMFC, AutoTokenizer as _AT
        torch = _torch
        AutoModelForCausalLM = _AMFC
        AutoTokenizer = _AT
        TRANSFORMERS_AVAILABLE = True
        return True
    except ImportError:
        return False


class CookieAIGenerator:
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-ai/deepseek-coder-1.3b-base')
    DEEPSEEK_USE_CPU = os.getenv('DEEPSEEK_USE_CPU', '1').lower() in ('1', 'true', 'yes')

    def __init__(self):
        self._deepseek_tokenizer = None
        self._deepseek_model = None
        self._model_loaded = False

    # ── público ───────────────────────────────────────────────────────────────

    def responder(self, pergunta: str) -> str:
        pergunta = pergunta.strip()
        if not pergunta:
            return 'Por favor, faça uma pergunta.'
        if self._is_model_available():
            r = self._gerar_com_deepseek(pergunta, mode='chat')
            if r:
                return r
        return self._fallback_resposta(pergunta)

    def gerar_codigo(self, prompt: str, language: str = 'cookiescript') -> str:
        prompt = prompt.strip()
        language = (language or 'cookiescript').lower().strip()
        if prompt and self._is_model_available():
            r = self._gerar_com_deepseek(prompt, language, mode='code')
            if r:
                return r
        if language == 'python':
            return self._gerar_python(prompt)
        if language in ('js', 'javascript', 'node'):
            return self._gerar_javascript(prompt)
        p = prompt.lower()
        if not p:
            return self._exemplo_basico()
        if 'abrir arquivo' in p or 'ler arquivo' in p:
            return self._gerar_abrir_arquivo(p)
        if 'escrever arquivo' in p or 'salvar arquivo' in p:
            return self._gerar_escrever_arquivo(p)
        if 'http' in p or 'request' in p or 'api' in p:
            return self._gerar_requisicao_http(p)
        if 'json' in p:
            return self._gerar_json(p)
        if 'loop' in p or 'repetir' in p or 'for' in p:
            return self._gerar_loop(p)
        if 'função' in p or 'function' in p:
            return self._gerar_funcao(p)
        return self._gerar_alvo_geral(p)

    def pesquisar_codigo(self, query: str, language: str = 'cookiescript') -> str:
        language = (language or 'cookiescript').lower().strip()
        if query.strip() and self._is_model_available():
            lang_name = 'CookieScript' if language == 'cookiescript' else language.capitalize()
            r = self._gerar_com_deepseek(
                f'Provide a code example for: {query} using {lang_name}',
                language, mode='code'
            )
            if r:
                return r
        return self._pesquisa_local(query, language)

    # ── modelo ────────────────────────────────────────────────────────────────

    def _is_model_available(self) -> bool:
        if os.getenv('DISABLE_LOCAL_AI', '').lower() in ('1', 'true', 'yes'):
            return False
        return TRANSFORMERS_AVAILABLE and self._model_loaded and self._deepseek_model is not None

    def _load_deepseek_model(self):
        if self._model_loaded:
            return
        if os.getenv('DISABLE_LOCAL_AI', '').lower() in ('1', 'true', 'yes'):
            return
        if not _try_import_transformers():
            print('[AI] torch/transformers não instalados.')
            return
        try:
            print(f'[AI] Carregando {self.DEEPSEEK_MODEL}...')
            self._deepseek_tokenizer = AutoTokenizer.from_pretrained(
                self.DEEPSEEK_MODEL, trust_remote_code=True, use_fast=False
            )
            kwargs = {'trust_remote_code': True, 'low_cpu_mem_usage': True}
            if self.DEEPSEEK_USE_CPU or not torch.cuda.is_available():
                kwargs['dtype'] = torch.float16
                kwargs['device_map'] = 'cpu'
            else:
                kwargs['dtype'] = torch.float16
                kwargs['device_map'] = 'auto'
            self._deepseek_model = AutoModelForCausalLM.from_pretrained(self.DEEPSEEK_MODEL, **kwargs)
            self._model_loaded = True
            print('[AI] Modelo carregado!')
        except Exception as e:
            print(f'[AI] Erro ao carregar modelo: {e}')
            self._deepseek_model = None
            self._deepseek_tokenizer = None
            self._model_loaded = False

    def _gerar_com_deepseek(self, prompt: str, language: str = '', mode: str = 'code') -> str:
        self._load_deepseek_model()
        if not self._is_model_available():
            return ''
        if mode == 'chat':
            instruction = f"You are a helpful assistant. Answer concisely.\n\nPergunta: {prompt}\n\nResposta:"
        else:
            lang_name = 'CookieScript' if language == 'cookiescript' else ('JavaScript' if language in ('js','javascript','node') else language.capitalize())
            instruction = f"Generate only valid {lang_name} code for: {prompt}\nReturn only executable code.\n\n### Response:\n"
        try:
            enc = self._deepseek_tokenizer(instruction, return_tensors='pt', truncation=True, max_length=1024)
            device = next(self._deepseek_model.parameters()).device
            enc = {k: v.to(device) for k, v in enc.items()}
            out = self._deepseek_model.generate(
                **enc, max_new_tokens=512, do_sample=False, temperature=0.2,
                pad_token_id=self._deepseek_tokenizer.eos_token_id
            )
            decoded = self._deepseek_tokenizer.decode(out[0], skip_special_tokens=True)
            if decoded.startswith(instruction):
                decoded = decoded[len(instruction):]
            return decoded.strip()
        except Exception as e:
            print(f'[AI] Erro na geração: {e}')
            return ''

    # ── fallbacks ─────────────────────────────────────────────────────────────

    def _fallback_resposta(self, pergunta: str) -> str:
        p = pergunta.lower()
        if 'capital' in p and ('brasil' in p or 'brazil' in p):
            return 'Olá! Sou a Cookie AI 🍪\nA capital do Brasil é Brasília.'
        if 'capital' in p and 'frança' in p:
            return 'Olá! Sou a Cookie AI 🍪\nA capital da França é Paris.'
        if any(x in p for x in ('olá', 'ola', 'oi', 'hey', 'hello', 'tudo bem', 'tudo bom')):
            return 'Olá! Sou a Cookie AI 🍪, assistente oficial do CookieScript IDE. Como posso ajudar você hoje?'
        if 'quem' in p and ('você' in p or 'voce' in p):
            return 'Sou a Cookie AI 🍪, a inteligência artificial integrada ao CookieScript IDE! Fui criada para ajudar você a programar em CookieScript e outras linguagens.'
        if 'cookiescript' in p:
            return 'Cookie AI aqui! 🍪\nCookieScript é uma linguagem de programação para automação e scripting, com suporte nativo a filesystem, HTTP, JSON e muito mais.'
        if 'ler arquivo' in p or 'abrir arquivo' in p:
            return 'Cookie AI aqui! 🍪\nPara ler um arquivo:\n\nconteudo = filesystem.ler_arquivo(caminho="meu_arquivo.txt")'
        if 'escrever arquivo' in p:
            return 'Cookie AI aqui! 🍪\nPara escrever em arquivo:\n\nfilesystem.escrever_arquivo(caminho="saida.txt", conteudo="texto", modo="w")'
        if 'http' in p or 'request' in p or 'requisição' in p:
            return 'Cookie AI aqui! 🍪\nPara fazer requisição HTTP:\n\nresult = network.http_request(url="https://api.exemplo.com", metodo="GET")'
        return f'Oi! Sou a Cookie AI 🍪\nRecebi sua pergunta: "{pergunta}"\nPara respostas completas, use o provedor Groq no AI Assistant!'

    def _exemplo_basico(self) -> str:
        return '// Exemplo CookieScript\nfilesystem.escrever_arquivo(caminho="output.txt", conteudo="CookieScript IDE!", modo="w")\nresultado = network.http_request(url="https://httpbin.org/get", metodo="GET")'

    def _gerar_abrir_arquivo(self, prompt: str) -> str:
        caminho = self._extrair_caminho(prompt) or 'entrada.txt'
        return f'// Abrir arquivo\nconteudo = filesystem.ler_arquivo(caminho="{caminho}")\nfilesystem.escrever_arquivo(caminho="lido.txt", conteudo=conteudo, modo="w")'

    def _gerar_escrever_arquivo(self, prompt: str) -> str:
        caminho = self._extrair_caminho(prompt) or 'saida.txt'
        texto = self._extrair_texto(prompt) or 'Texto gerado'
        return f'// Escrever arquivo\nfilesystem.escrever_arquivo(caminho="{caminho}", conteudo="{texto}", modo="w")'

    def _gerar_requisicao_http(self, prompt: str) -> str:
        url = self._extrair_url(prompt) or 'https://httpbin.org/get'
        return f'// Requisição HTTP\nresultado = network.http_request(url="{url}", metodo="GET")\nfilesystem.escrever_arquivo(caminho="response.txt", conteudo=resultado["body"], modo="w")'

    def _gerar_json(self, prompt: str) -> str:
        return '// JSON\ntexto = \'{"nome": "CookieScript", "versao": 1}\'\ndados = json.parse_json(texto)\nfilesystem.escrever_arquivo(caminho="saida.txt", conteudo=json.stringify_json(dados), modo="w")'

    def _gerar_loop(self, prompt: str) -> str:
        return '// Loop\ncontador = 0\nfor i in [1, 2, 3, 4, 5] {\n    contador = contador + i\n}\nfilesystem.escrever_arquivo(caminho="resultado.txt", conteudo="Soma: " + contador, modo="w")'

    def _gerar_funcao(self, prompt: str) -> str:
        return '// Função\nfunction somar(a, b) {\n    return a + b\n}\nresultado = somar(5, 7)\nfilesystem.escrever_arquivo(caminho="resultado.txt", conteudo="Resultado: " + resultado, modo="w")'

    def _gerar_alvo_geral(self, prompt: str) -> str:
        return f'// CookieScript para: {prompt}\nfilesystem.escrever_arquivo(caminho="pedido.txt", conteudo="{prompt}", modo="w")'

    def _gerar_python(self, prompt: str) -> str:
        p = prompt.lower()
        if 'arquivo' in p or 'ler' in p:
            return "with open('entrada.txt', 'r', encoding='utf-8') as f:\n    conteudo = f.read()\nprint(conteudo)"
        if 'http' in p or 'request' in p:
            return "import urllib.request\nwith urllib.request.urlopen('https://httpbin.org/get') as r:\n    print(r.read().decode())"
        if 'json' in p:
            return "import json\ndados = {'nome': 'CookieScript'}\nprint(json.dumps(dados, indent=2))"
        if 'loop' in p or 'for' in p:
            return "soma = 0\nfor i in range(1, 6):\n    soma += i\nprint(f'Soma: {soma}')"
        return "def main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()"

    def _gerar_javascript(self, prompt: str) -> str:
        p = prompt.lower()
        if 'arquivo' in p:
            return "const fs = require('fs');\nconst c = fs.readFileSync('entrada.txt', 'utf-8');\nconsole.log(c);"
        if 'http' in p or 'request' in p:
            return "const https = require('https');\nhttps.get('https://httpbin.org/get', r => {\n  let d = '';\n  r.on('data', c => d += c);\n  r.on('end', () => console.log(d));\n});"
        if 'json' in p:
            return "const dados = { nome: 'CookieScript', versao: 1 };\nconsole.log(JSON.stringify(dados, null, 2));"
        if 'loop' in p or 'for' in p:
            return "let soma = 0;\nfor (let i = 1; i <= 5; i++) soma += i;\nconsole.log('Soma:', soma);"
        return "function somar(a, b) { return a + b; }\nconsole.log('Resultado:', somar(5, 7));"

    def _extrair_caminho(self, prompt: str) -> Optional[str]:
        m = re.search(r'["\']([^"\']+)["\']', prompt)
        if m: return m.group(1)
        m = re.search(r'(?:arquivo|file|path)[\s:=]+["\']?([^\s\'"]+)["\']?', prompt, re.I)
        return m.group(1) if m else None

    def _extrair_texto(self, prompt: str) -> Optional[str]:
        m = re.search(r'["\']([^"\']+)["\']', prompt)
        return m.group(1) if m else None

    def _extrair_url(self, prompt: str) -> Optional[str]:
        m = re.search(r'https?://[^\s]+', prompt)
        return m.group(0) if m else None

    def _pesquisa_local(self, query: str, language: str) -> str:
        return f'// Exemplo para: {query}\nfilesystem.escrever_arquivo(caminho="resultado.txt", conteudo="{query}", modo="w")'
