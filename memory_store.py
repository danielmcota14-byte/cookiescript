"""
Memória persistente da Cookie AI.

- Conversas por sessão (histórico curto)
- Memória de longo prazo / aprendizagem (fatos, preferências)
  SQLite em data/cookie_memory.db, com fallback para JSON se o disco falhar.

Aprendizado automático ampliado: não depende só de "lembre que...".
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent


def _pick_data_dir() -> Path:
    preferred = Path(os.environ.get("COOKIE_DATA_DIR", str(BASE_DIR / "data")))
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        test = preferred / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return preferred
    except Exception:
        fallback = Path(os.environ.get("TMPDIR", "/tmp")) / "cookie_ai_data"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


DATA_DIR = _pick_data_dir()
DB_PATH = DATA_DIR / "cookie_memory.db"
JSON_FALLBACK = DATA_DIR / "cookie_memory.json"

_lock = threading.RLock()
_use_json = False


def _now() -> float:
    return time.time()


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=60)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA journal_mode=DELETE")
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass
    return c


def _load_json() -> dict:
    if not JSON_FALLBACK.exists():
        return {"long_term": [], "conversations": [], "sessions": []}
    try:
        return json.loads(JSON_FALLBACK.read_text(encoding="utf-8"))
    except Exception:
        return {"long_term": [], "conversations": [], "sessions": []}


def _save_json(data: dict) -> None:
    tmp = JSON_FALLBACK.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    tmp.replace(JSON_FALLBACK)


def init_db() -> None:
    global _use_json
    with _lock:
        try:
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
            _use_json = False
        except Exception as e:
            print(f"[memory] SQLite indisponível ({e}); usando JSON em {JSON_FALLBACK}")
            _use_json = True
            if not JSON_FALLBACK.exists():
                _save_json({"long_term": [], "conversations": [], "sessions": []})


def _migrate_owner() -> None:
    """Sessoes passam a ter dono (scope). Sessoes antigas ficam sem dono e nunca sao reaproveitadas."""
    if _use_json:
        return
    try:
        with _conn() as c:
            cols = [r[1] for r in c.execute("PRAGMA table_info(sessions)").fetchall()]
            if "owner" not in cols:
                c.execute("ALTER TABLE sessions ADD COLUMN owner TEXT DEFAULT ''")
    except Exception as e:
        print(f"[memory] migracao owner: {e}")


init_db()
_migrate_owner()

# Janela de contexto: a IA so "enxerga" as ultimas N mensagens. O que sai da janela e esquecido.
CONTEXT_LIMIT = max(2, int(os.environ.get("COOKIE_CONTEXT_LIMIT", "20")))
MAX_MSG_CHARS = 6000      # corta mensagens gigantes dentro da janela
MAX_CTX_CHARS = 24000     # teto total do historico enviado a IA (evita travar)
HARD_CAP = 400            # maximo guardado por sessao no disco


def add_memory(
    content: str,
    *,
    scope: str = "global",
    kind: str = "fact",
    metadata: Optional[dict] = None,
    importance: float = 0.5,
) -> str:
    content = (content or "").strip()
    if not content:
        return ""
    existing = list_memories(scope=scope, limit=100)
    low = content.lower()
    for it in existing:
        if (it.get("kind") or "fact") != (kind or "fact"):
            continue
        if it["content"].lower() == low:
            return it["id"]
        if low in it["content"].lower() or it["content"].lower() in low:
            if len(content) > len(it["content"]):
                update_memory(it["id"], content=content, importance=max(importance, it.get("importance") or 0.5))
                return it["id"]

    mid = str(uuid.uuid4())
    ts = _now()
    with _lock:
        if _use_json:
            data = _load_json()
            data["long_term"].append(
                {
                    "id": mid,
                    "scope": scope,
                    "kind": kind,
                    "content": content,
                    "metadata": metadata or {},
                    "importance": importance,
                    "created_at": ts,
                    "updated_at": ts,
                }
            )
            _save_json(data)
        else:
            with _conn() as c:
                c.execute(
                    "INSERT INTO long_term (id, scope, kind, content, metadata, importance, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (mid, scope, kind, content, json.dumps(metadata or {}), importance, ts, ts),
                )
    return mid


def update_memory(mem_id: str, content: str = None, importance: float = None) -> bool:
    with _lock:
        if _use_json:
            data = _load_json()
            for it in data["long_term"]:
                if it["id"] == mem_id:
                    if content is not None:
                        it["content"] = content
                    if importance is not None:
                        it["importance"] = importance
                    it["updated_at"] = _now()
                    _save_json(data)
                    return True
            return False
        fields = []
        params = []
        if content is not None:
            fields.append("content = ?")
            params.append(content)
        if importance is not None:
            fields.append("importance = ?")
            params.append(importance)
        if not fields:
            return False
        fields.append("updated_at = ?")
        params.append(_now())
        params.append(mem_id)
        with _conn() as c:
            cur = c.execute(f"UPDATE long_term SET {', '.join(fields)} WHERE id = ?", params)
            return cur.rowcount > 0


def list_memories(
    scope: str = "global",
    kind: Optional[str] = None,
    limit: int = 50,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    with _lock:
        if _use_json:
            items = [x for x in _load_json().get("long_term", []) if x.get("scope") == scope]
            if kind:
                items = [x for x in items if x.get("kind") == kind]
            if search:
                s = search.lower()
                items = [x for x in items if s in (x.get("content") or "").lower()]
            items.sort(key=lambda x: (-(x.get("importance") or 0), -(x.get("updated_at") or 0)))
            return items[:limit]
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
        try:
            with _conn() as c:
                rows = c.execute(q, params).fetchall()
        except Exception as e:
            print(f"[memory] list error: {e}")
            return []
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


def delete_memory(mem_id: str, scope: Optional[str] = None) -> bool:
    """Se scope for informado, so apaga memoria que pertence a esse scope."""
    with _lock:
        if _use_json:
            data = _load_json()
            before = len(data["long_term"])
            data["long_term"] = [x for x in data["long_term"]
                                 if not (x.get("id") == mem_id and (scope is None or x.get("scope") == scope))]
            _save_json(data)
            return len(data["long_term"]) < before
        with _conn() as c:
            if scope is None:
                cur = c.execute("DELETE FROM long_term WHERE id = ?", (mem_id,))
            else:
                cur = c.execute("DELETE FROM long_term WHERE id = ? AND scope = ?", (mem_id, scope))
            return cur.rowcount > 0


def clear_memories(scope: str = "global") -> int:
    with _lock:
        if _use_json:
            data = _load_json()
            before = len(data["long_term"])
            data["long_term"] = [x for x in data["long_term"] if x.get("scope") != scope]
            _save_json(data)
            return before - len(data["long_term"])
        with _conn() as c:
            cur = c.execute("DELETE FROM long_term WHERE scope = ?", (scope,))
            return cur.rowcount




def memory_count(scope: str = "global") -> int:
    return len(list_memories(scope=scope, limit=1000))


def _session_row(sid: str) -> Optional[dict]:
    if _use_json:
        for x in _load_json().get("sessions", []):
            if x.get("id") == sid:
                return x
        return None
    with _conn() as c:
        r = c.execute("SELECT id, owner FROM sessions WHERE id = ?", (sid,)).fetchone()
    return dict(r) if r else None


def owns_session(session_id: str, owner: str) -> bool:
    row = _session_row(session_id) if session_id else None
    return bool(row) and bool(owner) and (row.get("owner") or "") == owner


def ensure_session(session_id: Optional[str] = None, title: str = "", owner: str = "") -> str:
    """Devolve uma sessao DO dono. Se o id pertence a outra pessoa (ou nao existe), cria uma nova:
    ninguem consegue entrar na conversa de outro usuario so conhecendo o id."""
    ts = _now()
    with _lock:
        sid = session_id or ""
        if sid and not owns_session(sid, owner):
            sid = ""
        if sid:
            if _use_json:
                data = _load_json()
                for x in data["sessions"]:
                    if x["id"] == sid:
                        x["updated_at"] = ts
                _save_json(data)
            else:
                with _conn() as c:
                    c.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (ts, sid))
            return sid
        sid = str(uuid.uuid4())
        if _use_json:
            data = _load_json()
            data.setdefault("sessions", []).append(
                {"id": sid, "title": title or "Conversa", "owner": owner, "created_at": ts, "updated_at": ts})
            _save_json(data)
        else:
            with _conn() as c:
                c.execute("INSERT INTO sessions (id, title, owner, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                          (sid, title or "Conversa", owner, ts, ts))
    return sid


def append_message(session_id: str, role: str, content: str) -> None:
    mid = str(uuid.uuid4())
    ts = _now()
    with _lock:
        if _use_json:
            data = _load_json()
            data.setdefault("conversations", []).append(
                {"id": mid, "session_id": session_id, "role": role, "content": content, "created_at": ts})
            if len(data["conversations"]) > 4000:
                data["conversations"] = data["conversations"][-3000:]
            for s_ in data.get("sessions", []):
                if s_["id"] == session_id:
                    s_["updated_at"] = ts
            _save_json(data)
            return
        with _conn() as c:
            c.execute("INSERT INTO conversations (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                      (mid, session_id, role, content, ts))
            c.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (ts, session_id))


def count_messages(session_id: str) -> int:
    with _lock:
        if _use_json:
            return sum(1 for x in _load_json().get("conversations", []) if x.get("session_id") == session_id)
        with _conn() as c:
            return c.execute("SELECT COUNT(*) FROM conversations WHERE session_id = ?", (session_id,)).fetchone()[0]


def forgotten_count(session_id: str) -> int:
    """Quantas mensagens ja sairam da janela de contexto (a IA esqueceu)."""
    return max(0, count_messages(session_id) - CONTEXT_LIMIT)


def get_history(session_id: str, limit: Optional[int] = None, owner: str = "") -> List[Dict[str, str]]:
    """Ultimas `limit` mensagens (ordem cronologica). So devolve se a sessao for do `owner`."""
    limit = limit or CONTEXT_LIMIT
    if not owns_session(session_id, owner):
        return []
    with _lock:
        if _use_json:
            rows = [x for x in _load_json().get("conversations", []) if x.get("session_id") == session_id]
            rows.sort(key=lambda x: x.get("created_at") or 0)
            rows = rows[-limit:]
        else:
            with _conn() as c:
                rows = c.execute(
                    "SELECT role, content FROM (SELECT role, content, created_at FROM conversations "
                    "WHERE session_id = ? ORDER BY created_at DESC LIMIT ?) ORDER BY created_at ASC",
                    (session_id, limit)).fetchall()
    out, total = [], 0
    for r in reversed(rows):                      # do mais novo para o mais antigo
        txt = (r["content"] or "")[:MAX_MSG_CHARS]
        if total + len(txt) > MAX_CTX_CHARS and out:
            break                                 # estourou o teto: o resto tambem e esquecido
        total += len(txt)
        out.append({"role": r["role"], "content": txt})
    return list(reversed(out))


def context_info(session_id: str, forgotten_before: int = 0) -> Dict[str, Any]:
    total = count_messages(session_id)
    forgotten = max(0, total - CONTEXT_LIMIT)
    return {"limit": CONTEXT_LIMIT, "used": min(total, CONTEXT_LIMIT), "total": total,
            "forgotten": forgotten, "forgot_now": forgotten > forgotten_before}


def prune_session(session_id: str, keep: int = HARD_CAP) -> None:
    with _lock:
        if _use_json:
            data = _load_json()
            mine = sorted([x for x in data.get("conversations", []) if x.get("session_id") == session_id],
                          key=lambda x: x.get("created_at") or 0)
            drop = {x["id"] for x in mine[:-keep]} if len(mine) > keep else set()
            if drop:
                data["conversations"] = [x for x in data["conversations"] if x["id"] not in drop]
                _save_json(data)
            return
        with _conn() as c:
            c.execute("DELETE FROM conversations WHERE session_id = ? AND id NOT IN "
                      "(SELECT id FROM conversations WHERE session_id = ? ORDER BY created_at DESC LIMIT ?)",
                      (session_id, session_id, keep))


def list_sessions(limit: int = 20, owner: str = "") -> List[Dict[str, Any]]:
    if not owner:
        return []
    with _lock:
        if _use_json:
            sessions = [x for x in _load_json().get("sessions", []) if (x.get("owner") or "") == owner]
            sessions.sort(key=lambda x: -(x.get("updated_at") or 0))
            return [{k: v for k, v in x.items() if k != "owner"} for x in sessions[:limit]]
        with _conn() as c:
            rows = c.execute("SELECT id, title, created_at, updated_at FROM sessions WHERE owner = ? "
                             "ORDER BY updated_at DESC LIMIT ?", (owner, limit)).fetchall()
    return [dict(r) for r in rows]


def clear_session(session_id: str, owner: str = "") -> bool:
    if not owns_session(session_id, owner):
        return False
    with _lock:
        if _use_json:
            data = _load_json()
            data["conversations"] = [x for x in data.get("conversations", []) if x.get("session_id") != session_id]
            data["sessions"] = [x for x in data.get("sessions", []) if x.get("id") != session_id]
            _save_json(data)
            return True
        with _conn() as c:
            c.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    return True


EXPLICIT_HINTS = (
    "lembre que", "lembre-se", "lembra que", "guarde isso", "guarde que",
    "memorize", "memoriza", "aprenda que", "não esqueça", "nao esqueca",
    "anote que", "salva na memória", "salva na memoria", "grave isso", "grave que",
    "anota que", "fica sabendo", "importante:", "para futuro",
)

FACT_PATTERNS = [
    (re.compile(r"(?:meu nome (?:é|e)|me chamo|eu sou o|eu sou a)\s+([A-Za-zÀ-ÿ0-9 ._-]{2,40})", re.I), "name", 0.95),
    (re.compile(r"(?:pode me chamar de|me chama de)\s+([A-Za-zÀ-ÿ0-9 ._-]{2,40})", re.I), "name", 0.9),
    (re.compile(r"(?:eu (?:prefiro|gosto de|uso|adoro)|prefiro|gosto de|adoro)\s+(.{4,100})", re.I), "preference", 0.85),
    (re.compile(r"(?:não gosto|nao gosto|odeio|detesto)\s+(?:de\s+)?(.{4,80})", re.I), "preference", 0.8),
    (re.compile(r"(?:eu trabalho(?:o)? (?:com|em|como)|minha (?:empresa|área|area|profissão|profissao) (?:é|e))\s+(.{4,100})", re.I), "work", 0.85),
    (re.compile(r"(?:minha linguagem|linguagem (?:favorita|preferida)|sempre (?:uso|escrevo) em|stack(?: é| e)?)\s+(.{2,60})", re.I), "preference", 0.9),
    (re.compile(r"(?:meu (?:email|e-mail|github|usuário|usuario|user) (?:é|e))\s+(\S+)", re.I), "identity", 0.9),
    (re.compile(r"(?:eu moro (?:em|no|na)|sou de|vivo em)\s+(.{3,60})", re.I), "location", 0.75),
    (re.compile(r"(?:meu projeto|estou (?:fazendo|criando|desenvolvendo)|trabalhando (?:em|no|na))\s+(.{4,100})", re.I), "project", 0.8),
    (re.compile(r"(?:eu tenho|tenho)\s+(\d{1,3})\s+anos", re.I), "identity", 0.7),
    (re.compile(r"(?:responde em|fale em|use o idioma)\s+(.{3,40})", re.I), "preference", 0.85),
    (re.compile(r"(?:sempre|nunca)\s+(.{6,80})", re.I), "rule", 0.7),
]


def maybe_learn_from_user(text: str, scope: str = "global") -> Optional[str]:
    """Aprende com pedidos explícitos, padrões e frases relevantes sobre o usuário."""
    raw = (text or "").strip()
    if not raw or len(raw) < 4:
        return None
    low = raw.lower()
    learned_ids = []

    for h in EXPLICIT_HINTS:
        if h in low:
            idx = low.find(h)
            rest = raw[idx + len(h) :].strip(" :,-")
            content = rest if len(rest) >= 4 else raw
            mid = add_memory(content[:600], scope=scope, kind="preference", importance=0.9)
            if mid:
                learned_ids.append(mid)
            break

    for rx, kind, imp in FACT_PATTERNS:
        m = rx.search(raw)
        if m:
            snippet = m.group(0).strip()
            if len(snippet) >= 6:
                mid = add_memory(snippet[:500], scope=scope, kind=kind, importance=imp)
                if mid:
                    learned_ids.append(mid)

    if re.search(r"\beu sou\b", low) and len(raw) < 200:
        mid = add_memory(raw[:400], scope=scope, kind="identity", importance=0.75)
        if mid:
            learned_ids.append(mid)

    if any(w in low for w in ("resposta curta", "seja breve", "detalhado", "objetivo", "sem enrolação", "sem enrolacao")):
        mid = add_memory(raw[:400], scope=scope, kind="style", importance=0.8)
        if mid:
            learned_ids.append(mid)

    return learned_ids[0] if learned_ids else None


def learn_from_exchange(user_text: str, assistant_text: str, scope: str = "global") -> List[str]:
    ids = []
    mid = maybe_learn_from_user(user_text, scope=scope)
    if mid:
        ids.append(mid)
    asst = assistant_text or ""
    for rx in (
        re.compile(r"(?:anotei|guardei|lembrei|vou lembrar) que\s+(.{8,120})", re.I),
        re.compile(r"(?:preferência|preferencia) registrada[:\s]+(.{8,120})", re.I),
    ):
        m = rx.search(asst)
        if m:
            mid2 = add_memory(m.group(1).strip()[:400], scope=scope, kind="preference", importance=0.8)
            if mid2:
                ids.append(mid2)
    return ids


def user_scope(user_id: str) -> str:
    """Cada pessoa tem memória isolada. Nunca compartilhar entre usuários."""
    uid = (user_id or "").strip() or "anonymous"
    uid = "".join(ch for ch in uid if ch.isalnum() or ch in "-_")[:80]
    return f"user:{uid or 'anonymous'}"


def update_user_profile(user_text: str, assistant_text: str = "", scope: str = "global") -> list:
    """
    Memória contínua estilo ChatGPT/Claude:
    grava notas em 1ª pessoa e mantém um perfil consolidado do usuário.
    """
    ids = list(learn_from_exchange(user_text or "", assistant_text or "", scope=scope) or [])
    raw = (user_text or "").strip()
    if not raw:
        return ids

    low = raw.lower()
    first_person = any(
        p in low
        for p in (
            "eu ", "meu ", "minha ", "meus ", "minhas ", "sou ", "estou ",
            "trabalho", "prefiro", "gosto", "odeio", "quero que você",
            "quero que voce", "sempre ", "nunca ", "não quero", "nao quero",
            "lembre", "guarde", "meu projeto", "estou fazendo",
        )
    )
    is_question = raw.strip().endswith("?") and len(raw) < 120
    if first_person and not is_question and len(raw) >= 12:
        mid = add_memory(raw[:500], scope=scope, kind="note", importance=0.65)
        if mid:
            ids.append(mid)

    notes = list_memories(scope=scope, limit=50)
    useful = [it for it in notes if it.get("kind") != "profile"]
    if useful:
        lines = [f"- {it.get('content')}" for it in useful[:30]]
        profile = "Perfil do usuário (memória contínua):\n" + "\n".join(lines)
        for it in notes:
            if it.get("kind") == "profile":
                try:
                    delete_memory(it["id"])
                except Exception:
                    pass
        mid = add_memory(profile[:3500], scope=scope, kind="profile", importance=1.0)
        if mid:
            ids.append(mid)
    return ids


def memory_block_for_prompt(scope: str = "global", limit: int = 40) -> str:
    items = list_memories(scope=scope, limit=max(limit, 50))
    if not items:
        return (
            "(nenhuma memória deste usuário ainda — "
            "aprenda naturalmente com o que ele disser sobre si, projetos e preferências, "
            "como o ChatGPT faz)"
        )
    profiles = [it for it in items if it.get("kind") == "profile"]
    others = [it for it in items if it.get("kind") != "profile"]
    lines = []
    for it in profiles[:1]:
        lines.append(it["content"])
    for it in others[: max(1, limit - 1)]:
        lines.append(f"- [{it['kind']}] {it['content']}")
    return "\n".join(lines)
