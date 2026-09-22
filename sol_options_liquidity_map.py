"""SOL Options Liquidity Map V1.

Prospective causal options-chain map for SOLUSDT.

Important:
- gamma * OI is a concentration magnitude only, NOT dealer GEX.
- V1 does not alter the SOL detector or authorize a trade.
- snapshots are append-only and later studies must align only to snapshots
  whose timestamp is <= the detector decision timestamp.
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

import requests

MAP_VERSION = "SOL_OPTIONS_LIQUIDITY_MAP_V1"
EAPI = "https://eapi.binance.com"
UNDERLYING = "SOLUSDT"
UNDERLYING_ASSET = "SOL"
NEAREST_EXPIRIES = 3
IV_CONFLUENCE_PCT_SPOT = 1.0


def _get(path: str, params: dict | None = None, timeout: int = 15) -> Any:
    last = None
    for attempt in range(4):
        try:
            r = requests.get(EAPI + path, params=params or {}, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last = exc
            if attempt < 3:
                time.sleep(1.0 + attempt)
    raise RuntimeError(f"Binance Options fetch failed {path}: {last}")


def fetch_live_inputs() -> dict:
    info = _get("/eapi/v1/exchangeInfo")
    marks = _get("/eapi/v1/mark")
    index = _get("/eapi/v1/index", {"underlying": UNDERLYING})

    snap_ms = int(index["time"])
    sol_info = [
        x for x in info.get("optionSymbols", [])
        if x.get("underlying") == UNDERLYING and x.get("status") == "TRADING"
    ]

    expiry_by_ms = {}
    for x in sol_info:
        expiry_ms = int(x["expiryDate"])
        if expiry_ms > snap_ms:
            code = str(x["symbol"]).split("-")[1]
            expiry_by_ms[expiry_ms] = code

    expiries = [
        {"expiryDate": expiry_ms, "code": code}
        for expiry_ms, code in sorted(expiry_by_ms.items())[:NEAREST_EXPIRIES]
    ]

    oi_by_expiry = {}
    for e in expiries:
        oi_by_expiry[e["code"]] = _get(
            "/eapi/v1/openInterest",
            {"underlyingAsset": UNDERLYING_ASSET, "expiration": e["code"]},
        )

    return {
        "exchange_info": info,
        "marks": marks,
        "index": index,
        "expiries": expiries,
        "oi_by_expiry": oi_by_expiry,
    }


def _finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def build_map(inputs: dict) -> dict:
    info = inputs["exchange_info"]
    marks = inputs["marks"]
    index = inputs["index"]
    oi_by_expiry = inputs["oi_by_expiry"]

    spot = float(index["indexPrice"])
    snap_ms = int(index["time"])

    sol_info = [
        x for x in info.get("optionSymbols", [])
        if x.get("underlying") == UNDERLYING and x.get("status") == "TRADING"
    ]
    expiry_by_ms = {}
    for x in sol_info:
        expiry_ms = int(x["expiryDate"])
        if expiry_ms > snap_ms:
            expiry_by_ms[expiry_ms] = str(x["symbol"]).split("-")[1]
    expiries = [
        {"expiryDate": expiry_ms, "code": code}
        for expiry_ms, code in sorted(expiry_by_ms.items())[:NEAREST_EXPIRIES]
    ]

    allowed_expiries = {e["code"] for e in expiries}
    info_by_symbol = {x["symbol"]: x for x in sol_info}
    mark_by_symbol = {
        x["symbol"]: x
        for x in marks
        if str(x.get("symbol", "")).startswith("SOL-")
    }
    oi_by_symbol = {}
    for e in expiries:
        for x in oi_by_expiry.get(e["code"], []):
            oi_by_symbol[x["symbol"]] = x

    raw = []
    for symbol, inf in info_by_symbol.items():
        expiry_code = str(symbol).split("-")[1]
        if expiry_code not in allowed_expiries:
            continue
        mark = mark_by_symbol.get(symbol)
        oirow = oi_by_symbol.get(symbol)
        if mark is None or oirow is None:
            continue

        strike = float(inf["strikePrice"])
        gamma = abs(float(mark["gamma"]))
        mark_iv = float(mark["markIV"])
        oi = float(oirow["sumOpenInterest"])

        if not (
            _finite(strike)
            and _finite(gamma) and gamma >= 0
            and _finite(mark_iv) and mark_iv > 0
            and _finite(oi) and oi >= 0
        ):
            continue

        raw.append({
            "symbol": symbol,
            "expiry_code": expiry_code,
            "expiry_time_ms": int(inf["expiryDate"]),
            "side": inf["side"],
            "strike": strike,
            "markPrice": float(mark["markPrice"]),
            "bidIV": float(mark["bidIV"]),
            "askIV": float(mark["askIV"]),
            "markIV": mark_iv,
            "delta": float(mark["delta"]),
            "gamma": float(mark["gamma"]),
            "vega": float(mark["vega"]),
            "theta": float(mark["theta"]),
            "open_interest": oi,
            "open_interest_usd": float(oirow["sumOpenInterestUsd"]),
            "gamma_concentration": gamma * oi,
        })

    # Normalize within each expiry and option side.
    for e in expiries:
        for side in ("CALL", "PUT"):
            rows = [x for x in raw if x["expiry_code"] == e["code"] and x["side"] == side]
            oi_total = sum(x["open_interest"] for x in rows)
            gamma_total = sum(x["gamma_concentration"] for x in rows)
            for x in rows:
                x["oi_share"] = x["open_interest"] / oi_total if oi_total > 0 else 0.0
                x["gamma_share"] = x["gamma_concentration"] / gamma_total if gamma_total > 0 else 0.0

    def aggregate(side: str, is_valid_strike):
        strikes = sorted({
            x["strike"] for x in raw
            if x["side"] == side and is_valid_strike(x["strike"])
        })
        out = []
        for strike in strikes:
            oi_sum = 0.0
            gamma_sum = 0.0
            expiry_detail = []
            for e in expiries:
                rows = [
                    x for x in raw
                    if x["side"] == side
                    and x["expiry_code"] == e["code"]
                    and x["strike"] == strike
                ]
                oi_share = sum(x.get("oi_share", 0.0) for x in rows)
                gamma_share = sum(x.get("gamma_share", 0.0) for x in rows)
                oi_sum += oi_share
                gamma_sum += gamma_share
                expiry_detail.append({
                    "expiry": e["code"],
                    "oi_share": oi_share,
                    "gamma_share": gamma_share,
                })

            denom = max(1, len(expiries))
            mean_oi = oi_sum / denom
            mean_gamma = gamma_sum / denom
            out.append({
                "strike": strike,
                "side": side,
                "mean_oi_share": mean_oi,
                "mean_gamma_share": mean_gamma,
                "concentration_score": 0.5 * mean_oi + 0.5 * mean_gamma,
                "expiry_detail": expiry_detail,
            })

        return sorted(
            out,
            key=lambda x: (-x["concentration_score"], abs(x["strike"] - spot)),
        )

    upper = aggregate("CALL", lambda k: k > spot)[:3]
    lower = aggregate("PUT", lambda k: k < spot)[:3]

    iv_bands = []
    for e in expiries:
        rows = [x for x in raw if x["expiry_code"] == e["code"]]
        by_strike = {}
        for x in rows:
            by_strike.setdefault(x["strike"], []).append(x)

        strikes = sorted(by_strike, key=lambda k: abs(k - spot))
        chosen = None
        ivs = []

        # Prefer a complete call/put pair at the same closest-to-spot strike.
        for strike in strikes:
            srows = by_strike[strike]
            call = next((x for x in srows if x["side"] == "CALL" and x["markIV"] > 0), None)
            put = next((x for x in srows if x["side"] == "PUT" and x["markIV"] > 0), None)
            if call and put:
                chosen = strike
                ivs = [call["markIV"], put["markIV"]]
                break

        # Frozen fallback if a complete pair is unavailable.
        if chosen is None:
            for strike in strikes:
                vals = [x["markIV"] for x in by_strike[strike] if x["markIV"] > 0]
                if vals:
                    chosen = strike
                    ivs = vals
                    break

        if chosen is None:
            continue

        atm_iv = sum(ivs) / len(ivs)
        t_years = max(0.0, (e["expiryDate"] - snap_ms) / (365.0 * 24 * 3600 * 1000))
        expected_move = spot * atm_iv * math.sqrt(t_years)
        iv_bands.append({
            "expiry": e["code"],
            "expiry_time_ms": e["expiryDate"],
            "atm_strike": chosen,
            "atm_mark_iv": atm_iv,
            "time_years": t_years,
            "expected_move": expected_move,
            "iv_floor": spot - expected_move,
            "iv_ceiling": spot + expected_move,
        })

    def add_confluence(levels: list[dict], side: str):
        for level in levels:
            candidates = []
            for band in iv_bands:
                iv_level = band["iv_ceiling"] if side == "upper" else band["iv_floor"]
                candidates.append({
                    "expiry": band["expiry"],
                    "level": iv_level,
                    "distance_pct_spot": abs(level["strike"] - iv_level) / spot * 100.0,
                })
            candidates.sort(key=lambda x: x["distance_pct_spot"])
            nearest = candidates[0] if candidates else None
            level["nearest_iv_band"] = nearest
            level["confluence_label"] = (
                "IV_CONFLUENT"
                if nearest and nearest["distance_pct_spot"] <= IV_CONFLUENCE_PCT_SPOT
                else "NO_IV_CONFLUENCE"
            )

    add_confluence(upper, "upper")
    add_confluence(lower, "lower")

    snapshot_id = (
        "SOL_OPT_V1_"
        + datetime.fromtimestamp(snap_ms / 1000, tz=timezone.utc)
        .strftime("%Y%m%d%H%M%S%f")[:-3]
    )

    return {
        "map_version": MAP_VERSION,
        "status": "OPTIONS_MAP_CAPTURE_READY" if raw and iv_bands else "OPTIONS_MAP_DATA_INSUFFICIENT",
        "snapshot_id": snapshot_id,
        "snapshot_time_ms": snap_ms,
        "snapshot_time_utc": datetime.fromtimestamp(snap_ms / 1000, tz=timezone.utc).isoformat(),
        "spot": spot,
        "expiries": expiries,
        "counts": {
            "chain_rows": len(raw),
            "mark_rows": len([x for x in marks if str(x.get("symbol", "")).startswith("SOL-")]),
            "oi_rows": sum(len(oi_by_expiry.get(e["code"], [])) for e in expiries),
        },
        "iv_bands": iv_bands,
        "lower_put_concentration": lower,
        "upper_call_concentration": upper,
        "raw_chain": raw,
        "guardrail": {
            "gamma_oi_semantics": "gamma concentration magnitude only; dealer sign unknown",
            "trading_rule_promoted": False,
        },
    }


def ensure_snapshot_table(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sol_options_liquidity_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                map_version TEXT NOT NULL,
                snapshot_time_ms INTEGER NOT NULL,
                spot REAL NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at_utc TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sol_options_snapshot_time "
            "ON sol_options_liquidity_snapshots(snapshot_time_ms)"
        )
        conn.commit()
    finally:
        conn.close()


def persist_snapshot(db_path: str, payload: dict) -> dict:
    ensure_snapshot_table(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO sol_options_liquidity_snapshots
            (snapshot_id, map_version, snapshot_time_ms, spot, status, payload_json, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["snapshot_id"],
                payload["map_version"],
                int(payload["snapshot_time_ms"]),
                float(payload["spot"]),
                payload["status"],
                json.dumps(payload, separators=(",", ":"), sort_keys=True),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return {
            "inserted": cur.rowcount == 1,
            "snapshot_id": payload["snapshot_id"],
            "snapshot_time_ms": payload["snapshot_time_ms"],
        }
    finally:
        conn.close()


def capture_live_snapshot(db_path: str) -> dict:
    payload = build_map(fetch_live_inputs())
    storage = persist_snapshot(db_path, payload)
    return {"storage": storage, "map": payload}


def list_snapshots(db_path: str, limit: int = 100) -> list[dict]:
    ensure_snapshot_table(db_path)
    limit = max(1, min(int(limit), 1000))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT snapshot_id, map_version, snapshot_time_ms, spot, status, created_at_utc
            FROM sol_options_liquidity_snapshots
            ORDER BY snapshot_time_ms DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def latest_snapshot_before(db_path: str, decision_time_ms: int) -> dict | None:
    """Causal alignment helper for future detector studies."""
    ensure_snapshot_table(db_path)
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT payload_json
            FROM sol_options_liquidity_snapshots
            WHERE snapshot_time_ms <= ?
            ORDER BY snapshot_time_ms DESC
            LIMIT 1
            """,
            (int(decision_time_ms),),
        ).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        conn.close()
