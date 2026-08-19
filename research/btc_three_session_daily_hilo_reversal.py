#!/usr/bin/env python3
"""BTC three-session daily high/low sweep-reclaim reversal.

Frozen preregistration v2:
- 6 anchors/day (Asia/London/NY open+close)
- 15m sweep + same-candle reclaim
- next 15m open entry
- structural SL at sweep extreme
- TP = 1R (1:1)
- 6h max hold
- no 1m data
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

import btc_potential_b_august_2026_replay as dataio

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_ThreeSession_DailyHighLow_Reversal_Result.md"
OUT_JSON = ROOT / "BTC_ThreeSession_DailyHighLow_Reversal_Result.json"
OUT_CSV = ROOT / "BTC_ThreeSession_DailyHighLow_Reversal_August_Events.csv"

HIST_START = pd.Timestamp("2023-12-02T00:00:00Z")
HIST_END = pd.Timestamp("2026-07-30T00:00:00Z")
AUG_START = pd.Timestamp("2026-08-01T00:00:00Z")
AUG_END = pd.Timestamp("2026-08-20T00:00:00Z")
WINDOW_MIN = 90
FEE = 0.0015
NOTIONAL = 500.0
HOLD_5M_BARS = 72

ANCHORS = [
    {"name": "ASIA_OPEN", "hour": 0, "kind": "OPEN", "session": "ASIA", "session_close_hour": 8, "asia_prev_day": True},
    {"name": "ASIA_CLOSE", "hour": 8, "kind": "CLOSE", "session": "ASIA", "session_close_hour": None, "asia_prev_day": False},
    {"name": "LONDON_OPEN", "hour": 7, "kind": "OPEN", "session": "LONDON", "session_close_hour": 16, "asia_prev_day": False},
    {"name": "LONDON_CLOSE", "hour": 16, "kind": "CLOSE", "session": "LONDON", "session_close_hour": None, "asia_prev_day": False},
    {"name": "NEW_YORK_OPEN", "hour": 13, "kind": "OPEN", "session": "NEW_YORK", "session_close_hour": 22, "asia_prev_day": False},
    {"name": "NEW_YORK_CLOSE", "hour": 22, "kind": "CLOSE", "session": "NEW_YORK", "session_close_hour": None, "asia_prev_day": False},
]


def aggregate_15m(x: pd.DataFrame) -> pd.DataFrame:
    y = x.set_index("ts")
    agg = y.resample("15min", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        count=("close", "count"),
    ).dropna().reset_index()
    return agg[agg["count"] == 3].reset_index(drop=True)


def price_at_time_5m(x: pd.DataFrame, close_time: pd.Timestamp) -> Optional[float]:
    # price known exactly at close_time = close of 5m bar opened 5m earlier
    ts = close_time - pd.Timedelta(minutes=5)
    m = x.index[x.ts == ts]
    if len(m) == 0:
        return None
    return float(x.close.iloc[int(m[0])])


def signed_ret(direction: str, entry: float, px: float) -> float:
    return (px - entry) / entry if direction == "LONG" else (entry - px) / entry


def forward_diag(x: pd.DataFrame, entry_idx: int, direction: str, minutes: int) -> Optional[dict]:
    bars = minutes // 5
    end_idx = entry_idx + bars - 1
    if end_idx >= len(x):
        return None
    expected = x.ts.iloc[entry_idx] + pd.Timedelta(minutes=5 * (bars - 1))
    if x.ts.iloc[end_idx] != expected:
        return None
    entry = float(x.open.iloc[entry_idx])
    final = float(x.close.iloc[end_idx])
    hs = x.high.iloc[entry_idx:end_idx + 1].to_numpy(float)
    ls = x.low.iloc[entry_idx:end_idx + 1].to_numpy(float)
    if direction == "LONG":
        mfe = (float(np.max(hs)) - entry) / entry
        mae = (entry - float(np.min(ls))) / entry
    else:
        mfe = (entry - float(np.min(ls))) / entry
        mae = (float(np.max(hs)) - entry) / entry
    return {"ret": signed_ret(direction, entry, final), "mfe": mfe, "mae": mae}


def resolve_1r(x: pd.DataFrame, entry_idx: int, direction: str, sl: float) -> Optional[dict]:
    end_idx = entry_idx + HOLD_5M_BARS - 1
    if end_idx >= len(x):
        return None
    if x.ts.iloc[end_idx] != x.ts.iloc[entry_idx] + pd.Timedelta(minutes=5 * (HOLD_5M_BARS - 1)):
        return None
    entry = float(x.open.iloc[entry_idx])
    if direction == "LONG":
        risk = entry - sl
        if risk <= 0:
            return None
        tp = entry + risk
    else:
        risk = sl - entry
        if risk <= 0:
            return None
        tp = entry - risk
    risk_pct = risk / entry
    hs = x.high.iloc[entry_idx:end_idx + 1].to_numpy(float)
    ls = x.low.iloc[entry_idx:end_idx + 1].to_numpy(float)
    if direction == "LONG":
        tp_hits = np.flatnonzero(hs >= tp)
        sl_hits = np.flatnonzero(ls <= sl)
    else:
        tp_hits = np.flatnonzero(ls <= tp)
        sl_hits = np.flatnonzero(hs >= sl)
    ti = int(tp_hits[0]) if tp_hits.size else 10**9
    si = int(sl_hits[0]) if sl_hits.size else 10**9
    if si <= ti:
        outcome = "SL"
        raw_ret = -risk_pct
        decisive_win = 0
    elif ti < 10**9:
        outcome = "TP"
        raw_ret = risk_pct
        decisive_win = 1
    else:
        outcome = "TIME"
        final = float(x.close.iloc[end_idx])
        raw_ret = signed_ret(direction, entry, final)
        decisive_win = None
    net_ret = raw_ret - FEE
    return {
        "entry_price": entry,
        "sl_price": sl,
        "tp_price": tp,
        "risk_pct": risk_pct,
        "outcome": outcome,
        "decisive_win": decisive_win,
        "raw_ret": raw_ret,
        "net_ret": net_ret,
        "pnl": net_ret * NOTIONAL,
        "net_positive": int(net_ret > 0),
    }


def level_for_anchor(x: pd.DataFrame, day: pd.Timestamp, anchor: dict) -> Optional[tuple[float, float]]:
    if anchor["asia_prev_day"]:
        s = day - pd.Timedelta(days=1)
        e = day
    else:
        s = day
        e = day + pd.Timedelta(hours=anchor["hour"])
    z = x[(x.ts >= s) & (x.ts < e)]
    if z.empty:
        return None
    # Strict coverage sanity. Previous day should have 288 5m bars; intraday enough for anchor.
    expected = int((e - s).total_seconds() // 300)
    if len(z) < max(1, expected):
        return None
    return float(z.high.max()), float(z.low.min())


def detect(x5: pd.DataFrame, x15: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows = []
    day = start.normalize()
    while day < end.normalize():
        for anchor in ANCHORS:
            anchor_ts = day + pd.Timedelta(hours=anchor["hour"])
            levels = level_for_anchor(x5, day, anchor)
            if levels is None:
                continue
            frozen_high, frozen_low = levels
            win_end = anchor_ts + pd.Timedelta(minutes=WINDOW_MIN)
            z = x15[(x15.ts >= anchor_ts) & (x15.ts < win_end)]
            if z.empty:
                continue
            chosen = None
            for idx, r in z.iterrows():
                high_sweep = float(r.high) > frozen_high and float(r.close) < frozen_high
                low_sweep = float(r.low) < frozen_low and float(r.close) > frozen_low
                if high_sweep and low_sweep:
                    continue
                if high_sweep:
                    chosen = (idx, "SHORT", "HIGH", float(r.high))
                    break
                if low_sweep:
                    chosen = (idx, "LONG", "LOW", float(r.low))
                    break
            if chosen is None:
                continue
            idx15, direction, side, structural_sl = chosen
            reclaim_ts = x15.ts.iloc[int(idx15)]
            entry_ts = reclaim_ts + pd.Timedelta(minutes=15)
            m = x5.index[x5.ts == entry_ts]
            if len(m) == 0:
                continue
            entry_idx = int(m[0])
            rr = resolve_1r(x5, entry_idx, direction, structural_sl)
            if rr is None:
                continue
            d60 = forward_diag(x5, entry_idx, direction, 60)
            d120 = forward_diag(x5, entry_idx, direction, 120)
            d240 = forward_diag(x5, entry_idx, direction, 240)
            if d60 is None or d120 is None or d240 is None:
                continue

            session_close_ret = None
            session_close_ts = None
            if anchor["kind"] == "OPEN":
                session_close_ts = day + pd.Timedelta(hours=anchor["session_close_hour"])
                if session_close_ts > entry_ts:
                    pclose = price_at_time_5m(x5, session_close_ts)
                    if pclose is not None:
                        session_close_ret = signed_ret(direction, rr["entry_price"], pclose)

            rows.append({
                "utc_date": day.strftime("%Y-%m-%d"),
                "anchor": anchor["name"],
                "anchor_kind": anchor["kind"],
                "session": anchor["session"],
                "anchor_ts": anchor_ts,
                "frozen_high": frozen_high,
                "frozen_low": frozen_low,
                "side": side,
                "direction": direction,
                "reclaim_ts": reclaim_ts,
                "entry_ts": entry_ts,
                "entry_wib": entry_ts + pd.Timedelta(hours=7),
                "session_close_ts": session_close_ts,
                "session_close_ret": session_close_ret,
                **rr,
                "ret60": d60["ret"], "mfe60": d60["mfe"], "mae60": d60["mae"],
                "ret120": d120["ret"], "mfe120": d120["mfe"], "mae120": d120["mae"],
                "ret240": d240["ret"], "mfe240": d240["mfe"], "mae240": d240["mae"],
            })
        day += pd.Timedelta(days=1)
    return pd.DataFrame(rows)


def stats(z: pd.DataFrame) -> dict:
    if z is None or z.empty:
        return {"n": 0, "tp": 0, "sl": 0, "time": 0, "decisive_n": 0, "decisive_wr": None,
                "all_net_positive_rate": None, "pnl": 0.0, "avg_risk_pct": None, "median_risk_pct": None,
                "avg_ret60": None, "avg_ret120": None, "avg_ret240": None, "avg_session_close_ret": None}
    dec = z[z.outcome.isin(["TP", "SL"])]
    sc = z.session_close_ret.dropna() if "session_close_ret" in z else pd.Series(dtype=float)
    return {
        "n": int(len(z)),
        "tp": int((z.outcome == "TP").sum()),
        "sl": int((z.outcome == "SL").sum()),
        "time": int((z.outcome == "TIME").sum()),
        "decisive_n": int(len(dec)),
        "decisive_wr": float((dec.outcome == "TP").mean()) if len(dec) else None,
        "all_net_positive_rate": float(z.net_positive.mean()),
        "pnl": float(z.pnl.sum()),
        "avg_risk_pct": float(z.risk_pct.mean()),
        "median_risk_pct": float(z.risk_pct.median()),
        "avg_ret60": float(z.ret60.mean()),
        "avg_ret120": float(z.ret120.mean()),
        "avg_ret240": float(z.ret240.mean()),
        "avg_session_close_ret": float(sc.mean()) if len(sc) else None,
    }


def split_stats(z: pd.DataFrame) -> dict:
    if z.empty:
        return {"discovery": stats(z), "validation": stats(z)}
    z = z.sort_values("entry_ts").reset_index(drop=True)
    cut = int(np.floor(len(z) * 0.70))
    return {"discovery": stats(z.iloc[:cut]), "validation": stats(z.iloc[cut:])}


def blocks(z: pd.DataFrame) -> list[dict]:
    if z.empty:
        return []
    out = []
    for i, part in enumerate(np.array_split(z.sort_values("entry_ts").reset_index(drop=True), 4), 1):
        out.append({"block": f"B{i}", **stats(part)})
    return out


def theory_gate(s: dict, sp: dict, bl: list[dict]) -> dict:
    val = sp["validation"]
    positive_blocks = sum(1 for b in bl if b["pnl"] > 0)
    descriptive = bool(
        s["n"] >= 40 and s["decisive_wr"] is not None and s["decisive_wr"] >= 0.65 and
        val["decisive_wr"] is not None and val["decisive_wr"] >= 0.60 and s["pnl"] > 0 and
        positive_blocks >= 3
    )
    candidate80 = bool(
        s["decisive_n"] >= 25 and s["decisive_wr"] is not None and s["decisive_wr"] >= 0.80 and
        val["decisive_n"] >= 10 and val["decisive_wr"] is not None and val["decisive_wr"] >= 0.80 and
        sp["discovery"]["decisive_wr"] is not None and sp["discovery"]["decisive_wr"] >= 0.80 and
        s["pnl"] > 0
    )
    return {"descriptive_support": descriptive, "candidate80": candidate80, "positive_blocks": positive_blocks}


def pct(v):
    return "-" if v is None else f"{100*v:.2f}%"


def main():
    x5 = dataio.load_data()
    x15 = aggregate_15m(x5)
    hist = detect(x5, x15, HIST_START, HIST_END)
    aug = detect(x5, x15, AUG_START, AUG_END)
    if aug.empty:
        pd.DataFrame(columns=["utc_date"]).to_csv(OUT_CSV, index=False)
    else:
        aug.to_csv(OUT_CSV, index=False)

    keys = [(a["name"], side) for a in ANCHORS for side in ("HIGH", "LOW")]
    hist_rows = []
    aug_rows = []
    detailed = {}
    for anchor, side in keys:
        hz = hist[(hist.anchor == anchor) & (hist.side == side)] if not hist.empty else hist
        az = aug[(aug.anchor == anchor) & (aug.side == side)] if not aug.empty else aug
        s = stats(hz); sp = split_stats(hz); bl = blocks(hz); g = theory_gate(s, sp, bl)
        hist_rows.append({"anchor": anchor, "side": side, **s, **g,
                          "validation_n": sp["validation"]["n"],
                          "validation_decisive_n": sp["validation"]["decisive_n"],
                          "validation_decisive_wr": sp["validation"]["decisive_wr"],
                          "validation_pnl": sp["validation"]["pnl"]})
        aug_rows.append({"anchor": anchor, "side": side, **stats(az)})
        detailed[f"{anchor}_{side}"] = {"full": s, "split": sp, "blocks": bl, "gate": g}

    open_hist = stats(hist[hist.anchor_kind == "OPEN"] if not hist.empty else hist)
    close_hist = stats(hist[hist.anchor_kind == "CLOSE"] if not hist.empty else hist)
    open_aug = stats(aug[aug.anchor_kind == "OPEN"] if not aug.empty else aug)
    close_aug = stats(aug[aug.anchor_kind == "CLOSE"] if not aug.empty else aug)

    result = {
        "protocol": "BTC_THREE_SESSION_DAILY_HILO_REVERSAL_V2_STRUCTURAL_1R",
        "coverage": {"first_ts": str(x5.ts.min()), "last_ts": str(x5.ts.max()), "rows5m": int(len(x5)), "rows15m": int(len(x15))},
        "historical_event_count": int(len(hist)),
        "august_event_count": int(len(aug)),
        "historical_anchor_side": hist_rows,
        "august_anchor_side": aug_rows,
        "historical_open_aggregate": open_hist,
        "historical_close_aggregate": close_hist,
        "august_open_aggregate": open_aug,
        "august_close_aggregate": close_aug,
        "detail": detailed,
        "candidate80_keys": [f"{r['anchor']}_{r['side']}" for r in hist_rows if r["candidate80"]],
        "descriptive_support_keys": [f"{r['anchor']}_{r['side']}" for r in hist_rows if r["descriptive_support"]],
        "guardrails": {"one_minute_used": False, "rr": "1R:1R structural", "window_minutes": WINDOW_MIN, "fee": FEE},
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str) + "\n")

    md = [
        "# BTC Three-Session Daily High/Low Sweep-Reversal — Result",
        "",
        "Frozen mechanism: 15m sweep + same-candle reclaim, next-15m-open entry, structural sweep-extreme SL, **TP = 1R (1:1)**, max hold 6h.",
        "",
        f"Coverage: **{x5.ts.min()} -> {x5.ts.max()}**, 5m rows **{len(x5):,}**, 15m complete rows **{len(x15):,}**.",
        f"Historical events: **{len(hist):,}**. August events: **{len(aug):,}**.",
        "",
        "## Historical — each anchor and side",
        "",
        "| Anchor | Side | N | TP | SL | TIME | Decisive WR | Net+ rate | PnL | Median risk | Validation N | Validation WR | Support | 80% |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in hist_rows:
        md.append(
            f"| {r['anchor']} | {r['side']} | {r['n']} | {r['tp']} | {r['sl']} | {r['time']} | {pct(r['decisive_wr'])} | "
            f"{pct(r['all_net_positive_rate'])} | ${r['pnl']:.2f} | {pct(r['median_risk_pct'])} | {r['validation_decisive_n']} | "
            f"{pct(r['validation_decisive_wr'])} | {'YES' if r['descriptive_support'] else 'NO'} | {'YES' if r['candidate80'] else 'NO'} |"
        )
    md += [
        "",
        "## OPEN vs CLOSE aggregate",
        "",
        "| Historical cohort | N | TP | SL | TIME | Decisive WR | PnL | Avg session-close mark |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| OPEN anchors | {open_hist['n']} | {open_hist['tp']} | {open_hist['sl']} | {open_hist['time']} | {pct(open_hist['decisive_wr'])} | ${open_hist['pnl']:.2f} | {pct(open_hist['avg_session_close_ret'])} |",
        f"| CLOSE anchors | {close_hist['n']} | {close_hist['tp']} | {close_hist['sl']} | {close_hist['time']} | {pct(close_hist['decisive_wr'])} | ${close_hist['pnl']:.2f} | - |",
        "",
        "## August true post-cutoff — each anchor and side",
        "",
        "| Anchor | Side | N | TP | SL | TIME | Decisive WR | PnL | Median risk |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in aug_rows:
        md.append(f"| {r['anchor']} | {r['side']} | {r['n']} | {r['tp']} | {r['sl']} | {r['time']} | {pct(r['decisive_wr'])} | ${r['pnl']:.2f} | {pct(r['median_risk_pct'])} |")

    md += [
        "",
        "## August event ledger",
        "",
        "| Date | Anchor | Side | Entry WIB | Risk | Outcome | Net ret | PnL | 60m | 240m | Session-close mark |",
        "|---|---|---|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    if aug.empty:
        md.append("| - | - | - | - | - | - | - | - | - | - | - |")
    else:
        for _, r in aug.sort_values("entry_ts").iterrows():
            md.append(
                f"| {r.utc_date} | {r.anchor} | {r.side} | {pd.Timestamp(r.entry_wib).strftime('%Y-%m-%d %H:%M')} | {100*r.risk_pct:.3f}% | "
                f"{r.outcome} | {100*r.net_ret:.3f}% | ${r.pnl:.2f} | {100*r.ret60:.3f}% | {100*r.ret240:.3f}% | "
                f"{('-' if pd.isna(r.session_close_ret) else f'{100*r.session_close_ret:.3f}%')} |"
            )
    md += [
        "",
        f"Descriptively supported fixed anchor+side keys: **{result['descriptive_support_keys'] or 'NONE'}**.",
        f"80% candidate keys: **{result['candidate80_keys'] or 'NONE'}**.",
        "",
        "No anchor/window/RR/filter is retuned from these outcomes. Live BBC untouched.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
