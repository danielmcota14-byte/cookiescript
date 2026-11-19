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
        extra = ""
        try:
            # dimensões PNG
            if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
                w = int.from_bytes(data[16:20], "big")
                h = int.from_bytes(data[20:24], "big")
                extra = f", {w}x{h}px"
            # JPEG SOF
            elif data[:2] == b"\xff\xd8":
                extra = " (JPEG)"
        except Exception:
            pass
        return (
            f"[IMAGEM anexada: {filename}, {len(data)} bytes, mime={mime}{extra}. "
            "Descreva e analise visualmente se o modelo de visão estiver disponível; "
            "caso contrário explique limitações e peça detalhes do que o usuário quer saber.]",
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

    # PDF: extração real de texto (pypdf) com fallback leve sem dependências
    if ext == ".pdf" or mime == "application/pdf":
        text = _extract_pdf_text(data)
        if text.strip():
            if len(text) > 60_000:
                text = text[:60_000] + "\n\n...[PDF truncado]..."
            return f"[Texto extraído do PDF {filename}]\n{text}", "text"
        return (
            f"[PDF {filename}, {len(data)} bytes — não encontrei texto selecionável. "
            "Provavelmente é um PDF escaneado (só imagem). Avise o usuário e peça o texto ou uma foto da página.]",
            "binary",
        )

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


def _extract_pdf_text(data: bytes, max_pages: int = 80, max_chars: int = 70_000) -> str:
    """Extrai texto de PDF. Usa pypdf se instalado; senão um parser simples (zlib + operadores Tj/TJ)."""
    try:
        import io
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(io.BytesIO(data))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:
                return ""
        parts = []
        total = 0
        for i, page in enumerate(reader.pages):
            if i >= max_pages or total >= max_chars:
                break
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                parts.append(f"--- página {i + 1} ---\n{t.strip()}")
                total += len(t)
        return "\n\n".join(parts)
    except ImportError:
        pass
    except Exception as e:
        print(f"[pdf] pypdf falhou: {e}")
    return _extract_pdf_text_basic(data, max_chars)


def _extract_pdf_text_basic(data: bytes, max_chars: int = 70_000) -> str:
    import zlib
    chunks = []
    total = 0
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        raw = m.group(1)
        try:
            raw = zlib.decompress(raw)
        except Exception:
            pass
        if b"BT" not in raw:
            continue
        for bt in re.findall(rb"BT(.*?)ET", raw, re.S):
            line = []
            for s in re.findall(rb"\(((?:\\.|[^\\)])*)\)\s*Tj|\[(.*?)\]\s*TJ", bt, re.S):
                if s[0]:
                    line.append(s[0])
                else:
                    line.extend(re.findall(rb"\(((?:\\.|[^\\)])*)\)", s[1]))
            txt = b"".join(line).decode("latin-1", errors="ignore")
            txt = re.sub(r"\\([()\\])", r"\1", txt)
            if txt.strip():
                chunks.append(txt)
                total += len(txt)
        if total >= max_chars:
            break
    return "\n".join(chunks)



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
