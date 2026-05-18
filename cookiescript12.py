# cookiescript/html.py
from typing import Dict, Any, List
import re

class HTMLOps:
    """Operações com HTML - incorporação direta e manipulação"""

    def __init__(self):
        self.templates = {}

    def criar_template(self, nome: str, html: str) -> str:
        """Cria um template HTML para reutilização"""
        self.templates[nome] = html
        return f"Template '{nome}' criado"

    def renderizar_template(self, nome: str, dados: Dict[str, Any] = None) -> str:
        """Renderiza um template com dados dinâmicos"""
        if nome not in self.templates:
            return f"Template '{nome}' não encontrado"

        html = self.templates[nome]
        if dados:
            for chave, valor in dados.items():
                placeholder = "{{" + chave + "}}"
                html = html.replace(placeholder, str(valor))

        return html

    def incorporar_html(self, html: str) -> str:
        """Incorpora HTML diretamente no script - retorna o HTML como string"""
        return html

    def criar_pagina_completa(self, titulo: str = "Página CookieScript",
                            conteudo: str = "",
                            css: str = "",
                            javascript: str = "") -> str:
        """Cria uma página HTML completa"""
        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo}</title>
    <style>
        {css}
    </style>
</head>
<body>
    {conteudo}
    <script>
        {javascript}
    </script>
</body>
</html>"""
        return html

    def adicionar_elemento(self, html: str, seletor: str, elemento: str, posicao: str = "append") -> str:
        """Adiciona elemento HTML em uma posição específica"""
        # Implementação simplificada - em produção usaria uma biblioteca como BeautifulSoup
        if posicao == "append":
            # Adiciona no final do elemento pai
            return html.replace(f"</{seletor}>", f"{elemento}</{seletor}>")
        elif posicao == "prepend":
            # Adiciona no início do elemento pai
            pattern = f"<{seletor}[^>]*>"
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                start_tag = match.group()
                return html.replace(start_tag, start_tag + elemento)
        return html

    def extrair_texto(self, html: str) -> str:
        """Extrai texto puro do HTML (remove tags)"""
        # Remove tags HTML
        clean = re.compile('<.*?>')
        return re.sub(clean, '', html)

    def criar_formulario(self, acao: str = "", metodo: str = "POST",
                        campos: List[Dict[str, str]] = None) -> str:
        """Cria um formulário HTML dinamicamente"""
        campos_html = ""
        if campos:
            for campo in campos:
                tipo = campo.get('tipo', 'text')
                nome = campo.get('nome', '')
                valor = campo.get('valor', '')
                placeholder = campo.get('placeholder', '')
                label = campo.get('label', nome.capitalize())

                campos_html += f"""
                <div>
                    <label for="{nome}">{label}:</label>
                    <input type="{tipo}" id="{nome}" name="{nome}"
                           value="{valor}" placeholder="{placeholder}">
                </div>"""

        form = f"""
        <form action="{acao}" method="{metodo}">
            {campos_html}
            <button type="submit">Enviar</button>
        </form>"""
        return form

    def criar_tabela(self, dados: List[Dict[str, Any]], headers: List[str] = None) -> str:
        """Cria uma tabela HTML a partir de dados"""
        if not dados:
            return "<table><tr><td>Nenhum dado</td></tr></table>"

        # Se não especificar headers, usa as chaves do primeiro item
        if not headers:
            headers = list(dados[0].keys())

        # Cabeçalho
        header_html = "".join(f"<th>{h}</th>" for h in headers)

        # Linhas de dados
        rows_html = ""
        for item in dados:
            row = "".join(f"<td>{item.get(h, '')}</td>" for h in headers)
            rows_html += f"<tr>{row}</tr>"

        return f"""
        <table border="1">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>"""

    def escapar_html(self, texto: str) -> str:
        """Escapa caracteres especiais para HTML"""
        return (texto.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;"))