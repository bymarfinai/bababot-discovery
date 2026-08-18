#!/usr/bin/env python3
"""SUN1.0 — Sunday 01:00 WIB BUY TP/SL discovery-validation surface.

Research only; live BBC untouched.

Frozen entry/horizon from A1:
- BTCUSDT BUY every Sunday 01:00 WIB (Saturday 18:00 UTC)
- max hold 240m (A1 best long-horizon Sunday candidate)
- $500 notional = $10 margin x50
- 0.15% round-trip fee
- same-5m TP+SL ambiguity is adverse-first
- timeout exits at final completed 5m close

Broad grid (predeclared):
- TP 0.3% .. 2.5% in 0.1% steps
- SL 0.3% .. 1.5% in 0.1% steps

Selection protocol:
- first 83 Sunday trades = discovery; last 56 = validation
- validation is NEVER used to choose TP/SL
- discovery eligibility: net PnL >0, PF>1.10, >=4/5 discovery chronological blocks positive
- robust champion maximizes local-neighborhood median discovery PnL (same cell plus +/-0.1 TP/SL neighbors),
  then discovery PnL as tie-breaker. This prefers a plateau over an isolated spike.

Because A1 already inspected the historical Sunday edge, validation here is a robustness slice, not pristine OOS.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

import f517_regime_attribution as f517

OUT = Path(os.getenv("SUN10_OUT", "sun10_out"))
OUT.mkdir(parents=True, exist_ok=True)

NOTIONAL = 500.0
FEE = 0.0015 * NOTIONAL
HOLD_MIN = 240
DISC_N = 83
TP_GRID = [round(x / 10.0, 1) for x in range(3, 26)]  # percent
SL_GRID = [round(x / 10.0, 1) for x in range(3, 16)]  # percent


def sunday_entries(k: pd.DataFrame) -> list[pd.Timestamp]:
    # Build from local calendar to avoid weekday confusion across UTC boundary.
    tz = "Asia/Jakarta"
    local_start = f517.START.tz_convert(tz).normalize()
    local_end = f517.END.tz_convert(tz).normalize()
    out = []
    for d in pd.date_range(local_start, local_end, freq="D"):
        if d.weekday() != 6:  # Sunday local
            continue
        t_local = d + pd.Timedelta(hours=1)
        t = t_local.tz_convert("UTC")
        if f517.START <= t < f517.END and t in k.index:
            out.append(t)
    return out


def simulate(k: pd.DataFrame, t: pd.Timestamp, tp_pct: float, sl_pct: float) -> dict:
    entry = float(k.loc[t, "open"])
    tp = tp_pct / 100.0
    sl = sl_pct / 100.0
    tp_px = entry * (1.0 + tp)
    sl_px = entry * (1.0 - sl)
    bars = k[(k.index >= t) & (k.index < t + pd.Timedelta(minutes=HOLD_MIN))]
    if len(bars) != HOLD_MIN // 5:
        raise RuntimeError(f"incomplete 4h path {t}: {len(bars)} bars")

    mfe = 0.0
    mae = 0.0
    ambiguous = False
    for _, b in bars.iterrows():
        hi = float(b.high); lo = float(b.low)
        mfe = max(mfe, hi / entry - 1.0)
        mae = max(mae, 1.0 - lo / entry)
        hit_tp = hi >= tp_px
        hit_sl = lo <= sl_px
        if hit_tp and hit_sl:
            ambiguous = True
        # Conservative adverse-first handling.
        if hit_sl:
            ret = -sl
            return {
                "pnl": NOTIONAL * ret - FEE,
                "ret": ret,
                "reason": "SL",
                "exit_t": b.ts,
                "exit_px": sl_px,
                "mfe": mfe,
                "mae": mae,
                "ambiguous": ambiguous,
            }
        if hit_tp:
            ret = tp
            return {
                "pnl": NOTIONAL * ret - FEE,
                "ret": ret,
                "reason": "TP",
                "exit_t": b.ts,
                "exit_px": tp_px,
                "mfe": mfe,
                "mae": mae,
                "ambiguous": ambiguous,
            }

    last = bars.iloc[-1]
    exit_px = float(last.close)
    ret = exit_px / entry - 1.0
    return {
        "pnl": NOTIONAL * ret - FEE,
        "ret": ret,
        "reason": "TIMEOUT",
        "exit_t": last.ts + pd.Timedelta(minutes=5),
        "exit_px": exit_px,
        "mfe": mfe,
        "mae": mae,
        "ambiguous": ambiguous,
    }


def metrics(vals) -> dict:
    x = np.asarray(vals, dtype=float)
    pos = x[x > 0]
    neg = x[x <= 0]
    wins = int((x > 0).sum())
    losses = int((x <= 0).sum())
    gp = float(pos.sum()) if len(pos) else 0.0
    gl = float(-neg.sum()) if len(neg) else 0.0
    pf = gp / gl if gl > 0 else float("inf")
    eq = np.cumsum(x)
    peaks = np.maximum.accumulate(np.r_[0.0, eq])
    dd = float(np.max(peaks[1:] - eq)) if len(eq) else 0.0
    ls = 0; cur = 0
    for z in x:
        if z <= 0:
            cur += 1; ls = max(ls, cur)
        else:
            cur = 0
    return {
        "n": int(len(x)), "wins": wins, "losses": losses,
        "wr": wins / len(x) if len(x) else float("nan"),
        "pnl": float(x.sum()), "expectancy": float(x.mean()) if len(x) else float("nan"),
        "pf": float(pf), "dd": dd, "ls": int(ls),
    }


def block_pnls(vals, nblocks: int) -> list[float]:
    idxs = np.array_split(np.arange(len(vals)), nblocks)
    return [float(np.asarray(vals)[ix].sum()) for ix in idxs if len(ix)]


def main():
    k = f517.load_klines()
    entries = sunday_entries(k)
    if len(entries) != 139:
        raise RuntimeError(f"Sunday occurrence parity fail: {len(entries)} expected 139")

    # Precompute path outcomes for each cell. 299 x 139 is still tiny.
    surfaces = []
    trade_rows = []
    cache = {}
    for tp in TP_GRID:
        for sl in SL_GRID:
            outs = [simulate(k, t, tp, sl) for t in entries]
            pnls = np.array([o["pnl"] for o in outs], dtype=float)
            disc = pnls[:DISC_N]
            val = pnls[DISC_N:]
            dm = metrics(disc); vm = metrics(val); fm = metrics(pnls)
            dblocks = block_pnls(disc, 5)
            fblocks = block_pnls(pnls, 8)
            pos_dblocks = int(sum(x > 0 for x in dblocks))
            pos_fblocks = int(sum(x > 0 for x in fblocks))
            reasons = pd.Series([o["reason"] for o in outs]).value_counts().to_dict()
            amb = int(sum(bool(o["ambiguous"]) for o in outs))
            rec = {
                "tp_pct": tp, "sl_pct": sl, "rr": tp / sl,
                "D_pnl": dm["pnl"], "D_wr": dm["wr"], "D_pf": dm["pf"], "D_dd": dm["dd"],
                "D_expectancy": dm["expectancy"], "D_positive_blocks_5": pos_dblocks,
                "V_pnl": vm["pnl"], "V_wr": vm["wr"], "V_pf": vm["pf"], "V_dd": vm["dd"],
                "V_expectancy": vm["expectancy"],
                "full_pnl": fm["pnl"], "full_wr": fm["wr"], "full_pf": fm["pf"], "full_dd": fm["dd"],
                "full_expectancy": fm["expectancy"], "full_positive_blocks_8": pos_fblocks,
                "tp_count": int(reasons.get("TP", 0)), "sl_count": int(reasons.get("SL", 0)),
                "timeout_count": int(reasons.get("TIMEOUT", 0)), "ambiguous_count": amb,
                "D_block_pnls": dblocks, "full_block_pnls": fblocks,
            }
            rec["D_eligible"] = bool(dm["pnl"] > 0 and dm["pf"] > 1.10 and pos_dblocks >= 4)
            surfaces.append(rec)
            cache[(tp, sl)] = (outs, rec)

    df = pd.DataFrame(surfaces)

    # Discovery-only local-neighborhood plateau score.
    for i, r in df.iterrows():
        neigh = df[(df.tp_pct.sub(r.tp_pct).abs() <= 0.1000001) &
                   (df.sl_pct.sub(r.sl_pct).abs() <= 0.1000001)]
        df.loc[i, "neighbor_n"] = len(neigh)
        df.loc[i, "neighbor_D_pnl_median"] = float(neigh.D_pnl.median())
        df.loc[i, "neighbor_D_pnl_min"] = float(neigh.D_pnl.min())
        df.loc[i, "neighbor_D_positive_share"] = float((neigh.D_pnl > 0).mean())

    eligible = df[df.D_eligible].copy()
    if eligible.empty:
        raise RuntimeError("no discovery-eligible TP/SL cell")
    robust = eligible.sort_values(
        ["neighbor_D_pnl_median", "D_pnl", "neighbor_D_pnl_min"], ascending=False
    ).iloc[0]
    rawD = df.sort_values("D_pnl", ascending=False).iloc[0]
    rawFull = df.sort_values("full_pnl", ascending=False).iloc[0]

    # Detailed rows ONLY for discovery-selected robust champion.
    tp = float(robust.tp_pct); sl = float(robust.sl_pct)
    outs, _ = cache[(tp, sl)]
    for i, (t, o) in enumerate(zip(entries, outs)):
        trade_rows.append({
            "i": i, "period": "discovery" if i < DISC_N else "validation",
            "date_local": str(t.tz_convert("Asia/Jakarta").date()), "entry_t_utc": str(t),
            "tp_pct": tp, "sl_pct": sl, **o,
        })
    pd.DataFrame(trade_rows).to_csv(OUT / "sun10_champion_trades.csv", index=False)

    # Serialize surfaces without list columns to CSV.
    csvdf = df.drop(columns=["D_block_pnls", "full_block_pnls"])
    csvdf.to_csv(OUT / "sun10_surface.csv", index=False)

    def pack(s):
        keys = [
            "tp_pct","sl_pct","rr","D_pnl","D_wr","D_pf","D_dd","D_expectancy","D_positive_blocks_5",
            "V_pnl","V_wr","V_pf","V_dd","V_expectancy","full_pnl","full_wr","full_pf","full_dd",
            "full_expectancy","full_positive_blocks_8","tp_count","sl_count","timeout_count","ambiguous_count",
            "neighbor_n","neighbor_D_pnl_median","neighbor_D_pnl_min","neighbor_D_positive_share",
        ]
        return {k: (float(s[k]) if isinstance(s[k], (np.floating, float)) else int(s[k]) if isinstance(s[k], (np.integer,)) else s[k]) for k in keys}

    topD = [pack(r) for _, r in df.sort_values("D_pnl", ascending=False).head(15).iterrows()]
    topRob = [pack(r) for _, r in eligible.sort_values(["neighbor_D_pnl_median","D_pnl"], ascending=False).head(15).iterrows()]

    val_confirm = bool(robust.V_pnl > 0 and robust.V_pf > 1.0)
    out = {
        "status": "DISCOVERY_SELECTED_VALIDATION_REPORTED",
        "live_bbc_untouched": True,
        "definition": {
            "symbol": "BTCUSDT", "entry": "Sunday 01:00 WIB BUY, exact 5m open",
            "hold_min": HOLD_MIN, "notional": NOTIONAL, "margin_reference": 10.0, "leverage_reference": 50,
            "round_trip_fee_pct": 0.15, "funding": "none within fixed 18:00-22:00 UTC 4h window",
            "same_5m_ambiguity": "adverse-first",
            "tp_grid_pct": [min(TP_GRID), max(TP_GRID), 0.1],
            "sl_grid_pct": [min(SL_GRID), max(SL_GRID), 0.1],
            "occurrences": len(entries), "discovery_n": DISC_N, "validation_n": len(entries)-DISC_N,
        },
        "selection": {
            "validation_used_for_selection": False,
            "eligibility": "D PnL >0, D PF>1.10, >=4/5 D chronological blocks positive",
            "ranking": "max neighborhood median D PnL over +/-0.1 TP/SL, then max D PnL",
        },
        "robust_discovery_champion": pack(robust),
        "validation_confirms_positive_expectancy": val_confirm,
        "raw_discovery_pnl_champion": pack(rawD),
        "raw_full_sample_pnl_champion_for_reference_only": pack(rawFull),
        "top15_discovery_pnl": topD,
        "top15_robust_plateau": topRob,
        "guardrail": "A1 already inspected the full historical Sunday edge. Validation is a robustness slice, not untouched OOS. Do not retune to validation if the discovery-selected champion fails.",
    }
    (OUT / "sun10_summary.json").write_text(json.dumps(out, indent=2, default=str))

    c = out["robust_discovery_champion"]
    rd = out["raw_discovery_pnl_champion"]
    rf = out["raw_full_sample_pnl_champion_for_reference_only"]
    md = [
        "# BTC Sunday 01:00 WIB BUY — SUN1.0 TP/SL Surface",
        "",
        "**Status: COMPLETE — discovery-selected TP/SL with validation reported; live BBC untouched.**",
        "",
        "## Frozen test definition",
        f"- 139 Sunday 01:00 WIB BUY entries; first {DISC_N} discovery / last {139-DISC_N} validation",
        f"- max hold **{HOLD_MIN}m (4h)**",
        "- $500 notional = $10 margin x50; 0.15% round-trip fee",
        "- same-5m ambiguity adverse-first; timeout at final 5m close",
        "- TP grid 0.3–2.5%; SL grid 0.3–1.5%; step 0.1%",
        "- validation was not used to choose the champion",
        "",
        "## Discovery-selected robust champion",
        f"- **TP {c['tp_pct']:.1f}% / SL {c['sl_pct']:.1f}% (RR {c['rr']:.2f})**",
        f"- Discovery: PnL **${c['D_pnl']:+.3f}**, WR **{100*c['D_wr']:.2f}%**, PF **{c['D_pf']:.3f}**, DD **${c['D_dd']:.3f}**, positive blocks **{int(c['D_positive_blocks_5'])}/5**",
        f"- Validation: PnL **${c['V_pnl']:+.3f}**, WR **{100*c['V_wr']:.2f}%**, PF **{c['V_pf']:.3f}**, DD **${c['V_dd']:.3f}**",
        f"- Full: PnL **${c['full_pnl']:+.3f}**, WR **{100*c['full_wr']:.2f}%**, PF **{c['full_pf']:.3f}**, DD **${c['full_dd']:.3f}**, blocks positive **{int(c['full_positive_blocks_8'])}/8**",
        f"- TP/SL/timeout **{int(c['tp_count'])}/{int(c['sl_count'])}/{int(c['timeout_count'])}**; ambiguous bars **{int(c['ambiguous_count'])}**",
        f"- local +/-0.1 neighborhood median discovery PnL **${c['neighbor_D_pnl_median']:+.3f}**; minimum **${c['neighbor_D_pnl_min']:+.3f}**",
        f"- Validation positive-expectancy confirmation: **{'YES' if val_confirm else 'NO'}**",
        "",
        "## Reference champions (not selection targets)",
        f"- raw discovery max-PnL cell: TP {rd['tp_pct']:.1f}% / SL {rd['sl_pct']:.1f}% → D ${rd['D_pnl']:+.3f}, V ${rd['V_pnl']:+.3f}, full ${rd['full_pnl']:+.3f}",
        f"- raw full-sample max-PnL cell (look-ahead reference only): TP {rf['tp_pct']:.1f}% / SL {rf['sl_pct']:.1f}% → full ${rf['full_pnl']:+.3f}",
        "",
        "## Guardrail",
        "The full Sunday temporal edge was already inspected in A1, so the last-56 validation slice is robustness evidence rather than pristine OOS. If the discovery-selected cell fails validation, do not rescue it by choosing a validation-favored grid cell.",
    ]
    (OUT / "SUN1.0_CHECKPOINT.md").write_text("\n".join(md) + "\n")
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
