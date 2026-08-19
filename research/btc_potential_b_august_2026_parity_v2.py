#!/usr/bin/env python3
"""Potential B historical parity recovery V2 + August replay."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import btc_potential_b_august_2026_replay as v1

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_PotentialB_ParityRecovery_V2_Result.md"
OUT_JSON = ROOT / "BTC_PotentialB_ParityRecovery_V2_Result.json"
OUT_CSV = ROOT / "BTC_PotentialB_ParityRecovery_V2_August_Events.csv"

WINDOWS = (60, 90, 120)


def detect_events(x: pd.DataFrame, open_hour: int, trigger_mode: str, window_minutes: int,
                  start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows = []
    by_date = {d: g for d, g in x.groupby("utc_date", sort=False)}
    d = start.normalize()
    while d < end.normalize():
        # London cash/session concept: weekdays only.
        if d.weekday() >= 5:
            d += pd.Timedelta(days=1)
            continue
        ds = d.strftime("%Y-%m-%d")
        g = by_date.get(ds)
        d += pd.Timedelta(days=1)
        if g is None or g.empty:
            continue
        open_ts = pd.Timestamp(f"{ds}T{open_hour:02d}:00:00Z")
        event_end = open_ts + pd.Timedelta(minutes=window_minutes)
        pre = g[(g.ts >= pd.Timestamp(f"{ds}T00:00:00Z")) & (g.ts < open_ts)]
        sess = g[(g.ts >= open_ts) & (g.ts < event_end)]
        if pre.empty or len(sess) < 3:
            continue
        hod = float(pre.high.max())
        idxs = sess.index.to_numpy(int)
        confirm_idx = None
        for k in range(1, len(idxs)):
            a, b = int(idxs[k - 1]), int(idxs[k])
            if x.ts.iloc[b] - x.ts.iloc[a] != pd.Timedelta(minutes=5):
                continue
            if float(x.close.iloc[a]) > hod and float(x.close.iloc[b]) > hod:
                confirm_idx = b
                break
        if confirm_idx is None:
            continue
        trigger_idx = confirm_idx
        if trigger_mode == "TRAP_BACK_BELOW":
            later = [int(j) for j in idxs if int(j) > confirm_idx]
            back = [j for j in later if float(x.close.iloc[j]) < hod]
            if not back:
                continue
            trigger_idx = back[0]
        elif trigger_mode != "CONFIRM2":
            raise ValueError(trigger_mode)

        entry_idx = v1.next_15m_entry(x, trigger_idx)
        if entry_idx is None:
            continue
        r60 = v1.resolve_60m(x, entry_idx)
        r1 = v1.resolve_1pct(x, entry_idx)
        if r60 is None or r1 is None:
            continue
        aggr = float(x.taker_buy_share.iloc[confirm_idx]) > v1.AGGR_THRESHOLD
        rows.append({
            "utc_date": ds,
            "open_hour_utc": open_hour,
            "event_window_minutes": window_minutes,
            "trigger_mode": trigger_mode,
            "frozen_hod": hod,
            "confirm_ts": x.ts.iloc[confirm_idx],
            "trigger_ts": x.ts.iloc[trigger_idx],
            "entry_ts": x.ts.iloc[entry_idx],
            "entry_wib": x.ts.iloc[entry_idx] + pd.Timedelta(hours=7),
            "confirm_taker_buy_share": float(x.taker_buy_share.iloc[confirm_idx]),
            "aggressive": bool(aggr),
            **r60,
            **r1,
        })
    return pd.DataFrame(rows)


def parity_metrics(full: pd.DataFrame) -> dict:
    if full.empty:
        m = {k: 0 for k in v1.BENCH}
    else:
        dates = pd.to_datetime(full.utc_date, utc=True)
        rec = full[(dates >= v1.RECENT_START) & (dates < v1.HIST_END)]
        hist = full[(dates >= v1.HIST_START) & (dates < v1.HIST_END)]
        rec_ag = rec[rec.aggressive]
        hist_ag = hist[hist.aggressive]
        m = {
            "recent_base_n": int(len(rec)),
            "recent_base_wins": int(rec.dir_win_60m.sum()) if len(rec) else 0,
            "recent_aggr_n": int(len(rec_ag)),
            "recent_aggr_wins": int(rec_ag.dir_win_60m.sum()) if len(rec_ag) else 0,
            "full_aggr_n": int(len(hist_ag)),
            "full_aggr_wins": int(hist_ag.dir_win_60m.sum()) if len(hist_ag) else 0,
        }
    m["parity_score"] = int(sum(abs(m[k] - v1.BENCH[k]) for k in v1.BENCH))
    m["exact_parity"] = m["parity_score"] == 0
    return m


def pct(v):
    return "-" if v is None else f"{100*v:.2f}%"


def main():
    x = v1.load_data()
    candidates = []
    for h in (7, 8):
        for w in WINDOWS:
            for mode in ("CONFIRM2", "TRAP_BACK_BELOW"):
                ev = detect_events(x, h, mode, w, v1.HIST_START, v1.HIST_END)
                p = parity_metrics(ev)
                candidates.append({"key": f"H{h}_W{w}_{mode}", "open_hour_utc": h,
                                   "window_minutes": w, "trigger_mode": mode, **p})
                print("PARITY", candidates[-1])
    candidates.sort(key=lambda q: (q["parity_score"], q["window_minutes"], q["open_hour_utc"], q["trigger_mode"]))
    chosen = candidates[0]
    status = "PARITY_EXACT" if chosen["parity_score"] == 0 else ("PARITY_APPROXIMATE" if chosen["parity_score"] <= 6 else "PARITY_UNRESOLVED")

    aug = detect_events(x, chosen["open_hour_utc"], chosen["trigger_mode"], chosen["window_minutes"], v1.AUG_START, v1.AUG_END)
    base = v1.simple_stats(aug)
    ag = v1.simple_stats(aug[aug.aggressive] if not aug.empty else aug)
    one = v1.onepct_stats(aug)
    one_ag = v1.onepct_stats(aug[aug.aggressive] if not aug.empty else aug)
    if aug.empty:
        pd.DataFrame(columns=["utc_date"]).to_csv(OUT_CSV, index=False)
    else:
        aug.to_csv(OUT_CSV, index=False)

    out = {
        "protocol": "POTENTIAL_B_PARITY_RECOVERY_V2",
        "data_last_ts": str(x.ts.max()),
        "benchmark": v1.BENCH,
        "candidates": candidates,
        "selected": chosen,
        "parity_status": status,
        "august_base_60m": base,
        "august_aggressive_60m": ag,
        "august_base_1pct": one,
        "august_aggressive_1pct": one_ag,
        "guardrails": {"weekdays_only": True, "august_used_for_selection": False, "one_minute_data": False},
    }
    OUT_JSON.write_text(json.dumps(out, indent=2, default=str) + "\n")

    md = [
        "# BTC Potential B — Historical Parity Recovery V2 + August Replay",
        "",
        f"**Parity status: {status}**",
        "",
        "Benchmark: recent base 17/24; recent aggressive 11/15; full aggressive 43/67.",
        "",
        "| Variant | Recent base | Recent aggressive | Full aggressive | Score |",
        "|---|---:|---:|---:|---:|",
    ]
    for q in candidates:
        md.append(f"| `{q['key']}` | {q['recent_base_wins']}/{q['recent_base_n']} | {q['recent_aggr_wins']}/{q['recent_aggr_n']} | {q['full_aggr_wins']}/{q['full_aggr_n']} | {q['parity_score']} |")
    md += [
        "",
        f"Selected from historical parity only: **`{chosen['key']}`**.",
        "",
        "## August 60m directional",
        "",
        "| Cohort | N | Wins | WR | Avg SELL ret | Median MFE | Median MAE |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Base | {base['n']} | {base['wins']} | {pct(base['wr'])} | {pct(base['avg_signed_ret'])} | {pct(base['median_mfe'])} | {pct(base['median_mae'])} |",
        f"| Aggressive >50% | {ag['n']} | {ag['wins']} | {pct(ag['wr'])} | {pct(ag['avg_signed_ret'])} | {pct(ag['median_mfe'])} | {pct(ag['median_mae'])} |",
        "",
        "## August >1% diagnostic",
        "",
        "| Cohort | N | Wins | WR | TP | SL | TIME | PnL |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| Base | {one['n']} | {one['wins']} | {pct(one['wr'])} | {one['tp']} | {one['sl']} | {one['time']} | ${one['pnl']:.2f} |",
        f"| Aggressive >50% | {one_ag['n']} | {one_ag['wins']} | {pct(one_ag['wr'])} | {one_ag['tp']} | {one_ag['sl']} | {one_ag['time']} | ${one_ag['pnl']:.2f} |",
        "",
        "## August events",
        "",
    ]
    if aug.empty:
        md.append("No event in available completed August data.")
    else:
        md += ["| Date | Entry WIB | Aggressive | 60m | SELL ret | 1%/6h | MFE6h |",
               "|---|---|---|---|---:|---|---:|"]
        for _, r in aug.iterrows():
            md.append(f"| {r.utc_date} | {pd.Timestamp(r.entry_wib).strftime('%Y-%m-%d %H:%M')} | {'YES' if r.aggressive else 'NO'} | {'WIN' if r.dir_win_60m else 'LOSS'} | {100*r.signed_ret_60m:.3f}% | {r.onepct_reason} | {100*r.mfe_6h:.3f}% |")
    md += ["", "No August observation is used to select the historical parity variant; no post-result rescue."]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
