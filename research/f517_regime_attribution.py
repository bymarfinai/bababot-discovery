#!/usr/bin/env python3
"""F5.17 Friday15 T-Method regime-attribution forensic.

Purpose:
1) Reproduce the frozen F5.0 parent and F5.16 P15/P20 HALF_RISK_STOP results
   directly from official Binance Data Vision archives.
2) Only if reproduction passes, attribute the P15/P20 management chronology
   inversion to a compact set of causal pre-entry / prior-Friday regime states.

This script is research-only. It does not touch live BBC code.
"""
from __future__ import annotations

import io
import json
import math
import os
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

BASE = "https://data.binance.vision/data/futures/um"
SYMBOL = "BTCUSDT"
NOTIONAL = 500.0
ROUND_TRIP_FEE = 0.0015 * NOTIONAL
TP = 0.020
SL = 0.007
HALF_SL = 0.0035
HOLD_MIN = 360
START = pd.Timestamp("2023-12-02", tz="UTC")
END = pd.Timestamp("2026-07-30", tz="UTC")
SPLIT_N = 82
CACHE = Path(os.getenv("F517_CACHE", "/tmp/f517_cache"))
CACHE.mkdir(parents=True, exist_ok=True)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "bababot-discovery-f517/1.0"})


def get_zip_csv(url: str, cache_name: str) -> Optional[pd.DataFrame]:
    p = CACHE / cache_name
    data: bytes
    if p.exists():
        data = p.read_bytes()
    else:
        r = SESSION.get(url, timeout=60)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.content
        p.write_bytes(data)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise RuntimeError(f"no CSV in {url}")
            with zf.open(names[0]) as fh:
                return pd.read_csv(fh)
    except zipfile.BadZipFile as e:
        raise RuntimeError(f"bad zip: {url}") from e


def month_iter(start: pd.Timestamp, end: pd.Timestamp):
    cur = pd.Timestamp(start.year, start.month, 1, tz="UTC")
    last = pd.Timestamp(end.year, end.month, 1, tz="UTC")
    while cur <= last:
        yield cur.year, cur.month
        cur = cur + pd.offsets.MonthBegin(1)


def load_klines() -> pd.DataFrame:
    frames = []
    # Include Nov-2023 warmup for EMA / 24h regime features.
    kstart = pd.Timestamp("2023-11-01", tz="UTC")
    kend = pd.Timestamp("2026-07-31", tz="UTC")
    for y, m in month_iter(kstart, kend):
        ym = f"{y:04d}-{m:02d}"
        url = f"{BASE}/monthly/klines/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip"
        df = get_zip_csv(url, f"{SYMBOL}-5m-{ym}.zip")
        if df is None:
            raise RuntimeError(f"missing monthly kline {ym}")
        # Binance futures monthly kline archives may be headerless.
        if len(df.columns) == 12 and str(df.columns[0]).isdigit():
            # read_csv treated first data row as header; re-read headerless.
            p = CACHE / f"{SYMBOL}-5m-{ym}.zip"
            with zipfile.ZipFile(p) as zf:
                name = [n for n in zf.namelist() if n.lower().endswith('.csv')][0]
                with zf.open(name) as fh:
                    df = pd.read_csv(fh, header=None)
        if len(df.columns) < 12:
            raise RuntimeError(f"unexpected kline columns {df.columns.tolist()}")
        df = df.iloc[:, :12].copy()
        df.columns = [
            "open_time","open","high","low","close","volume","close_time",
            "quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"
        ]
        for c in ["open","high","low","close","volume","quote_volume","taker_buy_base","taker_buy_quote"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        ot = pd.to_numeric(df["open_time"], errors="coerce")
        # Futures archives use milliseconds for this historical period.
        unit = "us" if ot.dropna().median() > 1e14 else "ms"
        df["ts"] = pd.to_datetime(ot, unit=unit, utc=True)
        frames.append(df[["ts","open","high","low","close","volume","quote_volume","taker_buy_quote"]])
    out = pd.concat(frames, ignore_index=True).dropna(subset=["ts","open","high","low","close"])
    out = out.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    out["ema7"] = out["close"].ewm(span=7, adjust=False).mean()
    out["ema20"] = out["close"].ewm(span=20, adjust=False).mean()
    out["ema_spread"] = out["ema7"] / out["ema20"] - 1.0
    out["ret5"] = out["close"].pct_change()
    out["taker_imb"] = np.where(out["quote_volume"] > 0, 2.0*out["taker_buy_quote"]/out["quote_volume"] - 1.0, np.nan)
    out = out.set_index("ts", drop=False)
    return out


def parse_metrics_time(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s):
        vals = pd.to_numeric(s, errors="coerce")
        unit = "us" if vals.dropna().median() > 1e14 else "ms"
        return pd.to_datetime(vals, unit=unit, utc=True)
    return pd.to_datetime(s, utc=True, errors="coerce")


def load_metrics_for_date(d: pd.Timestamp) -> Optional[pd.DataFrame]:
    ds = d.strftime("%Y-%m-%d")
    url = f"{BASE}/daily/metrics/{SYMBOL}/{SYMBOL}-metrics-{ds}.zip"
    df = get_zip_csv(url, f"{SYMBOL}-metrics-{ds}.zip")
    if df is None:
        return None
    df.columns = [str(c).strip().lower() for c in df.columns]
    aliases = {
        "create_time": ["create_time","timestamp","time"],
        "oi": ["sum_open_interest"],
        "oi_value": ["sum_open_interest_value"],
        "top_account": ["count_toptrader_long_short_ratio"],
        "top_pos": ["sum_toptrader_long_short_ratio"],
        "global_account": ["count_long_short_ratio"],
        "taker_ls": ["sum_taker_long_short_vol_ratio"],
    }
    resolved = {}
    for key, opts in aliases.items():
        for o in opts:
            if o in df.columns:
                resolved[key] = o
                break
    needed = ["create_time","oi_value","top_account","top_pos","global_account"]
    missing = [x for x in needed if x not in resolved]
    if missing:
        raise RuntimeError(f"metrics missing {missing}; columns={df.columns.tolist()}")
    out = pd.DataFrame()
    out["ts"] = parse_metrics_time(df[resolved["create_time"]])
    for key in ["oi","oi_value","top_account","top_pos","global_account","taker_ls"]:
        if key in resolved:
            out[key] = pd.to_numeric(df[resolved[key]], errors="coerce")
    out = out.dropna(subset=["ts","top_account","top_pos","global_account"]).sort_values("ts")
    out = out.drop_duplicates("ts").set_index("ts", drop=False)
    return out


def latest_before(df: pd.DataFrame, t: pd.Timestamp) -> Optional[pd.Series]:
    x = df[df.index < t]
    if x.empty:
        return None
    return x.iloc[-1]


def latest_at_or_before(df: pd.DataFrame, t: pd.Timestamp) -> Optional[pd.Series]:
    x = df[df.index <= t]
    if x.empty:
        return None
    return x.iloc[-1]


def pctchg(cur: float, prev: float) -> float:
    if not np.isfinite(cur) or not np.isfinite(prev) or prev == 0:
        return np.nan
    return cur / prev - 1.0


def metric_state(mdf: pd.DataFrame, t: pd.Timestamp) -> Optional[dict]:
    cur = latest_before(mdf, t)
    if cur is None:
        return None
    prev15 = latest_at_or_before(mdf, cur.ts - pd.Timedelta(minutes=15))
    prev60 = latest_at_or_before(mdf, cur.ts - pd.Timedelta(minutes=60))
    if prev15 is None:
        return None
    top_vs_global = cur.top_pos / cur.global_account - 1.0
    top_vs_account = cur.top_pos / cur.top_account - 1.0
    st = {
        "metric_ts": cur.ts,
        "top_pos": float(cur.top_pos),
        "top_account": float(cur.top_account),
        "global_account": float(cur.global_account),
        "top_vs_global": float(top_vs_global),
        "top_vs_account": float(top_vs_account),
        "top_account_chg15": pctchg(float(cur.top_account), float(prev15.top_account)),
        "global_account_chg15": pctchg(float(cur.global_account), float(prev15.global_account)),
        "oi_chg60": np.nan,
    }
    if prev60 is not None and "oi_value" in cur.index and "oi_value" in prev60.index:
        st["oi_chg60"] = pctchg(float(cur.oi_value), float(prev60.oi_value))
    return st


def ema_state(k: pd.DataFrame, t: pd.Timestamp) -> Optional[dict]:
    # At decision open t, the 5m bar with open t-5m has just completed and is causal.
    cur_t = t - pd.Timedelta(minutes=5)
    prev_t = cur_t - pd.Timedelta(minutes=15)
    if cur_t not in k.index:
        return None
    cur = k.loc[cur_t]
    prev = latest_at_or_before(k, prev_t)
    if prev is None:
        return None
    return {
        "ema_spread": float(cur.ema_spread),
        "ema_spread_chg15": float(cur.ema_spread - prev.ema_spread),
        "ema7": float(cur.ema7),
        "ema20": float(cur.ema20),
    }


def warning_state(k: pd.DataFrame, mdf: pd.DataFrame, t: pd.Timestamp) -> Optional[dict]:
    ms = metric_state(mdf, t)
    es = ema_state(k, t)
    if ms is None or es is None:
        return None
    warn = (
        ms["top_vs_global"] <= 0 and
        ms["top_account_chg15"] < 0 and
        ms["global_account_chg15"] < 0 and
        es["ema_spread_chg15"] < 0
    )
    return {**ms, **es, "warning": bool(warn)}


@dataclass
class Trade:
    date: str
    entry_t: pd.Timestamp
    entry: float
    exit_t: pd.Timestamp
    exit_px: float
    reason: str
    gross_ret: float
    pnl: float
    mfe: float
    mae: float


def simulate_parent(k: pd.DataFrame, entry_t: pd.Timestamp) -> Trade:
    if entry_t not in k.index:
        raise RuntimeError(f"missing entry bar {entry_t}")
    entry = float(k.loc[entry_t, "open"])
    end_t = entry_t + pd.Timedelta(minutes=HOLD_MIN)
    bars = k[(k.index >= entry_t) & (k.index < end_t)]
    if len(bars) != HOLD_MIN // 5:
        raise RuntimeError(f"incomplete hold bars {entry_t}: {len(bars)}")
    tp_px = entry * (1+TP)
    sl_px = entry * (1-SL)
    mfe = 0.0
    mae = 0.0
    for _, b in bars.iterrows():
        mfe = max(mfe, float(b.high)/entry - 1.0)
        mae = max(mae, 1.0 - float(b.low)/entry)
        hit_sl = float(b.low) <= sl_px
        hit_tp = float(b.high) >= tp_px
        # Adverse-first for same 5m ambiguity.
        if hit_sl:
            ret = -SL
            return Trade(str(entry_t.date()), entry_t, entry, b.ts, sl_px, "SL", ret, NOTIONAL*ret-ROUND_TRIP_FEE, mfe, mae)
        if hit_tp:
            ret = TP
            return Trade(str(entry_t.date()), entry_t, entry, b.ts, tp_px, "TP", ret, NOTIONAL*ret-ROUND_TRIP_FEE, mfe, mae)
    last = bars.iloc[-1]
    exit_px = float(last.close)
    ret = exit_px/entry - 1.0
    return Trade(str(entry_t.date()), entry_t, entry, last.ts + pd.Timedelta(minutes=5), exit_px, "TIMEOUT", ret, NOTIONAL*ret-ROUND_TRIP_FEE, mfe, mae)


def simulate_half_risk(k: pd.DataFrame, parent: Trade, decision_t: pd.Timestamp) -> Trade:
    # If parent already exited no management action can occur.
    if parent.exit_t <= decision_t:
        return parent
    entry = parent.entry
    if decision_t not in k.index:
        raise RuntimeError(f"missing decision bar {decision_t}")
    decision_open = float(k.loc[decision_t, "open"])
    stop_px = entry * (1-HALF_SL)
    tp_px = entry * (1+TP)
    if decision_open <= stop_px:
        ret = decision_open/entry - 1.0
        return Trade(parent.date, parent.entry_t, entry, decision_t, decision_open, "HALF_RISK_OPEN_EXIT", ret, NOTIONAL*ret-ROUND_TRIP_FEE, parent.mfe, parent.mae)
    end_t = parent.entry_t + pd.Timedelta(minutes=HOLD_MIN)
    bars = k[(k.index >= decision_t) & (k.index < end_t)]
    for _, b in bars.iterrows():
        hit_stop = float(b.low) <= stop_px
        hit_tp = float(b.high) >= tp_px
        if hit_stop:
            ret = -HALF_SL
            return Trade(parent.date, parent.entry_t, entry, b.ts, stop_px, "HALF_RISK_SL", ret, NOTIONAL*ret-ROUND_TRIP_FEE, parent.mfe, parent.mae)
        if hit_tp:
            ret = TP
            return Trade(parent.date, parent.entry_t, entry, b.ts, tp_px, "TP", ret, NOTIONAL*ret-ROUND_TRIP_FEE, parent.mfe, parent.mae)
    last = bars.iloc[-1]
    exit_px = float(last.close)
    ret = exit_px/entry - 1.0
    return Trade(parent.date, parent.entry_t, entry, last.ts + pd.Timedelta(minutes=5), exit_px, "TIMEOUT", ret, NOTIONAL*ret-ROUND_TRIP_FEE, parent.mfe, parent.mae)


def path_alive(parent: Trade, t: pd.Timestamp) -> bool:
    return parent.exit_t > t


def first_warning_and_persistence(k: pd.DataFrame, mdf: pd.DataFrame, parent: Trade) -> dict:
    first = None
    states = {}
    for mins in range(15, 181, 5):
        t = parent.entry_t + pd.Timedelta(minutes=mins)
        if not path_alive(parent, t):
            break
        st = warning_state(k, mdf, t)
        states[t] = st
        if st is not None and st["warning"] and first is None:
            first = t
    out = {"first_warning": first, "p15_t": None, "p20_t": None, "first_state": None}
    if first is None:
        return out
    out["first_state"] = states.get(first)
    for p in (15,20):
        target = first + pd.Timedelta(minutes=p)
        ok = True
        for dt in range(0, p+1, 5):
            t = first + pd.Timedelta(minutes=dt)
            st = states.get(t)
            if st is None or not st["warning"]:
                ok = False
                break
        if ok and path_alive(parent, target):
            out[f"p{p}_t"] = target
    return out


def preentry_features(k: pd.DataFrame, mdf: Optional[pd.DataFrame], entry_t: pd.Timestamp) -> dict:
    # Kline features strictly before entry open.
    prior = k[(k.index < entry_t) & (k.index >= entry_t-pd.Timedelta(hours=24))]
    last60 = k[(k.index < entry_t) & (k.index >= entry_t-pd.Timedelta(minutes=60))]
    feat = {}
    if len(prior) >= 250 and len(last60) == 12:
        feat["rv24"] = float(prior["ret5"].std())
        p0 = float(last60.iloc[0].open)
        p1 = float(last60.iloc[-1].close)
        feat["ret60"] = p1/p0 - 1.0
        qv = float(last60.quote_volume.sum())
        tb = float(last60.taker_buy_quote.sum())
        feat["taker_imb60"] = (2*tb/qv - 1.0) if qv > 0 else np.nan
        # Natural rolling 60m baseline over the prior 24h.
        tmp = prior.copy()
        vol60 = tmp.quote_volume.rolling(12).sum()
        high60 = tmp.high.rolling(12).max()
        low60 = tmp.low.rolling(12).min()
        range60 = high60/low60 - 1.0
        cur_vol = float(last60.quote_volume.sum())
        cur_range = float(last60.high.max()/last60.low.min()-1.0)
        feat["volume_ratio60"] = cur_vol/float(vol60.dropna().median()) if len(vol60.dropna()) else np.nan
        feat["range_ratio60"] = cur_range/float(range60.dropna().median()) if len(range60.dropna()) else np.nan
        feat["seller_led"] = bool(feat["ret60"] < 0 and feat["taker_imb60"] < 0)
        feat["expansion"] = bool(feat["volume_ratio60"] > 1 and feat["range_ratio60"] > 1)
        feat["stress_core"] = bool(feat["seller_led"] and feat["expansion"])
    es = ema_state(k, entry_t)
    if es:
        feat["entry_ema_spread"] = es["ema_spread"]
        feat["entry_ema_spread_chg15"] = es["ema_spread_chg15"]
    if mdf is not None:
        ms = metric_state(mdf, entry_t)
        if ms:
            feat.update({f"entry_{kk}": vv for kk,vv in ms.items() if kk != "metric_ts"})
            feat["crowded_both"] = bool(ms["top_vs_global"] > 0 and ms["top_vs_account"] > 0)
            feat["stress_unwind"] = bool(feat.get("stress_core", False) and np.isfinite(ms.get("oi_chg60",np.nan)) and ms["oi_chg60"] <= 0)
    return feat


def mdd(pnls: List[float]) -> float:
    eq = np.cumsum(np.array(pnls, dtype=float))
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return float(dd.max()) if len(dd) else 0.0


def metrics_summary(trades: List[Trade]) -> dict:
    pnls = [t.pnl for t in trades]
    wins = sum(x > 0 for x in pnls)
    gp = sum(x for x in pnls if x > 0)
    gl = -sum(x for x in pnls if x < 0)
    return {
        "n": len(trades),
        "wins": wins,
        "losses": len(trades)-wins,
        "wr": wins/len(trades)*100 if trades else np.nan,
        "pnl": float(sum(pnls)),
        "pf": gp/gl if gl > 0 else math.inf,
        "mdd": mdd(pnls),
        "tp": sum(t.reason=="TP" for t in trades),
        "sl": sum(t.reason=="SL" for t in trades),
        "timeout": sum(t.reason=="TIMEOUT" for t in trades),
    }


def close(a,b,tol):
    return abs(a-b) <= tol


def assert_parent(parent: List[Trade]) -> None:
    s = metrics_summary(parent)
    expected = {"n":138,"wins":66,"losses":72,"tp":19,"sl":51,"timeout":68}
    for k,v in expected.items():
        if s[k] != v:
            raise AssertionError(f"PARENT MISMATCH {k}: got {s[k]} expected {v}; summary={s}")
    if not close(s["pnl"],64.630,0.05):
        raise AssertionError(f"PARENT PNL MISMATCH got {s['pnl']:.6f} expected 64.630")
    d = metrics_summary(parent[:SPLIT_N])
    v = metrics_summary(parent[SPLIT_N:])
    if not close(d["pnl"],99.194,0.05) or not close(v["pnl"],-34.563,0.05):
        raise AssertionError(f"SPLIT MISMATCH discovery={d['pnl']:.6f} validation={v['pnl']:.6f}")


def cohort_table(rows: pd.DataFrame, state_col: str) -> dict:
    out = {}
    for period, sub0 in [("discovery",rows.iloc[:SPLIT_N]),("validation",rows.iloc[SPLIT_N:]),("full",rows)]:
        sub = sub0[sub0["p15_changed"]]
        period_out = {}
        for val in [False, True]:
            x = sub[sub[state_col].fillna(False).astype(bool)==val]
            period_out[str(val)] = {
                "n": int(len(x)),
                "delta": float(x.p15_delta.sum()) if len(x) else 0.0,
                "improved": int((x.p15_delta>1e-9).sum()),
                "damaged": int((x.p15_delta<-1e-9).sum()),
            }
        out[period] = period_out
    return out


def main():
    print("F5.17 boot: loading official Binance Data Vision klines...", flush=True)
    k = load_klines()
    friday_dates = [d for d in pd.date_range(START, END, inclusive="left", freq="D") if d.weekday()==4]
    if len(friday_dates) != 138:
        raise AssertionError(len(friday_dates))

    parents=[]
    metrics_by_date={}
    rows=[]
    print("Simulating 138 frozen Friday15 parents and loading Friday metrics...", flush=True)
    for i,d in enumerate(friday_dates):
        entry_t = pd.Timestamp(d.date(), tz="UTC") + pd.Timedelta(hours=8)  # 15:00 WIB
        p = simulate_parent(k, entry_t)
        parents.append(p)
        mdf = load_metrics_for_date(d)
        metrics_by_date[str(d.date())] = mdf
        feat = preentry_features(k, mdf, entry_t)
        row={"i":i,"date":str(d.date()),"period":"discovery" if i<SPLIT_N else "validation",
             "entry_t":entry_t,"parent_pnl":p.pnl,"parent_reason":p.reason, **feat}
        rows.append(row)
        if (i+1)%25==0:
            print(f"  processed {i+1}/138", flush=True)

    assert_parent(parents)
    print("REPRO PASS: F5.0 parent matches frozen checkpoint.", flush=True)

    df = pd.DataFrame(rows)
    # Prior-Friday response health, known strictly before current entry.
    df["fast8"] = df.parent_pnl.shift(1).rolling(8,min_periods=8).mean()
    df["slow13"] = df.parent_pnl.shift(1).rolling(13,min_periods=13).mean()
    df["health_both_negative"] = (df.fast8 < 0) & (df.slow13 < 0)
    df["health_fast_negative"] = df.fast8 < 0
    df["health_slow_negative"] = df.slow13 < 0
    # Low-vol uses only prior 26 Fridays, natural trailing-median state from A6.41 family.
    rv_med = df.rv24.shift(1).rolling(26,min_periods=13).median()
    df["low_rv24"] = df.rv24 < rv_med

    usable=0
    for i,(row,p) in enumerate(zip(rows,parents)):
        mdf=metrics_by_date[row["date"]]
        fw={"first_warning":None,"p15_t":None,"p20_t":None,"first_state":None}
        if mdf is not None:
            usable += 1
            fw=first_warning_and_persistence(k,mdf,p)
        for pp in (15,20):
            t=fw[f"p{pp}_t"]
            managed=p if t is None else simulate_half_risk(k,p,t)
            df.loc[i,f"p{pp}_state"] = bool(t is not None)
            df.loc[i,f"p{pp}_decision_t"] = t
            df.loc[i,f"p{pp}_managed_pnl"] = managed.pnl
            df.loc[i,f"p{pp}_delta"] = managed.pnl-p.pnl
            df.loc[i,f"p{pp}_changed"] = abs(managed.pnl-p.pnl) > 1e-9
        if fw["first_state"]:
            for kk,vv in fw["first_state"].items():
                if kk not in ("warning","metric_ts"):
                    df.loc[i,f"warn_{kk}"]=vv

    print(f"usable metrics Fridays={usable}", flush=True)
    # Reproduction gates for F5.16.
    def stats(pp, lo, hi):
        x=df.iloc[lo:hi]
        return {
            "states":int(x[f"p{pp}_state"].fillna(False).sum()),
            "changed":int(x[f"p{pp}_changed"].fillna(False).sum()),
            "delta":float(x[f"p{pp}_delta"].sum()),
            "improved":int((x[f"p{pp}_delta"]>1e-9).sum()),
            "damaged":int((x[f"p{pp}_delta"]<-1e-9).sum()),
        }
    repro={
        "p15_discovery":stats(15,0,SPLIT_N),
        "p15_validation":stats(15,SPLIT_N,len(df)),
        "p15_full":stats(15,0,len(df)),
        "p20_discovery":stats(20,0,SPLIT_N),
        "p20_validation":stats(20,SPLIT_N,len(df)),
        "p20_full":stats(20,0,len(df)),
    }
    print("F5.16 reproduction:")
    print(json.dumps(repro,indent=2,default=str))

    exp={
        "p15_discovery":{"states":9,"changed":6,"delta":-3.453},
        "p15_validation":{"states":11,"changed":8,"delta":7.664},
        "p15_full":{"states":20,"changed":14,"delta":4.213},
        "p20_discovery":{"states":6,"changed":4,"delta":-0.516},
        "p20_validation":{"states":9,"changed":7,"delta":4.574},
        "p20_full":{"states":15,"changed":11,"delta":4.060},
    }
    mismatches=[]
    for key,e in exp.items():
        g=repro[key]
        for c in ("states","changed"):
            if g[c]!=e[c]: mismatches.append(f"{key}.{c}: {g[c]} != {e[c]}")
        if abs(g["delta"]-e["delta"])>0.08:
            mismatches.append(f"{key}.delta: {g['delta']:.3f} != {e['delta']:.3f}")
    if mismatches:
        print("REPRO FAIL: F5.16 does not match checkpoint; attribution aborted.")
        print("\n".join(mismatches))
        # Helpful sample for debugging.
        print(df[df.p15_state.fillna(False)][["date","period","parent_reason","parent_pnl","p15_decision_t","p15_delta"]].to_string(index=False))
        sys.exit(2)

    print("REPRO PASS: F5.16 P15/P20 half-risk matches frozen checkpoint.", flush=True)

    # F5.17 causal regime-attribution forensic. No new thresholds are swept.
    # States are all pre-existing natural states from prior Friday research families.
    state_cols=[
        "health_fast_negative","health_slow_negative","health_both_negative",
        "low_rv24","stress_core","stress_unwind","crowded_both",
    ]
    atlas={c:cohort_table(df,c) for c in state_cols if c in df.columns}

    # Zero-crossing states at pre-entry hidden positioning, also pre-existing families.
    df["entry_top_vs_global_nonpos"] = df.get("entry_top_vs_global",pd.Series(index=df.index,dtype=float)) <= 0
    df["entry_top_vs_account_nonpos"] = df.get("entry_top_vs_account",pd.Series(index=df.index,dtype=float)) <= 0
    df["entry_oi_nonincreasing"] = df.get("entry_oi_chg60",pd.Series(index=df.index,dtype=float)) <= 0
    for c in ["entry_top_vs_global_nonpos","entry_top_vs_account_nonpos","entry_oi_nonincreasing"]:
        atlas[c]=cohort_table(df,c)

    # Action cohort rows, enough to inspect chronology without calendar-era gating.
    cohort_cols=["date","period","parent_reason","parent_pnl","p15_delta","p20_delta",
                 "fast8","slow13","rv24","low_rv24","stress_core","stress_unwind","crowded_both",
                 "entry_top_vs_global","entry_top_vs_account","entry_oi_chg60"]
    cohort=df[df.p15_changed.fillna(False)][[c for c in cohort_cols if c in df.columns]].copy()

    print("\nF5.17 PREDECLARED REGIME ATLAS (P15 changed outcomes):")
    print(json.dumps(atlas,indent=2,default=str))
    print("\nP15 changed cohort:")
    print(cohort.to_string(index=False))

    # Discovery-only candidate ranking: require >=2 actions on each side and positive
    # delta for TRUE state relative to FALSE. Validation remains report-only.
    ranks=[]
    for c,tab in atlas.items():
        d=tab["discovery"]
        t=d["True"]; f=d["False"]
        if t["n"]>=2 and f["n"]>=2:
            avg_t=t["delta"]/t["n"]
            avg_f=f["delta"]/f["n"]
            ranks.append({"state":c,"disc_true_n":t["n"],"disc_false_n":f["n"],
                          "disc_true_avg_delta":avg_t,"disc_false_avg_delta":avg_f,
                          "disc_separation":avg_t-avg_f,
                          "validation":tab["validation"],"full":tab["full"]})
    ranks=sorted(ranks,key=lambda x:x["disc_separation"],reverse=True)
    print("\nF5.17 discovery-ranked regime separation (forensics only):")
    print(json.dumps(ranks,indent=2,default=str))

    result={
        "status":"F5.17_FORENSIC_COMPLETE",
        "parent":metrics_summary(parents),
        "repro":repro,
        "usable_metrics":usable,
        "atlas":atlas,
        "discovery_rank":ranks,
    }
    out=Path("f517_result.json")
    out.write_text(json.dumps(result,indent=2,default=str))
    df.to_csv("f517_rows.csv",index=False)
    print("\nF5.17 complete; wrote f517_result.json and f517_rows.csv", flush=True)

if __name__ == "__main__":
    main()
