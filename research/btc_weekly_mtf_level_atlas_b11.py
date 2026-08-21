#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd

import btc_h1_low_reject_structure_lr1 as dataio

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_Result.md"
OUT_JSON = ROOT / "BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_Result.json"
OUT_SEL = ROOT / "BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_Selected.csv"
OUT_RULES = ROOT / "BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_Rules.csv"
OUT_ATLAS = ROOT / "BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_Atlas.csv"

FEE = 0.0015
FAV = 0.0115
ADV = 0.0085
LOAD0 = pd.Timestamp("2019-09-01", tz="UTC")
EXT0 = pd.Timestamp("2020-01-01", tz="UTC")
EXT1 = pd.Timestamp("2022-01-01", tz="UTC")
DEV0 = pd.Timestamp("2022-01-01", tz="UTC")
DEV1 = pd.Timestamp("2025-01-01", tz="UTC")
VAL0 = pd.Timestamp("2025-01-01", tz="UTC")
VAL1 = pd.Timestamp("2026-07-30", tz="UTC")
AUG0 = pd.Timestamp("2026-08-01", tz="UTC")
AUG1 = pd.Timestamp("2026-08-20", tz="UTC")
SCAN_CUTOFF_DAYS = 5
SCAN_CUTOFF_HOUR = 12
SOURCE_TFS = ["H1", "H4", "D1", "W1"]
MODES = ["HOLD", "RECLAIM", "BODY", "WICK"]
FAMILIES = [
    "PREV_HIGH", "PREV_LOW", "PREV_OPEN",
    "R3_HIGH", "R3_LOW", "R6_HIGH", "R6_LOW", "R12_HIGH", "R12_LOW",
    "SWING2_HIGH", "SWING2_LOW",
]


def as_utc(v):
    t = pd.Timestamp(v)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def week_start(ts):
    t = as_utc(ts)
    d = t.floor("D")
    return d - pd.Timedelta(days=t.weekday())


def week_key(w):
    i = as_utc(w).isocalendar()
    return f"{int(i.year):04d}-W{int(i.week):02d}"


def complete_weeks(start, end_exclusive):
    start = as_utc(start); end = as_utc(end_exclusive)
    first = start.floor("D") - pd.Timedelta(days=start.weekday())
    if first < start:
        first += pd.Timedelta(days=7)
    out=[]; w=first
    while w + pd.Timedelta(days=7) <= end:
        out.append(w); w += pd.Timedelta(days=7)
    return out


def load_h1():
    # Add 2019 prehistory so W1/D1 levels entering 2020 are causal rather than truncated.
    base = "https://data.binance.vision/data/futures/um"
    urls=[]
    cur=pd.Timestamp("2019-09-01", tz="UTC")
    while cur < pd.Timestamp("2026-08-01", tz="UTC"):
        ym=cur.strftime("%Y-%m")
        urls.append(f"{base}/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-{ym}.zip")
        cur += pd.offsets.MonthBegin(1)
    d=pd.Timestamp("2026-08-01", tz="UTC")
    while d < AUG1:
        ds=d.strftime("%Y-%m-%d")
        urls.append(f"{base}/daily/klines/BTCUSDT/1h/BTCUSDT-1h-{ds}.zip")
        d += pd.Timedelta(days=1)

    from concurrent.futures import ThreadPoolExecutor, as_completed
    rows=[]
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs=[ex.submit(dataio.fetch_zip,u) for u in urls]
        for n,f in enumerate(as_completed(futs),1):
            rows.extend(f.result())
            if n % 10 == 0:
                print(f"downloaded {n}/{len(urls)} archives")
    if not rows:
        raise RuntimeError("no H1 data")
    x=pd.DataFrame(rows,columns=["ts","open","high","low","close"])
    x["ts"]=pd.to_datetime(pd.to_numeric(x.ts),unit="ms",utc=True)
    x=x.dropna().drop_duplicates("ts").sort_values("ts")
    x=x[(x.ts>=LOAD0)&(x.ts<AUG1)].set_index("ts")
    return x[["open","high","low","close"]].astype(float)


def source_bars(h1, tf):
    if tf == "H1":
        return h1.copy()
    if tf == "H4":
        return h1.resample("4h", origin="start_day", label="left", closed="left").agg(
            {"open":"first","high":"max","low":"min","close":"last"}).dropna()
    if tf == "D1":
        return h1.resample("1D", label="left", closed="left").agg(
            {"open":"first","high":"max","low":"min","close":"last"}).dropna()
    if tf == "W1":
        keys=pd.Series([week_start(t) for t in h1.index],index=h1.index)
        z=h1.groupby(keys).agg({"open":"first","high":"max","low":"min","close":"last"})
        z.index=pd.DatetimeIndex(z.index)
        return z.sort_index()
    raise ValueError(tf)


def rolling_extreme_with_id(src, n, field, kind):
    vals=np.full(len(src),np.nan,dtype=float)
    ids=np.empty(len(src),dtype=object); ids[:] = None
    a=src[field].to_numpy(float)
    idx=src.index
    for i in range(n,len(src)):
        w=a[i-n:i]
        j=int(np.argmax(w) if kind=="HIGH" else np.argmin(w))
        p=i-n+j
        vals[i]=float(a[p])
        ids[i]=f"{idx[p].isoformat()}"
    return pd.Series(vals,index=src.index),pd.Series(ids,index=src.index,dtype=object)


def swing2_state(src, kind):
    vals=np.full(len(src),np.nan,dtype=float)
    ids=np.empty(len(src),dtype=object); ids[:] = None
    a=src["high" if kind=="HIGH" else "low"].to_numpy(float)
    events={}
    for j in range(2,len(src)-2):
        left=a[j-2:j]; right=a[j+1:j+3]
        ok=(a[j]>left.max() and a[j]>=right.max()) if kind=="HIGH" else (a[j]<left.min() and a[j]<=right.min())
        if ok and j+3 < len(src):
            events[j+3]=(float(a[j]),f"{src.index[j].isoformat()}")
    lastv=np.nan; lastid=None
    for i in range(len(src)):
        if i in events:
            lastv,lastid=events[i]
        vals[i]=lastv; ids[i]=lastid
    return pd.Series(vals,index=src.index),pd.Series(ids,index=src.index,dtype=object)


def build_source_levels(src, tf):
    out={}
    prev_idx=pd.Series(src.index,index=src.index).shift(1)
    for field,name in [("high","PREV_HIGH"),("low","PREV_LOW"),("open","PREV_OPEN")]:
        out[name]=(src[field].shift(1),prev_idx.map(lambda x: x.isoformat() if pd.notna(x) else None))
    for n in (3,6,12):
        for kind,field in [("HIGH","high"),("LOW","low")]:
            out[f"R{n}_{kind}"]=rolling_extreme_with_id(src,n,field,kind)
    for kind in ("HIGH","LOW"):
        out[f"SWING2_{kind}"]=swing2_state(src,kind)
    return out


def map_level_to_h1(h1_index, s, sid):
    # Source state at timestamp t is information known at the start of that source bar.
    v=s.reindex(h1_index,method="ffill")
    q=sid.reindex(h1_index,method="ffill")
    return v.to_numpy(float),q.to_numpy(object)


def add_atr(h1):
    z=h1.copy()
    pc=z.close.shift(1)
    tr=pd.concat([z.high-z.low,(z.high-pc).abs(),(z.low-pc).abs()],axis=1).max(axis=1)
    z["atr14"]=tr.rolling(14,min_periods=14).mean()
    return z


def confirmation_mask(mode, side, o,h,l,c,level,atr):
    finite=np.isfinite(level)&np.isfinite(atr)&(atr>0)
    near=np.abs(c-level)<=0.75*atr
    body=np.abs(c-o)
    lower=np.maximum(0.0,np.minimum(o,c)-l)
    upper=np.maximum(0.0,h-np.maximum(o,c))
    if side=="LONG":
        hold=(l<=level)&(c>=level)
        if mode=="HOLD": extra=np.ones(len(c),dtype=bool)
        elif mode=="RECLAIM": extra=l<level
        elif mode=="BODY": extra=c>o
        elif mode=="WICK": extra=lower>=0.5*np.maximum(body,1e-12)
        else: raise ValueError(mode)
    else:
        hold=(h>=level)&(c<=level)
        if mode=="HOLD": extra=np.ones(len(c),dtype=bool)
        elif mode=="RECLAIM": extra=h>level
        elif mode=="BODY": extra=c<o
        elif mode=="WICK": extra=upper>=0.5*np.maximum(body,1e-12)
        else: raise ValueError(mode)
    return finite&near&hold&extra


def execution_engine(h1):
    idx=h1.index
    op=h1.open.to_numpy(float); hi=h1.high.to_numpy(float); lo=h1.low.to_numpy(float); cl=h1.close.to_numpy(float)
    cache={}
    def run(signal_i,side):
        key=(int(signal_i),side)
        if key in cache: return cache[key]
        ei=int(signal_i)+1
        if ei>=len(h1): return None
        ets=idx[ei]; w=week_start(ets); wend=w+pd.Timedelta(days=7)
        if not (w<=ets<wend): return None
        stop=int(idx.searchsorted(wend,side="left"))
        if stop<=ei: return None
        entry=float(op[ei])
        if side=="LONG": tp=entry*(1+FAV); sl=entry*(1-ADV)
        else: tp=entry*(1-FAV); sl=entry*(1+ADV)
        reason="TIME"; px=float(cl[stop-1]); xi=stop-1
        for j in range(ei,stop):
            if side=="LONG": hit_sl=lo[j]<=sl; hit_tp=hi[j]>=tp
            else: hit_sl=hi[j]>=sl; hit_tp=lo[j]<=tp
            if hit_sl:
                reason="SL"; px=sl; xi=j; break
            if hit_tp:
                reason="TP"; px=tp; xi=j; break
        gross=(px/entry-1.0)*(1.0 if side=="LONG" else -1.0)
        r={"entry_ts":ets,"exit_ts":idx[xi],"entry":entry,"tp":tp,"sl":sl,
           "reason":reason,"net_ret":gross-FEE,"hours":int(xi-ei+1)}
        cache[key]=r
        return r
    return run


def generate_candidates(h1, levels):
    z=add_atr(h1)
    idx=z.index
    o=z.open.to_numpy(float); h=z.high.to_numpy(float); l=z.low.to_numpy(float); c=z.close.to_numpy(float); atr=z.atr14.to_numpy(float)
    execute=execution_engine(z)
    rows=[]
    for tf,fams in levels.items():
        print(f"candidate atlas {tf}")
        for family,(s,sid) in fams.items():
            level,inst=map_level_to_h1(idx,s,sid)
            valid_inst=np.array([x is not None and str(x)!="nan" for x in inst],dtype=bool)
            for side in ("LONG","SHORT"):
                stype="SUPPORT" if side=="LONG" else "RESISTANCE"
                for mode in MODES:
                    mask=confirmation_mask(mode,side,o,h,l,c,level,atr)&valid_inst
                    inds=np.flatnonzero(mask)
                    seen=set()
                    rule=f"{tf}|{family}|{stype}|{mode}"
                    for i in inds:
                        instance=f"{tf}|{family}|{inst[i]}"
                        if instance in seen:
                            continue
                        seen.add(instance)
                        tr=execute(int(i),side)
                        if tr is None: continue
                        rows.append({
                            "rule":rule,"source_tf":tf,"family":family,"side_type":stype,"mode":mode,
                            "signal_i":int(i),"signal_ts":idx[i],"side":side,"level":float(level[i]),"instance":instance,
                            "week":week_key(week_start(idx[i])),**tr,
                        })
    q=pd.DataFrame(rows)
    if q.empty: raise RuntimeError("no level candidates")
    return q.sort_values(["signal_ts","rule"]).reset_index(drop=True)


def in_scan_window(ts):
    w=week_start(ts); cutoff=w+pd.Timedelta(days=SCAN_CUTOFF_DAYS,hours=SCAN_CUTOFF_HOUR)
    return w<=ts<=cutoff


def partition_weeks(name):
    if name=="external": return complete_weeks(EXT0,EXT1)
    if name=="development": return complete_weeks(DEV0,DEV1)
    if name=="reference_validation": return complete_weeks(VAL0,VAL1)
    if name=="august": return complete_weeks(AUG0,AUG1)
    raise ValueError(name)


def week_set(weeks): return {week_key(w) for w in weeks}


def route_rule(cand,rule,weeks):
    ws=week_set(weeks)
    q=cand[(cand.rule==rule)&cand.week.isin(ws)&cand.signal_ts.map(in_scan_window)].copy()
    if q.empty: return q
    q=q.sort_values(["signal_ts"]).groupby("week",as_index=False).head(1).copy()
    q["route"]="PRIMARY_RULE"
    return q.sort_values("signal_ts").reset_index(drop=True)


def stat(q,weeks):
    nweek=len(weeks)
    if q.empty:
        return {"weeks":nweek,"n":0,"coverage":0.0,"tp":0,"sl":0,"time":0,"wr":None,"exp":None,"pf":None,"max_ls":0,"wilson":0.0}
    win=(q.reason=="TP").to_numpy(bool)
    a=q.net_ret.to_numpy(float)
    gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    streak=mx=0
    for v in win:
        if not v: streak+=1; mx=max(mx,streak)
        else: streak=0
    return {"weeks":nweek,"n":int(len(q)),"coverage":float(q.week.nunique()/nweek) if nweek else 0.0,
            "tp":int((q.reason=="TP").sum()),"sl":int((q.reason=="SL").sum()),"time":int((q.reason=="TIME").sum()),
            "wr":float(win.mean()),"exp":float(a.mean()),"pf":float(gp/gl) if gl>0 else (999.0 if gp>0 else 0.0),
            "max_ls":int(mx),"wilson":wilson(int(win.sum()),len(win))}


def wilson(w,n,z=1.96):
    if n<=0:return 0.0
    p=w/n; den=1+z*z/n
    cen=p+z*z/(2*n); adj=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)
    return float((cen-adj)/den)


def block_stats(q,weeks):
    if not weeks:return []
    arr=list(weeks); edges=np.linspace(0,len(arr),5,dtype=int); out=[]
    for j in range(4):
        ww=arr[edges[j]:edges[j+1]]; keys=week_set(ww); sub=q[q.week.isin(keys)] if not q.empty else q
        out.append(stat(sub,ww))
    return out


def rank_development_rules(cand,dev_weeks):
    rules=sorted(cand.rule.unique())
    rows=[]
    for rule in rules:
        q=route_rule(cand,rule,dev_weeks); s=stat(q,dev_weeks)
        parts=rule.split("|")
        rows.append({"rule":rule,"source_tf":parts[0],"family":parts[1],"side_type":parts[2],"mode":parts[3],**s})
    r=pd.DataFrame(rows)
    r["fullcov"]=(r.coverage>=1.0-1e-12).astype(int)
    r["wr_sort"]=r.wr.fillna(-1.0); r["pf_sort"]=r.pf.fillna(-1.0)
    r=r.sort_values(["fullcov","wr_sort","wilson","pf_sort","n","rule"],ascending=[False,False,False,False,False,True]).reset_index(drop=True)
    r["rank"]=np.arange(1,len(r)+1)
    return r


def top4_distinct(ranks):
    out=[]; seen=set()
    for _,r in ranks.iterrows():
        pair=(r.source_tf,r.family)
        if pair in seen: continue
        seen.add(pair); out.append(r.rule)
        if len(out)==4: break
    return out


def route_top4(cand,rules,weeks):
    ws=week_set(weeks); rank={r:i for i,r in enumerate(rules)}
    q=cand[cand.rule.isin(rules)&cand.week.isin(ws)&cand.signal_ts.map(in_scan_window)].copy()
    if q.empty:return q
    q["router_rank"]=q.rule.map(rank).astype(int)
    q=q.sort_values(["signal_ts","router_rank","rule"])
    q=q.groupby("week",as_index=False).head(1).copy(); q["route"]="TOP4_ROUTER"
    return q.sort_values("signal_ts").reset_index(drop=True)


def atlas_summary(cand):
    q=cand[cand.signal_ts.map(in_scan_window)].copy()
    rows=[]
    for (tf,fam,mode),g in q.groupby(["source_tf","family","mode"]):
        raw_wr=float((g.reason=="TP").mean()) if len(g) else None
        for part in ("development","external","reference_validation"):
            weeks=partition_weeks(part); ws=week_set(weeks); x=g[g.week.isin(ws)].sort_values("signal_ts")
            routed=x.groupby("week",as_index=False).head(1) if len(x) else x
            s=stat(routed,weeks)
            rows.append({"source_tf":tf,"family":fam,"mode":mode,"partition":part,
                         "candidate_n":int(len(x)),"raw_candidate_wr":float((x.reason=="TP").mean()) if len(x) else None,
                         "long_n":int((x.side=="LONG").sum()) if len(x) else 0,"short_n":int((x.side=="SHORT").sum()) if len(x) else 0,
                         "median_hours":float(x.hours.median()) if len(x) else None,
                         "weekly_coverage":s["coverage"],"weekly_wr":s["wr"]})
    return pd.DataFrame(rows)


def gate(s,blocks,weeks,wrmin):
    return (s["n"]==len(weeks) and abs(s["coverage"]-1.0)<1e-12 and s["wr"] is not None and s["wr"]>=wrmin
            and s["exp"] is not None and s["exp"]>0 and s["pf"] is not None and s["pf"]>1
            and (s["max_ls"]==0 if wrmin>=1.0 else s["max_ls"]<=2)
            and sum(1 for b in blocks if b["exp"] is not None and b["exp"]>0) >= (4 if wrmin>=1.0 else 3))


def fmtpct(v): return "-" if v is None or (isinstance(v,float) and not np.isfinite(v)) else f"{100*float(v):.2f}%"

def fmtn(v,n=3): return "-" if v is None or (isinstance(v,float) and not np.isfinite(v)) else f"{float(v):.{n}f}"


def main():
    h1=load_h1(); print(f"H1 {h1.index.min()} -> {h1.index.max()} rows={len(h1)}")
    levels={}
    for tf in SOURCE_TFS:
        src=source_bars(h1,tf)
        levels[tf]=build_source_levels(src,tf)
        print(tf,len(src),len(levels[tf]))

    cand=generate_candidates(h1,levels)
    # Evaluation starts 2020; pre-2020 candidates were still needed to consume stale first touches.
    cand_eval=cand[cand.signal_ts>=EXT0].copy()
    dev_weeks=partition_weeks("development")
    ranks=rank_development_rules(cand_eval,dev_weeks)
    primary=str(ranks.iloc[0].rule)
    top4=top4_distinct(ranks)
    ranks.to_csv(OUT_RULES,index=False)

    atlas=atlas_summary(cand_eval); atlas.to_csv(OUT_ATLAS,index=False)
    selected=[]; summary={}
    for selector in ("PRIMARY_RULE","TOP4_ROUTER"):
        summary[selector]={}
        for part in ("development","external","reference_validation","august"):
            weeks=partition_weeks(part)
            q=route_rule(cand_eval,primary,weeks) if selector=="PRIMARY_RULE" else route_top4(cand_eval,top4,weeks)
            if not q.empty:
                q=q.copy(); q["selector"]=selector; q["partition"]=part; selected.append(q)
            s=stat(q,weeks); bs=block_stats(q,weeks)
            summary[selector][part]={"stat":s,"blocks":bs}

    extw=partition_weeks("external"); valw=partition_weeks("reference_validation")
    robust=False; highp=False; passing=None
    for selector in ("PRIMARY_RULE","TOP4_ROUTER"):
        es=summary[selector]["external"]; vs=summary[selector]["reference_validation"]
        if gate(es["stat"],es["blocks"],extw,1.0) and gate(vs["stat"],vs["blocks"],valw,1.0):
            robust=True; passing=selector
        if gate(es["stat"],es["blocks"],extw,0.80) and gate(vs["stat"],vs["blocks"],valw,0.80): highp=True

    sel=pd.concat(selected,ignore_index=True) if selected else pd.DataFrame()
    if not sel.empty: sel.to_csv(OUT_SEL,index=False)

    result={
        "experiment":"B11_MTF_LEVEL_ATLAS","coverage":{"first":str(h1.index.min()),"last":str(h1.index.max()),"h1_rows":int(len(h1))},
        "primary_rule":primary,"top4_router":top4,"development_top10":ranks.head(10).replace({np.nan:None}).to_dict("records"),
        "selectors":summary,"gates":{"B11_ROBUST_WEEKLY_100":"PASS" if robust else "FAIL","B11_HIGH_PRECISION_WEEKLY":"PASS" if highp else "FAIL","passing_selector":passing},
        "live_bbc_untouched":True,
    }
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding="utf-8")

    md=["# BTC Weekly MTF Level Atlas B11 — Result","",
        f"**Verdict: {'B11_ROBUST_WEEKLY_100_PASS' if robust else 'B11_NO_ROBUST_WEEKLY_100'}**","",
        f"Coverage **{h1.index.min()} -> {h1.index.max()}**, official Binance BTCUSDT H1 rows **{len(h1):,}** (includes 2019 prehistory for causal level state).","",
        "Execution: level signal on completed H1; next-H1-open; net target +1.00%; net loss -1.00%; fee 0.15%; adverse-first; same-week exit.","",
        f"Frozen development PRIMARY_RULE: **{primary}**","",
        "Frozen development TOP4_ROUTER:"]
    md += [f"- {i+1}. `{r}`" for i,r in enumerate(top4)]
    md += ["","## Selected-rule performance","",
           "| Selector | Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |","|---|---|---:|---:|---:|---:|---:|---:|"]
    for selector in ("PRIMARY_RULE","TOP4_ROUTER"):
        for part in ("development","external","reference_validation","august"):
            s=summary[selector][part]["stat"]
            md.append(f"| {selector} | {part} | {s['weeks']}/{s['n']}/{fmtpct(s['coverage'])} | {s['tp']}/{s['sl']}/{s['time']} | {fmtpct(s['wr'])} | {fmtpct(s['exp'])} | {fmtn(s['pf'])} | {s['max_ls']} |")
    md += ["","## Development top 10 frozen rule ranking","",
           "| Rank | Rule | Coverage | WR | Wilson LB | PF | N |","|---:|---|---:|---:|---:|---:|---:|"]
    for _,r in ranks.head(10).iterrows():
        md.append(f"| {int(r['rank'])} | `{r.rule}` | {fmtpct(r.coverage)} | {fmtpct(r.wr)} | {fmtpct(r.wilson)} | {fmtn(r.pf)} | {int(r.n)} |")
    md += ["","## Gates","",f"- B11_ROBUST_WEEKLY_100: **{'PASS' if robust else 'FAIL'}**",f"- B11_HIGH_PRECISION_WEEKLY: **{'PASS' if highp else 'FAIL'}**","",
           "No post-result atlas row is promoted. Atlas diagnostics are persisted separately for follow-up preregistration only.","","Live BBC untouched."]
    OUT_MD.write_text("\n".join(md)+"\n",encoding="utf-8")
    print("\n".join(md))

if __name__=="__main__":
    main()
