#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

import btc_weekly_mtf_level_atlas_b11 as b11

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_WEEKLY_DEFENDED_SR_B12_Result.md"
OUT_JSON = ROOT / "BTC_WEEKLY_DEFENDED_SR_B12_Result.json"
OUT_SEL = ROOT / "BTC_WEEKLY_DEFENDED_SR_B12_Selected.csv"
OUT_ATLAS = ROOT / "BTC_WEEKLY_DEFENDED_SR_B12_Atlas.csv"
OUT_THRESH = ROOT / "BTC_WEEKLY_DEFENDED_SR_B12_Thresholds.csv"
OUT_ZERO = ROOT / "BTC_WEEKLY_DEFENDED_SR_B12_ZeroWeeks.csv"

IMPL = "B12_V1"
SOURCE_TFS = ["H1", "H4", "D1", "W1"]
TF_HOURS = {"H1": 1, "H4": 4, "D1": 24, "W1": 168}
MAX_AGE_HOURS = {"H1": 168, "H4": 336, "D1": 720, "W1": 2016}
ORIGIN_LOOKBACK = 6
MIN_DISP_ATR = 1.50
CONFIRM_BARS = 3
MIN_CONFIRM_BODY_ATR = 0.25
SCAN_CUTOFF_DAYS = 5
SCAN_CUTOFF_HOUR = 12
THRESH_Q = [0.00, 0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95]

CAT_FEATURES = ["source_tf", "zone_kind", "side"]
NUM_FEATURES = [
    "source_displacement_atr",
    "bos_extension_atr",
    "zone_width_atr",
    "age_hours",
    "touch_to_confirm_bars",
    "penetration_zone_x",
    "distal_sweep",
    "confirm_body_atr",
    "micro_bos_extension_atr",
]


def source_atr(src: pd.DataFrame) -> pd.Series:
    pc = src.close.shift(1)
    tr = pd.concat([src.high-src.low, (src.high-pc).abs(), (src.low-pc).abs()], axis=1).max(axis=1)
    return tr.rolling(14, min_periods=14).mean()


def confirmed_swing_state(src: pd.DataFrame, kind: str):
    a = src["high" if kind == "HIGH" else "low"].to_numpy(float)
    vals = np.full(len(src), np.nan, dtype=float)
    piv = np.full(len(src), -1, dtype=int)
    events = {}
    for j in range(2, len(src)-2):
        if kind == "HIGH":
            ok = a[j] > np.max(a[j-2:j]) and a[j] >= np.max(a[j+1:j+3])
        else:
            ok = a[j] < np.min(a[j-2:j]) and a[j] <= np.min(a[j+1:j+3])
        # Pivot is known at the START of j+3 after both right bars complete.
        if ok and j+3 < len(src):
            events[j+3] = (float(a[j]), int(j))
    lastv = np.nan
    lastp = -1
    for i in range(len(src)):
        if i in events:
            lastv, lastp = events[i]
        vals[i] = lastv
        piv[i] = lastp
    return vals, piv


def generate_origin_zones(src: pd.DataFrame, tf: str):
    atr = source_atr(src).to_numpy(float)
    o = src.open.to_numpy(float); h = src.high.to_numpy(float)
    l = src.low.to_numpy(float); c = src.close.to_numpy(float)
    shi, ship = confirmed_swing_state(src, "HIGH")
    slo, slop = confirmed_swing_state(src, "LOW")
    dur = pd.Timedelta(hours=TF_HOURS[tf])
    rows = []
    seen = set()

    for k in range(max(20, ORIGIN_LOOKBACK), len(src)):
        if not np.isfinite(atr[k]) or atr[k] <= 0:
            continue

        # Demand: completed bullish BOS of an already-known confirmed swing high.
        if np.isfinite(shi[k]) and c[k] > shi[k]:
            candidates = [p for p in range(max(0, k-ORIGIN_LOOKBACK), k) if c[p] < o[p]]
            if candidates:
                p = candidates[-1]
                key = ("DEMAND", p)
                prox = max(o[p], c[p]); distal = l[p]
                disp = (c[k] - prox) / atr[k]
                if key not in seen and disp >= MIN_DISP_ATR and prox > distal:
                    aorg = atr[p] if np.isfinite(atr[p]) and atr[p] > 0 else atr[k]
                    rows.append({
                        "source_tf": tf, "zone_kind": "ORIGIN", "zone_side": "DEMAND",
                        "side": "LONG", "origin_i": p, "bos_i": k,
                        "origin_ts": src.index[p], "bos_ts": src.index[k],
                        "create_ts": src.index[k] + dur,
                        "zlo": float(distal), "zhi": float(prox),
                        "source_displacement_atr": float(disp),
                        "bos_extension_atr": float((c[k]-shi[k]) / atr[k]),
                        "zone_width_atr": float((prox-distal) / aorg),
                        "structure_pivot_i": int(ship[k]),
                    })
                    seen.add(key)

        # Supply: completed bearish BOS of already-known confirmed swing low.
        if np.isfinite(slo[k]) and c[k] < slo[k]:
            candidates = [p for p in range(max(0, k-ORIGIN_LOOKBACK), k) if c[p] > o[p]]
            if candidates:
                p = candidates[-1]
                key = ("SUPPLY", p)
                prox = min(o[p], c[p]); distal = h[p]
                disp = (prox - c[k]) / atr[k]
                if key not in seen and disp >= MIN_DISP_ATR and distal > prox:
                    aorg = atr[p] if np.isfinite(atr[p]) and atr[p] > 0 else atr[k]
                    rows.append({
                        "source_tf": tf, "zone_kind": "ORIGIN", "zone_side": "SUPPLY",
                        "side": "SHORT", "origin_i": p, "bos_i": k,
                        "origin_ts": src.index[p], "bos_ts": src.index[k],
                        "create_ts": src.index[k] + dur,
                        "zlo": float(prox), "zhi": float(distal),
                        "source_displacement_atr": float(disp),
                        "bos_extension_atr": float((slo[k]-c[k]) / atr[k]),
                        "zone_width_atr": float((distal-prox) / aorg),
                        "structure_pivot_i": int(slop[k]),
                    })
                    seen.add(key)
    return rows


def add_flip_zones(origins, src: pd.DataFrame, tf: str):
    c = src.close.to_numpy(float)
    dur_h = TF_HOURS[tf]
    dur = pd.Timedelta(hours=dur_h)
    max_bars = max(2, int(MAX_AGE_HOURS[tf] // dur_h))
    out = []
    for z in origins:
        k = int(z["bos_i"])
        stop = min(len(src)-1, k + max_bars)
        r = k + 1
        while r < stop:
            if z["zone_side"] == "DEMAND":
                accepted = c[r] < z["zlo"] and c[r+1] < z["zlo"]
                new_side = "SUPPLY"; side = "SHORT"
            else:
                accepted = c[r] > z["zhi"] and c[r+1] > z["zhi"]
                new_side = "DEMAND"; side = "LONG"
            if accepted:
                q = dict(z)
                q.update({
                    "zone_kind": "FLIP", "zone_side": new_side, "side": side,
                    "flip_accept_i": r+1, "flip_accept_ts": src.index[r+1],
                    "create_ts": src.index[r+1] + dur,
                })
                out.append(q)
                break
            r += 1
    return out


def first_defense_signal(h1: pd.DataFrame, execute, z: dict):
    idx = h1.index
    o = h1.open.to_numpy(float); h = h1.high.to_numpy(float)
    l = h1.low.to_numpy(float); c = h1.close.to_numpy(float)
    atr = h1.atr14.to_numpy(float)
    start = int(idx.searchsorted(pd.Timestamp(z["create_ts"]), side="left"))
    end_ts = pd.Timestamp(z["create_ts"]) + pd.Timedelta(hours=MAX_AGE_HOURS[z["source_tf"]])
    stop = min(len(h1), int(idx.searchsorted(end_ts, side="right")))
    if start >= stop:
        return None
    zlo = float(z["zlo"]); zhi = float(z["zhi"]); width = zhi-zlo
    if width <= 0:
        return None

    touch = None
    for i in range(start, stop):
        if h[i] >= zlo and l[i] <= zhi:
            touch = i
            break
    if touch is None:
        return None

    min_low = float("inf")
    max_high = -float("inf")
    sweep = False
    for j in range(touch, min(stop, touch + CONFIRM_BARS)):
        if not np.isfinite(atr[j]) or atr[j] <= 0:
            continue
        min_low = min(min_low, l[j]); max_high = max(max_high, h[j])
        body = abs(c[j]-o[j])
        if z["zone_side"] == "DEMAND":
            if c[j] < zlo:
                return None
            sweep = sweep or (l[j] < zlo)
            prev_h = h[j-1] if j > 0 else np.nan
            ok = c[j] > zhi and c[j] > o[j] and body >= MIN_CONFIRM_BODY_ATR*atr[j] and np.isfinite(prev_h) and c[j] > prev_h
            if ok:
                pen = (zhi-min_low)/width
                micro = (c[j]-prev_h)/atr[j]
                tr = execute(j, "LONG")
                if tr is None: return None
                return {**z, "signal_i": j, "signal_ts": idx[j], "touch_ts": idx[touch],
                        "touch_to_confirm_bars": int(j-touch+1), "penetration_zone_x": float(pen),
                        "distal_sweep": int(sweep), "confirm_body_atr": float(body/atr[j]),
                        "micro_bos_extension_atr": float(micro), **tr}
        else:
            if c[j] > zhi:
                return None
            sweep = sweep or (h[j] > zhi)
            prev_l = l[j-1] if j > 0 else np.nan
            ok = c[j] < zlo and c[j] < o[j] and body >= MIN_CONFIRM_BODY_ATR*atr[j] and np.isfinite(prev_l) and c[j] < prev_l
            if ok:
                pen = (max_high-zlo)/width
                micro = (prev_l-c[j])/atr[j]
                tr = execute(j, "SHORT")
                if tr is None: return None
                return {**z, "signal_i": j, "signal_ts": idx[j], "touch_ts": idx[touch],
                        "touch_to_confirm_bars": int(j-touch+1), "penetration_zone_x": float(pen),
                        "distal_sweep": int(sweep), "confirm_body_atr": float(body/atr[j]),
                        "micro_bos_extension_atr": float(micro), **tr}
    return None


def build_signals(h1: pd.DataFrame):
    hz = b11.add_atr(h1)
    execute = b11.execution_engine(hz)
    signals = []
    zone_counts = []
    for tf in SOURCE_TFS:
        src = b11.source_bars(h1, tf)
        origins = generate_origin_zones(src, tf)
        flips = add_flip_zones(origins, src, tf)
        zones = origins + flips
        print(f"{tf}: origins={len(origins)} flips={len(flips)} zones={len(zones)}")
        got = 0
        for n,z in enumerate(zones,1):
            s = first_defense_signal(hz, execute, z)
            if s is not None:
                got += 1
                signals.append(s)
            if n % 2000 == 0:
                print(f"  {tf} defense scan {n}/{len(zones)} signals={got}")
        zone_counts.append({"source_tf":tf,"origins":len(origins),"flips":len(flips),"defended_signals":got})
    q = pd.DataFrame(signals)
    if q.empty:
        raise RuntimeError("B12 generated no defended-zone signals")
    q["age_hours"] = (pd.to_datetime(q.touch_ts, utc=True)-pd.to_datetime(q.create_ts, utc=True)).dt.total_seconds()/3600.0
    q["week"] = q.signal_ts.map(lambda t: b11.week_key(b11.week_start(t)))
    q["is_tp"] = (q.reason == "TP").astype(int)
    return q.sort_values(["signal_ts","source_tf","zone_kind"]).reset_index(drop=True), zone_counts


def in_scan_window(ts):
    w = b11.week_start(ts)
    cutoff = w + pd.Timedelta(days=SCAN_CUTOFF_DAYS, hours=SCAN_CUTOFF_HOUR)
    return w <= ts <= cutoff


def partition_weeks(name):
    return b11.partition_weeks(name)


def week_keys(weeks):
    return {b11.week_key(w) for w in weeks}


def oracle_summary(sig, weeks):
    keys = week_keys(weeks)
    q = sig[sig.week.isin(keys) & sig.signal_ts.map(in_scan_window)].copy()
    rows = []
    zero_signal = []
    zero_tp = []
    for w in weeks:
        k = b11.week_key(w)
        x = q[q.week == k]
        n = len(x); wins = int(x.is_tp.sum()) if n else 0
        rows.append({"week":k,"signals":n,"tp_signals":wins})
        if n == 0: zero_signal.append(k)
        if wins == 0: zero_tp.append(k)
    d = pd.DataFrame(rows)
    return {
        "weeks": len(weeks), "signal_weeks": int((d.signals>0).sum()), "tp_weeks": int((d.tp_signals>0).sum()),
        "signal_coverage": float((d.signals>0).mean()) if len(d) else 0.0,
        "oracle_tp_coverage": float((d.tp_signals>0).mean()) if len(d) else 0.0,
        "signals": int(d.signals.sum()), "tp_signals": int(d.tp_signals.sum()),
        "median_signals_week": float(d.signals.median()) if len(d) else 0.0,
        "median_tp_signals_week": float(d.tp_signals.median()) if len(d) else 0.0,
        "zero_signal_weeks": zero_signal, "zero_tp_weeks": zero_tp,
    }, d


def atlas_summary(sig):
    rows=[]
    for (tf,kind),g in sig.groupby(["source_tf","zone_kind"]):
        for part in ("development","external","reference_validation","august"):
            weeks=partition_weeks(part); keys=week_keys(weeks)
            x=g[g.week.isin(keys)&g.signal_ts.map(in_scan_window)]
            o,_=oracle_summary(x,weeks)
            rows.append({"source_tf":tf,"zone_kind":kind,"partition":part,
                         "signals":len(x),"raw_wr":float(x.is_tp.mean()) if len(x) else None,
                         "signal_coverage":o["signal_coverage"],"oracle_tp_coverage":o["oracle_tp_coverage"],
                         "median_signals_week":o["median_signals_week"],"median_tp_signals_week":o["median_tp_signals_week"]})
    return pd.DataFrame(rows)


def fit_model(dev):
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES),
        ("num", StandardScaler(), NUM_FEATURES),
    ])
    model = LogisticRegression(C=0.5, solver="liblinear", class_weight="balanced", max_iter=2000, random_state=20260821)
    pipe = Pipeline([("pre",pre),("lr",model)])
    pipe.fit(dev[CAT_FEATURES+NUM_FEATURES], dev.is_tp.to_numpy(int))
    return pipe


def route(sig, weeks, threshold=None, route_name="MODEL"):
    keys=week_keys(weeks)
    q=sig[sig.week.isin(keys)&sig.signal_ts.map(in_scan_window)].copy()
    if threshold is not None:
        q=q[q.prob>=threshold]
    if q.empty:
        q["route"] = []
        return q
    q=q.sort_values(["signal_ts","prob"],ascending=[True,False]).groupby("week",as_index=False).head(1).copy()
    q["route"]=route_name
    return q.sort_values("signal_ts").reset_index(drop=True)


def stat(q,weeks):
    nweek=len(weeks)
    if q.empty:
        return {"weeks":nweek,"n":0,"coverage":0.0,"tp":0,"sl":0,"time":0,"wr":None,"exp":None,"pf":None,"max_ls":0}
    win=(q.reason=="TP").to_numpy(bool); a=q.net_ret.to_numpy(float)
    gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    streak=mx=0
    for v in win:
        if not v: streak+=1; mx=max(mx,streak)
        else: streak=0
    return {"weeks":nweek,"n":int(len(q)),"coverage":float(q.week.nunique()/nweek) if nweek else 0.0,
            "tp":int((q.reason=="TP").sum()),"sl":int((q.reason=="SL").sum()),"time":int((q.reason=="TIME").sum()),
            "wr":float(win.mean()),"exp":float(a.mean()),"pf":float(gp/gl) if gl>0 else (999.0 if gp>0 else 0.0),"max_ls":int(mx)}


def blocks(q,weeks):
    arr=list(weeks); edges=np.linspace(0,len(arr),5,dtype=int); out=[]
    for i in range(4):
        ww=arr[edges[i]:edges[i+1]]; keys=week_keys(ww)
        x=q[q.week.isin(keys)] if not q.empty else q
        out.append(stat(x,ww))
    return out


def selector_gate(s,bs,weeks,wrmin):
    return (s["n"]==len(weeks) and abs(s["coverage"]-1.0)<1e-12 and s["wr"] is not None and s["wr"]>=wrmin
            and s["exp"] is not None and s["exp"]>0 and s["pf"] is not None and s["pf"]>1
            and (s["max_ls"]==0 if wrmin>=1.0 else s["max_ls"]<=2)
            and sum(1 for b in bs if b["exp"] is not None and b["exp"]>0)>=(4 if wrmin>=1.0 else 3))


def fmtpct(v):
    return "-" if v is None or (isinstance(v,float) and not np.isfinite(v)) else f"{100*float(v):.2f}%"


def fmtn(v,n=3):
    return "-" if v is None or (isinstance(v,float) and not np.isfinite(v)) else f"{float(v):.{n}f}"


def main():
    h1=b11.load_h1()
    print(f"H1 {h1.index.min()} -> {h1.index.max()} rows={len(h1)}")
    sig,zone_counts=build_signals(h1)
    sig=sig[sig.signal_ts>=b11.EXT0].copy()

    # Stage A: descriptive oracle only. Candidate formation itself is causal.
    oracle={}; zero_rows=[]
    for part in ("development","external","reference_validation","august"):
        weeks=partition_weeks(part)
        o,d=oracle_summary(sig,weeks); oracle[part]=o
        for _,r in d.iterrows():
            if int(r.signals)==0 or int(r.tp_signals)==0:
                zero_rows.append({"partition":part,**r.to_dict()})
    pd.DataFrame(zero_rows).to_csv(OUT_ZERO,index=False)
    atlas=atlas_summary(sig); atlas.to_csv(OUT_ATLAS,index=False)

    oracle100=(oracle["external"]["oracle_tp_coverage"]==1.0 and oracle["reference_validation"]["oracle_tp_coverage"]==1.0)

    # Stage B: train only on development defended signals.
    dev_keys=week_keys(partition_weeks("development"))
    dev=sig[sig.week.isin(dev_keys)&sig.signal_ts.map(in_scan_window)].copy()
    if dev.is_tp.nunique()<2:
        raise RuntimeError("development labels lack both classes")
    model=fit_model(dev)
    sig["prob"]=model.predict_proba(sig[CAT_FEATURES+NUM_FEATURES])[:,1]

    dev_sc=sig[sig.week.isin(dev_keys)&sig.signal_ts.map(in_scan_window)]
    threshold_rows=[]
    for qv in THRESH_Q:
        th=float(np.quantile(dev_sc.prob.to_numpy(float),qv))
        r=route(sig,partition_weeks("development"),th,f"MODEL_Q{qv:.3f}")
        s=stat(r,partition_weeks("development"))
        threshold_rows.append({"quantile":qv,"threshold":th,**s})
    tdf=pd.DataFrame(threshold_rows)
    tdf["wr_sort"]=tdf.wr.fillna(-1.0); tdf["exp_sort"]=tdf.exp.fillna(-999.0); tdf["pf_sort"]=tdf.pf.fillna(-1.0)
    tdf=tdf.sort_values(["coverage","wr_sort","exp_sort","pf_sort","quantile"],ascending=[False,False,False,False,True]).reset_index(drop=True)
    chosen_q=float(tdf.iloc[0].quantile); chosen_th=float(tdf.iloc[0].threshold)
    tdf.to_csv(OUT_THRESH,index=False)

    selectors={}; selected=[]
    for name in ("FIRST_DEFENSE","MODEL_TRIGGER"):
        selectors[name]={}
        for part in ("development","external","reference_validation","august"):
            weeks=partition_weeks(part)
            r=route(sig,weeks,None,"FIRST_DEFENSE") if name=="FIRST_DEFENSE" else route(sig,weeks,chosen_th,"MODEL_TRIGGER")
            if not r.empty:
                x=r.copy(); x["selector"]=name; x["partition"]=part; selected.append(x)
            selectors[name][part]={"stat":stat(r,weeks),"blocks":blocks(r,weeks)}
    if selected:
        pd.concat(selected,ignore_index=True).to_csv(OUT_SEL,index=False)

    extw=partition_weeks("external"); valw=partition_weeks("reference_validation")
    robust=False; highp=False; passing=None
    for name in ("FIRST_DEFENSE","MODEL_TRIGGER"):
        es=selectors[name]["external"]; vs=selectors[name]["reference_validation"]
        if selector_gate(es["stat"],es["blocks"],extw,1.0) and selector_gate(vs["stat"],vs["blocks"],valw,1.0):
            robust=True; passing=name
        if selector_gate(es["stat"],es["blocks"],extw,0.80) and selector_gate(vs["stat"],vs["blocks"],valw,0.80):
            highp=True

    result={
        "experiment":"B12_DEFENDED_SR","implementation_revision":IMPL,
        "coverage":{"first":str(h1.index.min()),"last":str(h1.index.max()),"h1_rows":int(len(h1))},
        "frozen":{"source_tfs":SOURCE_TFS,"max_age_hours":MAX_AGE_HOURS,"origin_lookback":ORIGIN_LOOKBACK,
                  "min_displacement_atr":MIN_DISP_ATR,"confirm_bars":CONFIRM_BARS,"min_confirm_body_atr":MIN_CONFIRM_BODY_ATR,
                  "chosen_threshold_quantile":chosen_q,"chosen_threshold":chosen_th},
        "zone_counts":zone_counts,"oracle":oracle,"selectors":selectors,
        "gates":{"B12_DEFENDED_ORACLE_100":"PASS" if oracle100 else "FAIL",
                 "B12_ROBUST_WEEKLY_100":"PASS" if robust else "FAIL",
                 "B12_HIGH_PRECISION_WEEKLY":"PASS" if highp else "FAIL","passing_selector":passing},
        "live_bbc_untouched":True,
    }
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding="utf-8")

    verdict="B12_ROBUST_WEEKLY_100_PASS" if robust else ("B12_DEFENDED_ORACLE_100_SELECTOR_FAIL" if oracle100 else "B12_DEFENDED_ORACLE_NOT_100")
    md=["# BTC Weekly Defended S/R B12 — Result","",f"Implementation revision **{IMPL}**.","",f"**Verdict: {verdict}**","",
        f"Coverage **{h1.index.min()} -> {h1.index.max()}**, official Binance BTCUSDT H1 rows **{len(h1):,}**.","",
        "Definition: H1/H4/D1/W1 displacement-origin or accepted polarity-flip zone; fresh first H1 revisit; no close through distal; directional H1 reclaim above/below proximal; body >=0.25 ATR; micro-BOS; next-H1-open execution; net +1.00% vs -1.00%; 0.15% fee; adverse-first; same-week exit.","",
        "## Stage A — defended-zone feasibility (hindsight outcome only; NOT a strategy)","",
        "| Partition | Weeks | Signal weeks | TP weeks | Signal coverage | Oracle TP coverage | Signals | TP signals | Median signals/week |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for part in ("development","external","reference_validation","august"):
        o=oracle[part]
        md.append(f"| {part} | {o['weeks']} | {o['signal_weeks']} | {o['tp_weeks']} | {fmtpct(o['signal_coverage'])} | {fmtpct(o['oracle_tp_coverage'])} | {o['signals']} | {o['tp_signals']} | {o['median_signals_week']:.1f} |")
    md += ["","## Stage B — causal one-trade selectors","",f"Development-frozen model threshold: quantile **{chosen_q:.3f}**, probability **{chosen_th:.6f}**.","",
           "| Selector | Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |","|---|---|---:|---:|---:|---:|---:|---:|"]
    for name in ("FIRST_DEFENSE","MODEL_TRIGGER"):
        for part in ("development","external","reference_validation","august"):
            s=selectors[name][part]["stat"]
            md.append(f"| {name} | {part} | {s['weeks']}/{s['n']}/{fmtpct(s['coverage'])} | {s['tp']}/{s['sl']}/{s['time']} | {fmtpct(s['wr'])} | {fmtpct(s['exp'])} | {fmtn(s['pf'])} | {s['max_ls']} |")
    md += ["","## Source-zone counts","","| TF | Origins | Flips | Defended signals |","|---|---:|---:|---:|"]
    for r in zone_counts:
        md.append(f"| {r['source_tf']} | {r['origins']} | {r['flips']} | {r['defended_signals']} |")
    md += ["","## Gates","",f"- B12_DEFENDED_ORACLE_100: **{'PASS' if oracle100 else 'FAIL'}**",
           f"- B12_ROBUST_WEEKLY_100: **{'PASS' if robust else 'FAIL'}**",f"- B12_HIGH_PRECISION_WEEKLY: **{'PASS' if highp else 'FAIL'}**","",
           "If the oracle gate fails, this frozen defended-S/R vocabulary itself does not contain a +1R winner in every week; selector tuning cannot mathematically rescue those zero-TP weeks.","",
           "No post-result retuning is promoted. Live BBC untouched."]
    OUT_MD.write_text("\n".join(md)+"\n",encoding="utf-8")
    print("\n".join(md))

if __name__ == "__main__":
    main()
