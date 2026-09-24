#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_reset_winner_first_v1 as wf1

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_MTF_15M_RR1_V2"
COST_PCT=0.15
NOTIONAL=500.0
HOLD_5M=288

EXITS=((1.00,1.00),(1.25,1.00),(1.25,1.25),(1.50,1.00),(1.50,1.25),
       (1.50,1.50),(2.00,1.00),(2.00,1.25),(2.00,1.50),(2.00,2.00))
CONTEXTS=("LOC80","LOC65","H4_ABOVE","H4_UP","H1H4_UP")
PARTITIONS=(
 ("DEV_2023_2024",pd.Timestamp("2023-01-01",tz="UTC"),pd.Timestamp("2025-01-01",tz="UTC")),
 ("REF_2025",pd.Timestamp("2025-01-01",tz="UTC"),pd.Timestamp("2026-01-01",tz="UTC")),
 ("REF_2026",pd.Timestamp("2026-01-01",tz="UTC"),None),
)

def resample_complete(x5,rule,expected):
    z=x5.resample(rule,label="left",closed="left").agg(
      open=("open","first"),high=("high","max"),low=("low","min"),
      close=("close","last"),n=("close","count"))
    return z[z.n==expected].drop(columns=["n"]).dropna().copy()

def tr(df):
    pc=df.close.shift(1)
    return pd.concat([df.high-df.low,(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)

def build_features(x5):
    q=resample_complete(x5,"15min",3)
    h1=resample_complete(x5,"1h",12)
    h4=resample_complete(x5,"4h",48)

    for h in (h1,h4):
        h["ema20"]=h.close.ewm(span=20,adjust=False,min_periods=20).mean()
        h["ema_prev"]=h.ema20.shift(1)
        h["ema_up"]=h.ema20>h.ema_prev
        h["above20"]=h.close>=h.ema20

    h1["lo72"]=h1.low.rolling(72,min_periods=72).min()
    h1["hi72"]=h1.high.rolling(72,min_periods=72).max()
    h1["loc72"]=(h1.close-h1.lo72)/(h1.hi72-h1.lo72).replace(0,np.nan)

    c1=h1[["loc72","above20","ema_up"]].rename(columns={"above20":"h1_above","ema_up":"h1_up"}).copy()
    c1["avail1"]=c1.index+pd.Timedelta(hours=1)
    c4=h4[["above20","ema_up"]].rename(columns={"above20":"h4_above","ema_up":"h4_up"}).copy()
    c4["avail4"]=c4.index+pd.Timedelta(hours=4)

    q["bar_start"]=q.index
    q["signal_end"]=q.index+pd.Timedelta(minutes=15)
    q["rng"]=q.high-q.low
    q["close_loc"]=(q.close-q.low)/q.rng.replace(0,np.nan)
    q["body_abs"]=(q.close-q.open).abs()
    q["body_med20"]=q.body_abs.shift(1).rolling(20,min_periods=20).median()
    q["body_mult"]=q.body_abs/q.body_med20.replace(0,np.nan)
    q["atr20"]=tr(q).shift(1).rolling(20,min_periods=20).mean()
    q["bull"]=q.close>q.open
    q["prior4_high"]=q.high.shift(1).rolling(4,min_periods=4).max()
    q["prior4_low"]=q.low.shift(1).rolling(4,min_periods=4).min()
    q["prior4_range"]=q.high.shift(1).rolling(4,min_periods=4).max()-q.low.shift(1).rolling(4,min_periods=4).min()
    q["compression4"]=q.prior4_range/q.atr20.replace(0,np.nan)

    q=pd.merge_asof(q.reset_index(drop=True).sort_values("signal_end"),
                    c1.dropna().sort_values("avail1"),
                    left_on="signal_end",right_on="avail1",direction="backward")
    q=pd.merge_asof(q.sort_values("signal_end"),
                    c4.dropna().sort_values("avail4"),
                    left_on="signal_end",right_on="avail4",direction="backward")
    q.index=pd.DatetimeIndex(q.bar_start)
    return q.drop(columns=["bar_start"]).sort_index()

def build_masks(q):
    masks={}
    # Sweep-reclaim families.
    for lb in (4,8,12,24):
        prior_low=q.low.shift(1).rolling(lb,min_periods=lb).min()
        base=(q.low<prior_low)&(q.close>prior_low)
        depth=(prior_low-q.low)/q.atr20.replace(0,np.nan)
        for cl in (.55,.65,.75):
            for dep in (0.0,.10,.20):
                sr=base&(q.close_loc>=cl)&(depth>=dep)
                masks[("SR_ANY",lb,cl,dep)]=sr
                prev=sr.shift(1).fillna(False)
                masks[("SR_FOLLOW",lb,cl,dep)]=prev&q.bull&(q.close>q.high.shift(1))
                # Break above the 4-bar high that was already known at sweep close.
                pre_sweep_high=q.high.shift(2).rolling(4,min_periods=4).max()
                masks[("SR_BOS4",lb,cl,dep)]=prev&q.bull&(q.close>pre_sweep_high)

    # Breakout-displacement families.
    for lb in (8,12,24):
        ph=q.high.shift(1).rolling(lb,min_periods=lb).max()
        br=(q.close>ph)&q.bull
        for cl in (.65,.75):
            for bm in (1.25,1.50):
                masks[("BREAK_DISP",lb,cl,bm)]=br&(q.close_loc>=cl)&(q.body_mult>=bm)
                for comp in (2.0,2.5):
                    masks[("COMP_BREAK",lb,cl,bm*10+comp)]=(
                        br&(q.close_loc>=cl)&(q.body_mult>=bm)&(q.compression4<=comp)
                    )
    return masks

def ctx(q,name):
    if name=="LOC80": return q.loc72<=.80
    if name=="LOC65": return q.loc72<=.65
    if name=="H4_ABOVE": return (q.loc72<=.80)&q.h4_above.fillna(False)
    if name=="H4_UP": return (q.loc72<=.80)&q.h4_above.fillna(False)&q.h4_up.fillna(False)
    if name=="H1H4_UP":
        return (q.loc72<=.80)&q.h4_above.fillna(False)&q.h4_up.fillna(False)&q.h1_above.fillna(False)&q.h1_up.fillna(False)
    raise KeyError(name)

@dataclass
class Trade:
    signal_time:pd.Timestamp
    entry_time:pd.Timestamp
    exit_time:pd.Timestamp
    outcome:str
    gross_pct:float
    net_pct:float
    pnl_usd:float

def resolve(st,x5,tp_pct,sl_pct):
    idx=x5.index
    p=int(idx.searchsorted(st+pd.Timedelta(minutes=15)))
    if p>=len(idx) or idx[p] != st+pd.Timedelta(minutes=15): return None
    entry=float(x5.open.iloc[p])
    tp=entry*(1+tp_pct/100)
    sl=entry*(1-sl_pct/100)
    last=min(p+HOLD_5M-1,len(idx)-1)
    out="TIME"; ex=last; gross=(float(x5.close.iloc[last])/entry-1)*100
    hi=x5.high.astype(float).to_numpy(); lo=x5.low.astype(float).to_numpy()
    for j in range(p,last+1):
        ht=hi[j]>=tp; hs=lo[j]<=sl
        if ht and hs:
            out="SL_AMBIG"; ex=j; gross=-sl_pct; break
        if hs:
            out="SL"; ex=j; gross=-sl_pct; break
        if ht:
            out="TP"; ex=j; gross=tp_pct; break
    net=gross-COST_PCT
    return Trade(st,idx[p],idx[ex],out,gross,net,net/100*NOTIONAL)

def build_cache(times,x5):
    cache={}
    for st in times:
        for tp,sl in EXITS:
            z=resolve(st,x5,tp,sl)
            if z is not None: cache[(st,tp,sl)]=z
    return cache

def simulate(mask,q,tp,sl,cache):
    active=pd.Timestamp.min.tz_localize("UTC")
    out=[]
    for st in q.index[mask.fillna(False).to_numpy()]:
        et=st+pd.Timedelta(minutes=15)
        if et<=active: continue
        z=cache.get((st,tp,sl))
        if z is None: continue
        out.append(z); active=z.exit_time
    return out

def pf(pnls):
    a=np.asarray(pnls,float); pos=a[a>0].sum(); neg=-a[a<0].sum()
    return float(pos/neg) if neg>0 else (math.inf if pos>0 else np.nan)

def part_stats(trades,end_avail):
    rows=[]
    for name,start,end in PARTITIONS:
        stop=end if end is not None else end_avail
        z=[t for t in trades if start<=t.entry_time<stop]
        days=(stop-start).total_seconds()/86400
        n=len(z); w=sum(t.outcome=="TP" for t in z)
        pnls=[t.pnl_usd for t in z]; nets=[t.net_pct for t in z]
        rows.append(dict(partition=name,n=n,wr=w/n if n else np.nan,tpd=n/days,
                         exp=np.mean(nets) if nets else np.nan,pnl=np.sum(pnls) if pnls else 0.0,
                         pf=pf(pnls) if pnls else np.nan,timeouts=sum(t.outcome=="TIME" for t in z)))
    return rows

def main():
    wf1.v3.v1.base.fetch_one=wf1.v3.v1.fetch_one_with_volume
    x5,coverage=wf1.v3.v1.base.load5("SOLUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage:.6%}")
    x5=x5.sort_index()
    q=build_features(x5)
    masks=build_masks(q)
    contexts={c:ctx(q,c) for c in CONTEXTS}
    union=pd.Series(False,index=q.index)
    for m in masks.values(): union|=m.fillna(False)
    cache=build_cache(q.index[union.to_numpy()],x5)
    end_avail=min(pd.Timestamp("2026-09-24",tz="UTC"),x5.index[-1]+pd.Timedelta(minutes=5))

    rows=[]
    for key,m0 in masks.items():
        fam,p1,p2,p3=key
        for c in CONTEXTS:
            m=m0&contexts[c]
            for tp,sl in EXITS:
                trades=simulate(m,q,tp,sl,cache)
                ps=part_stats(trades,end_avail); by={x["partition"]:x for x in ps}
                if any(by[n]["n"]==0 for n,_,_ in PARTITIONS): continue
                minwr=min(by[n]["wr"] for n,_,_ in PARTITIONS)
                mintpd=min(by[n]["tpd"] for n,_,_ in PARTITIONS)
                minexp=min(by[n]["exp"] for n,_,_ in PARTITIONS)
                full=minwr>=.70 and mintpd>=1.0 and minexp>0
                ef=mintpd>=1.0 and minexp>0
                r=dict(family=fam,p1=p1,p2=p2,p3=p3,context=c,tp_pct=tp,sl_pct=sl,rr=tp/sl,
                       min_wr=minwr,min_tpd=mintpd,min_exp=minexp,full_pass=full,econ_freq_pass=ef)
                for z in ps:
                    pref=z["partition"].replace("DEV_","D_").replace("REF_","R_")
                    for k,v in z.items():
                        if k!="partition": r[f"{pref}_{k}"]=v
                rows.append(r)

    out=pd.DataFrame(rows).sort_values(
      ["full_pass","econ_freq_pass","min_wr","min_exp","min_tpd"],
      ascending=[False,False,False,False,False]).reset_index(drop=True)
    full=out[out.full_pass].copy()
    ef=out[out.econ_freq_pass].copy()
    out.to_csv(ROOT/f"{PFX}_Grid.csv",index=False)
    full.to_csv(ROOT/f"{PFX}_FullPass.csv",index=False)
    ef.head(100).to_csv(ROOT/f"{PFX}_EconFreq.csv",index=False)

    lines=[
      "# SOL MTF 15M RR>=1 V2 — Result","",
      f"- coverage: **{coverage*100:.5f}%**",
      f"- complete 15m bars: **{len(q):,}**",
      f"- structural masks: **{len(masks):,}**",
      f"- tested configs: **{len(out):,}**",
      f"- full passes: **{len(full):,}**",
      f"- >=1/day + positive net expectancy all partitions: **{len(ef):,}**","",
      "Target: **WR>=70%, >=1/day, TP>=1%, RR>=1, net expectancy>0 in every partition.**","",
      "## Top 25","",
      "|#|Family|Params|Context|TP/SL|RR|DEV WR/tpd/exp|2025 WR/tpd/exp|2026 WR/tpd/exp|Min WR|PASS|",
      "|---:|---|---|---|---|---:|---|---|---|---:|---|"]
    for i,r in out.head(25).iterrows():
        lines.append(
          f"|{i+1}|{r.family}|{r.p1}/{r.p2:.2f}/{r.p3:.2f}|{r.context}|{r.tp_pct:.2f}/{r.sl_pct:.2f}|{r.rr:.2f}|"
          f"{r.D_2023_2024_wr*100:.1f}%/{r.D_2023_2024_tpd:.2f}/{r.D_2023_2024_exp:.3f}%|"
          f"{r.R_2025_wr*100:.1f}%/{r.R_2025_tpd:.2f}/{r.R_2025_exp:.3f}%|"
          f"{r.R_2026_wr*100:.1f}%/{r.R_2026_tpd:.2f}/{r.R_2026_exp:.3f}%|"
          f"{r.min_wr*100:.1f}%|{'YES' if r.full_pass else 'NO'}|")
    if len(full):
        b=full.iloc[0]; verdict="FULL_TARGET_PASS_FOUND"
        lines += ["","## Best full pass","",
          f"{b.family} params={b.p1}/{b.p2:.2f}/{b.p3:.2f}, context={b.context}, TP/SL={b.tp_pct:.2f}/{b.sl_pct:.2f}, "
          f"min WR={b.min_wr*100:.2f}%, min frequency={b.min_tpd:.3f}/day, min net exp={b.min_exp:.4f}%."]
    else:
        b=out.iloc[0]; verdict="NO_FULL_PASS_RR1_V2"
        lines += ["","## Frontier","",
          f"Best robust ordering: {b.family} params={b.p1}/{b.p2:.2f}/{b.p3:.2f}, context={b.context}, TP/SL={b.tp_pct:.2f}/{b.sl_pct:.2f}, "
          f"min WR={b.min_wr*100:.2f}%, min frequency={b.min_tpd:.3f}/day, min net exp={b.min_exp:.4f}%."]
        if len(ef):
            e=ef.iloc[0]
            lines += [f"Best >=1/day + positive-economics candidate: {e.family}, TP/SL={e.tp_pct:.2f}/{e.sl_pct:.2f}, "
                      f"min WR={e.min_wr*100:.2f}%, min frequency={e.min_tpd:.3f}/day, min net exp={e.min_exp:.4f}%."]
    lines += ["",f"# VERDICT: {verdict}"]
    txt="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(txt,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n",encoding="utf-8")
    print(txt)

if __name__=="__main__":
    main()
