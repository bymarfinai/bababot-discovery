#!/usr/bin/env python3
"""MH0 preregistered cross-sectional Market Hunter backtest.

Research-only. Broad USDT perpetual universe, causal 1h cross-sectional ranks,
next-1h-open execution. No live order code.
"""
from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
END = pd.Timestamp("2026-08-19T00:00:00Z")
DAYS = 365
WARMUP_DAYS = 10
COST = 0.0015
TP = 0.013
SL = 0.013
HOLD_H = 6
NOTIONAL = 500.0
SEED = 20260819

# Broad, frozen before results. Missing/not-yet-listed histories are dynamically ineligible.
SYMBOLS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","LINKUSDT",
    "AVAXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","TRXUSDT","ETCUSDT","XLMUSDT","ATOMUSDT",
    "UNIUSDT","AAVEUSDT","NEARUSDT","FILUSDT","APTUSDT","INJUSDT","SUIUSDT","OPUSDT",
    "ARBUSDT","TIAUSDT","SEIUSDT","WLDUSDT","ENAUSDT","JUPUSDT","WIFUSDT","1000PEPEUSDT",
    "FETUSDT","RUNEUSDT","LDOUSDT","DYDXUSDT","CRVUSDT","STXUSDT","PENDLEUSDT","ORDIUSDT",
    "NOTUSDT","CATIUSDT","TONUSDT","TAOUSDT","RENDERUSDT","POLUSDT","NEIROUSDT","KAIAUSDT",
    "GALAUSDT","SANDUSDT","MANAUSDT","AXSUSDT","APEUSDT","IMXUSDT","MKRUSDT","COMPUSDT",
]
BASES = ["https://fapi.binance.com/fapi/v1/klines", "https://fapi1.binance.com/fapi/v1/klines"]

FEATURES_LONG = ["ret4h","ret24h","rel_quote_volume","range_expansion","breakout_position","taker_imbalance"]

@dataclass
class Selection:
    decision_bar_open: str
    decision_available_at: str
    entry_time: str
    symbol: str
    side: str
    score: float
    eligible_n: int
    liquid_n: int
    kind: str


def _request(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> list:
    rows = []
    cur = start
    while cur < end:
        params = {
            "symbol": symbol, "interval": "1h", "limit": 1500,
            "startTime": int(cur.timestamp()*1000),
            "endTime": int(end.timestamp()*1000)-1,
        }
        data = None; errs=[]
        for base in BASES:
            try:
                r=requests.get(base,params=params,timeout=30,headers={"User-Agent":"bababot-mh0/1.0"})
                if r.status_code==200 and isinstance(r.json(),list):
                    data=r.json(); break
                errs.append(f"{r.status_code}:{r.text[:80]}")
            except Exception as e:
                errs.append(str(e))
        if data is None:
            raise RuntimeError(" | ".join(errs))
        if not data: break
        rows.extend(data)
        last=pd.to_datetime(int(data[-1][0]),unit="ms",utc=True)
        nxt=last+pd.Timedelta(hours=1)
        if nxt<=cur: break
        cur=nxt
        if len(data)<1500: break
        time.sleep(0.04)
    return rows


def load_symbol(symbol: str) -> pd.DataFrame:
    start=END-pd.Timedelta(days=DAYS+WARMUP_DAYS)
    raw=_request(symbol,start,END)
    if not raw: return pd.DataFrame()
    z=pd.DataFrame(raw)
    df=pd.DataFrame({
        "ts":pd.to_datetime(pd.to_numeric(z.iloc[:,0]),unit="ms",utc=True),
        "open":pd.to_numeric(z.iloc[:,1],errors="coerce"),
        "high":pd.to_numeric(z.iloc[:,2],errors="coerce"),
        "low":pd.to_numeric(z.iloc[:,3],errors="coerce"),
        "close":pd.to_numeric(z.iloc[:,4],errors="coerce"),
        "quote_volume":pd.to_numeric(z.iloc[:,7],errors="coerce"),
        "taker_buy_quote":pd.to_numeric(z.iloc[:,10],errors="coerce"),
    }).dropna().drop_duplicates("ts").sort_values("ts").set_index("ts")
    if len(df)<180: return pd.DataFrame()
    prev=df.close.shift(1)
    tr=pd.concat([(df.high-df.low).abs(),(df.high-prev).abs(),(df.low-prev).abs()],axis=1).max(axis=1)
    trp=tr/df.close
    prior_qv_med=df.quote_volume.shift(1).rolling(168,min_periods=168).median()
    prior_tr_med=trp.shift(1).rolling(168,min_periods=168).median()
    prior_hi=df.high.shift(1).rolling(24,min_periods=24).max()
    prior_lo=df.low.shift(1).rolling(24,min_periods=24).min()
    span=(prior_hi-prior_lo).replace(0,np.nan)
    df["ret4h"]=df.close/df.close.shift(4)-1
    df["ret24h"]=df.close/df.close.shift(24)-1
    df["rel_quote_volume"]=df.quote_volume/prior_qv_med
    df["range_expansion"]=trp/prior_tr_med
    df["breakout_position"]=(df.close-prior_lo)/span-0.5
    df["taker_imbalance"]=np.where(df.quote_volume>0,2*df.taker_buy_quote/df.quote_volume-1,np.nan)
    df["liq24"]=df.quote_volume.rolling(24,min_periods=24).sum()
    return df.replace([np.inf,-np.inf],np.nan)


def pct_rank(s: pd.Series) -> pd.Series:
    return s.rank(pct=True,method="average")


def build_selections(data: dict[str,pd.DataFrame]) -> dict[str,list[Selection]]:
    eval_start=END-pd.Timedelta(days=DAYS)
    timestamps=sorted(set().union(*[set(d.index[(d.index>=eval_start)&(d.index<END-pd.Timedelta(hours=7))]) for d in data.values() if len(d)]))
    out={"composite":[],"momentum":[],"random":[],"top3":[]}
    rng=random.Random(SEED)
    for t in timestamps:
        rows=[]
        for sym,df in data.items():
            if t not in df.index: continue
            r=df.loc[t]
            vals=[r.get(x,np.nan) for x in FEATURES_LONG]+[r.get("liq24",np.nan)]
            if not all(pd.notna(x) and math.isfinite(float(x)) for x in vals): continue
            rows.append({"symbol":sym,**{x:float(r[x]) for x in FEATURES_LONG},"liq24":float(r.liq24)})
        if len(rows)<10: continue
        x=pd.DataFrame(rows).set_index("symbol")
        # Causal liquidity: top 50% trailing 24h quote-volume among currently eligible.
        q=x.liq24.quantile(0.5)
        liquid=x[x.liq24>=q].copy()
        if len(liquid)<10: continue
        long_cols=[]; short_cols=[]
        for f in FEATURES_LONG:
            pr=pct_rank(liquid[f])
            long_cols.append(pr)
            if f in ("rel_quote_volume","range_expansion"):
                short_cols.append(pr)
            else:
                short_cols.append(pct_rank(-liquid[f]))
        liquid["long_score"]=pd.concat(long_cols,axis=1).mean(axis=1)
        liquid["short_score"]=pd.concat(short_cols,axis=1).mean(axis=1)
        candidates=[]
        for sym,r in liquid.iterrows():
            if r.long_score>=r.short_score: candidates.append((float(r.long_score),sym,"LONG"))
            else: candidates.append((float(r.short_score),sym,"SHORT"))
        candidates.sort(reverse=True)
        entry_t=t+pd.Timedelta(hours=1)
        avail=t+pd.Timedelta(hours=1)  # bar t becomes known at its close
        def sel(c,kind):
            score,sym,side=c
            return Selection(str(t),str(avail),str(entry_t),sym,side,score,len(x),len(liquid),kind)
        out["composite"].append(sel(candidates[0],"composite"))
        for c in candidates[:3]: out["top3"].append(sel(c,"top3"))
        # Raw momentum: largest absolute completed 24h return; direction follows sign.
        msym=liquid.ret24h.abs().idxmax(); mr=float(liquid.loc[msym,"ret24h"])
        out["momentum"].append(Selection(str(t),str(avail),str(entry_t),msym,"LONG" if mr>=0 else "SHORT",abs(mr),len(x),len(liquid),"momentum"))
        # Deterministic random control over same liquid universe.
        rsym=rng.choice(list(liquid.index)); rside=rng.choice(["LONG","SHORT"])
        out["random"].append(Selection(str(t),str(avail),str(entry_t),rsym,rside,0.0,len(x),len(liquid),"random"))
    return out


def evaluate_selection(s: Selection, data: dict[str,pd.DataFrame]) -> dict|None:
    df=data.get(s.symbol)
    if df is None or not len(df): return None
    et=pd.Timestamp(s.entry_time)
    if et not in df.index: return None
    side=1 if s.side=="LONG" else -1
    ep=float(df.loc[et,"open"])
    if ep<=0:return None
    res={**asdict(s),"entry_price":ep}
    for h in (1,3,6):
        tt=et+pd.Timedelta(hours=h-1)
        if tt not in df.index: return None
        px=float(df.loc[tt,"close"])
        raw=side*(px/ep-1)
        res[f"gross_{h}h"]=raw
        res[f"net_{h}h"]=raw-COST
    # TP/SL control across exactly six executable hourly bars.
    tp=ep*(1+TP) if side==1 else ep*(1-TP)
    sl=ep*(1-SL) if side==1 else ep*(1+SL)
    exit_raw=None; exit_reason=None; exit_available=None; exit_px=None
    for k in range(HOLD_H):
        tt=et+pd.Timedelta(hours=k)
        if tt not in df.index:return None
        r=df.loc[tt]; hi=float(r.high); lo=float(r.low)
        hit_tp=hi>=tp if side==1 else lo<=tp
        hit_sl=lo<=sl if side==1 else hi>=sl
        if hit_sl: # includes dual touch: adverse-first
            exit_px=sl;exit_raw=-SL;exit_reason="SL";exit_available=tt+pd.Timedelta(hours=1);break
        if hit_tp:
            exit_px=tp;exit_raw=TP;exit_reason="TP";exit_available=tt+pd.Timedelta(hours=1);break
    if exit_raw is None:
        tt=et+pd.Timedelta(hours=HOLD_H-1)
        exit_px=float(df.loc[tt,"close"])
        exit_raw=side*(exit_px/ep-1);exit_reason="TIME";exit_available=tt+pd.Timedelta(hours=1)
    res.update({"exec_raw":exit_raw,"exec_net":exit_raw-COST,"exec_pnl_usd":(exit_raw-COST)*NOTIONAL,
                "exit_reason":exit_reason,"exit_price":exit_px,"exit_available":str(exit_available)})
    return res


def evaluate_all(selections,data):
    return {k:[z for z in (evaluate_selection(s,data) for s in v) if z is not None] for k,v in selections.items()}


def pf(vals):
    gp=sum(v for v in vals if v>0); gl=-sum(v for v in vals if v<0)
    return gp/gl if gl>0 else (float("inf") if gp>0 else None)


def max_dd(vals):
    eq=0;pk=0;dd=0
    for v in vals:
        eq+=v;pk=max(pk,eq);dd=max(dd,pk-eq)
    return dd


def stats(rows,key="exec_pnl_usd"):
    vals=[float(r[key]) for r in rows if r.get(key) is not None]
    if not vals:return {"n":0,"wr_pct":None,"pnl_usd":0,"expectancy_usd":None,"pf":None,"max_dd_usd":0}
    wins=sum(v>0 for v in vals)
    return {"n":len(vals),"wr_pct":100*wins/len(vals),"pnl_usd":sum(vals),"expectancy_usd":sum(vals)/len(vals),"pf":pf(vals),"max_dd_usd":max_dd(vals)}


def horizon_stats(rows,h=6):
    vals=[float(r[f"net_{h}h"])*NOTIONAL for r in rows]
    if not vals:return {"n":0}
    return {"n":len(vals),"positive_pct":100*sum(v>0 for v in vals)/len(vals),"net_expectancy_usd":float(np.mean(vals)),"total_net_usd":float(np.sum(vals)),"pf":pf(vals)}


def sequential(rows):
    out=[];free=pd.Timestamp.min.tz_localize("UTC")
    for r in sorted(rows,key=lambda z:pd.Timestamp(z["entry_time"])):
        et=pd.Timestamp(r["entry_time"])
        if et<free:continue
        out.append(r);free=pd.Timestamp(r["exit_available"])
    return out


def window(rows,days):
    cut=END-pd.Timedelta(days=days)
    return [r for r in rows if pd.Timestamp(r["entry_time"])>=cut and pd.Timestamp(r["entry_time"])<END]


def blocks(rows,n=4):
    start=END-pd.Timedelta(days=DAYS);span=(END-start)/n;out={}
    for i in range(n):
        a=start+i*span;b=start+(i+1)*span
        z=[r for r in rows if a<=pd.Timestamp(r["entry_time"])<b]
        out[f"B{i+1}"]={"start":str(a),"end":str(b),**stats(z),"h6":horizon_stats(z,6)}
    return out


def attribution(rows):
    by_side={s:stats([r for r in rows if r["side"]==s]) for s in ("LONG","SHORT")}
    syms=sorted(set(r["symbol"] for r in rows))
    by_pair={s:stats([r for r in rows if r["symbol"]==s]) for s in syms}
    contrib=sorted(((s,v["pnl_usd"],v["n"]) for s,v in by_pair.items()),key=lambda x:x[1],reverse=True)
    return by_side,by_pair,contrib


def fmt(x,d=2):
    if x is None:return "-"
    if isinstance(x,float) and math.isinf(x):return "inf"
    return f"{x:.{d}f}"


def render(report,path):
    lines=["# Market Hunter MH0 — Cross-Sectional Backtest","", "**Research-only. Live systems untouched.**","",
           f"Frozen window end-exclusive: `{END.isoformat()}`",f"Requested universe: **{len(SYMBOLS)}** symbols; usable data: **{report['coverage']['usable_symbols']}**.","",
           "Primary: causal 1h cross-sectional composite rank → top-1 → next-1h-open entry. Cost 0.15%. Sequential control uses TP/SL 1.3%/1.3%, max 6h.",""]
    for days in (90,120,365):
        lines += [f"## {days} days","","### Independent hourly opportunities","","| Selector | N | 6h positive | 6h net exp | 6h PF |","|---|---:|---:|---:|---:|"]
        for k in ("composite","momentum","random"):
            x=report["windows"][str(days)][k]["independent_h6"]
            lines.append(f"| {k} | {x.get('n',0)} | {fmt(x.get('positive_pct'))}% | ${fmt(x.get('net_expectancy_usd'),4)} | {fmt(x.get('pf'),3)} |")
        lines += ["","### Single-position sequential TP/SL execution","","| Selector | Trades | WR | PnL | Exp/trade | PF | Max DD |","|---|---:|---:|---:|---:|---:|---:|"]
        for k in ("composite","momentum","random"):
            x=report["windows"][str(days)][k]["sequential_exec"]
            lines.append(f"| {k} | {x.get('n',0)} | {fmt(x.get('wr_pct'))}% | ${fmt(x.get('pnl_usd'))} | ${fmt(x.get('expectancy_usd'),4)} | {fmt(x.get('pf'),3)} | ${fmt(x.get('max_dd_usd'))} |")
        lines.append("")
    c365=report["windows"]["365"]["composite"]
    lines += ["## 365d composite attribution","", "### Side", "", "| Side | Trades | WR | PnL | PF |","|---|---:|---:|---:|---:|"]
    for s,x in c365["side"].items(): lines.append(f"| {s} | {x['n']} | {fmt(x['wr_pct'])}% | ${fmt(x['pnl_usd'])} | {fmt(x['pf'],3)} |")
    lines += ["","### Top pair contributions","","| Pair | PnL | Trades |","|---|---:|---:|"]
    for s,p,n in c365["pair_contribution"][:12]:lines.append(f"| {s} | ${fmt(p)} | {n} |")
    lines += ["","## Chronological blocks — composite sequential","","| Block | Trades | WR | PnL | PF | 6h net exp (independent-selected rows within block) |","|---|---:|---:|---:|---:|---:|"]
    for b,x in report["blocks_composite_sequential"].items():lines.append(f"| {b} | {x['n']} | {fmt(x['wr_pct'])}% | ${fmt(x['pnl_usd'])} | {fmt(x['pf'],3)} | ${fmt(x['h6'].get('net_expectancy_usd'),4)} |")
    lines += ["","## Coverage","",f"- Median eligible contracts/hour: **{fmt(report['coverage']['eligible_median'],1)}**",f"- Median liquid contracts/hour: **{fmt(report['coverage']['liquid_median'],1)}**",f"- Composite decision timestamps: **{report['coverage']['decision_timestamps']}**","",
              "## Frozen verdict", "", f"**{report['verdict']}**", "", report["verdict_reason"], "",
              "MH0 uses a survivorship-screened preregistered symbol list. Even a KEEP only earns a stricter delist-aware MH1; it never authorizes live trading."]
    path.write_text("\n".join(lines)+"\n")


def main():
    coverage={};data={}
    for i,s in enumerate(SYMBOLS,1):
        try:
            df=load_symbol(s)
            if len(df):
                data[s]=df;coverage[s]={"rows":len(df),"first":str(df.index[0]),"last":str(df.index[-1])}
                print(f"[{i}/{len(SYMBOLS)}] {s}: {len(df)}")
            else: coverage[s]={"rows":0,"error":"no/insufficient data"}
        except Exception as e:
            coverage[s]={"rows":0,"error":str(e)};print(f"[{i}] {s} ERROR {e}")
    if len(data)<10: raise RuntimeError(f"only {len(data)} usable symbols")
    sels=build_selections(data); ev=evaluate_all(sels,data)
    report={"protocol":"MH0","end_exclusive":str(END),"coverage_detail":coverage,"windows":{}}
    elig=[s.eligible_n for s in sels["composite"]];liq=[s.liquid_n for s in sels["composite"]]
    report["coverage"]={"requested_symbols":len(SYMBOLS),"usable_symbols":len(data),"decision_timestamps":len(sels["composite"]),
                        "eligible_median":float(np.median(elig)) if elig else None,"liquid_median":float(np.median(liq)) if liq else None}
    for d in (90,120,365):
        report["windows"][str(d)]={}
        for k in ("composite","momentum","random"):
            r=window(ev[k],d);seq=sequential(r)
            by_side,by_pair,contrib=attribution(seq)
            report["windows"][str(d)][k]={"independent_h1":horizon_stats(r,1),"independent_h3":horizon_stats(r,3),"independent_h6":horizon_stats(r,6),
                                                      "independent_exec":stats(r),"sequential_exec":stats(seq),"sequential_n":len(seq),
                                                      "side":by_side,"by_pair":by_pair,"pair_contribution":contrib}
    seq365=sequential(window(ev["composite"],365))
    report["blocks_composite_sequential"]=blocks(seq365,4)
    # Top3 is descriptive ranking-quality only.
    report["top3_365_h6"]=horizon_stats(window(ev["top3"],365),6)
    c=report["windows"]["365"]["composite"]
    h6=c["independent_h6"];ex=c["sequential_exec"]
    # Concentration guard: largest absolute positive pair contribution cannot exceed 50% of positive total.
    contrib=c["pair_contribution"];positive=sum(max(0,float(p)) for _,p,_ in contrib)
    largest=max([max(0,float(p)) for _,p,_ in contrib] or [0]);concentration=(largest/positive if positive>0 else 1.0)
    blocks_positive=sum(1 for x in report["blocks_composite_sequential"].values() if x["pnl_usd"]>0)
    pass_cond=(h6.get("net_expectancy_usd",-1)>0 and ex.get("expectancy_usd",-1)>0 and ex.get("pf",0)>1 and ex.get("pnl_usd",-1)>0 and concentration<=0.5 and blocks_positive>=3)
    report["verdict"]="KEEP_FOR_MH1" if pass_cond else "REJECT_MH0_LIVE_CANDIDATE"
    report["verdict_reason"]=("Composite passed the preregistered feasibility gates; proceed only to stricter historical-universe MH1 validation." if pass_cond else
                              f"Composite failed one or more preregistered feasibility gates (365d 6h net exp={h6.get('net_expectancy_usd')}, sequential exp={ex.get('expectancy_usd')}, PF={ex.get('pf')}, positive blocks={blocks_positive}/4, concentration={concentration:.3f}). No tuning follows automatically.")
    outj=ROOT/"MARKET_HUNTER_MH0_Result.json";outm=ROOT/"MARKET_HUNTER_MH0_Result.md";outc=ROOT/"MARKET_HUNTER_MH0_Top1.csv"
    outj.write_text(json.dumps(report,indent=2,allow_nan=False,default=str)+"\n")
    render(report,outm)
    pd.DataFrame(window(ev["composite"],365)).to_csv(outc,index=False)
    print(json.dumps({"verdict":report["verdict"],"coverage":report["coverage"],"365":report["windows"]["365"]["composite"]},indent=2,default=str))

if __name__=="__main__":main()
