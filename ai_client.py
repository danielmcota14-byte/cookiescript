"""
Cliente unificado OpenAI-compatible para:
  - OmniRoute  (OMNIROUTE_URL + OMNIROUTE_API_KEY)
  - Grok / xAI (GROK_API_KEY  → https://api.x.ai/v1)
  - Groq       (GROQ_API_KEY)
  - fallbacks locais

As imagens são criadas pelo app (botão "Criar imagem"), não por este cliente. Suporta chat, visão (quando o modelo permitir) e tool-like
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


def _base_url(url: str) -> str:
    """Normaliza base OpenAI-compatible: remove barra final e sufixo /chat/completions se vier no env."""
    u = (url or "").strip().rstrip("/")
    # Evita .../chat/completions/chat/completions quando GROQ_URL já veio com o path completo
    for suffix in ("/chat/completions", "/v1/chat/completions"):
        if u.lower().endswith(suffix):
            u = u[: -len(suffix)].rstrip("/")
            break
    # se removeu /v1/chat/completions e ficou sem /v1, não — o endswith /v1/chat/completions
    # já deixa a base correta (ex: https://api.groq.com/openai)
    return u


OMNIROUTE_URL = _base_url(_env("OMNIROUTE_URL", "http://54.227.158.25:20128/v1"))
OMNIROUTE_KEY = _env("OMNIROUTE_API_KEY") or _env("OMNIROUTE_KEY")
GROK_URL = _base_url(_env("GROK_URL", "https://api.x.ai/v1"))
GROK_KEY = _env("GROK_API_KEY") or _env("XAI_API_KEY")
GROQ_URL = _base_url(_env("GROQ_URL", "https://api.groq.com/openai/v1"))
GROQ_KEY = _env("GROQ_API_KEY")

# Modelos padrão (podem ser sobrescritos por env ou pelo request)
DEFAULT_OMNIROUTE_MODEL = _env("OMNIROUTE_MODEL", "auto")
DEFAULT_GROK_MODEL = _env("GROK_MODEL", "grok-2-latest")
DEFAULT_GROQ_MODEL = _env("GROQ_MODEL", "openai/gpt-oss-120b")
# Modelos com visão no Groq (o Llama 4 Scout foi aposentado em 17/07/2026). Troque por env GROQ_VISION_MODEL se mudar.
GROQ_VISION_MODELS = [m for m in dict.fromkeys((_env("GROQ_VISION_MODEL", ""), "qwen/qwen3.8-27b", "qwen/qwen3.6-27b")) if m]
GROK_VISION_MODEL = _env("GROK_VISION_MODEL", "grok-2-vision-latest")

# System prompt obrigatório — define comportamento de arquivos + memória
SYSTEM_BASE = """Você é a Jertruge, assistente integrada ao CookieScript IDE.
Responda sempre em português brasileiro, de forma clara e útil.

IDENTIDADE E DESENVOLVEDOR:
- Seu nome é Jertruge.
- Você foi desenvolvida por Daniel Moriconi Cota, um estudante da FAETEC e pesquisador voluntário da FAPERJ, de 17 anos.
- Se perguntarem quem desenvolveu você, quem é seu criador, quem programou você ou uma pergunta equivalente, responda de forma direta e natural: "Fui desenvolvida por Daniel Moriconi Cota, um estudante da FAETEC e pesquisador voluntário da FAPERJ, de 17 anos."
- Não atribua seu desenvolvimento a outra pessoa ou empresa. Não invente outros dados biográficos sobre Daniel.
- Não diga que você é Daniel: você é a Jertruge, e Daniel é seu desenvolvedor.

REGRAS OBRIGATÓRIAS:
1. A Jertruge CRIA imagens: o app tem o botão "Criar imagem" e entende pedidos como "crie uma imagem de ...". Se o usuário perguntar se você faz imagens, diga que sim e explique que basta usar esse botão ou pedir "crie uma imagem de ...". Você mesmo escreve só texto: não finja ter gerado a imagem na resposta e não invente links de imagem. Vídeos não são suportados.
2. Você PODE e DEVE criar arquivos, códigos, planilhas (CSV/JSON), scripts, documentos e qualquer artefato de texto que uma IA normal construa.
3. Quando for criar um arquivo, use exatamente este formato (um bloco por arquivo):

<<<FILE path="caminho/relativo/arquivo.ext">>>
conteúdo completo do arquivo aqui
<<<END_FILE>>>

4. Você tem memória CONTÍNUA e PESSOAL deste usuário (estilo ChatGPT/Claude).
   Use o bloco MEMÓRIA DE LONGO PRAZO para personalizar tudo: nome, projetos, preferências, estilo.
   Essa memória é só DESTA pessoa — nunca invente dados de outros.
   Quando o usuário contar algo sobre si, assuma que deve ser lembrado nas próximas conversas.
5. Analise SEMPRE os arquivos enviados (código, texto, planilhas, imagens, PDFs, logs etc.).
   Se houver bloco "Arquivos enviados para análise", use esse conteúdo como fonte principal.
   Para imagens, descreva o que conseguir e responda com base nisso (para criar imagens novas, o usuário usa o botão "Criar imagem").
6. Para planilhas, prefira CSV ou JSON limpo que possa ser aberto no Excel/Google Sheets.
7. Grave na prática o que o usuário revelar sobre si (nome, preferências, projetos) usando a memória.
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
                elif str(m).startswith("qwen/"):
                    body["reasoning_effort"] = "default"
                    body["top_p"] = 0.95
                data = _http_json(url, headers={"Authorization": f"Bearer {key}"}, body=body)
                text = _extract_text(data)
                if str(m).startswith("qwen/"):
                    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
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
        for h in history[-30:]:  # o limite real é o orçamento de tokens do chamador
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


# ── Conselho de IAs: várias respondem, Grok organiza e potencializa ───────────

GROK_SYNTH_SYSTEM = """Você é o Grok, coordenador central do Conselho Jertruge.
Várias IAs especializadas já responderam à mesma pergunta do usuário.
Sua missão é:

1. Ler TODAS as respostas das outras IAs.
2. Identificar o que cada uma acertou, errou ou omitiu.
3. Combinar os melhores trechos, corrigir erros e preencher lacunas.
4. Produzir UMA resposta final, clara, completa e em português brasileiro.
5. Se houver código ou arquivos, unifique no melhor formato possível e use:
   <<<FILE path="caminho/arquivo.ext">>>
   conteúdo
   <<<END_FILE>>>
6. Não invente links nem finja gerar imagens (o app cuida disso). NUNCA diga que é um "resumo de várias IAs" de forma meta demais —
   entregue a resposta final como se fosse a resposta definitiva da Jertruge.
7. Se as outras IAs divergirem, escolha a solução mais correta e explique brevemente o motivo só se for importante.
8. Use a memória de longo prazo quando estiver no contexto.

Resposta final: só o conteúdo útil para o usuário (sem prefácio do tipo "Como coordenador...").
"""


def _single_provider(
    provider: str,
    messages: List[Dict[str, Any]],
    *,
    temperature: float = 0.6,
    max_tokens: int = 4096,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Chama um provedor isolado.
    Retorna (texto|None, label, erro|None).
    """
    try:
        text, label = chat_completion(
            messages,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
        )
        return text, label, None
    except Exception as e:
        return None, provider, str(e)


def council_chat(
    messages: List[Dict[str, Any]],
    *,
    temperature: float = 0.6,
    max_tokens: int = 8192,
    api_key: Optional[str] = None,
    include_providers: Optional[List[str]] = None,
    skip_grok_as_member: bool = True,
) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    Conselho de IAs:
      1) OmniRoute, Groq (e opcionalmente Grok) geram respostas em paralelo lógico
      2) Grok (central) recebe todas e produz a resposta potencializada

    Retorna (texto_final, label, membros: [{provider, model/label, text, error}]).
    """
    members_cfg = include_providers or ["omniroute", "groq"]
    # Grok como membro só se pedido; por padrão ele só sintetiza
    if not skip_grok_as_member and "grok" not in members_cfg:
        members_cfg = list(members_cfg) + ["grok"]

    # Mensagens para os membros: mesma pergunta, sem o system de síntese
    member_messages = list(messages)

    results: List[Dict[str, Any]] = []
    for p in members_cfg:
        text, label, err = _single_provider(
            p,
            member_messages,
            temperature=temperature,
            max_tokens=min(max_tokens, 4096),
            api_key=api_key,
        )
        results.append({
            "provider": p,
            "label": label,
            "text": text,
            "error": err,
        })

    # Monta bloco com as respostas das outras IAs
    blocks = []
    for i, r in enumerate(results, 1):
        if r["text"]:
            blocks.append(f"--- Resposta da IA #{i} ({r['label']}) ---\n{r['text'].strip()}\n")
        else:
            blocks.append(f"--- IA #{i} ({r['provider']}) indisponível: {r['error'] or 'sem resposta'} ---\n")

    if not any(r["text"] for r in results):
        # Ninguém respondeu — tenta Grok sozinho como fallback total
        try:
            text, label = chat_completion(
                messages,
                provider="grok",
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
            )
            return text, f"Grok-solo/{label}", results
        except Exception as e:
            raise AIClientError(
                "Nenhuma IA do conselho respondeu e Grok também falhou: " + str(e)
            )

    # Extrai a pergunta original do usuário (última message user)
    user_q = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                user_q = c
            elif isinstance(c, list):
                user_q = " ".join(
                    (p.get("text") or "") for p in c if isinstance(p, dict) and p.get("type") == "text"
                )
            break

    synth_user = (
        f"Pergunta original do usuário:\n{user_q}\n\n"
        f"Respostas das outras IAs do conselho (use o melhor de cada uma):\n\n"
        + "\n".join(blocks)
        + "\n\nProduza a resposta final potencializada."
    )

    # System do sintetizador = Grok coordenador (+ memória já estava no system original se houver)
    # Mantém SYSTEM_BASE regras (arquivos, sem imagem) + papel de coordenador
    synth_system = SYSTEM_BASE + "\n\n" + GROK_SYNTH_SYSTEM

    # Preserva memória se estava no system original
    orig_system = ""
    if messages and messages[0].get("role") == "system":
        orig_system = messages[0].get("content") or ""
        if "MEMÓRIA DE LONGO PRAZO" in orig_system:
            # reaproveita o bloco de memória
            idx = orig_system.find("=== MEMÓRIA")
            if idx >= 0:
                synth_system += "\n\n" + orig_system[idx:]

    synth_messages: List[Dict[str, Any]] = [
        {"role": "system", "content": synth_system},
        {"role": "user", "content": synth_user},
    ]

    try:
        final_text, grok_label = chat_completion(
            synth_messages,
            provider="grok",
            temperature=min(temperature, 0.5),
            max_tokens=max_tokens,
            api_key=api_key,
        )
        return final_text, f"Conselho→{grok_label}", results
    except Exception as e:
        # Se Grok falhar na síntese, escolhe a melhor resposta disponível
        candidates = [r for r in results if r["text"]]
        if not candidates:
            raise AIClientError(f"Síntese Grok falhou e não há fallback: {e}") from e
        # Prefere a mais longa (heurística simples de completude)
        best = max(candidates, key=lambda r: len(r["text"] or ""))
        note = (
            f"\n\n_[Nota: síntese Grok indisponível ({e}); "
            f"exibindo resposta de {best['label']}.]_"
        )
        return (best["text"] or "") + note, f"Fallback/{best['label']}", results


# ── Pipeline unificado: DeepSeek Local → OmniRoute (valida) → Groq (central) ─

PIPELINE_VALIDATE_SYSTEM = """Você é o validador OmniRoute do Conselho Jertruge.
Recebeu a RESPOSTA PRIMÁRIA gerada pelo DeepSeek Local para a pergunta do usuário.

Sua tarefa:
1. Verificar se a resposta é correta, completa e segura.
2. Corrigir erros factuais, de código ou de lógica.
3. Completar o que estiver incompleto.
4. Manter o idioma português brasileiro.
5. Não invente links de imagens.
6. Se a resposta primária estiver boa, refine e estruture melhor.
7. Se estiver ruim ou vazia, gere uma resposta correta do zero.
8. Quando criar arquivos, use:
<<<FILE path="caminho/arquivo.ext">>>
conteúdo
<<<END_FILE>>>

Devolva APENAS a resposta validada/refinada (sem meta-comentários do tipo "validei que...").
"""

PIPELINE_MAIN_SYSTEM = """Você é a Jertruge. Responda à pergunta do usuário de forma DEFINITIVA, clara, completa e em português brasileiro.
Se houver um RASCUNHO de outra IA, valide e corrija: use o que estiver certo, conserte erros de fato, de código ou de lógica e complete o que faltar; se estiver ruim ou vazio, responda do zero.
Não invente links de imagens. Quando criar arquivos, use exatamente:
<<<FILE path="caminho/arquivo.ext">>>
conteúdo
<<<END_FILE>>>
Entregue só o conteúdo útil, sem prefácio e sem comentar o processo.
"""

PIPELINE_GROQ_SYSTEM = """Você é o Groq, coordenador CENTRAL do Conselho Jertruge.
Você recebe a pergunta do usuário e a resposta já PROCESSADA E VALIDADA pelo OmniRoute
(que por sua vez partiu da resposta primária do DeepSeek Local).

Sua missão final:
1. Produzir a resposta DEFINITIVA, clara, completa e em português brasileiro.
2. Usar o melhor da resposta validada; corrija qualquer residual e eleve a qualidade.
3. Não invente links de imagens.
4. Quando criar arquivos, use exatamente:
<<<FILE path="caminho/arquivo.ext">>>
conteúdo
<<<END_FILE>>>
5. Entregue só o conteúdo útil — sem prefácio "como coordenador...".

Esta é a resposta que o usuário vai ver.
"""


def pipeline_chat(
    messages: List[Dict[str, Any]],
    *,
    temperature: float = 0.6,
    max_tokens: int = 8192,
    api_key: Optional[str] = None,
    deepseek_text: Optional[str] = None,
    estado_atual: Optional[Dict[str, Any]] = None,
    state_out: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    Pipeline:
      1) DeepSeek Local  → rascunho opcional (passado em deepseek_text)
      2) OmniRoute       → 1ª opção: resposta final + estado da conversa
      3) Groq            → 2ª opção: só se o OmniRoute falhar

    Retorna (texto_final, label, etapas).
    """
    steps: List[Dict[str, Any]] = []

    # ── 1. Resposta primária (DeepSeek) ───────────────────────────────────────
    primary = (deepseek_text or "").strip()
    if primary:
        steps.append({"provider": "deepseek_local", "label": "DeepSeek Local", "text": primary, "error": None})
    else:
        steps.append({
            "provider": "deepseek_local",
            "label": "DeepSeek Local",
            "text": None,
            "error": "Resposta primária não fornecida (DeepSeek local desligado ou falhou)",
        })

    # Extrai pergunta do usuário
    user_q = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                user_q = c
            elif isinstance(c, list):
                user_q = " ".join(
                    (p.get("text") or "") for p in c if isinstance(p, dict) and p.get("type") == "text"
                )
            break

    # Memória do system original
    mem_extra = ""
    if messages and messages[0].get("role") == "system":
        orig = messages[0].get("content") or ""
        if "MEMÓRIA DE LONGO PRAZO" in orig:
            idx = orig.find("=== MEMÓRIA")
            if idx >= 0:
                mem_extra = "\n\n" + orig[idx:]

    # histórico recente da conversa (só texto) — sem isso a IA "esquece" tudo entre mensagens
    hist_msgs: List[Dict[str, Any]] = []
    for hm in messages[1:-1]:
        if hm.get("role") in ("user", "assistant") and isinstance(hm.get("content"), str) and hm["content"].strip():
            hist_msgs.append({"role": hm["role"], "content": hm["content"][:4000]})
    hist_msgs = hist_msgs[-30:]

    # ── 2. OmniRoute = 1ª opção: responde de vez e já devolve o estado ──────────
    main_user = (
        f"Pergunta do usuário:\n{user_q}\n\n"
        + (f"RASCUNHO (DeepSeek Local):\n{primary}\n\n" if primary else "")
        + "ESTADO ATUAL (JSON): " + json.dumps(clean_state(estado_atual), ensure_ascii=False)
    )
    main_messages = [
        {"role": "system", "content": SYSTEM_BASE + "\n\n" + PIPELINE_MAIN_SYSTEM + PIPELINE_STATE_GROQ + mem_extra},
        *hist_msgs,
        {"role": "user", "content": main_user},
    ]
    final_text, omni_label, omni_err = _single_provider(
        "omniroute", main_messages,
        temperature=min(temperature, 0.6), max_tokens=min(max_tokens, 4096), api_key=api_key,
    )
    final_text, final_state = split_state_block(final_text or "")
    steps.append({"provider": "omniroute", "label": omni_label or "OmniRoute", "text": final_text, "error": omni_err})
    if final_text:
        if state_out is not None and final_state:
            state_out["estado"] = final_state
        return final_text, f"Pipeline→{omni_label or 'OmniRoute'}", steps

    # ── 3. Groq = 2ª opção: só entra se o OmniRoute falhar (poupa o limite grátis) ─
    groq_text, groq_label, groq_err = _single_provider(
        "groq", main_messages,
        temperature=min(temperature, 0.5), max_tokens=max_tokens, api_key=api_key,
    )
    groq_text, groq_state = split_state_block(groq_text or "")
    steps.append({"provider": "groq", "label": groq_label or "Groq", "text": groq_text, "error": groq_err})
    if groq_text:
        if state_out is not None and groq_state:
            state_out["estado"] = groq_state
        return groq_text, f"Pipeline→{groq_label or 'Groq'} (2ª opção)", steps

    if primary:
        return primary + "\n\n_[Nota: OmniRoute e Groq falharam; usando DeepSeek primário.]_", "Pipeline/DeepSeek-fallback", steps

    raise AIClientError(
        "Pipeline falhou em todas as etapas. "
        + " | ".join(f"{s['provider']}: {s['error']}" for s in steps if s.get("error"))
    )


def vision_chat(
    messages: List[Dict[str, Any]],
    *,
    temperature: float = 0.5,
    max_tokens: int = 4096,
    api_key: Optional[str] = None,
) -> Tuple[str, str]:
    """Responde mensagens que contêm imagens (image_url). Tenta modelos com visão em sequência."""
    errors: List[str] = []
    for m in GROQ_VISION_MODELS:
        try:
            return chat_completion(messages, provider="groq", model=m, temperature=temperature,
                                   max_tokens=max_tokens, api_key=api_key)
        except Exception as e:
            errors.append(f"groq/{m}: {e}")
    if GROK_KEY or api_key:
        try:
            return chat_completion(messages, provider="grok", model=GROK_VISION_MODEL, temperature=temperature,
                                   max_tokens=max_tokens, api_key=api_key)
        except Exception as e:
            errors.append(f"grok/{GROK_VISION_MODEL}: {e}")
    try:
        return chat_completion(messages, provider="omniroute", temperature=temperature,
                               max_tokens=max_tokens, api_key=api_key)
    except Exception as e:
        errors.append(f"omniroute: {e}")
    raise AIClientError("Nenhum modelo com visão respondeu. " + " | ".join(errors))


# ───────────────────────── Estado da conversa (substitui "cortar em N mensagens") ─────────────────────────
STATE_SYSTEM = """Você mantém o ESTADO de uma conversa, como o registro que uma máquina atualiza a cada passo.
Receba o ESTADO ATUAL (JSON) e a última troca (usuário + assistente) e devolva o NOVO ESTADO.
Responda SOMENTE com JSON válido, sem texto antes ou depois, neste formato exato:
{"objetivo": "string curta", "fatos": ["..."], "decisoes": ["..."], "pendente": ["..."], "detalhes": ["..."], "resumo": "string curta"}
Regras:
- Atualize apenas o que mudou; mantenha o resto igual. Remova o que ficou resolvido ou foi corrigido.
- Preserve nomes, números, versões, caminhos de arquivo, comandos e decisões EXATAMENTE como ditos.
- fatos: sobre o usuário ou o projeto (máx. 8). decisoes: o que foi combinado/escolhido (máx. 8). pendente: o que ainda falta (máx. 6).
- detalhes: nuances que não cabem nos outros campos mas podem voltar a importar (máx. 12).
- resumo: no máximo 3 frases sobre o que já foi tratado e ainda importa. Nunca invente nada que não foi dito.
- Cada item com no máximo 160 caracteres. Se nada mudou, devolva o estado atual."""

_STATE_LIMITS = {"fatos": 8, "decisoes": 8, "pendente": 6, "detalhes": 12}


def clean_state(raw: Any) -> Dict[str, Any]:
    """Valida e limita um estado vindo do cliente ou do modelo (nunca confia no formato)."""
    out: Dict[str, Any] = {"objetivo": "", "fatos": [], "decisoes": [], "pendente": [], "detalhes": [], "resumo": ""}
    if not isinstance(raw, dict):
        return out
    out["objetivo"] = str(raw.get("objetivo") or "")[:200].strip()
    out["resumo"] = str(raw.get("resumo") or "")[:600].strip()
    for k, n in _STATE_LIMITS.items():
        v = raw.get(k)
        if isinstance(v, list):
            out[k] = [str(x)[:160].strip() for x in v if str(x).strip()][:n]
    return out


def state_is_empty(st: Dict[str, Any]) -> bool:
    return not (st.get("objetivo") or st.get("resumo") or st.get("fatos") or st.get("decisoes") or st.get("pendente") or st.get("detalhes"))


def _norm_words(s: str) -> set:
    import unicodedata
    t = unicodedata.normalize("NFD", (s or "").lower())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return {w for w in re.findall(r"[a-z0-9]{4,}", t)}


def format_state_block(estado: Any, query: str = "") -> str:
    """Estado mínimo sempre; 'detalhes' (as nuances) só os que combinam com o assunto atual."""
    st = clean_state(estado)
    if state_is_empty(st):
        return ""
    lines = ["ESTADO DA CONVERSA (registro atualizado a cada mensagem; é fiel ao que foi dito antes):"]
    if st["objetivo"]:
        lines.append(f"- objetivo atual: {st['objetivo']}")
    for k, label in (("fatos", "fatos"), ("decisoes", "decisões"), ("pendente", "pendente")):
        if st[k]:
            lines.append(f"- {label}: " + " | ".join(st[k]))
    if st["resumo"]:
        lines.append(f"- já tratado: {st['resumo']}")
    q = _norm_words(query)
    if q and st["detalhes"]:
        scored = sorted(((len(q & _norm_words(d)), d) for d in st["detalhes"]), key=lambda x: -x[0])
        rel = [d for n, d in scored if n > 0][:3]
        if rel:
            lines.append("- detalhes antigos ligados a este assunto: " + " | ".join(rel))
    return "\n".join(lines)


STATE_TAG = "[[ESTADO]]"


def split_state_block(text: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Separa o bloco [[ESTADO]] do texto. O bloco SEMPRE sai do texto, mesmo quando vem quebrado."""
    t = text or ""
    i = t.rfind(STATE_TAG)
    if i < 0:
        return t.strip(), None
    visible, raw = t[:i].rstrip(), t[i + len(STATE_TAG):]
    visible = re.sub(r"```(?:json)?\s*$", "", visible).rstrip()
    obj = _parse_json_obj(raw)
    if obj is None:
        return visible, None
    st = clean_state(obj)
    return visible, (None if state_is_empty(st) else st)


PIPELINE_STATE_OMNI = (
    "\n\n=== ESTADO (tarefa extra, depois da resposta) ===\n"
    "Depois de refinar a resposta, escreva em uma nova linha " + STATE_TAG + " seguido de UM JSON, sem texto depois, com o MÁXIMO de informação útil "
    "desta troca mesclado ao ESTADO ATUAL: "
    '{"objetivo":"","fatos":[],"decisoes":[],"pendente":[],"detalhes":[],"resumo":""}. '
    "Só registre o que foi realmente dito na conversa; nunca invente. Preserve nomes, números e comandos exatamente."
)
PIPELINE_STATE_GROQ = (
    "\n\n=== ESTADO (tarefa extra, depois da resposta) ===\n"
    "Depois da resposta final, escreva em uma nova linha " + STATE_TAG + " seguido de UM JSON, sem texto depois: o estado FINAL da conversa. "
    "Parta do ESTADO CANDIDATO (sugerido pela etapa anterior) e do ESTADO ATUAL, descarte tudo o que não aparece na conversa, "
    "mantenha em fatos/decisoes/pendente só o essencial e mande as nuances restantes para detalhes. "
    '{"objetivo":"","fatos":[],"decisoes":[],"pendente":[],"detalhes":[],"resumo":""}'
)


def _parse_json_obj(text: str) -> Optional[Dict[str, Any]]:
    t = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    t = re.sub(r"```(?:json)?", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        v = json.loads(t[i:j + 1])
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def update_conversation_state(estado: Any, user_msg: str, assistant_msg: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Pede à IA o novo estado. Se falhar, devolve o estado atual intacto (nunca quebra a conversa)."""
    cur = clean_state(estado)
    payload = (
        "ESTADO ATUAL:\n" + json.dumps(cur, ensure_ascii=False) +
        "\n\nÚLTIMA TROCA:\nUsuário: " + (user_msg or "")[:3000] +
        "\nAssistente: " + (assistant_msg or "")[:3000]
    )
    msgs = [{"role": "system", "content": STATE_SYSTEM}, {"role": "user", "content": payload}]
    for prov in ("omniroute", "groq"):
        try:
            text, _ = chat_completion(msgs, provider=prov, temperature=0.1, max_tokens=700, api_key=api_key)
            obj = _parse_json_obj(text)
            if obj is not None:
                return clean_state(obj)
        except Exception as e:
            print(f"[state] {prov} falhou: {e}")
    return cur
