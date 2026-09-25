#!/usr/bin/env python3
from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "SOL_DONOR_TRANSPLANT_STAGE3_Result.md"
OUT_SUM = ROOT / "SOL_DONOR_TRANSPLANT_STAGE3_Summary.csv"
OUT_TRADES = ROOT / "SOL_DONOR_TRANSPLANT_STAGE3_Trades.csv"
OUT_STATUS = ROOT / "SOL_DONOR_TRANSPLANT_STAGE3_Status.txt"

SYMBOL = "SOLUSDT"
BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
FETCH_START = pd.Timestamp("2022-12-01T00:00:00Z")
END = pd.Timestamp("2026-09-01T00:00:00Z")
TEST_START = pd.Timestamp("2023-01-01T00:00:00Z")
TP = 0.01
SL = 0.01
FEE = 0.0015

PARTS = {
    "DEV_2023_24": (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")),
    "HOLDOUT_2025": (pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC")),
    "FINAL_2026": (pd.Timestamp("2026-01-01", tz="UTC"), END),
}
DETECTORS = ("E0V1E", "CCI_BB", "OVERLAP", "DNA_V1")


def month_urls():
    cur = pd.Timestamp(FETCH_START.year, FETCH_START.month, 1, tz="UTC")
    end = pd.Timestamp(END.year, END.month, 1, tz="UTC")
    out = []
    while cur < end:
        ym = cur.strftime("%Y-%m")
        out.append(f"{BASE}/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        cur += pd.offsets.MonthBegin(1)
    return out


def fetch_one(url):
    r = requests.get(url, timeout=90, headers={"User-Agent": "bababot-stage3/1.0"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh, header=None, usecols=[0,1,2,3,4,5],
                names=["ts","open","high","low","close","volume"]
            )


def load5():
    frames = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(fetch_one, u) for u in month_urls()]
        for fut in as_completed(futs):
            x = fut.result()
            if x is not None and len(x):
                frames.append(x)
    if not frames:
        raise RuntimeError("No SOLUSDT 5m data")
    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x.ts, errors="coerce")
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    x["ts"] = pd.to_datetime(t, unit="ms", utc=True, errors="coerce")
    for c in ["open","high","low","close","volume"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna().drop_duplicates("ts").sort_values("ts")
    x = x[(x.ts >= FETCH_START) & (x.ts < END)].set_index("ts")
    expected = int((x.index[-1] - x.index[0]) / pd.Timedelta(minutes=5)) + 1
    coverage = len(x) / expected
    if coverage < 0.995:
        raise RuntimeError(f"5m coverage too low: {coverage:.6f}")
    return x, coverage


def rsi(s, n):
    d = s.diff()
    up = d.clip(lower=0.0)
    dn = (-d.clip(upper=0.0))
    au = up.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rs = au / ad.replace(0, np.nan)
    z = 100 - 100 / (1 + rs)
    return z.fillna(100.0)


def cti(s, n=20):
    arr = np.arange(n, dtype=float)
    def f(v):
        if np.std(v) == 0:
            return 0.0
        return float(np.corrcoef(v, arr)[0,1])
    return s.rolling(n).apply(f, raw=True)


def cci(h, l, c, n=14):
    tp = (h+l+c)/3.0
    ma = tp.rolling(n).mean()
    md = tp.rolling(n).apply(lambda v: np.mean(np.abs(v - np.mean(v))), raw=True)
    return (tp-ma) / (0.015 * md.replace(0, np.nan))


def indicators5(x):
    z = x.copy()
    z["rsi4"] = rsi(z.close, 4)
    z["rsi14"] = rsi(z.close, 14)
    z["rsi20"] = rsi(z.close, 20)
    z["ema8"] = z.close.ewm(span=8, adjust=False, min_periods=8).mean()
    z["ema16"] = z.close.ewm(span=16, adjust=False, min_periods=16).mean()
    ema50 = z.close.ewm(span=50, adjust=False, min_periods=50).mean()
    ema200 = z.close.ewm(span=200, adjust=False, min_periods=200).mean()
    z["ewo"] = (ema50-ema200)/z.low*100.0
    z["sma15"] = z.close.rolling(15).mean()
    z["cti20"] = cti(z.close, 20)
    z["cci14"] = cci(z.high,z.low,z.close,14)
    typ = (z.high+z.low+z.close)/3.0
    mid = typ.rolling(20).mean()
    sd = typ.rolling(20).std(ddof=0)
    z["bb_low"] = mid - 2.0*sd

    ewo = (
        (z.rsi4 < 42) &
        (z.close < z.ema8 * 0.956) &
        (z.ewo > -5.836) &
        (z.close < z.ema16 * 1.043) &
        (z.rsi14 < 35)
    )
    buy1 = (
        (z.rsi20 < z.rsi20.shift(1)) &
        (z.rsi4 < 40) &
        (z.rsi14 > 29) &
        (z.close < z.sma15 * 0.975) &
        (z.cti20 < -0.55)
    )
    z["sig_e0v1e"] = (ewo | buy1).fillna(False)
    z["sig_cci"] = ((z.cci14 <= -134) & (z.close < z.bb_low)).fillna(False)
    return z


def hourly_context(x):
    h = x.resample("1h", label="left", closed="left").agg(
        open=("open","first"), high=("high","max"), low=("low","min"),
        close=("close","last"), volume=("volume","sum")
    ).dropna()
    h["green"] = h.close > h.open

    h4 = x.resample("4h", label="left", closed="left").agg(
        open=("open","first"), high=("high","max"), low=("low","min"),
        close=("close","last")
    ).dropna()
    h4["ema50"] = h4.close.ewm(span=50, adjust=False, min_periods=50).mean()
    h4["regime_ok"] = h4.close > h4.ema50

    # value known at each 1h signal close: use 4h candle whose END <= signal-hour END
    rows = []
    for t in h.index:
        signal_end = t + pd.Timedelta(hours=1)
        eligible = h4.index[(h4.index + pd.Timedelta(hours=4)) <= signal_end]
        rows.append(bool(h4.loc[eligible[-1],"regime_ok"]) if len(eligible) else False)
    h["regime_ok"] = rows
    return h


def build_hour_signals(z5, h):
    g = z5[z5.index >= TEST_START].copy()
    byhour = pd.DataFrame(index=h.index)
    byhour["e"] = g.sig_e0v1e.resample("1h").max().reindex(h.index, fill_value=False).astype(bool)
    byhour["c"] = g.sig_cci.resample("1h").max().reindex(h.index, fill_value=False).astype(bool)
    byhour["E0V1E"] = byhour.e
    byhour["CCI_BB"] = byhour.c
    byhour["OVERLAP"] = byhour.e & byhour.c
    byhour["DNA_V1"] = (byhour.e | byhour.c) & h.green & h.regime_ok
    return byhour


def partition(ts):
    for name,(a,b) in PARTS.items():
        if a <= ts < b:
            return name
    return None


def run_detector(name, hs, x5):
    rows = []
    active_until = None
    idx = x5.index
    highs = x5.high.to_numpy(float)
    lows = x5.low.to_numpy(float)
    opens = x5.open.to_numpy(float)
    for signal_hour in hs.index[hs[name].fillna(False)]:
        entry_ts = signal_hour + pd.Timedelta(hours=1)
        if entry_ts < TEST_START or entry_ts >= END:
            continue
        if active_until is not None and entry_ts <= active_until:
            continue
        p = int(idx.searchsorted(entry_ts, side="left"))
        if p >= len(idx) or idx[p] != entry_ts:
            continue
        entry = float(opens[p])
        tp_px = entry*(1+TP)
        sl_px = entry*(1-SL)
        exit_ts = None
        outcome = None
        exit_px = np.nan
        for j in range(p, len(idx)):
            hit_tp = float(highs[j]) >= tp_px
            hit_sl = float(lows[j]) <= sl_px
            if hit_tp and hit_sl:
                outcome = "LOSS"
                exit_px = sl_px
                exit_ts = idx[j]
                break
            if hit_sl:
                outcome = "LOSS"
                exit_px = sl_px
                exit_ts = idx[j]
                break
            if hit_tp:
                outcome = "WIN"
                exit_px = tp_px
                exit_ts = idx[j]
                break
        if outcome is None:
            continue
        active_until = exit_ts
        gross = TP if outcome=="WIN" else -SL
        net = gross - FEE
        rows.append({
            "detector":name, "partition":partition(entry_ts),
            "signal_hour":signal_hour, "entry_ts":entry_ts, "exit_ts":exit_ts,
            "entry":entry, "exit":exit_px, "outcome":outcome,
            "gross_return":gross, "net_return_fee015":net,
            "hold_hours":(exit_ts-entry_ts).total_seconds()/3600.0,
        })
    return pd.DataFrame(rows)


def summarize(trades):
    rows = []
    for det in DETECTORS:
        for part,(a,b) in PARTS.items():
            q = trades[(trades.detector==det)&(trades.partition==part)].copy()
            days = (b-a).total_seconds()/86400.0
            if part=="FINAL_2026":
                days = max(1.0, (END-a).total_seconds()/86400.0)
            n = len(q)
            wins = int((q.outcome=="WIN").sum()) if n else 0
            losses = n-wins
            wr = wins/n if n else np.nan
            net_sum = q.net_return_fee015.sum() if n else 0.0
            rows.append({
                "detector":det,"partition":part,"trades":n,"wins":wins,"losses":losses,
                "wr":wr,"trades_per_day":n/days,"net_return_units":net_sum,
                "avg_net_per_trade":q.net_return_fee015.mean() if n else np.nan,
                "median_hold_h":q.hold_hours.median() if n else np.nan,
                "p90_hold_h":q.hold_hours.quantile(.9) if n else np.nan,
            })
    return pd.DataFrame(rows)


def pct(v):
    return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def num(v,d=3):
    return "-" if pd.isna(v) else f"{float(v):.{d}f}"


def main():
    x, coverage = load5()
    z = indicators5(x)
    h = hourly_context(x)
    hs = build_hour_signals(z,h)

    tf = []
    for d in DETECTORS:
        q = run_detector(d,hs,x)
        if len(q):
            tf.append(q)
    trades = pd.concat(tf, ignore_index=True) if tf else pd.DataFrame()
    trades.to_csv(OUT_TRADES,index=False)
    s = summarize(trades)
    s.to_csv(OUT_SUM,index=False)

    lines = [
        "# SOL Donor Transplant — Stage 3 Result","",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.","",
        "Frozen execution: donor signal on completed 5m bars -> hourly latch -> **next 1H open** entry; one active LONG; TP +1%; SL -1%; same-5m double-touch = SL first; fee assumption 0.15%.","",
        "## Results","",
        "| Detector | Partition | Trades | WR | Trades/day | Avg net/trade | Median hold h | P90 hold h |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _,r in s.iterrows():
        lines.append(
            f"| {r.detector} | {r.partition} | {int(r.trades)} | {pct(r.wr)} | "
            f"{num(r.trades_per_day,3)} | {pct(r.avg_net_per_trade)} | "
            f"{num(r.median_hold_h,2)} | {num(r.p90_hold_h,2)} |"
        )

    lines += ["","## Raw hourly signal density","",
              "| Detector | Signal-hours | Signals/day (2023-2026 window) |",
              "|---|---:|---:|"]
    total_days = (END-TEST_START).total_seconds()/86400.0
    for d in DETECTORS:
        n = int(hs.loc[(hs.index>=TEST_START)&(hs.index<END),d].sum())
        lines.append(f"| {d} | {n} | {n/total_days:.3f} |")

    # Simple, non-selective Stage-3 interpretation.
    lines += ["","## Stage 3 interpretation",""]
    dev = s[s.partition=="DEV_2023_24"].set_index("detector")
    hold = s[s.partition=="HOLDOUT_2025"].set_index("detector")
    final = s[s.partition=="FINAL_2026"].set_index("detector")
    for d in DETECTORS:
        if d in dev.index:
            lines.append(
                f"- **{d}:** DEV WR {pct(dev.loc[d,'wr'])}, "
                f"2025 WR {pct(hold.loc[d,'wr']) if d in hold.index else '-'}, "
                f"2026 WR {pct(final.loc[d,'wr']) if d in final.index else '-'}; "
                f"DEV frequency {dev.loc[d,'trades_per_day']:.3f}/day."
            )
    lines += ["",
        "Stage 3 does **not** tune thresholds and does not promote a final strategy. "
        "Its purpose is to test whether public-repo entry DNA survives BabaBot's fixed +1%/-1% first-hit execution.",
    ]
    OUT_MD.write_text("\n".join(lines)+"\n")
    OUT_STATUS.write_text("SOL_DONOR_TRANSPLANT_STAGE3_COMPLETE\n")


if __name__ == "__main__":
    main()
