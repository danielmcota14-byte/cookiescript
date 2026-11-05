"""
Cliente unificado OpenAI-compatible para:
  - OmniRoute  (OMNIROUTE_URL + OMNIROUTE_API_KEY)
  - Grok / xAI (GROK_API_KEY  → https://api.x.ai/v1)
  - Groq       (GROQ_API_KEY)
  - fallbacks locais

Não gera imagens. Suporta chat, visão (quando o modelo permitir) e tool-like
respostas estruturadas para criar arquivos.
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


OMNIROUTE_URL = _env("OMNIROUTE_URL", "http://54.227.158.25:20128/v1").rstrip("/")
OMNIROUTE_KEY = _env("OMNIROUTE_API_KEY") or _env("OMNIROUTE_KEY")
GROK_URL = _env("GROK_URL", "https://api.x.ai/v1").rstrip("/")
GROK_KEY = _env("GROK_API_KEY") or _env("XAI_API_KEY")
GROQ_URL = _env("GROQ_URL", "https://api.groq.com/openai/v1").rstrip("/")
GROQ_KEY = _env("GROQ_API_KEY")

# Modelos padrão (podem ser sobrescritos por env ou pelo request)
DEFAULT_OMNIROUTE_MODEL = _env("OMNIROUTE_MODEL", "auto")
DEFAULT_GROK_MODEL = _env("GROK_MODEL", "grok-2-latest")
DEFAULT_GROQ_MODEL = _env("GROQ_MODEL", "openai/gpt-oss-120b")

# System prompt obrigatório — proíbe geração de imagens e define comportamento de arquivos + memória
SYSTEM_BASE = """Você é a Cookie AI, assistente integrada ao CookieScript IDE.
Responda sempre em português brasileiro, de forma clara e útil.

REGRAS OBRIGATÓRIAS:
1. NUNCA gere, descreva prompts para, ou ofereça geração de imagens, arte, fotos ou vídeos. Se pedirem imagem, diga educadamente que você não gera imagens e ofereça alternativas (código, planilha, texto, diagrama ASCII, etc.).
2. Você PODE e DEVE criar arquivos, códigos, planilhas (CSV/JSON), scripts, documentos e qualquer artefato de texto que uma IA normal construa.
3. Quando for criar um arquivo, use exatamente este formato (um bloco por arquivo):

<<<FILE path="caminho/relativo/arquivo.ext">>>
conteúdo completo do arquivo aqui
<<<END_FILE>>>

4. Você tem memória de longo prazo: use o que estiver no contexto de memória para personalizar respostas e aprender preferências do usuário.
5. Analise arquivos enviados (código, texto, planilhas, imagens, PDFs etc.) e responda com base no conteúdo.
6. Para planilhas, prefira CSV ou JSON limpo que possa ser aberto no Excel/Google Sheets.
"""


class AIClientError(RuntimeError):
    pass


def _http_json(
    url: str,
    method: str = "POST",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[dict] = None,
    timeout: int = 120,
) -> dict:
    data = None
    req_headers = {"Content-Type": "application/json", "User-Agent": "CookieAI/2.0"}
    if headers:
        req_headers.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("error", {}).get("message") or err_json.get("message") or err_body
        except Exception:
            msg = err_body or str(e)
        raise AIClientError(f"HTTP {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise AIClientError(f"Falha de rede: {e.reason}") from e


def _extract_text(data: dict) -> str:
    """Extrai texto de resposta OpenAI-compatible (chat.completions ou responses)."""
    if not data:
        return ""
    # chat.completions
    choices = data.get("choices")
    if choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):  # multimodal parts
            parts = []
            for p in content:
                if isinstance(p, dict) and p.get("type") == "text":
                    parts.append(p.get("text") or "")
                elif isinstance(p, str):
                    parts.append(p)
            return "\n".join(parts).strip()
        # legacy
        if "text" in choices[0]:
            return str(choices[0]["text"]).strip()
    # responses API
    if "output_text" in data:
        return str(data["output_text"]).strip()
    return ""


def chat_completion(
    messages: List[Dict[str, Any]],
    *,
    provider: str = "auto",
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    api_key: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Chama o provedor escolhido.
    Retorna (texto, label_modelo_usado).
    provider: auto | omniroute | grok | groq
    """
    provider = (provider or "auto").lower().strip()
    errors: List[str] = []

    order: List[str] = []
    if provider == "omniroute":
        order = ["omniroute"]
    elif provider == "grok":
        order = ["grok"]
    elif provider == "groq":
        order = ["groq"]
    else:
        # auto: OmniRoute → Grok → Groq
        order = ["omniroute", "grok", "groq"]

    for p in order:
        try:
            if p == "omniroute":
                key = api_key or OMNIROUTE_KEY
                if not key and not _env("OMNIROUTE_NO_KEY"):
                    # alguns setups locais não exigem key
                    key = "local"
                url = f"{OMNIROUTE_URL}/chat/completions"
                m = model or DEFAULT_OMNIROUTE_MODEL
                body = {
                    "model": m,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }
                headers = {"Authorization": f"Bearer {key}"} if key and key != "local" else {}
                data = _http_json(url, headers=headers, body=body)
                text = _extract_text(data)
                if text:
                    return text, f"OmniRoute/{m}"
                errors.append("OmniRoute: resposta vazia")

            elif p == "grok":
                key = api_key or GROK_KEY
                if not key:
                    errors.append("Grok: GROK_API_KEY não configurada")
                    continue
                url = f"{GROK_URL}/chat/completions"
                m = model or DEFAULT_GROK_MODEL
                body = {
                    "model": m,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }
                data = _http_json(url, headers={"Authorization": f"Bearer {key}"}, body=body)
                text = _extract_text(data)
                if text:
                    return text, f"Grok/{m}"
                errors.append("Grok: resposta vazia")

            elif p == "groq":
                key = api_key or GROQ_KEY
                if not key:
                    errors.append("Groq: GROQ_API_KEY não configurada")
                    continue
                url = f"{GROQ_URL}/chat/completions"
                m = model or DEFAULT_GROQ_MODEL
                body = {
                    "model": m,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }
                if str(m).startswith("openai/gpt-oss"):
                    body["reasoning_effort"] = "low"
                data = _http_json(url, headers={"Authorization": f"Bearer {key}"}, body=body)
                text = _extract_text(data)
                if text:
                    return text, f"Groq/{m}"
                errors.append("Groq: resposta vazia")
        except AIClientError as e:
            errors.append(f"{p}: {e}")
        except Exception as e:
            errors.append(f"{p}: {e}")

    raise AIClientError("Nenhum provedor respondeu. " + " | ".join(errors))


def build_messages(
    user_text: str,
    *,
    system_extra: str = "",
    memory_block: str = "",
    history: Optional[List[Dict[str, str]]] = None,
    file_parts: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Monta a lista de messages com system + memória + histórico + mensagem atual (multimodal se houver arquivos)."""
    system = SYSTEM_BASE
    if memory_block:
        system += "\n\n=== MEMÓRIA DE LONGO PRAZO (use e atualize quando fizer sentido) ===\n" + memory_block
    if system_extra:
        system += "\n\n" + system_extra

    messages: List[Dict[str, Any]] = [{"role": "system", "content": system}]

    if history:
        for h in history[-20:]:  # limita histórico recente
            role = h.get("role") or "user"
            content = h.get("content") or ""
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    # Mensagem do usuário (texto + possíveis imagens em base64 para visão)
    if file_parts:
        content_parts: List[Any] = [{"type": "text", "text": user_text or "Analise o(s) arquivo(s) enviado(s)."}]
        for part in file_parts:
            if part.get("type") == "image_url":
                content_parts.append(part)
            elif part.get("type") == "text":
                content_parts.append(part)
        messages.append({"role": "user", "content": content_parts})
    else:
        messages.append({"role": "user", "content": user_text})

    return messages


FILE_BLOCK_RE = re.compile(
    r'<<<FILE\s+path=["\']([^"\']+)["\']\s*>>>\s*(.*?)\s*<<<END_FILE>>>',
    re.DOTALL | re.IGNORECASE,
)


def extract_file_blocks(text: str) -> List[Dict[str, str]]:
    """Extrai blocos <<<FILE path="...">>> ... <<<END_FILE>>> da resposta da IA."""
    files = []
    for m in FILE_BLOCK_RE.finditer(text or ""):
        path = m.group(1).strip().lstrip("/\\")
        content = m.group(2)
        if path:
            files.append({"path": path, "content": content})
    return files


def strip_file_blocks(text: str) -> str:
    """Remove os blocos de arquivo do texto visível (opcional)."""
    return FILE_BLOCK_RE.sub("", text or "").strip()
