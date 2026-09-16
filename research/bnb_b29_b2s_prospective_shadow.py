#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import bnb_b29_a1_structure_fingerprint as a1

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B29_B2S_PROSPECTIVE_SHADOW"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_LEDGER = ROOT / f"{PFX}_Ledger.csv"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"
OUT_CHECKPOINT = ROOT / f"{PFX}_Checkpoint.json"

SYMBOL = "BNBUSDT"
INTERVAL_MS = 5 * 60 * 1000
BAR = pd.Timedelta(minutes=5)
STEP15 = pd.Timedelta(minutes=15)
COOLDOWN = pd.Timedelta(minutes=60)
FETCH_START = pd.Timestamp("2026-09-14T00:00:00Z")
SHADOW_START = pd.Timestamp("2026-09-15T07:00:00Z")
HORIZONS = [15, 30, 60, 120, 360]
PRIMARY_H = 60
CHECKPOINT_N = 30
CHECKPOINT_MIN_WINS = 17
HALF_N = 15
HALF_MIN_WINS = 8
API = "https://fapi.binance.com/fapi/v1/klines"

LEDGER_COLUMNS = [
    "event_ts", "first_seen_at_utc", "event_close", "status",
    "ret_15", "ret_30", "ret_60", "ret_120", "ret_360", "hit_60",
]


def utcnow_floor_safe() -> pd.Timestamp:
    now = pd.Timestamp.now(tz="UTC")
    # only bars whose nominal close is at least 5 seconds in the past are accepted
    return now - pd.Timedelta(seconds=5)


def fetch_recent_5m() -> tuple[pd.DataFrame, dict]:
    safe_now = utcnow_floor_safe()
    start_ms = int(FETCH_START.timestamp() * 1000)
    end_ms = int(safe_now.timestamp() * 1000)
    rows: list[list] = []
    cursor = start_ms
    sess = requests.Session()
    sess.headers.update({"User-Agent": "bababot-b29-b2s-shadow/1.0"})

    while cursor <= end_ms:
        params = {
            "symbol": SYMBOL,
            "interval": "5m",
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 1500,
        }
        last_exc = None
        payload = None
        for attempt in range(5):
            try:
                r = sess.get(API, params=params, timeout=30)
                r.raise_for_status()
                payload = r.json()
                break
            except Exception as exc:  # tooling retry only
                last_exc = exc
                time.sleep(2 ** attempt)
        if payload is None:
            raise RuntimeError(f"Binance futures kline fetch failed after retries: {last_exc}")
        if not payload:
            break
        rows.extend(payload)
        last_open_ms = int(payload[-1][0])
        nxt = last_open_ms + INTERVAL_MS
        if nxt <= cursor:
            raise RuntimeError("non-advancing Binance pagination cursor")
        cursor = nxt
        if len(payload) < 1500:
            break
        time.sleep(0.05)

    if not rows:
        raise RuntimeError("no prospective BNBUSDT 5m rows returned")

    q = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
    ])
    q["ts"] = pd.to_datetime(pd.to_numeric(q["open_time"]), unit="ms", utc=True)
    q["close_time_ts"] = pd.to_datetime(pd.to_numeric(q["close_time"]), unit="ms", utc=True)
    for c in ["open", "high", "low", "close"]:
        q[c] = pd.to_numeric(q[c], errors="coerce")
    q = q.dropna(subset=["ts", "open", "high", "low", "close"])
    q = q[q["close_time_ts"] < safe_now]
    q = q.drop_duplicates("ts").sort_values("ts")
    x = q.set_index("ts")[["open", "high", "low", "close"]].astype(float)

    if x.empty or x.index.has_duplicates or not x.index.is_monotonic_increasing:
        raise RuntimeError("prospective raw data index invalid")
    diffs = x.index.to_series().diff().dropna()
    gaps = diffs[diffs != BAR]
    expected = int((x.index[-1] - x.index[0]) / BAR) + 1
    coverage = len(x) / expected
    diag = {
        "rows": int(len(x)),
        "first_open": x.index[0].isoformat(),
        "last_open": x.index[-1].isoformat(),
        "last_close": (x.index[-1] + BAR).isoformat(),
        "coverage": float(coverage),
        "gap_count": int(len(gaps)),
        "safe_now": safe_now.isoformat(),
    }
    if coverage < 0.99999 or len(gaps) != 0:
        raise RuntimeError(f"prospective 5m continuity failure: {diag}")
    return x, diag


def cooldown_select(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    accepted = []
    last = None
    for ts in index:
        if last is None or ts - last >= COOLDOWN:
            accepted.append(ts)
            last = ts
    return pd.DatetimeIndex(accepted)


def character_events(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    fp = a1.build_fingerprint(raw)
    if fp.empty:
        return fp, pd.Series(dtype=float)

    # Map exact completed 5m candle close to decision timestamp.
    decision_close = raw["close"].copy()
    decision_close.index = pd.DatetimeIndex(decision_close.index) + BAR
    decision_close = decision_close[~decision_close.index.duplicated(keep="last")].sort_index()

    base_idx = pd.DatetimeIndex(fp.index[fp["sweep_low_60"].eq(1.0)])
    selected_base = cooldown_select(base_idx)
    rows = []
    for ts in selected_base:
        if ts < SHADOW_START:
            continue
        pre_ts = ts - STEP15
        if pre_ts not in fp.index:
            continue
        cur = fp.loc[ts]
        pre = fp.loc[pre_ts]
        if str(pre["path_state"]) != "CONT_DOWN":
            continue
        if float(cur["close_location"]) < 0.50:
            continue
        if float(cur["body_range"]) >= 0.33:
            continue
        if ts not in decision_close.index:
            continue
        rows.append({
            "event_ts": ts,
            "event_close": float(decision_close.loc[ts]),
            "pre_path_state": str(pre["path_state"]),
            "close_location": float(cur["close_location"]),
            "body_range": float(cur["body_range"]),
        })
    E = pd.DataFrame(rows)
    if len(E):
        E = E.sort_values("event_ts").reset_index(drop=True)
    return E, decision_close


def outcome_for(ts: pd.Timestamp, event_close: float, decision_close: pd.Series) -> dict:
    out = {}
    all_primary = True
    for h in HORIZONS:
        z = ts + pd.Timedelta(minutes=h)
        if z in decision_close.index:
            out[f"ret_{h}"] = float(decision_close.loc[z] / event_close - 1.0)
        else:
            out[f"ret_{h}"] = np.nan
            if h == PRIMARY_H:
                all_primary = False
    out["status"] = "MATURED" if all_primary else "PENDING"
    out["hit_60"] = bool(out["ret_60"] > 0.0) if all_primary else np.nan
    return out


def load_ledger() -> pd.DataFrame:
    if not OUT_LEDGER.exists():
        return pd.DataFrame(columns=LEDGER_COLUMNS)
    q = pd.read_csv(OUT_LEDGER)
    if len(q):
        q["event_ts"] = pd.to_datetime(q["event_ts"], utc=True, errors="raise")
        q["first_seen_at_utc"] = pd.to_datetime(q["first_seen_at_utc"], utc=True, errors="raise")
    return q


def update_ledger(events: pd.DataFrame, decision_close: pd.Series, run_ts: pd.Timestamp) -> tuple[pd.DataFrame, list[str]]:
    old = load_ledger()
    errors: list[str] = []
    old_by_ts = {}
    if len(old):
        if old["event_ts"].duplicated().any():
            errors.append("existing ledger contains duplicate event_ts")
        old_by_ts = {pd.Timestamp(r.event_ts): r for r in old.itertuples(index=False)}

    rows = []
    current_event_ts = set(pd.to_datetime(events["event_ts"], utc=True)) if len(events) else set()

    # Existing ledger events must still be rediscoverable from current prospective raw history.
    for ts in old_by_ts:
        if ts not in current_event_ts:
            errors.append(f"previously persisted event disappeared from recomputation: {ts.isoformat()}")

    for r in events.itertuples(index=False):
        ts = pd.Timestamp(r.event_ts)
        outcome = outcome_for(ts, float(r.event_close), decision_close)
        if ts in old_by_ts:
            prev = old_by_ts[ts]
            first_seen = pd.Timestamp(prev.first_seen_at_utc)
            prev_close = float(prev.event_close)
            if not np.isclose(prev_close, float(r.event_close), rtol=0, atol=1e-10):
                errors.append(f"event close revised for {ts.isoformat()}: {prev_close} -> {r.event_close}")
            if str(prev.status) == "MATURED":
                # Matured primary outcomes are immutable; compare rather than silently rewrite.
                prev_ret60 = float(prev.ret_60)
                if not np.isclose(prev_ret60, float(outcome["ret_60"]), rtol=0, atol=1e-12):
                    errors.append(f"matured +60 outcome revised for {ts.isoformat()}")
                for h in HORIZONS:
                    val = getattr(prev, f"ret_{h}")
                    outcome[f"ret_{h}"] = float(val) if pd.notna(val) else np.nan
                outcome["status"] = "MATURED"
                outcome["hit_60"] = bool(prev.hit_60) if pd.notna(prev.hit_60) else bool(prev_ret60 > 0)
        else:
            first_seen = run_ts

        rows.append({
            "event_ts": ts,
            "first_seen_at_utc": first_seen,
            "event_close": float(r.event_close),
            "status": outcome["status"],
            "ret_15": outcome["ret_15"],
            "ret_30": outcome["ret_30"],
            "ret_60": outcome["ret_60"],
            "ret_120": outcome["ret_120"],
            "ret_360": outcome["ret_360"],
            "hit_60": outcome["hit_60"],
        })

    ledger = pd.DataFrame(rows, columns=LEDGER_COLUMNS)
    if len(ledger):
        ledger = ledger.sort_values("event_ts").drop_duplicates("event_ts", keep="first").reset_index(drop=True)
    return ledger, errors


def checkpoint_status(ledger: pd.DataFrame, integrity_errors: list[str]) -> tuple[str, dict]:
    matured = ledger[ledger["status"] == "MATURED"].sort_values("event_ts").copy()
    stats = {
        "matured_n": int(len(matured)),
        "pending_n": int((ledger["status"] == "PENDING").sum()) if len(ledger) else 0,
        "total_events": int(len(ledger)),
    }
    if integrity_errors:
        stats["integrity_errors"] = integrity_errors
        return "BNB_B29_B2S_DATA_TOOLING_FAILURE", stats

    if len(matured) < CHECKPOINT_N:
        if len(matured):
            stats.update({
                "wins_so_far": int(matured["hit_60"].astype(bool).sum()),
                "hit_so_far": float(matured["hit_60"].astype(bool).mean()),
                "median_ret60_so_far": float(matured["ret_60"].median()),
            })
        return "BNB_B29_B2S_PROSPECTIVE_SHADOW_WARMUP", stats

    cp = matured.iloc[:CHECKPOINT_N].copy()
    wins = int(cp["hit_60"].astype(bool).sum())
    first_wins = int(cp.iloc[:HALF_N]["hit_60"].astype(bool).sum())
    second_wins = int(cp.iloc[HALF_N:CHECKPOINT_N]["hit_60"].astype(bool).sum())
    median_ret = float(cp["ret_60"].median())
    passed = (
        wins >= CHECKPOINT_MIN_WINS and
        median_ret > 0.0 and
        first_wins >= HALF_MIN_WINS and
        second_wins >= HALF_MIN_WINS
    )
    stats.update({
        "checkpoint_n": CHECKPOINT_N,
        "checkpoint_wins": wins,
        "checkpoint_hit": wins / CHECKPOINT_N,
        "checkpoint_median_ret60": median_ret,
        "first15_wins": first_wins,
        "second15_wins": second_wins,
        "checkpoint_first_event": cp.iloc[0]["event_ts"].isoformat(),
        "checkpoint_last_event": cp.iloc[-1]["event_ts"].isoformat(),
    })
    return (
        "BNB_B29_B2S_PROSPECTIVE_SHADOW_PASS"
        if passed else "BNB_B29_B2S_PROSPECTIVE_SHADOW_REJECT"
    ), stats


def pct(v) -> str:
    if v is None or pd.isna(v):
        return "n/a"
    return f"{100.0 * float(v):.2f}%"


def main():
    run_ts = pd.Timestamp.now(tz="UTC")
    raw, raw_diag = fetch_recent_5m()
    events, decision_close = character_events(raw)
    ledger, errors = update_ledger(events, decision_close, run_ts)

    # Explicit prospective boundary and duplicate guards.
    if len(ledger):
        if (ledger["event_ts"] < SHADOW_START).any():
            errors.append("ledger contains event before SHADOW_START")
        if ledger["event_ts"].duplicated().any():
            errors.append("ledger duplicate event_ts after update")

    status, stats = checkpoint_status(ledger, errors)

    # Stable serialization.
    if len(ledger):
        out = ledger.copy()
        out["event_ts"] = pd.to_datetime(out["event_ts"], utc=True).map(lambda x: x.isoformat())
        out["first_seen_at_utc"] = pd.to_datetime(out["first_seen_at_utc"], utc=True).map(lambda x: x.isoformat())
        out.to_csv(OUT_LEDGER, index=False)
    else:
        pd.DataFrame(columns=LEDGER_COLUMNS).to_csv(OUT_LEDGER, index=False)

    OUT_STATUS.write_text(status + "\n")
    checkpoint_payload = {
        "scientific_identity": "B29-B2S-v1",
        "status": status,
        "shadow_start": SHADOW_START.isoformat(),
        "run_ts": run_ts.isoformat(),
        "raw_diag": raw_diag,
        "stats": stats,
    }
    OUT_CHECKPOINT.write_text(json.dumps(checkpoint_payload, indent=2, sort_keys=True) + "\n")

    lines = [
        "# BNB B29-B2S — Prospective Event-Close Shadow Result", "",
        f"**Status: {status}**", "",
        "B2S observes only new post-freeze BNB character events using the frozen B1J character and E0 event-close entry. No TP/SL, leverage, fees, sizing, dollar PnL, or live orders are included.", "",
        "## Frozen identity", "",
        f"- Shadow start: `{SHADOW_START.isoformat()}`",
        "- Direction: LONG",
        "- Character: `CONT_DOWN -> sweep_low_60 -> close_location>=0.50 -> body_range<0.33`",
        "- Entry: event close (`E0_EVENT_CLOSE`)",
        "- Primary outcome: exact event-anchor +60m close-to-close return",
        "- Primary checkpoint: first 30 matured events; PASS requires >=17 wins, positive median +60m return, and >=8 wins in each 15-event half.", "",
        "## Prospective data integrity", "",
        f"- Raw source: Binance USD-M Futures REST `{SYMBOL}` 5m",
        f"- Raw rows: {raw_diag['rows']:,}",
        f"- Raw span: {raw_diag['first_open']} -> {raw_diag['last_close']}",
        f"- Raw coverage: {raw_diag['coverage']:.6%}",
        f"- Raw gaps: {raw_diag['gap_count']}",
        f"- Integrity errors: {len(errors)}", "",
        "## Shadow ledger", "",
        f"- Total character events: {stats['total_events']}",
        f"- Matured +60m events: {stats['matured_n']} / {CHECKPOINT_N} required",
        f"- Pending events: {stats['pending_n']}",
    ]
    if stats.get("matured_n", 0) and stats.get("matured_n", 0) < CHECKPOINT_N:
        lines += [
            f"- Wins so far: {stats['wins_so_far']}/{stats['matured_n']}",
            f"- Descriptive hit so far: {pct(stats['hit_so_far'])}",
            f"- Median +60m return so far: {pct(stats['median_ret60_so_far'])}",
            "- These are warmup diagnostics only; early PASS is forbidden.",
        ]
    if stats.get("checkpoint_n"):
        lines += [
            "", "## Frozen first-30 checkpoint", "",
            f"- Wins: {stats['checkpoint_wins']}/30 ({pct(stats['checkpoint_hit'])})",
            f"- Median +60m return: {pct(stats['checkpoint_median_ret60'])}",
            f"- First 15 wins: {stats['first15_wins']}/15",
            f"- Second 15 wins: {stats['second15_wins']}/15",
            f"- First event: {stats['checkpoint_first_event']}",
            f"- 30th event: {stats['checkpoint_last_event']}",
        ]
    if errors:
        lines += ["", "## Integrity errors", ""] + [f"- {e}" for e in errors]

    lines += ["", "## Current decision", "", f"**{status}**", ""]
    if status.endswith("WARMUP"):
        lines += ["Continue prospective collection unchanged. Do not tune character/entry or proceed to TP/SL before the first-30 checkpoint passes."]
    elif status.endswith("PASS"):
        lines += ["The frozen character + event-close entry is promoted to B3 TP/SL discovery. This is still not READY TO TRADE."]
    elif status.endswith("REJECT"):
        lines += ["Freeze B2S-v1 as rejected. Do not rescue the character or entry using these prospective outcomes."]
    else:
        lines += ["Do not interpret scientifically until the tooling/data-integrity failure is corrected without changing the frozen rule."]
    lines += ["", "No live orders were placed."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")

    print(json.dumps(checkpoint_payload, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
