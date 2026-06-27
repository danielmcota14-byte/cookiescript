import os
import re
from typing import Optional

# Lazy loading: não importar torch/transformers no topo
# Isso será feito apenas quando necessário
TRANSFORMERS_AVAILABLE = False
torch = None
AutoModelForCausalLM = None
AutoTokenizer = None

def _try_import_transformers():
    """Tenta importar transformers apenas quando necessário."""
    global TRANSFORMERS_AVAILABLE, torch, AutoModelForCausalLM, AutoTokenizer
    
    if TRANSFORMERS_AVAILABLE:
        return True
    
    try:
        import torch as _torch
        from transformers import AutoModelForCausalLM as _AutoModelForCausalLM
        from transformers import AutoTokenizer as _AutoTokenizer
        torch = _torch
        AutoModelForCausalLM = _AutoModelForCausalLM
        AutoTokenizer = _AutoTokenizer
        TRANSFORMERS_AVAILABLE = True
        return True
    except ImportError:
        return False

class CookieAIGenerator:
    # Modelo leve que roda em CPU (phi-2 precisa ~8GB RAM, flan-t5-base ~1GB)
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-ai/deepseek-coder-1.3b-base')
    DEEPSEEK_USE_CPU = os.getenv('DEEPSEEK_USE_CPU', '1').lower() in ('1', 'true', 'yes')

    def __init__(self):
        self._deepseek_tokenizer = None
        self._deepseek_model = None
        self._model_loaded = False   # flag para saber se carregou

    # ----- Métodos públicos -----
    def responder(self, pergunta: str) -> str:
        pergunta = pergunta.strip()
        if not pergunta:
            return "Por favor, faça uma pergunta."

        if self._is_model_available():
            resposta = self._gerar_com_deepseek(pergunta, mode='chat')
            if resposta:
                return resposta
        return self._fallback_resposta(pergunta)

    def gerar_codigo(self, prompt: str, language: str = 'cookiescript') -> str:
        prompt_text = prompt.strip()
        language = language.lower().strip() if language else 'cookiescript'

        if prompt_text and self._is_model_available():
            deepseek_result = self._gerar_com_deepseek(prompt_text, language, mode='code')
            if deepseek_result:
                return deepseek_result

        # Fallback para templates locais
        if language == 'python':
            return self._gerar_python(prompt_text)
        if language in ['js', 'javascript', 'node']:
            return self._gerar_javascript(prompt_text)

        prompt = prompt_text.lower()
        if not prompt:
            return self._exemplo_basico()
        if "abrir arquivo" in prompt or "ler arquivo" in prompt:
            return self._gerar_abrir_arquivo(prompt)
        if "escrever arquivo" in prompt or "salvar arquivo" in prompt:
            return self._gerar_escrever_arquivo(prompt)
        if "http" in prompt or "request" in prompt or "api" in prompt:
            return self._gerar_requisicao_http(prompt)
        if "json" in prompt:
            return self._gerar_json(prompt)
        if "loop" in prompt or "repetir" in prompt or "for" in prompt:
            return self._gerar_loop(prompt)
        if "função" in prompt or "function" in prompt:
            return self._gerar_funcao(prompt)

        return self._gerar_alvo_geral(prompt)

    def pesquisar_codigo(self, query: str, language: str = 'cookiescript') -> str:
        language = language.lower().strip() if language else 'cookiescript'
        if query.strip() and self._is_model_available():
            result = self._gerar_com_deepseek(
                f'Provide a concise code example for the following request using only valid {"CookieScript" if language == "cookiescript" else ("JavaScript" if language in ["js", "javascript", "node"] else language.capitalize())} code. Request: {query}',
                language, mode='code'
            )
            if result:
                return result
        return self._pesquisa_local(query, language)

    # ----- Métodos internos de modelo -----
    def _is_model_available(self) -> bool:
        # Respeitar variável de ambiente DISABLE_LOCAL_AI
        if os.getenv('DISABLE_LOCAL_AI', '').lower() in ('1', 'true', 'yes'):
            return False
        return TRANSFORMERS_AVAILABLE and self._model_loaded and self._deepseek_model is not None

    def _load_deepseek_model(self):
        if self._model_loaded:
            return
        
        # Tentar importar transformers se ainda não foi feito
        if not TRANSFORMERS_AVAILABLE:
            if not _try_import_transformers():
                print("Transformers não instalado. Execute: pip install torch transformers")
                return

        try:
            print(f"Carregando modelo {self.DEEPSEEK_MODEL}... (pode levar vários minutos na primeira vez)")
            self._deepseek_tokenizer = AutoTokenizer.from_pretrained(
                self.DEEPSEEK_MODEL,
                trust_remote_code=True,
                use_fast=False,
            )
            load_kwargs = {
                'trust_remote_code': True,
                'low_cpu_mem_usage': True,
            }
            if self.DEEPSEEK_USE_CPU or not torch.cuda.is_available():
                # float16 usa metade da RAM que float32 (essencial para cloud com pouca memória)
                load_kwargs['torch_dtype'] = torch.float16
                load_kwargs['device_map'] = 'cpu'
                # Carrega pesos em 8bit para economizar ainda mais memória (~60% menos RAM)
                try:
                    import bitsandbytes
                    load_kwargs['load_in_8bit'] = True
                    load_kwargs.pop('torch_dtype', None)
                    print("Usando CPU com quantização 8bit (baixo uso de memória)")
                except ImportError:
                    print("Usando CPU com float16 (memória reduzida)")
            else:
                load_kwargs['torch_dtype'] = torch.float16
                load_kwargs['device_map'] = 'auto'
                print("Usando GPU se disponível")

            self._deepseek_model = AutoModelForCausalLM.from_pretrained(
                self.DEEPSEEK_MODEL,
                **load_kwargs,
            )
            self._model_loaded = True
            print("Modelo carregado com sucesso!")
        except Exception as err:
            print(f'ERRO ao carregar modelo: {err}')
            self._deepseek_model = None
            self._deepseek_tokenizer = None
            self._model_loaded = False

    def _gerar_com_deepseek(self, prompt: str, language: str = '', mode: str = 'code') -> str:
        self._load_deepseek_model()
        if not self._is_model_available():
            return ''

        if mode == 'chat':
            instruction = (
                "You are a helpful assistant. Answer the user's question concisely in the same language.\n\n"
                f"Pergunta: {prompt}\n\nResposta:"
            )
        else:  # code
            lang_name = 'CookieScript' if language == 'cookiescript' else ('JavaScript' if language in ['js','javascript','node'] else language.capitalize())
            instruction = (
                f"Generate only valid {lang_name} code for: {prompt}\n"
                "Do not add explanations. Return only executable code.\n\n"
                f"### Response:\n"
            )

        try:
            encoded = self._deepseek_tokenizer(instruction, return_tensors='pt', truncation=True, max_length=1024)
            device = next(self._deepseek_model.parameters()).device
            encoded = {k: v.to(device) for k, v in encoded.items()}
            outputs = self._deepseek_model.generate(
                **encoded,
                max_new_tokens=512,
                do_sample=False,
                temperature=0.2,
                pad_token_id=self._deepseek_tokenizer.eos_token_id
            )
            decoded = self._deepseek_tokenizer.decode(outputs[0], skip_special_tokens=True)
            if decoded.startswith(instruction):
                decoded = decoded[len(instruction):]
            return decoded.strip()
        except Exception as e:
            print(f"Erro na geração: {e}")
            return ''

    def _fallback_resposta(self, pergunta: str) -> str:
        pergunta_lower = pergunta.lower()
        if "capital" in pergunta_lower and ("brasil" in pergunta_lower or "brazil" in pergunta_lower):
            return "A capital do Brasil é Brasília."
        if "capital" in pergunta_lower and "frança" in pergunta_lower:
            return "A capital da França é Paris."
        if "olá" in pergunta_lower or "oi" in pergunta_lower:
            return "Olá! Como posso ajudar?"
        return f"Pergunta recebida: '{pergunta}'. (Modelo não disponível. Verifique o terminal para erros.)"

    # ------------------- TODOS OS MÉTODOS DE FALLBACK (gerar código, templates, pesquisa) -------------------
    def _exemplo_basico(self) -> str:
        return '''// Exemplo CookieScript gerado automaticamente
filesystem.escrever_arquivo(caminho="output.txt", conteudo="CookieScript IDE funcionando!", modo="w")
resultado_http = network.http_request(url="https://httpbin.org/get", metodo="GET")
filesystem.escrever_arquivo(caminho="api_response.txt", conteudo=resultado_http['body'], modo="w")'''

    def _gerar_abrir_arquivo(self, prompt: str) -> str:
        caminho = self._extrair_caminho(prompt) or "entrada.txt"
        return f'''// Abrir arquivo e exibir conteúdo
conteudo = filesystem.ler_arquivo(caminho="{caminho}")
filesystem.escrever_arquivo(caminho="arquivo_lido.txt", conteudo=conteudo, modo="w")'''

    def _gerar_escrever_arquivo(self, prompt: str) -> str:
        caminho = self._extrair_caminho(prompt) or "saida.txt"
        texto = self._extrair_texto(prompt) or "Texto gerado pelo CookieScript IDE"
        return f'''// Escrever arquivo a partir de prompt
filesystem.escrever_arquivo(caminho="{caminho}", conteudo="{texto}", modo="w")'''

    def _gerar_requisicao_http(self, prompt: str) -> str:
        url = self._extrair_url(prompt) or "https://httpbin.org/get"
        return f'''// Requisição HTTP gerada automaticamente
resultado_http = network.http_request(url="{url}", metodo="GET")
filesystem.escrever_arquivo(caminho="http_response.txt", conteudo=resultado_http['body'], modo="w")'''

    def _gerar_json(self, prompt: str) -> str:
        return '''// Conversão JSON
texto_json = '{"nome": "CookieScript", "versao": 1}'
dados = json.parse_json(texto_json)
filesystem.escrever_arquivo(caminho="json_saida.txt", conteudo=json.stringify_json(dados), modo="w")'''

    def _gerar_loop(self, prompt: str) -> str:
        return '''// Loop de repetição em CookieScript
contador = 0
for i in [1, 2, 3, 4, 5] {
    contador = contador + i
}
filesystem.escrever_arquivo(caminho="loop_resultado.txt", conteudo="Contador: " + contador, modo="w")'''

    def _gerar_funcao(self, prompt: str) -> str:
        return '''// Função simples em CookieScript
function somar(a, b) {
    return a + b
}
resultado = somar(5, 7)
filesystem.escrever_arquivo(caminho="funcao_resultado.txt", conteudo="Resultado: " + resultado, modo="w")'''

    def _gerar_alvo_geral(self, prompt: str) -> str:
        return f'''// Código CookieScript gerado para: {prompt}
filesystem.escrever_arquivo(caminho="pedido.txt", conteudo="{prompt}", modo="w")'''

    def _gerar_python(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "abrir arquivo" in prompt_lower or "ler arquivo" in prompt_lower:
            return '''# Abrir arquivo em Python
with open('entrada.txt', 'r', encoding='utf-8') as f:
    conteudo = f.read()

with open('arquivo_lido.txt', 'w', encoding='utf-8') as out:
    out.write(conteudo)'''
        if "escrever arquivo" in prompt_lower or "salvar arquivo" in prompt_lower:
            return '''# Escrever arquivo em Python
with open('saida.txt', 'w', encoding='utf-8') as f:
    f.write('Texto gerado pelo CookieScript IDE')'''
        if "http" in prompt_lower or "request" in prompt_lower or "api" in prompt_lower:
            return '''# Requisição HTTP em Python
import urllib.request

url = 'https://httpbin.org/get'
with urllib.request.urlopen(url) as response:
    body = response.read().decode('utf-8')

with open('http_response.txt', 'w', encoding='utf-8') as f:
    f.write(body)'''
        if "json" in prompt_lower:
            return '''# Manipulação JSON em Python
import json

dados = {'nome': 'CookieScript', 'versao': 1}
texto_json = json.dumps(dados)
parsed = json.loads(texto_json)
with open('json_saida.txt', 'w', encoding='utf-8') as f:
    f.write(texto_json)'''
        if "loop" in prompt_lower or "repetir" in prompt_lower or "for" in prompt_lower:
            return '''# Loop em Python
soma = 0
for i in range(1, 6):
    soma += i

with open('loop_resultado.txt', 'w', encoding='utf-8') as f:
    f.write(f'Soma: {soma}')'''
        if "função" in prompt_lower or "function" in prompt_lower:
            return '''# Função em Python
def somar(a, b):
    return a + b

resultado = somar(5, 7)
with open('funcao_resultado.txt', 'w', encoding='utf-8') as f:
    f.write(f'Resultado: {resultado}')'''
        return '''# Código Python gerado para o prompt
print('Insira um prompt mais específico para gerar código Python.')'''

    def _gerar_javascript(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "arquivo" in prompt_lower or "ler arquivo" in prompt_lower:
            return '''// Operações de arquivo em Node.js
const fs = require('fs');
const conteudo = fs.readFileSync('entrada.txt', 'utf-8');
fs.writeFileSync('arquivo_lido.txt', conteudo);'''
        if "escrever arquivo" in prompt_lower or "salvar arquivo" in prompt_lower:
            return '''// Escrever arquivo em Node.js
const fs = require('fs');
fs.writeFileSync('saida.txt', 'Texto gerado pelo CookieScript IDE');'''
        if "http" in prompt_lower or "request" in prompt_lower or "api" in prompt_lower:
            return '''// Requisição HTTP em Node.js
const https = require('https');

https.get('https://httpbin.org/get', (res) => {
  let data = '';
  res.on('data', (chunk) => { data += chunk; });
  res.on('end', () => {
    console.log(data);
  });
});'''
        if "json" in prompt_lower:
            return '''// Manipulação JSON em JavaScript
const dados = { nome: 'CookieScript', versao: 1 };
const textoJson = JSON.stringify(dados, null, 2);
console.log(textoJson);'''
        if "loop" in prompt_lower or "repetir" in prompt_lower or "for" in prompt_lower:
            return '''// Loop em JavaScript
let soma = 0;
for (let i = 1; i <= 5; i++) {
  soma += i;
}
console.log('Soma:', soma);'''
        if "função" in prompt_lower or "function" in prompt_lower:
            return '''// Função em JavaScript
function somar(a, b) {
  return a + b;
}

const resultado = somar(5, 7);
console.log('Resultado:', resultado);'''
        return '''// Código JavaScript gerado para o prompt
console.log('Insira um prompt mais específico para gerar código JavaScript.');'''

    def _extrair_caminho(self, prompt: str) -> Optional[str]:
        match = re.search(r'["\']([^"\']*)["\']', prompt)
        if match:
            return match.group(1)
        # Fallback: look for words after certain keywords
        match = re.search(r'(?:arquivo|file|path)[\s:=]+["\']?([^\s\'"]+)["\']?', prompt, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _extrair_texto(self, prompt: str) -> Optional[str]:
        # Look for quoted text
        match = re.search(r'["\']([^"\']*)["\']', prompt)
        if match:
            return match.group(1)
        return None

    def _extrair_url(self, prompt: str) -> Optional[str]:
        # Look for a URL pattern
        match = re.search(r'https?://[^\s]+', prompt)
        if match:
            return match.group(0)
        return None

    def _pesquisa_local(self, query: str, language: str) -> str:
        # This is a placeholder for local search (we keep the original fallback)
        # We'll return a simple message indicating no local search implementation
        return "// Pesquisa local não implementada nesta versão de fallback."