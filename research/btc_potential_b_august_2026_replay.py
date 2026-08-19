#!/usr/bin/env python3
"""Potential B parity reconstruction + August 2026 true-OOS replay.

Research-only. No live order path. No 1m data.
"""
from __future__ import annotations

import csv
import io
import json
import math
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_PotentialB_August2026_Replay_Result.md"
OUT_JSON = ROOT / "BTC_PotentialB_August2026_Replay_Result.json"
OUT_CSV = ROOT / "BTC_PotentialB_August2026_Replay_Events.csv"

BASE = "https://data.binance.vision/data/futures/um"
SYMBOL = "BTCUSDT"
TF = "5m"
HIST_START = pd.Timestamp("2023-12-02T00:00:00Z")
HIST_END = pd.Timestamp("2026-07-30T00:00:00Z")
RECENT_START = HIST_END - pd.Timedelta(days=240)
AUG_START = pd.Timestamp("2026-08-01T00:00:00Z")
AUG_END = pd.Timestamp("2026-08-20T00:00:00Z")
AGGR_THRESHOLD = 0.50
SESSION_END_HOUR = 16
FEE = 0.0015
NOTIONAL = 500.0

BENCH = {
    "recent_base_n": 24,
    "recent_base_wins": 17,
    "recent_aggr_n": 15,
    "recent_aggr_wins": 11,
    "full_aggr_n": 67,
    "full_aggr_wins": 43,
}


def fetch_zip(url: str) -> list[list[float]]:
    r = requests.get(url, timeout=60, headers={"User-Agent": "bababot-potential-b-aug/1.0"})
    if r.status_code == 404:
        return []
    r.raise_for_status()
    out = []
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return []
        with zf.open(names[0]) as fh:
            for row in csv.reader(io.TextIOWrapper(fh, encoding="utf-8")):
                if len(row) < 11:
                    continue
                try:
                    ts = int(row[0])
                except Exception:
                    continue
                if ts > 100_000_000_000_000:
                    ts //= 1000
                try:
                    out.append([
                        ts,
                        float(row[1]), float(row[2]), float(row[3]), float(row[4]),
                        float(row[7]), float(row[10]),
                    ])
                except Exception:
                    continue
    return out


def urls() -> list[str]:
    jobs = []
    cur = pd.Timestamp(HIST_START.year, HIST_START.month, 1, tz="UTC")
    last_month = pd.Timestamp(2026, 8, 1, tz="UTC")
    while cur < last_month:
        ym = cur.strftime("%Y-%m")
        jobs.append(f"{BASE}/monthly/klines/{SYMBOL}/{TF}/{SYMBOL}-{TF}-{ym}.zip")
        cur += pd.offsets.MonthBegin(1)
    d = AUG_START
    while d < AUG_END:
        ds = d.strftime("%Y-%m-%d")
        jobs.append(f"{BASE}/daily/klines/{SYMBOL}/{TF}/{SYMBOL}-{TF}-{ds}.zip")
        d += pd.Timedelta(days=1)
    return jobs


def load_data() -> pd.DataFrame:
    jobs = urls()
    rows = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        fs = {ex.submit(fetch_zip, u): u for u in jobs}
        done = 0
        for f in as_completed(fs):
            rows.extend(f.result())
            done += 1
            if done % 10 == 0:
                print(f"downloaded {done}/{len(jobs)} archives")
    if not rows:
        raise RuntimeError("no Binance 5m data")
    x = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "quote_volume", "taker_buy_quote"])
    x["ts"] = pd.to_datetime(pd.to_numeric(x.ts), unit="ms", utc=True)
    x = x.dropna().drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    x = x[(x.ts >= HIST_START) & (x.ts < AUG_END)].reset_index(drop=True)
    x["taker_buy_share"] = np.where(x.quote_volume > 0, x.taker_buy_quote / x.quote_volume, np.nan)
    x["utc_date"] = x.ts.dt.strftime("%Y-%m-%d")
    return x


def next_15m_entry(x: pd.DataFrame, trigger_idx: int) -> int | None:
    after = x.ts.iloc[trigger_idx] + pd.Timedelta(minutes=5)
    target = after.ceil("15min")
    arr = x.ts.values
    j = int(np.searchsorted(arr, np.datetime64(target.to_datetime64()), side="left"))
    if j >= len(x) or x.ts.iloc[j] != target:
        return None
    return j


def resolve_60m(x: pd.DataFrame, entry_idx: int) -> dict | None:
    end_idx = entry_idx + 11
    if end_idx >= len(x):
        return None
    expected = x.ts.iloc[entry_idx] + pd.Timedelta(minutes=55)
    if x.ts.iloc[end_idx] != expected:
        return None
    ep = float(x.open.iloc[entry_idx])
    fc = float(x.close.iloc[end_idx])
    hs = x.high.iloc[entry_idx:end_idx + 1].to_numpy(float)
    ls = x.low.iloc[entry_idx:end_idx + 1].to_numpy(float)
    signed = (ep - fc) / ep
    mfe = (ep - float(np.min(ls))) / ep
    mae = (float(np.max(hs)) - ep) / ep
    return {
        "entry_price": ep,
        "close_60m": fc,
        "signed_ret_60m": signed,
        "dir_win_60m": int(signed > 0),
        "mfe_60m": mfe,
        "mae_60m": mae,
    }


def resolve_1pct(x: pd.DataFrame, entry_idx: int) -> dict | None:
    bars = 72  # 6h of 5m bars
    end_idx = entry_idx + bars - 1
    if end_idx >= len(x):
        return None
    if x.ts.iloc[end_idx] != x.ts.iloc[entry_idx] + pd.Timedelta(minutes=5 * (bars - 1)):
        return None
    ep = float(x.open.iloc[entry_idx])
    tp = ep * 0.99
    sl = ep * 1.01
    hs = x.high.iloc[entry_idx:end_idx + 1].to_numpy(float)
    ls = x.low.iloc[entry_idx:end_idx + 1].to_numpy(float)
    tp_hits = np.flatnonzero(ls <= tp)
    sl_hits = np.flatnonzero(hs >= sl)
    ti = int(tp_hits[0]) if tp_hits.size else 10**9
    si = int(sl_hits[0]) if sl_hits.size else 10**9
    if si <= ti:
        raw = -0.01
        reason = "SL_1PCT"
        win = 0
    elif ti < 10**9:
        raw = 0.01
        reason = "TP_1PCT"
        win = 1
    else:
        fc = float(x.close.iloc[end_idx])
        raw = (ep - fc) / ep
        reason = "TIME_6H"
        win = int(raw - FEE > 0)
    net = raw - FEE
    return {
        "onepct_reason": reason,
        "onepct_win": win,
        "onepct_raw_ret": raw,
        "onepct_net_ret": net,
        "onepct_pnl": net * NOTIONAL,
        "mfe_6h": (ep - float(np.min(ls))) / ep,
        "mae_6h": (float(np.max(hs)) - ep) / ep,
    }


def detect_events(x: pd.DataFrame, open_hour: int, trigger_mode: str,
                  start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows = []
    date0 = start.normalize()
    date1 = end.normalize()
    by_date = {d: g for d, g in x.groupby("utc_date", sort=False)}
    d = date0
    while d < date1:
        ds = d.strftime("%Y-%m-%d")
        g = by_date.get(ds)
        d += pd.Timedelta(days=1)
        if g is None or g.empty:
            continue
        open_ts = pd.Timestamp(f"{ds}T{open_hour:02d}:00:00Z")
        end_ts = pd.Timestamp(f"{ds}T{SESSION_END_HOUR:02d}:00:00Z")
        pre = g[(g.ts >= pd.Timestamp(f"{ds}T00:00:00Z")) & (g.ts < open_ts)]
        sess = g[(g.ts >= open_ts) & (g.ts < end_ts)]
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
            later = idxs[idxs > confirm_idx]
            back = [int(j) for j in later if float(x.close.iloc[int(j)]) < hod]
            if not back:
                continue
            trigger_idx = back[0]
        elif trigger_mode != "CONFIRM2":
            raise ValueError(trigger_mode)

        entry_idx = next_15m_entry(x, trigger_idx)
        if entry_idx is None:
            continue
        r60 = resolve_60m(x, entry_idx)
        r1 = resolve_1pct(x, entry_idx)
        if r60 is None or r1 is None:
            continue
        aggr = float(x.taker_buy_share.iloc[confirm_idx]) > AGGR_THRESHOLD
        rows.append({
            "utc_date": ds,
            "open_hour_utc": open_hour,
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


def simple_stats(z: pd.DataFrame) -> dict:
    if z is None or z.empty:
        return {"n": 0, "wins": 0, "wr": None, "avg_signed_ret": None, "median_mfe": None, "median_mae": None}
    return {
        "n": int(len(z)),
        "wins": int(z.dir_win_60m.sum()),
        "wr": float(z.dir_win_60m.mean()),
        "avg_signed_ret": float(z.signed_ret_60m.mean()),
        "median_mfe": float(z.mfe_60m.median()),
        "median_mae": float(z.mae_60m.median()),
    }


def onepct_stats(z: pd.DataFrame) -> dict:
    if z is None or z.empty:
        return {"n": 0, "wins": 0, "wr": None, "pnl": 0.0, "tp": 0, "sl": 0, "time": 0}
    return {
        "n": int(len(z)),
        "wins": int(z.onepct_win.sum()),
        "wr": float(z.onepct_win.mean()),
        "pnl": float(z.onepct_pnl.sum()),
        "tp": int((z.onepct_reason == "TP_1PCT").sum()),
        "sl": int((z.onepct_reason == "SL_1PCT").sum()),
        "time": int((z.onepct_reason == "TIME_6H").sum()),
        "median_mfe_6h": float(z.mfe_6h.median()),
        "median_mae_6h": float(z.mae_6h.median()),
    }


def parity_metrics(full: pd.DataFrame) -> dict:
    rec = full[(pd.to_datetime(full.utc_date, utc=True) >= RECENT_START) &
               (pd.to_datetime(full.utc_date, utc=True) < HIST_END)] if not full.empty else full
    hist = full[(pd.to_datetime(full.utc_date, utc=True) >= HIST_START) &
                (pd.to_datetime(full.utc_date, utc=True) < HIST_END)] if not full.empty else full
    rec_ag = rec[rec.aggressive] if not rec.empty else rec
    hist_ag = hist[hist.aggressive] if not hist.empty else hist
    m = {
        "recent_base_n": int(len(rec)),
        "recent_base_wins": int(rec.dir_win_60m.sum()) if len(rec) else 0,
        "recent_aggr_n": int(len(rec_ag)),
        "recent_aggr_wins": int(rec_ag.dir_win_60m.sum()) if len(rec_ag) else 0,
        "full_aggr_n": int(len(hist_ag)),
        "full_aggr_wins": int(hist_ag.dir_win_60m.sum()) if len(hist_ag) else 0,
    }
    m["parity_score"] = int(sum(abs(m[k] - BENCH[k]) for k in BENCH))
    m["exact_parity"] = bool(m["parity_score"] == 0)
    return m


def fmt_pct(v):
    return "-" if v is None else f"{100*v:.2f}%"


def main():
    x = load_data()
    last_ts = x.ts.max()
    coverage = {
        "rows": int(len(x)),
        "first_ts": str(x.ts.min()),
        "last_ts": str(last_ts),
        "august_last_complete_utc_date_in_data": str(last_ts.date()),
    }
    print(json.dumps(coverage, indent=2))

    candidates = []
    cache = {}
    for hour in (7, 8):
        for mode in ("CONFIRM2", "TRAP_BACK_BELOW"):
            key = f"H{hour}_{mode}"
            ev = detect_events(x, hour, mode, HIST_START, HIST_END)
            cache[key] = ev
            pm = parity_metrics(ev)
            candidates.append({"key": key, "open_hour_utc": hour, "trigger_mode": mode, **pm})
            print("PARITY", key, pm)
    candidates.sort(key=lambda q: (q["parity_score"], q["open_hour_utc"], q["trigger_mode"]))
    chosen = candidates[0]
    if chosen["exact_parity"]:
        parity_status = "PARITY_EXACT"
    elif chosen["parity_score"] <= 6:
        parity_status = "PARITY_APPROXIMATE"
    else:
        parity_status = "PARITY_UNRESOLVED"

    aug = detect_events(x, chosen["open_hour_utc"], chosen["trigger_mode"], AUG_START, AUG_END)
    aug_base = simple_stats(aug)
    aug_ag = simple_stats(aug[aug.aggressive] if not aug.empty else aug)
    aug_1_base = onepct_stats(aug)
    aug_1_ag = onepct_stats(aug[aug.aggressive] if not aug.empty else aug)

    # Save every August event. No selective omission.
    if aug.empty:
        pd.DataFrame(columns=["utc_date"]).to_csv(OUT_CSV, index=False)
    else:
        aug.to_csv(OUT_CSV, index=False)

    out = {
        "protocol": "POTENTIAL_B_AUGUST_2026_REPLAY_V1",
        "coverage": coverage,
        "historical_benchmark": BENCH,
        "parity_candidates": candidates,
        "selected_variant": chosen,
        "parity_status": parity_status,
        "august_window": {"start": str(AUG_START), "end_exclusive": str(AUG_END)},
        "august_base_60m": aug_base,
        "august_aggressive_60m": aug_ag,
        "august_base_1pct_6h": aug_1_base,
        "august_aggressive_1pct_6h": aug_1_ag,
        "guardrails": {
            "august_used_for_parity_selection": False,
            "one_minute_data_used": False,
            "aggressive_threshold": AGGR_THRESHOLD,
            "direction": "SELL",
            "historical_horizon_minutes": 60,
            "large_move_diagnostic": "TP1.0%/SL1.0% max6h adverse-first, fee0.15%, $500 notional",
        },
    }
    OUT_JSON.write_text(json.dumps(out, indent=2, default=str) + "\n")

    md = [
        "# BTC Potential B — August 2026 True-OOS Replay Result",
        "",
        f"**Parity status: {parity_status}**",
        "",
        f"Official 5m coverage: **{coverage['first_ts']} -> {coverage['last_ts']}**, rows **{coverage['rows']}**.",
        "",
        "## Historical parity reconstruction",
        "",
        "Known benchmark: recent base **17/24**, recent aggressive **11/15**, full aggressive **43/67**.",
        "",
        "| Variant | Recent base | Recent aggressive | Full aggressive | Parity score |",
        "|---|---:|---:|---:|---:|",
    ]
    for q in candidates:
        md.append(
            f"| `{q['key']}` | {q['recent_base_wins']}/{q['recent_base_n']} | "
            f"{q['recent_aggr_wins']}/{q['recent_aggr_n']} | {q['full_aggr_wins']}/{q['full_aggr_n']} | {q['parity_score']} |"
        )
    md += [
        "",
        f"Selected only by historical parity: **`{chosen['key']}`**. August was not used to choose the variant.",
        "",
        "## August 2026 — Potential B 60m directional replay",
        "",
        "| Cohort | N | Wins | WR | Avg SELL return | Median MFE | Median MAE |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Base sequence | {aug_base['n']} | {aug_base['wins']} | {fmt_pct(aug_base['wr'])} | {fmt_pct(aug_base['avg_signed_ret'])} | {fmt_pct(aug_base['median_mfe'])} | {fmt_pct(aug_base['median_mae'])} |",
        f"| Aggressive >50% | {aug_ag['n']} | {aug_ag['wins']} | {fmt_pct(aug_ag['wr'])} | {fmt_pct(aug_ag['avg_signed_ret'])} | {fmt_pct(aug_ag['median_mfe'])} | {fmt_pct(aug_ag['median_mae'])} |",
        "",
        "## >1% move diagnostic — same trigger, no 1m data",
        "",
        "TP1.0% / SL1.0%, max6h, same-bar adverse-first, fee0.15%, $500 reference notional.",
        "",
        "| Cohort | N | Wins | WR | TP | SL | TIME | PnL |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| Base sequence | {aug_1_base['n']} | {aug_1_base['wins']} | {fmt_pct(aug_1_base['wr'])} | {aug_1_base['tp']} | {aug_1_base['sl']} | {aug_1_base['time']} | ${aug_1_base['pnl']:.2f} |",
        f"| Aggressive >50% | {aug_1_ag['n']} | {aug_1_ag['wins']} | {fmt_pct(aug_1_ag['wr'])} | {aug_1_ag['tp']} | {aug_1_ag['sl']} | {aug_1_ag['time']} | ${aug_1_ag['pnl']:.2f} |",
        "",
        "## August event ledger",
        "",
    ]
    if aug.empty:
        md.append("No Potential B event occurred in the available completed August data.")
    else:
        md += [
            "| UTC date | Entry WIB | HOD | Taker buy | Aggressive | 60m | 60m SELL ret | 1%/6h | 6h MFE |",
            "|---|---|---:|---:|---|---|---:|---|---:|",
        ]
        for _, r in aug.iterrows():
            md.append(
                f"| {r.utc_date} | {pd.Timestamp(r.entry_wib).strftime('%Y-%m-%d %H:%M')} | {r.frozen_hod:.2f} | "
                f"{100*r.confirm_taker_buy_share:.1f}% | {'YES' if r.aggressive else 'NO'} | "
                f"{'WIN' if r.dir_win_60m else 'LOSS'} | {100*r.signed_ret_60m:.3f}% | {r.onepct_reason} | {100*r.mfe_6h:.3f}% |"
            )
    md += [
        "",
        "August is true post-cutoff evidence; no rule, clock, direction, taker threshold, or TP/SL is retuned from these outcomes.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
