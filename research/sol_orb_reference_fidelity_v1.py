#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ORB_REFERENCE_FIDELITY_V1"
DEV_START, DEV_END = base.PARTS["development"]
BAR = pd.Timedelta(minutes=5)
HORIZONS = (15, 30, 60, 120)
VARIANTS = ("RETEST_REACTION_VWAP", "SMALL_BOS_VWAP", "REACTION_THEN_BOS_VWAP", "REFERENCE_UNION")
NOTIONAL = 500.0
ROUNDTRIP_COST_PCT = 0.15


def row_at(x: pd.DataFrame, ts: pd.Timestamp):
    try:
        r = x.loc[ts]
    except KeyError:
        return None
    if isinstance(r, pd.DataFrame):
        r = r.iloc[0]
    return r


def anchored_vwap(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float:
    q = x[(x.index >= start) & (x.index <= end)]
    if q.empty or "volume" not in q.columns:
        return np.nan
    vol = pd.to_numeric(q["volume"], errors="coerce").astype(float)
    tp = (q["high"].astype(float) + q["low"].astype(float) + q["close"].astype(float)) / 3.0
    mask = np.isfinite(vol.to_numpy()) & np.isfinite(tp.to_numpy())
    if not mask.any():
        return np.nan
    vs = float(vol.to_numpy()[mask].sum())
    if vs <= 0:
        return np.nan
    return float((tp.to_numpy()[mask] * vol.to_numpy()[mask]).sum() / vs)


def close_after(x: pd.DataFrame, entry_ts: pd.Timestamp, minutes: int):
    ts = entry_ts + pd.Timedelta(minutes=minutes) - BAR
    if ts >= DEV_END:
        return np.nan
    r = row_at(x, ts)
    return np.nan if r is None else float(r.close)


def profit_factor(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return pos / neg


def max_loss_streak(pnls) -> int:
    best = cur = 0
    for x in pd.Series(pnls, dtype=float).dropna():
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def max_drawdown(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    if a.empty:
        return np.nan
    eq = a.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def signal_payload(x5, start, ts):
    if ts is None or ts + BAR >= DEV_END:
        return None
    entry_ts = ts + BAR
    er = row_at(x5, entry_ts)
    if er is None:
        return None
    return {
        "signal_time": ts,
        "entry_time": entry_ts,
        "entry_price": float(er.open),
    }


def detect_session(x5: pd.DataFrame, start: pd.Timestamp):
    orb_times = [start + i * BAR for i in range(3)]
    orb = [row_at(x5, t) for t in orb_times]
    if any(r is None for r in orb):
        return None
    oh = max(float(r.high) for r in orb)
    ol = min(float(r.low) for r in orb)
    if not np.isfinite(oh - ol) or oh <= ol:
        return None
    rng = oh - ol
    out = {
        "session_start": start,
        "hour_utc": int(start.hour),
        "hour_wib": int((start.hour + 7) % 24),
        "year": int(start.year),
        "orb_high": oh,
        "orb_low": ol,
        "orb_range_pct": rng / float(orb[0].open) * 100.0,
        "has_breakout": False,
        "breakout_time": pd.NaT,
        "breakout_above_vwap": False,
        "has_retest_touch": False,
        "retest_time": pd.NaT,
        "retest_reclaim": False,
        "retest_bullish_body": False,
        "retest_wick_rejection": False,
        "retest_bullish_reaction": False,
        "retest_above_vwap": False,
        "has_small_bos": False,
        "bos_time": pd.NaT,
        "bos_above_vwap": False,
    }
    for v in VARIANTS:
        out[f"{v}_signal_time"] = pd.NaT
        out[f"{v}_entry_time"] = pd.NaT
        out[f"{v}_entry_price"] = np.nan
        for h in HORIZONS:
            out[f"{v}_net_{h}m_pct"] = np.nan
            out[f"{v}_pnl_{h}m_usd"] = np.nan

    breakout_ts = None
    breakout_row = None
    for i in range(3, 12):
        ts = start + i * BAR
        if ts >= DEV_END:
            break
        r = row_at(x5, ts)
        if r is not None and float(r.close) > oh:
            breakout_ts, breakout_row = ts, r
            break
    if breakout_ts is None:
        return out
    out["has_breakout"] = True
    out["breakout_time"] = breakout_ts
    bv = anchored_vwap(x5, start, breakout_ts)
    out["breakout_above_vwap"] = bool(np.isfinite(bv) and float(breakout_row.close) > bv)

    retest_ts = None
    retest_row = None
    for j in range(1, 7):
        ts = breakout_ts + j * BAR
        if ts >= DEV_END:
            break
        r = row_at(x5, ts)
        if r is not None and float(r.low) <= oh:
            retest_ts, retest_row = ts, r
            break
    if retest_ts is None:
        return out

    out["has_retest_touch"] = True
    out["retest_time"] = retest_ts
    ro, rh, rl, rc = map(float, (retest_row.open, retest_row.high, retest_row.low, retest_row.close))
    body = abs(rc - ro)
    lower_wick = max(0.0, min(ro, rc) - rl)
    reclaim = rc >= oh
    bull_body = rc > ro
    wick_reject = lower_wick >= body
    bull_reaction = reclaim and (bull_body or wick_reject)
    rv = anchored_vwap(x5, start, retest_ts)
    retest_above_vwap = bool(np.isfinite(rv) and rc > rv)
    out["retest_reclaim"] = reclaim
    out["retest_bullish_body"] = bull_body
    out["retest_wick_rejection"] = wick_reject
    out["retest_bullish_reaction"] = bull_reaction
    out["retest_above_vwap"] = retest_above_vwap

    reaction_ts = retest_ts if (bull_reaction and retest_above_vwap) else None

    prev = row_at(x5, retest_ts - BAR)
    prev_high = float(prev.high) if prev is not None else rh
    micro_level = max(rh, prev_high)
    bos_ts = None
    for k in range(1, 4):
        ts = retest_ts + k * BAR
        if ts >= DEV_END:
            break
        r = row_at(x5, ts)
        if r is None:
            continue
        cv = anchored_vwap(x5, start, ts)
        if float(r.close) > micro_level and float(r.close) > oh and np.isfinite(cv) and float(r.close) > cv:
            bos_ts = ts
            break
    if bos_ts is not None:
        out["has_small_bos"] = True
        out["bos_time"] = bos_ts
        out["bos_above_vwap"] = True

    signals = {
        "RETEST_REACTION_VWAP": reaction_ts,
        "SMALL_BOS_VWAP": bos_ts,
        "REACTION_THEN_BOS_VWAP": bos_ts if (reaction_ts is not None and bos_ts is not None) else None,
    }
    candidates = [t for t in (reaction_ts, bos_ts) if t is not None]
    signals["REFERENCE_UNION"] = min(candidates) if candidates else None

    for v, sts in signals.items():
        p = signal_payload(x5, start, sts)
        if p is None:
            continue
        out[f"{v}_signal_time"] = p["signal_time"]
        out[f"{v}_entry_time"] = p["entry_time"]
        out[f"{v}_entry_price"] = p["entry_price"]
        for h in HORIZONS:
            xp = close_after(x5, p["entry_time"], h)
            if not np.isfinite(xp):
                continue
            gross = (xp / p["entry_price"] - 1.0) * 100.0
            net = gross - ROUNDTRIP_COST_PCT
            out[f"{v}_net_{h}m_pct"] = net
            out[f"{v}_pnl_{h}m_usd"] = net / 100.0 * NOTIONAL
    return out


def collect(x5: pd.DataFrame) -> pd.DataFrame:
    q = x5[(x5.index >= DEV_START) & (x5.index < DEV_END)]
    days = pd.Index(q.index.normalize().unique()).sort_values()
    rows = []
    for day in days:
        if day.weekday() >= 5:
            continue
        for hour in range(24):
            st = day + pd.Timedelta(hours=hour)
            d = detect_session(x5, st)
            if d is not None:
                rows.append(d)
    return pd.DataFrame(rows)


def structure_summary(ev):
    rows = []
    for hour, g in ev.groupby("hour_utc"):
        n = len(g)
        rows.append({
            "hour_utc": int(hour), "hour_wib": int((hour + 7) % 24), "sessions": n,
            "breakout_n": int(g.has_breakout.sum()),
            "breakout_above_vwap_n": int(g.breakout_above_vwap.sum()),
            "retest_touch_n": int(g.has_retest_touch.sum()),
            "bullish_reaction_n": int(g.retest_bullish_reaction.sum()),
            "reaction_vwap_n": int(g["RETEST_REACTION_VWAP_entry_time"].notna().sum()),
            "small_bos_vwap_n": int(g["SMALL_BOS_VWAP_entry_time"].notna().sum()),
            "both_n": int(g["REACTION_THEN_BOS_VWAP_entry_time"].notna().sum()),
            "reference_union_n": int(g["REFERENCE_UNION_entry_time"].notna().sum()),
        })
    return pd.DataFrame(rows).sort_values("hour_utc")


def econ_summary(ev, by_year=False):
    rows = []
    group_cols = ["hour_utc", "year"] if by_year else ["hour_utc"]
    for keys, g in ev.groupby(group_cols):
        if by_year:
            hour, year = keys
        else:
            hour, year = keys, None
        for v in VARIANTS:
            for h in HORIZONS:
                col = f"{v}_pnl_{h}m_usd"
                ret = f"{v}_net_{h}m_pct"
                gg = g.dropna(subset=[col]).sort_values(f"{v}_entry_time")
                p = gg[col].astype(float)
                row = {
                    "hour_utc": int(hour), "hour_wib": int((int(hour)+7)%24),
                    "variant": v, "exit_minutes": h, "n": len(gg),
                    "net_wr": float((gg[ret] > 0).mean()) if len(gg) else np.nan,
                    "net_pnl_usd": float(p.sum()) if len(gg) else np.nan,
                    "expectancy_usd": float(p.mean()) if len(gg) else np.nan,
                    "profit_factor": profit_factor(p),
                }
                if by_year:
                    row["year"] = int(year)
                else:
                    row["max_dd_usd"] = max_drawdown(p)
                    row["max_loss_streak"] = max_loss_streak(p)
                rows.append(row)
    sort_cols = ["variant", "hour_utc", "exit_minutes"] + (["year"] if by_year else [])
    return pd.DataFrame(rows).sort_values(sort_cols)


def pooled_summary(ev):
    rows = []
    for v in VARIANTS:
        for h in HORIZONS:
            col = f"{v}_pnl_{h}m_usd"; ret = f"{v}_net_{h}m_pct"
            g = ev.dropna(subset=[col]).sort_values(f"{v}_entry_time")
            p = g[col].astype(float)
            rows.append({"variant": v, "exit_minutes": h, "n": len(g),
                         "net_wr": float((g[ret] > 0).mean()) if len(g) else np.nan,
                         "net_pnl_usd": float(p.sum()) if len(g) else np.nan,
                         "expectancy_usd": float(p.mean()) if len(g) else np.nan,
                         "profit_factor": profit_factor(p), "max_dd_usd": max_drawdown(p),
                         "max_loss_streak": max_loss_streak(p)})
    return pd.DataFrame(rows)


def main():
    x5, coverage = base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")
    if "volume" not in x5.columns:
        raise RuntimeError("volume column required for VWAP")
    ev = collect(x5)
    st = structure_summary(ev)
    ec = econ_summary(ev, False)
    yr = econ_summary(ev, True)
    pool = pooled_summary(ev)

    ev.to_csv(ROOT/f"{PFX}_Events.csv", index=False)
    st.to_csv(ROOT/f"{PFX}_StructureByHour.csv", index=False)
    ec.to_csv(ROOT/f"{PFX}_EconomicsByHour.csv", index=False)
    yr.to_csv(ROOT/f"{PFX}_YearStability.csv", index=False)
    pool.to_csv(ROOT/f"{PFX}_PooledEconomics.csv", index=False)

    stable = []
    for (v,hour,ex), g in yr.groupby(["variant","hour_utc","exit_minutes"]):
        if set(g.year) >= {2022,2023,2024}:
            q = g[g.year.isin([2022,2023,2024])]
            if len(q)==3 and bool(((q.net_pnl_usd > 0) & (q.profit_factor > 1)).all()):
                stable.append((v,int(hour),int(ex)))

    lines = [
        "# SOL ORB Reference Fidelity Detector v1 — Development", "",
        f"- Data coverage: {coverage*100:.6f}%",
        f"- Sessions evaluated: **{len(ev)}**",
        "- Literal structure: 15m ORB -> upside breakout -> retest reaction and/or small BOS -> above anchored VWAP -> next-5m-open entry.",
        "- All 24 anchor hours swept because crypto has no universal market open.",
        "- Reference/OOS closed; no TP/SL optimization.", "",
        "## Pooled economics by literal structure", "",
        "| Variant | Exit | N | Net WR | Net PnL | Exp | PF | Max DD | Max LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _,r in pool.iterrows():
        lines.append(f"| {r.variant} | {int(r.exit_minutes)}m | {int(r.n)} | {r.net_wr*100:.1f}% | ${r.net_pnl_usd:.2f} | ${r.expectancy_usd:.3f} | {r.profit_factor:.3f} | ${r.max_dd_usd:.2f} | {int(r.max_loss_streak)} |")
    lines += ["", "## Three-year stable hour/exit diagnostics", ""]
    if stable:
        for v,h,e in stable:
            lines.append(f"- `{v}` — {h:02d}:00 UTC / {(h+7)%24:02d}:00 WIB — {e}m")
    else:
        lines.append("No variant/hour/exit combination was positive with PF>1 in all three Development years.")
    lines += ["", "## Boundary", "", "This run characterizes the reference-image structure. It may nominate a structural archetype, but it does not authorize threshold tuning, hour cherry-picking, or Reference/OOS opening."]
    text = "\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("COMPLETE_DEVELOPMENT_REFERENCE_FIDELITY_CHARACTERIZATION\n", encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
