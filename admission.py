"""Controle de entrada do Cookie AI: no máximo N usuários ativos ao mesmo tempo.

Regras
- "Ativo" = usuário que mandou algo nos últimos ACTIVE_TTL segundos (padrão 10 min).
- Cabem MAX_ACTIVE_USERS ativos (padrão 180). O próximo espera em fila FIFO.
- Quem espera precisa "bater o ponto" (chamar /api/queue/join) a cada poucos
  segundos; se parar, sai da fila (QUEUE_TTL) e não trava ninguém.
- Quando abre vaga, o primeiro da fila é promovido. Se não aparecer para
  assumir a vaga em CLAIM_TTL, a vaga volta para o próximo.
- Ninguém "fura" a fila: usuário novo entra atrás de quem já espera.

O estado fica na memória do processo. Com mais de uma máquina no Fly cada uma
teria a sua própria contagem (hoje o fly.toml usa uma máquina).
"""
import os
import threading
import time


def _env_int(nome, padrao):
    try:
        return int(os.environ.get(nome, padrao))
    except (TypeError, ValueError):
        return padrao


class AdmissionControl:
    def __init__(self, max_active=180, active_ttl=600, queue_ttl=30,
                 claim_ttl=45, max_queue=2000, clock=time.time):
        self.max_active = max_active          # 0 = sem limite
        self.active_ttl = active_ttl
        self.queue_ttl = queue_ttl
        self.claim_ttl = claim_ttl
        self.max_queue = max_queue
        self._clock = clock
        self._lock = threading.Lock()
        self._active = {}     # uid -> {"seen": t, "claimed": bool}
        self._queue = []      # [{"uid": str, "seen": t, "since": t}]

    # ── interno (chamar com o lock) ──────────────────────────────────────────
    def _purge(self, now):
        for uid in list(self._active):
            a = self._active[uid]
            ttl = self.active_ttl if a["claimed"] else self.claim_ttl
            if now - a["seen"] > ttl:
                del self._active[uid]
        self._queue = [q for q in self._queue if now - q["seen"] <= self.queue_ttl]

    def _promote(self, now):
        while self._queue and len(self._active) < self.max_active:
            q = self._queue.pop(0)
            self._active[q["uid"]] = {"seen": now, "claimed": False}

    def _eta(self, pos, now):
        """Segundos até abrir a vaga da posição `pos` (1 = primeiro da fila)."""
        free = max(0, self.max_active - len(self._active))
        if pos <= free:
            return 0
        saidas = sorted(
            a["seen"] + (self.active_ttl if a["claimed"] else self.claim_ttl)
            for a in self._active.values()
        )
        i = pos - free - 1
        if i < len(saidas):
            return max(1, int(saidas[i] - now))
        return self.active_ttl

    def _snapshot(self, uid, now):
        base = {"limit": self.max_active, "active": len(self._active),
                "waiting": len(self._queue)}
        if uid in self._active:
            self._active[uid]["claimed"] = True
            return dict(base, status="active", position=0, eta_seconds=0)
        for i, q in enumerate(self._queue):
            if q["uid"] == uid:
                return dict(base, status="waiting", position=i + 1,
                            ahead=i, eta_seconds=self._eta(i + 1, now))
        return dict(base, status="none", position=0, eta_seconds=0)

    # ── API pública ──────────────────────────────────────────────────────────
    def enter(self, uid, touch=True):
        """Pede/renova a entrada. Retorna dict com status: active | waiting | full."""
        if not self.max_active:
            return {"status": "active", "position": 0, "eta_seconds": 0,
                    "limit": 0, "active": 0, "waiting": 0}
        now = self._clock()
        with self._lock:
            self._purge(now)
            if uid in self._active:
                if touch:
                    self._active[uid]["seen"] = now
                self._active[uid]["claimed"] = True
                return self._snapshot(uid, now)
            for q in self._queue:
                if q["uid"] == uid:
                    q["seen"] = now
                    break
            else:
                if len(self._queue) >= self.max_queue:
                    return dict(self._snapshot(uid, now), status="full")
                self._queue.append({"uid": uid, "seen": now, "since": now})
            self._promote(now)
            return self._snapshot(uid, now)

    def leave(self, uid):
        with self._lock:
            self._active.pop(uid, None)
            self._queue = [q for q in self._queue if q["uid"] != uid]
            self._promote(self._clock())

    def stats(self):
        now = self._clock()
        with self._lock:
            self._purge(now)
            self._promote(now)
            return {"active": len(self._active), "waiting": len(self._queue),
                    "limit": self.max_active}


ADMISSION = AdmissionControl(
    max_active=_env_int("MAX_ACTIVE_USERS", 180),
    active_ttl=_env_int("ACTIVE_TTL_SECONDS", 600),
    queue_ttl=_env_int("QUEUE_TTL_SECONDS", 30),
    claim_ttl=_env_int("CLAIM_TTL_SECONDS", 45),
    max_queue=_env_int("MAX_QUEUE_LENGTH", 2000),
)
