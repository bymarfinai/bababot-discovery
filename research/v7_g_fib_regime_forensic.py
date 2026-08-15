#!/usr/bin/env python3
"""V7-G — causal market-state forensic for FIB 61.8-70.5 ON/OFF regimes.

Research only. Uses the exact V7-F frozen 971d window and official Binance
USD-M archive reconstruction. The FIB event definition/outcome logic remains
unchanged (V4-B2, RR=1, confirm_bars=3). We do not optimize a trading filter.

Question:
Which market state, already observable before the 5m confirmation entry,
co-moves with the large 120d FIB WR variation (25% -> 75%)?

Feature inventory is frozen from the pre-existing V4-B6 forensic before this
run: own-pair 4h/24h/7d signed returns, ATR/realized-vol expansion, trend
efficiency, cross-pair synchronization/alignment/breadth, and BTC context.
No new indicators, no threshold sweep, no TP/SL sweep.

The eight 120d blocks are exactly the V7-F blocks. Block 5-6 are labeled BAD
and block 8 GOOD only for descriptive distribution comparison because those
labels were already observed in V7-F. Formal ranking uses all eight blocks.
"""
import json
import math
import os
import sqlite3
import statistics
from datetime import datetime, timedelta, timezone

import numpy as np

from research import v7_f_fib_120d_archive_audit as archive

PAIRS = archive.PAIRS
DAYS = 971
BLOCK_DAYS = 120
BAND = "61.8-70.5"
DB = "/tmp/v7_g_fib_regime.db"
# Exact successful V7-F audit boundary; do not drift the block edges on rerun.
WINDOW_END = datetime.fromisoformat("2026-08-15T15:11:15.831175+00:00")
WINDOW_START = WINDOW_END - timedelta(days=DAYS)
FEATURES = [
    "own_signed_ret4h_pct", "own_signed_ret24h_pct", "own_signed_ret7d_pct",
    "own_atr1h_pct", "own_atr_ratio_7d", "own_rv24_vs_prior7d",
    "own_trend_eff24h", "own_trend_eff7d",
    "market_sync24h", "market_sync7d", "market_alignment24h", "market_alignment7d",
    "market_avg_abs_ret24h_pct", "market_avg_abs_ret7d_pct",
    "market_avg_atr1h_pct", "market_avg_atr_ratio_7d", "market_avg_rv24_ratio",
    "market_expanding_breadth", "market_rv_expanding_breadth",
    "btc_signed_ret24h_pct", "btc_signed_ret7d_pct",
]


def stat(rows):
    n = len(rows); w = sum(int(r["win"]) for r in rows)
    return {"n": n, "wins": w, "losses": n-w,
            "wr_pct": round(100.0*w/n, 2) if n else None}


def med(vals):
    z=[]
    for v in vals:
        try:
            x=float(v)
            if math.isfinite(x): z.append(x)
        except Exception:
            pass
    return float(statistics.median(z)) if z else None


def qtile(vals, q):
    z=[]
    for v in vals:
        try:
            x=float(v)
            if math.isfinite(x): z.append(x)
        except Exception:
            pass
    return float(np.quantile(np.asarray(z,dtype=float),q)) if z else None


def ranks(vals):
    # Average ranks for ties, 1-based.
    n=len(vals); order=sorted(range(n), key=lambda i: vals[i])
    out=[0.0]*n; i=0
    while i<n:
        j=i+1
        while j<n and vals[order[j]]==vals[order[i]]: j+=1
        r=(i+1+j)/2.0
        for k in range(i,j): out[order[k]]=r
        i=j
    return out


def spearman(xs, ys):
    if len(xs)!=len(ys) or len(xs)<3: return None
    rx=np.asarray(ranks(xs),dtype=float); ry=np.asarray(ranks(ys),dtype=float)
    if np.std(rx)==0 or np.std(ry)==0: return 0.0
    return float(np.corrcoef(rx,ry)[0,1])


def quartile_wr(rows, feature):
    z=[]
    for r in rows:
        try:
            x=float(r.get(feature))
            if math.isfinite(x): z.append((x,r))
        except Exception:
            pass
    z.sort(key=lambda t:t[0])
    if len(z)<8: return None
    groups=np.array_split(np.arange(len(z)),4)
    out=[]
    for qi,idx in enumerate(groups,1):
        rr=[z[int(k)][1] for k in idx]
        s=stat(rr)
        s["value_median"]=round(med([z[int(k)][0] for k in idx]),6)
        s["q"]=qi
        out.append(s)
    return out


def state_bucket_flags(r):
    def g(k,default=0.0):
        try:return float(r.get(k))
        except Exception:return default
    return {
        # Identical predeclared V4-B6 bucket definitions.
        "own_24h_aligned": g("own_signed_ret24h_pct") > 0,
        "own_7d_aligned": g("own_signed_ret7d_pct") > 0,
        "own_24h_and_7d_aligned": g("own_signed_ret24h_pct") > 0 and g("own_signed_ret7d_pct") > 0,
        "market_3of4_or_more_aligned_24h": g("market_alignment24h") >= 0.75,
        "market_3of4_or_more_aligned_7d": g("market_alignment7d") >= 0.75,
        "own_atr_expanding": g("own_atr_ratio_7d") > 1.0,
        "market_atr_majority_expanding": g("market_expanding_breadth") >= 0.75,
        "market_rv_majority_expanding": g("market_rv_expanding_breadth") >= 0.75,
        "direction_and_market_alignment_24h": g("own_signed_ret24h_pct") > 0 and g("market_alignment24h") >= 0.75,
        "direction_and_atr_expansion": g("own_signed_ret24h_pct") > 0 and g("own_atr_ratio_7d") > 1.0,
    }


def build_db():
    if os.path.exists(DB): os.unlink(DB)
    conn=sqlite3.connect(DB)
    conn.execute("""CREATE TABLE klines(
        symbol TEXT,timeframe TEXT,open_time INTEGER,
        open REAL,high REAL,low REAL,close REAL,volume REAL,
        close_time INTEGER,quote_volume REAL,trades INTEGER,
        taker_buy_volume REAL,taker_buy_quote_volume REAL,
        PRIMARY KEY(symbol,timeframe,open_time))""")
    coverage={}
    for p in PAIRS:
        coverage[p]={}
        for tf in ("1h","5m"):
            rows=archive.load_series(p,tf,WINDOW_START,WINDOW_END)
            conn.executemany("INSERT OR REPLACE INTO klines VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",rows)
            conn.commit()
            coverage[p][tf]={
                "rows":len(rows),
                "first":datetime.fromtimestamp(rows[0][2]/1000,tz=timezone.utc).isoformat() if rows else None,
                "last":datetime.fromtimestamp(rows[-1][2]/1000,tz=timezone.utc).isoformat() if rows else None,
            }
    conn.close()
    return coverage


def fixed_load(symbol,timeframe,days):
    conn=sqlite3.connect(DB)
    try:
        return conn.execute("""
            SELECT open_time,open,high,low,close,volume
            FROM klines
            WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<?
            ORDER BY open_time ASC""",
            (symbol,timeframe,int(WINDOW_START.timestamp()*1000),int(WINDOW_END.timestamp()*1000))).fetchall()
    finally:
        conn.close()


def build_series(symbol, atr_func):
    rows=fixed_load(symbol,"1h",DAYS)
    T=[int(r[0]) for r in rows]
    H=np.asarray([r[2] for r in rows],dtype=float)
    L=np.asarray([r[3] for r in rows],dtype=float)
    C=np.asarray([r[4] for r in rows],dtype=float)
    ATR=atr_func(H,L,C,14)
    atr_pct=np.asarray([(100.0*ATR[i]/C[i]) if C[i]>0 else 0.0 for i in range(len(C))],dtype=float)
    return {"T":T,"C":C,"ATR_PCT":atr_pct}


def pair_side_expected(block_rows, all_full_rows):
    if not block_rows:return {"n":0,"actual_wins":0,"expected_wins":None,"expected_wr_pct":None,"residual_wins":None}
    block_ids={id(r) for r in block_rows}
    expected=[]
    for r in block_rows:
        base=[x for x in all_full_rows if id(x) not in block_ids and x["pair"]==r["pair"] and x["side"]==r["side"]]
        if not base:
            base=[x for x in all_full_rows if id(x) not in block_ids and x["pair"]==r["pair"]]
        if not base:
            base=[x for x in all_full_rows if id(x) not in block_ids]
        expected.append(sum(x["win"] for x in base)/len(base))
    actual=sum(r["win"] for r in block_rows); exp=sum(expected)
    return {"n":len(block_rows),"actual_wins":actual,"expected_wins":round(exp,3),
            "expected_wr_pct":round(100.0*exp/len(block_rows),2),"residual_wins":round(actual-exp,3)}


def main():
    coverage=build_db()
    os.environ["DB_PATH"]=DB

    import v4_context_fib_forensic_endpoint as fib
    import v4_market_state_forensic_endpoint as ms
    from v4_structural_zone_endpoint import _atr

    # Force the event generator to the exact V7-F time window instead of datetime.now().
    fib._load=fixed_load
    all_series={p:build_series(p,_atr) for p in PAIRS}

    events=[]; source={}; errors={}
    for p in PAIRS:
        d=fib.context_fib_forensic(symbols=p,days=DAYS,rr=1.0,confirm_bars=3,sample_limit=500)
        source[p]={"overall":d.get("overall"),"fib_bands":d.get("fib_bands"),"errors":d.get("errors")}
        if d.get("errors"): errors[p]=d.get("errors")
        sample=d.get("sample") or []
        if int((d.get("overall") or {}).get("n",0) or 0)>len(sample):
            raise RuntimeError(f"sample truncated {p}")
        for x in sample:
            if x.get("fib_band")!=BAND or x.get("outcome") not in ("BOUNCE","BREAK"):continue
            z=dict(x); z["pair"]=p; z["win"]=1 if x["outcome"]=="BOUNCE" else 0
            dt=datetime.fromisoformat(x["confirm_time"])
            if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
            dt=dt.astimezone(timezone.utc)
            event_close_ms=int(dt.timestamp()*1000)+300_000
            oi=ms._latest_completed_index(all_series[p]["T"],event_close_ms)
            own=ms._pair_state(all_series[p],oi) if oi>=0 else None
            if not own:continue
            trade_dir=1 if z.get("side")=="DEMAND" else -1
            z.update({
                "own_signed_ret4h_pct":100.0*own["ret4h"]*trade_dir if own.get("ret4h") is not None else None,
                "own_signed_ret24h_pct":100.0*own["ret24h"]*trade_dir if own.get("ret24h") is not None else None,
                "own_signed_ret7d_pct":100.0*own["ret7d"]*trade_dir if own.get("ret7d") is not None else None,
                "own_atr1h_pct":own.get("atr1h_pct"),
                "own_atr_ratio_7d":own.get("atr_ratio_7d"),
                "own_rv24_vs_prior7d":own.get("rv24_vs_prior7d"),
                "own_trend_eff24h":own.get("trend_eff24h"),
                "own_trend_eff7d":own.get("trend_eff7d"),
            })
            z.update(ms._market_state(all_series,event_close_ms,trade_dir))
            z["t"]=dt
            delta=(dt-WINDOW_START).total_seconds()
            z["block"]=int(delta//(BLOCK_DAYS*86400))+1 if delta>=0 else 0
            events.append(z)
    events.sort(key=lambda r:r["t"])

    full=[r for r in events if 1<=r["block"]<=8]
    remainder=[r for r in events if r["block"]==9]
    blocks=[]
    for b in range(1,9):
        xs=[r for r in full if r["block"]==b]
        fmed={f:round(med([r.get(f) for r in xs]),6) if med([r.get(f) for r in xs]) is not None else None for f in FEATURES}
        bucket_prev={}
        for name in state_bucket_flags(xs[0]).keys() if xs else []:
            selected=[r for r in xs if state_bucket_flags(r)[name]]
            bucket_prev[name]={"prevalence_pct":round(100.0*len(selected)/len(xs),2) if xs else None,"selected":stat(selected)}
        blocks.append({"block":b,"stats":stat(xs),"feature_medians":fmed,
                       "pair_side_expected":pair_side_expected(xs,full),"state_buckets":bucket_prev})

    block_wr=[b["stats"]["wr_pct"] for b in blocks]
    feature_reports=[]
    for f in FEATURES:
        xmed=[b["feature_medians"][f] for b in blocks]
        valid=[i for i,x in enumerate(xmed) if x is not None and block_wr[i] is not None]
        rho=spearman([xmed[i] for i in valid],[block_wr[i] for i in valid]) if len(valid)>=3 else None
        qs=quartile_wr(full,f)
        spread=None
        monotonic=None
        if qs:
            spread=round(qs[-1]["wr_pct"]-qs[0]["wr_pct"],2)
            wrs=[q["wr_pct"] for q in qs]
            if rho is not None and rho>=0: monotonic=all(wrs[i]<=wrs[i+1] for i in range(3))
            elif rho is not None: monotonic=all(wrs[i]>=wrs[i+1] for i in range(3))
        good=[r for r in full if r["block"]==8]
        bad=[r for r in full if r["block"] in (5,6)]
        gm=med([r.get(f) for r in good]); bm=med([r.get(f) for r in bad])
        direction_ok=(rho is not None and gm is not None and bm is not None and ((rho>0 and gm>bm) or (rho<0 and gm<bm)))
        expected_spread=(spread is not None and rho is not None and ((rho>0 and spread>=15.0) or (rho<0 and spread<=-15.0)))
        candidate=bool(rho is not None and abs(rho)>=0.65 and direction_ok and expected_spread and monotonic is True)
        feature_reports.append({
            "feature":f,"block_spearman_rho":round(rho,4) if rho is not None else None,
            "block_medians":[round(x,6) if x is not None else None for x in xmed],
            "bad_blocks_5_6_median":round(bm,6) if bm is not None else None,
            "good_block_8_median":round(gm,6) if gm is not None else None,
            "quartiles":qs,"q4_minus_q1_wr_pp":spread,"quartile_monotonic_in_block_rho_direction":monotonic,
            "candidate_gate_pass":candidate,
        })
    feature_reports.sort(key=lambda x:abs(x["block_spearman_rho"] or 0),reverse=True)

    # Existing B6 buckets: evaluate true-vs-false over all eight blocks, plus block consistency.
    bucket_report={}
    names=list(state_bucket_flags(full[0]).keys()) if full else []
    for name in names:
        tr=[r for r in full if state_bucket_flags(r)[name]]; fa=[r for r in full if not state_bucket_flags(r)[name]]
        per=[]
        for b in range(1,9):
            xs=[r for r in full if r["block"]==b]
            bt=[r for r in xs if state_bucket_flags(r)[name]]; bf=[r for r in xs if not state_bucket_flags(r)[name]]
            per.append({"block":b,"true":stat(bt),"false":stat(bf),"prevalence_pct":round(100.0*len(bt)/len(xs),2) if xs else None})
        comparable=[x for x in per if x["true"]["n"]>=3 and x["false"]["n"]>=3]
        better=sum(x["true"]["wr_pct"]>x["false"]["wr_pct"] for x in comparable)
        bucket_report[name]={"true":stat(tr),"false":stat(fa),"wr_lift_pp":round((stat(tr)["wr_pct"] or 0)-(stat(fa)["wr_pct"] or 0),2),
                             "comparable_blocks":len(comparable),"blocks_true_beats_false":better,"per_block":per}

    # Candidate rule is intentionally strict and predeclared above; this does not create a live filter.
    candidates=[x for x in feature_reports if x["candidate_gate_pass"]]
    overall=stat(events)
    result={
        "phase":"V7-G",
        "status":"CAUSAL_FIB_REGIME_FORENSIC",
        "definition":{
            "frozen_window_start":WINDOW_START.isoformat(),"frozen_window_end":WINDOW_END.isoformat(),
            "history_days":DAYS,"fib_band":BAND,"rr":1.0,"confirm_bars":3,
            "blocks":"same 8x120d + 11d remainder as V7-F","feature_inventory":"unchanged V4-B6 predeclared market-state features",
            "no_threshold_sweep":True,"no_strategy_filter_added":True,
            "candidate_gate":"abs block Spearman >=0.65 + good-vs-bad shift same direction + Q4-Q1 >=15pp in direction + monotonic quartile WR",
        },
        "coverage":coverage,"errors":errors,
        "parity":{"all_fixed_band_events":overall,"full_8_blocks":stat(full),"remainder_11d":stat(remainder),
                  "v7_f_fingerprint":{"n":120,"wins":61,"losses":59,"wr_pct":50.83}},
        "blocks":blocks,
        "top_feature_rank":feature_reports,
        "predeclared_binary_bucket_report":bucket_report,
        "candidate_features_for_separate_frozen_test":[x["feature"] for x in candidates],
        "verdict":"CANDIDATE_STATE_FOUND" if candidates else "NO_ROBUST_CAUSAL_STATE_SEPARATOR_FOUND",
        "source_pair_diagnostics":source,
    }
    print("V7_G_FIB_REGIME_RESULT",json.dumps(result,separators=(",",":"),default=str))

if __name__=="__main__":main()
