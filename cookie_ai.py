import os
import re
from typing import Optional

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    torch = None
    AutoModelForCausalLM = None
    AutoTokenizer = None
    TRANSFORMERS_AVAILABLE = False

class CookieAIGenerator:
    """Gerador simples de código multi-linguagem adaptado para DeepSeek Coder."""

    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-ai/deepseek-coder-1b-base')
    DEEPSEEK_USE_CPU = os.getenv('DEEPSEEK_USE_CPU', '1').lower() in ('1', 'true', 'yes')

    def __init__(self):
        self._deepseek_tokenizer = None
        self._deepseek_model = None

    def gerar_codigo(self, prompt: str, language: str = 'cookiescript') -> str:
        prompt_text = prompt.strip()
        language = language.lower().strip() if language else 'cookiescript'

        if prompt_text and self._can_use_deepseek():
            deepseek_result = self._gerar_com_deepseek(prompt_text, language)
            if deepseek_result:
                return deepseek_result

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

    def _can_use_deepseek(self) -> bool:
        return TRANSFORMERS_AVAILABLE and self.DEEPSEEK_MODEL is not None

    def _load_deepseek_model(self):
        if self._deepseek_model is not None and self._deepseek_tokenizer is not None:
            return
        if not TRANSFORMERS_AVAILABLE:
            return

        try:
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
                load_kwargs['torch_dtype'] = torch.float32
                load_kwargs['device_map'] = 'auto'
            else:
                load_kwargs['torch_dtype'] = torch.float16
                load_kwargs['device_map'] = 'auto'

            self._deepseek_model = AutoModelForCausalLM.from_pretrained(
                self.DEEPSEEK_MODEL,
                **load_kwargs,
            )
        except Exception as err:
            print(f'Erro ao carregar DeepSeek model {self.DEEPSEEK_MODEL}: {err}')
            self._deepseek_model = None
            self._deepseek_tokenizer = None

    def _gerar_com_deepseek(self, prompt: str, language: str) -> str:
        self._load_deepseek_model()
        if self._deepseek_model is None or self._deepseek_tokenizer is None:
            return ''

        language_name = 'CookieScript' if language == 'cookiescript' else ('JavaScript' if language in ['js', 'javascript', 'node'] else language.capitalize())
        instruction = (
            f'You are a code generation assistant using DeepSeek Coder. '
            f'Generate only valid {language_name} code for the request below. '
            'Do not add explanations or comments outside the code. '
            'Return only executable code.\n\n'
            f'Request: {prompt}\n\n'
            '### Response:\n'
        )

        try:
            encoded = self._deepseek_tokenizer(instruction, return_tensors='pt', truncation=True, max_length=2048)
            encoded = {k: v.to(self._deepseek_model.device) for k, v in encoded.items()}
            outputs = self._deepseek_model.generate(
                **encoded,
                max_new_tokens=512,
                do_sample=False,
                top_p=0.95,
                temperature=0.2,
                eos_token_id=self._deepseek_tokenizer.eos_token_id if hasattr(self._deepseek_tokenizer, 'eos_token_id') else None,
                pad_token_id=self._deepseek_tokenizer.eos_token_id if hasattr(self._deepseek_tokenizer, 'eos_token_id') else None,
            )
            decoded = self._deepseek_tokenizer.decode(outputs[0], skip_special_tokens=True)
            if decoded.startswith(instruction):
                decoded = decoded[len(instruction):]
            return decoded.strip()
        except Exception as err:
            print(f'Erro ao gerar com DeepSeek: {err}')
            return ''

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

    def _extrair_caminho(self, prompt: str) -> str:
        match = re.search(r'arquivo\s+([\w\-\.\/\\]+)', prompt)
        return match.group(1) if match else None
    def _extrair_texto(self, prompt: str) -> str:
        match = re.search(r'texto\s+"([^"]+)"', prompt)
        if match:
            return match.group(1)
        return None

    def pesquisar_codigo(self, query: str, language: str = 'cookiescript') -> str:
        """Pesquisa códigos e módulos relevantes usando DeepSeek Coder quando disponível"""
        language = language.lower().strip() if language else 'cookiescript'
        if query.strip() and self._can_use_deepseek():
            result = self._gerar_com_deepseek(
                f'Provide a concise code example for the following request using only valid {"CookieScript" if language == "cookiescript" else ("JavaScript" if language in ["js", "javascript", "node"] else language.capitalize())} code. Request: {query}',
                language
            )
            if result:
                return result
        return self._pesquisa_local(query, language)

    def _pesquisa_local(self, query: str, language: str = 'cookiescript') -> str:
        """Fallback local para pesquisa de códigos"""
        query_lower = query.lower()
        language = language.lower().strip() if language else 'cookiescript'
        if language == 'python':
            if "arquivo" in query_lower or "ler arquivo" in query_lower:
                return '''# Operações com arquivos em Python
with open('teste.txt', 'w', encoding='utf-8') as f:
    f.write('Teste Python')
with open('teste.txt', 'r', encoding='utf-8') as f:
    conteudo = f.read()
print(conteudo)'''
            if "http" in query_lower or "request" in query_lower or "api" in query_lower:
                return '''# Requisição HTTP em Python
import urllib.request
with urllib.request.urlopen('https://httpbin.org/get') as response:
    body = response.read().decode('utf-8')
print(body)'''
            if "json" in query_lower:
                return '''# Manipulação JSON em Python
import json
dados = {'nome': 'CookieScript', 'versao': 1}
texto_json = json.dumps(dados, indent=2)
parsed = json.loads(texto_json)
print(parsed)'''
            return '''# Código Python gerado para a pesquisa
print('Aprimore sua busca para obter um exemplo de Python mais específico.')'''

        if language in ['js', 'javascript', 'node']:
            if "arquivo" in query_lower or "ler arquivo" in query_lower:
                return '''// Operações de arquivo em Node.js
const fs = require('fs');
const conteudo = fs.readFileSync('teste.txt', 'utf-8');
console.log(conteudo);'''
            if "http" in query_lower or "request" in query_lower or "api" in query_lower:
                return '''// Requisição HTTP em Node.js
const https = require('https');
https.get('https://httpbin.org/get', (res) => {
  let data = '';
  res.on('data', (chunk) => { data += chunk; });
  res.on('end', () => { console.log(data); });
});'''
            if "json" in query_lower:
                return '''// Manipulação JSON em JavaScript
const dados = { nome: 'CookieScript', versao: 1 };
console.log(JSON.stringify(dados, null, 2));'''
            return '''// Código JavaScript gerado para a pesquisa
console.log('Aprimore sua busca para obter um exemplo de JavaScript mais específico.');'''

        if "filesystem" in query_lower or "arquivo" in query_lower:
            return '''// Operações com arquivos
filesystem.escrever_arquivo(caminho="teste.txt", conteudo="Conteúdo de teste", modo="w")
conteudo = filesystem.ler_arquivo(caminho="teste.txt")
filesystem.escrever_arquivo(caminho="resultado.txt", conteudo=conteudo, modo="w")'''
        if "network" in query_lower or "http" in query_lower or "api" in query_lower:
            return '''// Requisições HTTP
resultado = network.http_request(url="https://httpbin.org/get", metodo="GET")
filesystem.escrever_arquivo(caminho="api_response.txt", conteudo=resultado['body'], modo="w")'''

        if "json" in query_lower:
            return '''// Manipulação JSON
dados = {"nome": "CookieScript", "versao": 1, "modulos": ["filesystem", "network", "json"]}
texto_json = json.stringify_json(dados)
dados_parseados = json.parse_json(texto_json)
filesystem.escrever_arquivo(caminho="json_teste.txt", conteudo=texto_json, modo="w")'''

        if "database" in query_lower or "sqlite" in query_lower:
            return '''// Operações com banco de dados
database.conectar(caminho="teste.db")
database.executar_sql(sql="CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nome TEXT)")
database.executar_sql(sql="INSERT INTO usuarios (nome) VALUES ('João')")
resultados = database.executar_sql(sql="SELECT * FROM usuarios")
database.desconectar()'''

        if "crypto" in query_lower or "hash" in query_lower:
            return '''// Criptografia e hashing
hash_sha256 = crypto.hash_sha256(dados="texto para hash")
filesystem.escrever_arquivo(caminho="hash.txt", conteudo=hash_sha256, modo="w")'''

        if "math" in query_lower or "matematica" in query_lower:
            return '''// Operações matemáticas
resultado_soma = math.somar(a=10, b=5)
resultado_potencia = math.potencia(base=2, expoente=3)
resultado_raiz = math.raiz_quadrada(valor=16)
filesystem.escrever_arquivo(caminho="math_result.txt", conteudo="Soma: " + resultado_soma + ", Potência: " + resultado_potencia + ", Raiz: " + resultado_raiz, modo="w")'''

        if "time" in query_lower or "data" in query_lower:
            return '''// Operações com data e hora
data_atual = time.data_atual()
hora_atual = time.hora_atual()
timestamp = time.timestamp()
filesystem.escrever_arquivo(caminho="time_info.txt", conteudo="Data: " + data_atual + ", Hora: " + hora_atual + ", Timestamp: " + timestamp, modo="w")'''

        if "string" in query_lower or "texto" in query_lower:
            return '''// Manipulação de strings
texto = "Olá, CookieScript!"
maiusculo = string.maiusculo(texto=texto)
minusculo = string.minusculo(texto=texto)
comprimento = string.comprimento(texto=texto)
substituido = string.substituir(texto=texto, antigo="Olá", novo="Oi")
filesystem.escrever_arquivo(caminho="string_ops.txt", conteudo="Original: " + texto + ", Maiúsculo: " + maiusculo + ", Comprimento: " + comprimento, modo="w")'''

        if "webservice" in query_lower or "servico web" in query_lower:
            return '''// Criação de serviços web
webservice.criar_servico(caminho="/api/teste", metodo="GET", resposta="Olá do CookieScript!")
webservice.iniciar_servidor(porta=8080)'''

        return f'''// Pesquisa para: {query}
// Não foi possível encontrar um exemplo específico. Tente ser mais específico.
// Exemplos disponíveis: filesystem, network, json, database, crypto, math, time, string, webservice'''

