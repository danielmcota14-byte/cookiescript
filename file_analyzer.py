"""
Análise de arquivos enviados pelo usuário (qualquer tipo comum).
Extrai texto quando possível; para imagens prepara data-URL para modelos de visão.
Não gera imagens.
"""

from __future__ import annotations

import base64
import csv
import io
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

UPLOAD_DIR = Path(os.environ.get("COOKIE_UPLOAD_DIR", Path(__file__).resolve().parent / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Limite por arquivo (bytes) — ajuste via env se precisar
MAX_FILE_BYTES = int(os.environ.get("COOKIE_MAX_UPLOAD", 15 * 1024 * 1024))  # 15 MB

TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".jsonl", ".xml", ".html", ".htm",
    ".css", ".js", ".ts", ".jsx", ".tsx", ".py", ".rb", ".go", ".rs", ".java", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".php", ".sql", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".sh", ".bash", ".zsh", ".bat", ".ps1", ".cookiescript", ".log", ".env", ".gitignore",
    ".dockerfile", ".makefile", ".r", ".swift", ".kt", ".scala", ".lua", ".pl", ".vue",
    ".svelte", ".astro",
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
SPREADSHEET_EXTS = {".csv", ".tsv", ".xlsx", ".xls", ".ods"}


def _safe_name(name: str) -> str:
    name = os.path.basename(name or "arquivo")
    name = re.sub(r"[^\w.\- ()\[\]]+", "_", name)
    return name[:180] or "arquivo"


def guess_mime(filename: str, fallback: str = "application/octet-stream") -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or fallback


def save_upload(filename: str, data: bytes) -> Path:
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"Arquivo maior que o limite ({MAX_FILE_BYTES // (1024*1024)} MB).")
    path = UPLOAD_DIR / _safe_name(filename)
    # evita sobrescrever: acrescenta sufixo se existir
    if path.exists():
        stem, suf = path.stem, path.suffix
        i = 1
        while path.exists():
            path = UPLOAD_DIR / f"{stem}_{i}{suf}"
            i += 1
    path.write_bytes(data)
    return path


def extract_text_from_bytes(filename: str, data: bytes) -> Tuple[str, str]:
    """
    Retorna (texto_extraido_ou_descricao, tipo_detectado).
    tipo: text | image | binary | spreadsheet | code
    """
    ext = Path(filename).suffix.lower()
    mime = guess_mime(filename)

    # Imagens → só metadados + base64 preparado depois
    if ext in IMAGE_EXTS or (mime and mime.startswith("image/")):
        return (
            f"[Imagem: {filename}, {len(data)} bytes, mime={mime}. "
            "O conteúdo visual será enviado ao modelo de visão se disponível.]",
            "image",
        )

    # Texto / código
    if ext in TEXT_EXTS or (mime and mime.startswith("text/")):
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                text = data.decode(enc)
                kind = "spreadsheet" if ext in {".csv", ".tsv"} else "code" if ext in {
                    ".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".cookiescript"
                } else "text"
                # limita tamanho no prompt
                if len(text) > 120_000:
                    text = text[:120_000] + "\n\n...[truncado]..."
                return text, kind
            except UnicodeDecodeError:
                continue

    # JSON
    if ext == ".json":
        try:
            obj = json.loads(data.decode("utf-8"))
            text = json.dumps(obj, ensure_ascii=False, indent=2)
            if len(text) > 120_000:
                text = text[:120_000] + "\n...[truncado]..."
            return text, "text"
        except Exception:
            pass

    # CSV via módulo csv (já coberto se decodificar, mas reforça)
    if ext in {".csv", ".tsv"}:
        try:
            text = data.decode("utf-8", errors="replace")
            return text[:120_000], "spreadsheet"
        except Exception:
            pass

    # PDF básico sem dependência: tenta extrair strings legíveis
    if ext == ".pdf" or mime == "application/pdf":
        try:
            # extração tosca de strings ASCII/UTF-16 embutidas
            raw = data
            strings = re.findall(rb"[\x20-\x7E]{6,}", raw)
            text = "\n".join(s.decode("ascii", errors="ignore") for s in strings[:500])
            if text.strip():
                return f"[PDF texto aproximado de {filename}]\n{text[:80000]}", "text"
        except Exception:
            pass
        return f"[PDF binário: {filename}, {len(data)} bytes — texto não extraído automaticamente]", "binary"

    # Office antigo / zip-based: só informa
    if ext in {".docx", ".xlsx", ".pptx", ".odt", ".ods"}:
        return (
            f"[Arquivo Office/binário: {filename}, {len(data)} bytes. "
            "Envie exportado como .txt/.csv/.md para análise completa de texto, "
            "ou descreva o que precisa.]",
            "binary",
        )

    # Fallback binário
    return (
        f"[Arquivo binário: {filename}, {len(data)} bytes, mime={mime}. "
        "Não foi possível extrair texto legível.]",
        "binary",
    )


def prepare_for_ai(
    filename: str,
    data: bytes,
) -> Dict[str, Any]:
    """
    Prepara um arquivo para inclusão no prompt da IA.
    Retorna dict com:
      - name, size, kind, text (sempre)
      - image_part (opcional, para vision): {"type":"image_url","image_url":{"url":"data:..."}}
    """
    text, kind = extract_text_from_bytes(filename, data)
    out: Dict[str, Any] = {
        "name": filename,
        "size": len(data),
        "kind": kind,
        "text": text,
        "image_part": None,
    }
    ext = Path(filename).suffix.lower()
    if kind == "image" or ext in IMAGE_EXTS:
        mime = guess_mime(filename, "image/png")
        b64 = base64.b64encode(data).decode("ascii")
        # limita imagens muito grandes no prompt
        if len(data) <= 4 * 1024 * 1024:
            out["image_part"] = {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            }
        else:
            out["text"] += " (imagem grande demais para visão inline; envie redimensionada)"
    return out


def build_file_context(files: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    A partir de lista de prepare_for_ai(), monta:
      - bloco de texto para o prompt
      - lista de parts multimodais (imagens)
    """
    text_blocks = []
    image_parts = []
    for f in files:
        text_blocks.append(
            f"=== Arquivo: {f['name']} ({f['kind']}, {f['size']} bytes) ===\n{f['text']}\n"
        )
        if f.get("image_part"):
            image_parts.append(f["image_part"])
    return "\n".join(text_blocks), image_parts
