#!/usr/bin/env python3
from pathlib import Path
import numpy as np
import pandas as pd
import btc_h1_low_reject_structure_lr1 as dataio

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_WEEKLY_ONEPCT_WINDOW_Diagnostic.md"
OUT_CSV = ROOT / "BTC_WEEKLY_ONEPCT_WINDOW_Diagnostic.csv"

START = pd.Timestamp("2020-01-01", tz="UTC")
END = pd.Timestamp("2026-08-20", tz="UTC")


def week_start(ts):
    t = pd.Timestamp(ts)
    d = t.floor("D")
    return d - pd.Timedelta(days=t.weekday())


def prep(k, tf):
    x = k[["open","high","low","close"]].copy()
    if tf == "H4":
        x = x.resample("4h", origin="start_day", label="left", closed="left").agg(
            {"open":"first","high":"max","low":"min","close":"last"}
        ).dropna()
    return x


def complete_weeks(start, end_exclusive):
    first = start.floor("D") - pd.Timedelta(days=start.weekday())
    if first < start:
        first += pd.Timedelta(days=7)
    out=[]
    w=first
    while w + pd.Timedelta(days=7) <= end_exclusive:
        out.append(w)
        w += pd.Timedelta(days=7)
    return out


def first_hit(fut, entry, side, tp_frac=0.01, sl_frac=0.01):
    if side == "LONG":
        tp = entry * (1+tp_frac)
        sl = entry * (1-sl_frac)
        for _, b in fut.iterrows():
            hit_sl = float(b.low) <= sl
            hit_tp = float(b.high) >= tp
            if hit_sl:
                return "SL"
            if hit_tp:
                return "TP"
    else:
        tp = entry * (1-tp_frac)
        sl = entry * (1+sl_frac)
        for _, b in fut.iterrows():
            hit_sl = float(b.high) >= sl
            hit_tp = float(b.low) <= tp
            if hit_sl:
                return "SL"
            if hit_tp:
                return "TP"
    return "TIME"


def scan_tf(x, tf, weeks):
    rows=[]
    for w in weeks:
        wend = w + pd.Timedelta(days=7)
        idxs = np.flatnonzero((x.index >= w) & (x.index < wend)).tolist()
        cand=0; wins=0; long_w=0; short_w=0; both_w=0
        first_win_ts=None
        for i in idxs:
            if i+1 >= len(x):
                continue
            entry_ts = x.index[i+1]
            if not (w <= entry_ts < wend):
                continue
            entry=float(x.iloc[i+1].open)
            fut=x.iloc[i+1:]
            fut=fut[fut.index < wend]
            if fut.empty:
                continue
            cand += 1
            lo=first_hit(fut, entry, "LONG")
            sh=first_hit(fut, entry, "SHORT")
            lw = lo == "TP"
            sw = sh == "TP"
            if lw or sw:
                wins += 1
                long_w += int(lw)
                short_w += int(sw)
                both_w += int(lw and sw)
                if first_win_ts is None:
                    first_win_ts = entry_ts
        rows.append({
            "tf":tf,
            "week":f"{w.isocalendar().year:04d}-W{w.isocalendar().week:02d}",
            "week_start":w,
            "candidates":cand,
            "winning_windows":wins,
            "long_winning_windows":long_w,
            "short_winning_windows":short_w,
            "both_direction_winning_windows":both_w,
            "has_any_win":int(wins>0),
            "first_win_entry_ts":first_win_ts,
        })
    return pd.DataFrame(rows)


def summarize(z):
    return {
        "weeks": int(len(z)),
        "weeks_with_win": int(z.has_any_win.sum()),
        "coverage_pct": float(100*z.has_any_win.mean()),
        "min_windows": int(z.winning_windows.min()),
        "p10_windows": float(z.winning_windows.quantile(.10)),
        "median_windows": float(z.winning_windows.median()),
        "mean_windows": float(z.winning_windows.mean()),
        "p90_windows": float(z.winning_windows.quantile(.90)),
        "max_windows": int(z.winning_windows.max()),
        "median_candidates": float(z.candidates.median()),
    }


def main():
    k=dataio.load_1h().copy()
    k["ts"] = pd.to_datetime(k["ts"], utc=True)
    k=k[(k.ts>=START)&(k.ts<END)].set_index("ts").sort_index()
    weeks=complete_weeks(START, END)
    allz=[]; stats={}
    for tf in ["H1","H4"]:
        z=scan_tf(prep(k,tf),tf,weeks)
        allz.append(z); stats[tf]=summarize(z)
    out=pd.concat(allz,ignore_index=True)
    out.to_csv(OUT_CSV,index=False)

    lines=[
        "# BTC Weekly 1% Winning-Window Diagnostic",
        "",
        f"Coverage **{k.index.min()} -> {k.index.max()}**, official H1 rows **{len(k):,}**. Complete ISO weeks: **{len(weeks)}**.",
        "",
        "Diagnostic only, not a live selector. For every completed H1/H4 bar, entry is the next bar open. LONG and SHORT are evaluated separately against a symmetric **+1% TP / -1% SL** until the end of the same ISO week. Same-bar TP+SL ambiguity is adverse-first. A `winning window` means at least one direction reaches +1% before -1% from that next-open entry.",
        "",
        "| TF | Weeks with >=1 winning window | Min | P10 | Median | Mean | P90 | Max | Median candidates/week |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for tf in ["H1","H4"]:
        s=stats[tf]
        lines.append(f"| {tf} | {s['weeks_with_win']}/{s['weeks']} ({s['coverage_pct']:.2f}%) | {s['min_windows']} | {s['p10_windows']:.1f} | {s['median_windows']:.1f} | {s['mean_windows']:.1f} | {s['p90_windows']:.1f} | {s['max_windows']} | {s['median_candidates']:.1f} |")
    lines += ["", "## Weeks with the fewest winning windows"]
    for tf in ["H1","H4"]:
        q=out[out.tf==tf].sort_values(["winning_windows","week"]).head(10)
        lines += ["", f"### {tf}", "", "| Week | Candidates | Winning windows | Long wins | Short wins | Both-dir wins |", "|---|---:|---:|---:|---:|---:|"]
        for _,r in q.iterrows():
            lines.append(f"| {r.week} | {int(r.candidates)} | {int(r.winning_windows)} | {int(r.long_winning_windows)} | {int(r.short_winning_windows)} | {int(r.both_direction_winning_windows)} |")
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
