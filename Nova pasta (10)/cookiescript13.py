# cookiescript/webservice.py
import os
import subprocess
import tempfile
from typing import Dict, Any, List, Callable
import json

class WebServiceOps:
    """Operações para criar e compilar serviços web"""

    def __init__(self):
        self.servicos = {}
        self.rotas = {}

    def criar_servico(self, nome: str, porta: int = 8000, host: str = "localhost") -> str:
        """Cria um novo serviço web"""
        if nome in self.servicos:
            return f"Serviço '{nome}' já existe"

        self.servicos[nome] = {
            "nome": nome,
            "porta": porta,
            "host": host,
            "rotas": {},
            "middleware": [],
            "config": {}
        }

        self.rotas[nome] = {}
        return f"Serviço '{nome}' criado na porta {porta}"

    def adicionar_rota(self, servico: str, metodo: str, caminho: str,
                      funcao_callback: str, middlewares: List[str] = None) -> str:
        """Adiciona uma rota ao serviço"""
        if servico not in self.servicos:
            return f"Serviço '{servico}' não encontrado"

        rota_key = f"{metodo.upper()}:{caminho}"
        self.rotas[servico][rota_key] = {
            "metodo": metodo.upper(),
            "caminho": caminho,
            "callback": funcao_callback,
            "middlewares": middlewares or []
        }

        return f"Rota {metodo.upper()} {caminho} adicionada ao serviço '{servico}'"

    def adicionar_middleware(self, servico: str, nome: str, funcao: str) -> str:
        """Adiciona middleware ao serviço"""
        if servico not in self.servicos:
            return f"Serviço '{servico}' não encontrado"

        self.servicos[servico]["middleware"].append({
            "nome": nome,
            "funcao": funcao
        })

        return f"Middleware '{nome}' adicionado ao serviço '{servico}'"

    def gerar_codigo_flask(self, servico: str) -> str:
        """Gera código Flask para o serviço"""
        if servico not in self.servicos:
            return f"Serviço '{servico}' não encontrado"

        svc = self.servicos[servico]
        rotas = self.rotas[servico]

        # Cabeçalho
        codigo = f'''from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Configurações
HOST = "{svc["host"]}"
PORT = {svc["porta"]}

'''

        # Middlewares
        for mw in svc["middleware"]:
            codigo += f'''
def {mw["funcao"]}():
    # Middleware: {mw["nome"]}
    pass

'''

        # Rotas
        for rota_key, rota_info in rotas.items():
            metodo = rota_info["metodo"]
            caminho = rota_info["caminho"]
            callback = rota_info["callback"]

            # Converte caminho Flask (ex: /api/:id -> /api/<id>)
            flask_path = caminho.replace(":id", "<id>").replace(":nome", "<nome>")

            codigo += f'''
@app.route("{flask_path}", methods=["{metodo}"])
def {callback}():
    # Rota: {metodo} {caminho}
    # Implementar lógica aqui
    return jsonify({{"message": "Rota {caminho} executada"}})

'''

        # Main
        codigo += f'''
if __name__ == "__main__":
    print(f"Serviço {servico} rodando em http://{{HOST}}:{{PORT}}")
    app.run(host=HOST, port=PORT, debug=True)
'''

        return codigo

    def gerar_codigo_fastapi(self, servico: str) -> str:
        """Gera código FastAPI para o serviço"""
        if servico not in self.servicos:
            return f"Serviço '{servico}' não encontrado"

        svc = self.servicos[servico]
        rotas = self.rotas[servico]

        # Cabeçalho
        codigo = f'''from fastapi import FastAPI
from typing import Optional
import uvicorn

app = FastAPI(title="{servico}", version="1.0.0")

'''

        # Rotas
        for rota_key, rota_info in rotas.items():
            metodo = rota_info["metodo"]
            caminho = rota_info["caminho"]
            callback = rota_info["callback"]

            # Converte caminho FastAPI (ex: /api/:id -> /api/{{id}})
            fastapi_path = caminho.replace(":id", "{id}").replace(":nome", "{nome}")

            if metodo.upper() == "GET":
                codigo += f'''
@app.get("{fastapi_path}")
async def {callback}():
    # Rota: {metodo} {caminho}
    return {{"message": "Rota {caminho} executada"}}
'''
            elif metodo.upper() == "POST":
                codigo += f'''
@app.post("{fastapi_path}")
async def {callback}():
    # Rota: {metodo} {caminho}
    return {{"message": "Rota {caminho} executada"}}
'''

        # Main
        codigo += f'''
if __name__ == "__main__":
    print(f"Serviço {servico} rodando em http://{{HOST}}:{{PORT}}")
    uvicorn.run(app, host="{svc["host"]}", port={svc["porta"]})
'''

        return codigo

    def compilar_servico(self, servico: str, framework: str = "flask",
                        saida: str = None) -> str:
        """Compila o serviço em um executável ou arquivo Python"""
        if servico not in self.servicos:
            return f"Serviço '{servico}' não encontrado"

        if framework.lower() == "flask":
            codigo = self.gerar_codigo_flask(servico)
        elif framework.lower() == "fastapi":
            codigo = self.gerar_codigo_fastapi(servico)
        else:
            return f"Framework '{framework}' não suportado"

        # Define arquivo de saída
        if not saida:
            saida = f"{servico}_service.py"

        # Salva o código
        with open(saida, 'w', encoding='utf-8') as f:
            f.write(codigo)

        return f"Serviço '{servico}' compilado em '{saida}' usando {framework}"

    def executar_servico(self, arquivo: str) -> str:
        """Executa um serviço compilado"""
        try:
            # Executa em background
            subprocess.Popen(["python", arquivo], creationflags=subprocess.CREATE_NO_WINDOW)
            return f"Serviço '{arquivo}' iniciado"
        except Exception as e:
            return f"Erro ao executar serviço: {str(e)}"

    def criar_api_rest_basica(self, nome: str, entidade: str, porta: int = 8000) -> str:
        """Cria uma API REST básica para uma entidade"""
        # Cria serviço
        self.criar_servico(nome, porta)

        # Adiciona rotas CRUD básicas
        self.adicionar_rota(nome, "GET", f"/{entidade}", f"listar_{entidade}")
        self.adicionar_rota(nome, "GET", f"/{entidade}/:id", f"obter_{entidade}")
        self.adicionar_rota(nome, "POST", f"/{entidade}", f"criar_{entidade}")
        self.adicionar_rota(nome, "PUT", f"/{entidade}/:id", f"atualizar_{entidade}")
        self.adicionar_rota(nome, "DELETE", f"/{entidade}/:id", f"deletar_{entidade}")

        return f"API REST básica criada para entidade '{entidade}' no serviço '{nome}'"