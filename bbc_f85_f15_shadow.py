"""Shadow-first control plane for frozen B27DQ LONG + SHORT20.

No exchange writes live here. The module owns causal closed-bar gating, durable
state, one-BTC transactional lock, ACK-gated order lifecycle, floor replacement
ACK semantics, and startup reconciliation primitives.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

STATE_IDLE = "IDLE"
STATE_ENTRY_PENDING = "ENTRY_PENDING_ACK"
STATE_ACTIVE = "ACTIVE"
STATE_HALT = "HALT_MISMATCH"


@dataclass
class LiveState:
    lifecycle: str = STATE_IDLE
    last_closed_bar: Optional[str] = None
    candidate_id: Optional[str] = None
    side: Optional[str] = None
    source: Optional[str] = None
    entry_order_id: Optional[str] = None
    entry_ts: Optional[str] = None
    expected_exit_ts: Optional[str] = None
    runner_armed: bool = False
    active_floor: Optional[float] = None
    pending_floor: Optional[float] = None
    pending_floor_order_id: Optional[str] = None
    exchange_position_id: Optional[str] = None
    halt_reason: Optional[str] = None


class SQLiteDurableStore:
    """Transactional store used by shadow/CI; API mirrors a shared DB/CAS backend."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._init()

    def connect(self):
        c = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _init(self):
        with self.connect() as c:
            c.execute("CREATE TABLE IF NOT EXISTS engine_state (engine TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS position_lock (symbol TEXT PRIMARY KEY, owner TEXT NOT NULL, candidate_id TEXT NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS processed_event (engine TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY(engine,event_id))")

    def load(self, engine: str) -> LiveState:
        with self.connect() as c:
            r = c.execute("SELECT payload FROM engine_state WHERE engine=?", (engine,)).fetchone()
        return LiveState(**json.loads(r[0])) if r else LiveState()

    def save(self, engine: str, state: LiveState):
        payload = json.dumps(asdict(state), sort_keys=True)
        with self.connect() as c:
            c.execute("INSERT INTO engine_state(engine,payload) VALUES(?,?) ON CONFLICT(engine) DO UPDATE SET payload=excluded.payload", (engine, payload))

    def mark_event_once(self, engine: str, event_id: str) -> bool:
        with self.connect() as c:
            try:
                c.execute("INSERT INTO processed_event(engine,event_id) VALUES(?,?)", (engine, event_id))
                return True
            except sqlite3.IntegrityError:
                return False

    def acquire_btc(self, owner: str, candidate_id: str) -> bool:
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT owner,candidate_id FROM position_lock WHERE symbol='BTCUSDT'").fetchone()
            if row is None:
                c.execute("INSERT INTO position_lock(symbol,owner,candidate_id) VALUES('BTCUSDT',?,?)", (owner, candidate_id))
                c.execute("COMMIT")
                return True
            if row == (owner, candidate_id):
                c.execute("COMMIT")
                return True
            c.execute("ROLLBACK")
            return False

    def release_btc(self, owner: str, candidate_id: Optional[str] = None):
        with self.connect() as c:
            if candidate_id is None:
                c.execute("DELETE FROM position_lock WHERE symbol='BTCUSDT' AND owner=?", (owner,))
            else:
                c.execute("DELETE FROM position_lock WHERE symbol='BTCUSDT' AND owner=? AND candidate_id=?", (owner, candidate_id))

    def lock_row(self):
        with self.connect() as c:
            return c.execute("SELECT owner,candidate_id FROM position_lock WHERE symbol='BTCUSDT'").fetchone()


class ShadowControlPlane:
    def __init__(self, engine_id: str, store: SQLiteDurableStore):
        self.engine_id = engine_id
        self.store = store
        self.state = store.load(engine_id)

    @staticmethod
    def _ts(value):
        import pandas as pd
        return pd.Timestamp(value)

    @staticmethod
    def _valid_5m(ts) -> bool:
        t = ShadowControlPlane._ts(ts)
        return t.second == 0 and t.microsecond == 0 and t.minute % 5 == 0

    def _persist(self):
        self.store.save(self.engine_id, self.state)

    def on_closed_bar(self, close_ts, intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Consume one *completed* 5m boundary and return entry-submit intents.

        All supplied candidate intents must have entry_ts == close_ts, which is the
        frozen same-bar-confirmation close / next-bar-open boundary.
        """
        t = self._ts(close_ts)
        if not self._valid_5m(t):
            raise ValueError("closed bar timestamp is not 5m aligned")
        if self.state.last_closed_bar is not None:
            last = self._ts(self.state.last_closed_bar)
            if t < last:
                self.state.lifecycle = STATE_HALT
                self.state.halt_reason = "OUT_OF_ORDER_CLOSED_BAR"
                self._persist()
                raise RuntimeError("out-of-order closed bar")
            if t == last:
                return []

        self.state.last_closed_bar = t.isoformat()
        self._persist()
        if self.state.lifecycle == STATE_HALT:
            return []

        out = []
        ordered = sorted(intents, key=lambda x: (0 if x["side"] == "LONG" else 1, int(x.get("clock_min", -1)), x["candidate_id"]))
        for it in ordered:
            if self._ts(it["entry_ts"]) != t:
                raise AssertionError("candidate exposed before/after frozen next-open boundary")
            event_id = f"ENTRY|{it['candidate_id']}|{t.isoformat()}"
            if not self.store.mark_event_once(self.engine_id, event_id):
                continue
            if self.state.lifecycle != STATE_IDLE:
                continue
            cid = str(it["candidate_id"])
            if not self.store.acquire_btc(self.engine_id, cid):
                continue
            self.state.lifecycle = STATE_ENTRY_PENDING
            self.state.candidate_id = cid
            self.state.side = str(it["side"])
            self.state.source = str(it.get("source", ""))
            self.state.entry_ts = t.isoformat()
            self.state.expected_exit_ts = self._ts(it["exit_ts"]).isoformat()
            self.state.entry_order_id = f"shadow-entry:{cid}"
            self._persist()
            out.append({"action":"SUBMIT_ENTRY", "candidate_id":cid, "order_id":self.state.entry_order_id, "side":self.state.side})
            break
        return out

    def ack_entry(self, order_id: str, exchange_position_id: Optional[str] = None):
        if self.state.lifecycle != STATE_ENTRY_PENDING or order_id != self.state.entry_order_id:
            raise RuntimeError("entry ACK does not match pending order")
        self.state.lifecycle = STATE_ACTIVE
        self.state.exchange_position_id = exchange_position_id or f"shadow-pos:{self.state.candidate_id}"
        self._persist()

    def request_floor(self, floor: float, order_id: str):
        if self.state.lifecycle != STATE_ACTIVE:
            raise RuntimeError("cannot replace floor without active position")
        if self.state.pending_floor_order_id is not None:
            raise RuntimeError("floor replacement already pending ACK")
        if self.state.active_floor is not None and float(floor) <= float(self.state.active_floor):
            raise ValueError("floor must ratchet upward for LONG runner")
        self.state.pending_floor = float(floor)
        self.state.pending_floor_order_id = str(order_id)
        self._persist()

    def ack_floor(self, order_id: str):
        if order_id != self.state.pending_floor_order_id or self.state.pending_floor is None:
            raise RuntimeError("floor ACK does not match pending replacement")
        self.state.active_floor = float(self.state.pending_floor)
        self.state.pending_floor = None
        self.state.pending_floor_order_id = None
        self.state.runner_armed = True
        self._persist()

    def close_position(self, candidate_id: Optional[str] = None):
        cid = candidate_id or self.state.candidate_id
        if cid:
            self.store.release_btc(self.engine_id, cid)
        keep_bar = self.state.last_closed_bar
        self.state = LiveState(last_closed_bar=keep_bar)
        self._persist()

    def reconcile_exchange(self, exchange_position: Optional[dict[str, Any]]):
        """Exchange is authoritative for whether a BTC position exists."""
        local_open = self.state.lifecycle in (STATE_ENTRY_PENDING, STATE_ACTIVE)
        ex_open = bool(exchange_position and float(exchange_position.get("qty", 0)) != 0)

        if not ex_open and local_open:
            self.close_position()
            return "CLEARED_STALE_LOCAL"

        if ex_open and not local_open:
            side = str(exchange_position.get("side", ""))
            cid = str(exchange_position.get("candidate_id") or f"EXCHANGE_ADOPT:{exchange_position.get('position_id','UNKNOWN')}")
            if not self.store.acquire_btc(self.engine_id, cid):
                self.state.lifecycle = STATE_HALT
                self.state.halt_reason = "EXCHANGE_OPEN_LOCK_CONFLICT"
                self._persist()
                return "HALT_LOCK_CONFLICT"
            self.state.lifecycle = STATE_ACTIVE
            self.state.candidate_id = cid
            self.state.side = side
            self.state.source = "EXCHANGE_RECONCILED"
            self.state.exchange_position_id = str(exchange_position.get("position_id") or "UNKNOWN")
            self._persist()
            return "ADOPTED_EXCHANGE_POSITION"

        if ex_open and local_open:
            ex_side = str(exchange_position.get("side", ""))
            if self.state.side and ex_side and self.state.side != ex_side:
                self.state.lifecycle = STATE_HALT
                self.state.halt_reason = "EXCHANGE_LOCAL_SIDE_MISMATCH"
                self._persist()
                return "HALT_SIDE_MISMATCH"
            return "MATCHED"

        return "FLAT_MATCHED"
