"""
Memória persistente da Cookie AI.

- Conversas por sessão/usuário (histórico curto)
- Memória de longo prazo / aprendizagem (fatos, preferências, aprendizados)
  armazenada em SQLite (arquivo data/cookie_memory.db)

A IA recebe o resumo da memória de longo prazo no system prompt a cada chamada.
Aprendizados novos podem ser gravados via API ou extraídos da resposta.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("COOKIE_DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "cookie_memory.db"

_lock = threading.RLock()


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init_db() -> None:
    with _lock:
        with _conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS long_term (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL DEFAULT 'global',
                    kind TEXT NOT NULL DEFAULT 'fact',
                    content TEXT NOT NULL,
                    metadata TEXT,
                    importance REAL DEFAULT 0.5,
                    created_at REAL,
                    updated_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_lt_scope ON long_term(scope);
                CREATE INDEX IF NOT EXISTS idx_lt_kind ON long_term(kind);

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id, created_at);

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at REAL,
                    updated_at REAL
                );
                """
            )


init_db()


def _now() -> float:
    return time.time()


# ── Memória de longo prazo ────────────────────────────────────────────────────

def add_memory(
    content: str,
    *,
    scope: str = "global",
    kind: str = "fact",
    metadata: Optional[dict] = None,
    importance: float = 0.5,
) -> str:
    mid = str(uuid.uuid4())
    ts = _now()
    with _lock:
        with _conn() as c:
            c.execute(
                "INSERT INTO long_term (id, scope, kind, content, metadata, importance, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (mid, scope, kind, content.strip(), json.dumps(metadata or {}), importance, ts, ts),
            )
    return mid


def list_memories(
    scope: str = "global",
    kind: Optional[str] = None,
    limit: int = 50,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    q = "SELECT * FROM long_term WHERE scope = ?"
    params: list = [scope]
    if kind:
        q += " AND kind = ?"
        params.append(kind)
    if search:
        q += " AND content LIKE ?"
        params.append(f"%{search}%")
    q += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
    params.append(limit)
    with _lock:
        with _conn() as c:
            rows = c.execute(q, params).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "scope": r["scope"],
                "kind": r["kind"],
                "content": r["content"],
                "metadata": json.loads(r["metadata"] or "{}"),
                "importance": r["importance"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
        )
    return out


def delete_memory(mem_id: str) -> bool:
    with _lock:
        with _conn() as c:
            cur = c.execute("DELETE FROM long_term WHERE id = ?", (mem_id,))
            return cur.rowcount > 0


def clear_memories(scope: str = "global") -> int:
    with _lock:
        with _conn() as c:
            cur = c.execute("DELETE FROM long_term WHERE scope = ?", (scope,))
            return cur.rowcount


def memory_block_for_prompt(scope: str = "global", limit: int = 30) -> str:
    """Texto compacto para injetar no system prompt."""
    items = list_memories(scope=scope, limit=limit)
    if not items:
        return "(nenhuma memória de longo prazo ainda)"
    lines = []
    for it in items:
        lines.append(f"- [{it['kind']}] {it['content']}")
    return "\n".join(lines)


# ── Histórico de conversa ─────────────────────────────────────────────────────

def ensure_session(session_id: Optional[str] = None, title: str = "") -> str:
    sid = session_id or str(uuid.uuid4())
    ts = _now()
    with _lock:
        with _conn() as c:
            row = c.execute("SELECT id FROM sessions WHERE id = ?", (sid,)).fetchone()
            if not row:
                c.execute(
                    "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (sid, title or "Conversa", ts, ts),
                )
            else:
                c.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (ts, sid))
    return sid


def append_message(session_id: str, role: str, content: str) -> None:
    ensure_session(session_id)
    with _lock:
        with _conn() as c:
            c.execute(
                "INSERT INTO conversations (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), session_id, role, content, _now()),
            )
            c.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (_now(), session_id))


def get_history(session_id: str, limit: int = 40) -> List[Dict[str, str]]:
    with _lock:
        with _conn() as c:
            rows = c.execute(
                "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit),
            ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def list_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    with _lock:
        with _conn() as c:
            rows = c.execute(
                "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def clear_session(session_id: str) -> None:
    with _lock:
        with _conn() as c:
            c.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


# ── Aprendizado automático simples (extrai preferências de frases-chave) ─────

LEARN_HINTS = (
    "lembre que",
    "lembre-se",
    "sempre que",
    "prefiro",
    "eu gosto",
    "não gosto",
    "meu nome é",
    "me chamo",
    "minha preferência",
    "guarde isso",
    "memorize",
    "aprenda que",
)


def maybe_learn_from_user(text: str, scope: str = "global") -> Optional[str]:
    """Se o usuário pedir explicitamente para lembrar, grava na memória de longo prazo."""
    low = (text or "").lower().strip()
    if not any(h in low for h in LEARN_HINTS):
        return None
    # grava a frase inteira como fato
    mid = add_memory(text.strip(), scope=scope, kind="preference", importance=0.8)
    return mid
