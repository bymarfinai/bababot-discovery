#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import math
import numpy as np
import pandas as pd
import requests

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as b38s1
import bnb_b38_s3_adaptive_execution as b38s3

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/"forward"/"bnb_b38_s6"
OUT.mkdir(parents=True,exist_ok=True)

SEED=OUT/"BNB_B38_S6_HistoricalSeed5m.csv.gz"
TAIL=OUT/"BNB_B38_S6_BridgeForward5m.csv.gz"
LEDGER=OUT/"BNB_B38_S6_ProspectiveLedger.csv"
STATUS=OUT/"BNB_B38_S6_Status.md"
SUMMARY=OUT/"BNB_B38_S6_ByMode.csv"
AUDIT=OUT/"BNB_B38_S6_RunAudit.json"
MANIFEST=ROOT/"results"/"bnb_b38_s5"/"BNB_B38_S5_ADAPTIVE_POLICY_ForwardManifest.csv"

FREEZE=pd.Timestamp("2026-09-20T06:30:00Z")
START_HISTORY=pd.Timestamp("2022-01-01T00:00:00Z")
STEP=pd.Timedelta(minutes=5)
BASE_URLS=[
    "https://fapi.binance.com/fapi/v1/klines",
    "https://www.binance.com/fapi/v1/klines",
]
SYMBOL="BNBUSDT"
MODE_POLICY={
    "IMMEDIATE_CLEAN_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "IMMEDIATE_SWEEP_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "DELAYED_CLEAN_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "DELAYED_SWEEP_RECLAIM":("TP2","tp2_level","tp2_rr"),
}
IMMUTABLE_ENTRY_FIELDS=[
    "zone_id","first_touch_ts","first_touch_archetype","execution_mode",
    "entry_ts","entry_price","sl_reference","selected_target","target_level","target_rr"
]

def utc_now():
    return pd.Timestamp(datetime.now(timezone.utc))

def latest_complete_close(now=None):
    now=utc_now() if now is None else pd.Timestamp(now)
    return now.floor("5min")

def request_chunk(start_open,end_open):
    params={
        "symbol":SYMBOL,"interval":"5m",
        "startTime":int(start_open.timestamp()*1000),
        "endTime":int(end_open.timestamp()*1000)-1,
        "limit":1500,
    }
    errs=[]
    for url in BASE_URLS:
        try:
            r=requests.get(url,params=params,timeout=45,headers={"User-Agent":"bababot-b38-s6/1.0"})
            if r.status_code!=200:
                errs.append(f"{url} HTTP{r.status_code} {r.text[:120]}")
                continue
            data=r.json()
            if not isinstance(data,list):
                errs.append(f"{url} non-list")
                continue
            return data
        except Exception as exc:
            errs.append(f"{url} {type(exc).__name__}:{exc}")
    raise RuntimeError("Binance request failed: "+" | ".join(errs))

def fetch_completed_5m(start_open,end_open):
    if end_open<=start_open:
        return pd.DataFrame(columns=["open","high","low","close"])
    rows=[]; cur=start_open
    while cur<end_open:
        data=request_chunk(cur,end_open)
        if not data: break
        rows.extend(data)
        last=pd.to_datetime(int(data[-1][0]),unit="ms",utc=True)
        nxt=last+STEP
        if nxt<=cur:
            raise RuntimeError("pagination failed to advance")
        cur=nxt
        if len(data)<1500: break
    if not rows:
        return pd.DataFrame(columns=["open","high","low","close"])
    z=pd.DataFrame(rows)
    open_ts=pd.to_datetime(pd.to_numeric(z.iloc[:,0]),unit="ms",utc=True)
    out=pd.DataFrame({
        "ts":open_ts+STEP,
        "open":pd.to_numeric(z.iloc[:,1],errors="coerce"),
        "high":pd.to_numeric(z.iloc[:,2],errors="coerce"),
        "low":pd.to_numeric(z.iloc[:,3],errors="coerce"),
        "close":pd.to_numeric(z.iloc[:,4],errors="coerce"),
    }).dropna()
    out=out.drop_duplicates("ts",keep="last").sort_values("ts")
    out=out[out.ts<=end_open].copy()
    return out.set_index("ts")[["open","high","low","close"]].astype(float)

def read_ohlc(path):
    if not path.exists():
        return pd.DataFrame(columns=["open","high","low","close"],index=pd.DatetimeIndex([],tz="UTC",name="ts"))
    q=pd.read_csv(path,compression="gzip")
    q["ts"]=pd.to_datetime(q.ts,utc=True)
    return q.set_index("ts")[["open","high","low","close"]].astype(float).sort_index()

def write_ohlc(q,path):
    z=q.reset_index()
    if z.columns[0]!="ts": z=z.rename(columns={z.columns[0]:"ts"})
    z.to_csv(path,index=False,compression="gzip")

def build_market_cache():
    created_seed=False
    if not SEED.exists():
        seed,diag=b31.load_raw()
        if diag["coverage"]<.995:
            raise RuntimeError(f"seed coverage low {diag}")
        write_ohlc(seed,SEED)
        created_seed=True
    seed=read_ohlc(SEED)
    if seed.empty: raise RuntimeError("empty historical seed")

    tail=read_ohlc(TAIL)
    last_close=tail.index.max() if len(tail) else seed.index.max()
    end_close=latest_complete_close()
    # Next Binance open begins exactly at the previous close timestamp.
    fresh=fetch_completed_5m(last_close,end_close)
    if len(fresh):
        if len(tail):
            tail=pd.concat([tail,fresh]).sort_index()
        else:
            tail=fresh.copy()
        tail=tail[~tail.index.duplicated(keep="last")]
        tail=tail[tail.index>seed.index.max()].copy()
        write_ohlc(tail,TAIL)
    elif not TAIL.exists():
        write_ohlc(tail,TAIL)

    combined=pd.concat([seed,tail]).sort_index()
    combined=combined[~combined.index.duplicated(keep="last")]
    diffs=combined.index.to_series().diff().dropna()
    bad=diffs[diffs!=STEP]
    if len(bad):
        # Only enforce continuity from the final 7 days of seed onward, where forward state depends on the join.
        cutoff=seed.index.max()-pd.Timedelta(days=7)
        bad2=bad[bad.index>=cutoff]
        if len(bad2):
            raise RuntimeError(f"5m cache discontinuity near bridge: {bad2.head().to_dict()}")
    return combined,created_seed,end_close

def verify_manifest():
    if not MANIFEST.exists():
        raise RuntimeError("S5 forward manifest missing")
    m=pd.read_csv(MANIFEST).iloc[0]
    if str(m["identity"])!="BNB_B38_S5_ADAPTIVE_POLICY_V1":
        raise RuntimeError("unexpected S5 identity")
    if pd.Timestamp(m["freeze_timestamp_utc"])!=FREEZE:
        raise RuntimeError("freeze timestamp mismatch")
    expect={
        "immediate_clean_target":"TP1",
        "immediate_sweep_target":"TP1",
        "delayed_clean_target":"TP1",
        "delayed_sweep_target":"TP2",
        "missing_required_target_action":"NO_POLICY_TARGET",
    }
    for k,v in expect.items():
        if str(m[k])!=v: raise RuntimeError(f"manifest mismatch {k}")

def rebuild_plans(raw,latest):
    # Reuse exact frozen B38 algorithms, extending only their data horizon.
    b38s1.START=START_HISTORY
    b38s1.END=latest
    b38s3.END=latest

    h1=b38s1.exact_exec(raw,"1h",12)
    m15=b38s1.exact_exec(raw,"15min",3)
    h1=h1[h1.index<=latest].copy()
    m15=m15[m15.index<=latest].copy()

    zones=b38s1.demand_zones(h1)
    fam=b38s1.visual_family(m15,zones)
    fam=fam[(pd.to_datetime(fam.first_touch_ts,utc=True)>=START_HISTORY)&
            (pd.to_datetime(fam.first_touch_ts,utc=True)<=latest)].copy()

    # Frozen development parity remains mandatory.
    dev=fam[pd.to_datetime(fam.first_touch_ts,utc=True)<=pd.Timestamp("2024-12-31T23:59:59Z")]
    if len(dev)!=788:
        raise RuntimeError(f"B38 parent parity drift: {len(dev)} != 788")

    P=b38s3.adaptive_plan(m15,h1,fam)
    devp=P[pd.to_datetime(P.first_touch_ts,utc=True)<=pd.Timestamp("2024-12-31T23:59:59Z")]
    dc=devp.execution_status.value_counts().to_dict()
    if len(devp)!=788 or dc.get("ENTRY",0)!=690 or dc.get("CANCELLED_DEMAND_ACCEPTANCE",0)!=98:
        raise RuntimeError(f"B38 S3 parity drift {len(devp)} {dc}")

    # Strict prospective evidence: interaction itself must begin after freeze.
    fwd=P[pd.to_datetime(P.first_touch_ts,utc=True)>FREEZE].copy()
    return fwd,h1,m15

def read_ledger():
    if not LEDGER.exists():
        return pd.DataFrame()
    q=pd.read_csv(LEDGER)
    for c in ["first_touch_ts","entry_ts","resolution_ts","first_seen_at_utc","last_checked_at_utc"]:
        if c in q.columns: q[c]=pd.to_datetime(q[c],utc=True,errors="coerce")
    return q

def ffloat(x):
    try:
        v=float(x)
        return v if np.isfinite(v) else np.nan
    except Exception:
        return np.nan

def resolve_open(raw,entry_ts,sl,tp,latest):
    q=raw[(raw.index>entry_ts)&(raw.index<=latest)]
    for t,b in q.iterrows():
        stop=float(b.low)<=sl
        target=float(b.high)>=tp
        if stop and target:return "PAPER_AMBIGUOUS_SAME_5M",t
        if target:return "PAPER_WIN",t
        if stop:return "PAPER_LOSS",t
    return "PAPER_ENTRY_OPEN",pd.NaT

def current_rows(P,raw,latest,now):
    rows=[]
    for r in P.itertuples(index=False):
        base={
            "zone_id":r.zone_id,
            "first_touch_ts":r.first_touch_ts,
            "first_touch_archetype":r.first_touch_archetype,
            "execution_mode":r.execution_mode,
            "source_execution_status":r.execution_status,
            "entry_ts":r.entry_ts,
            "entry_price":ffloat(r.entry_price),
            "sl_reference":ffloat(r.sl_reference),
            "selected_target":"",
            "target_level":np.nan,
            "target_rr":np.nan,
            "forward_status":"",
            "resolution_ts":pd.NaT,
            "realized_r":np.nan,
            "first_seen_at_utc":now,
            "last_checked_at_utc":now,
        }
        if r.execution_status=="NO_TRIGGER_BY_END":
            base["forward_status"]="PENDING_RECLAIM"
        elif r.execution_status=="CANCELLED_DEMAND_ACCEPTANCE":
            base["forward_status"]="CANCELLED_DEMAND_ACCEPTANCE"
        elif r.execution_status=="ENTRY":
            policy,tcol,rrcol=MODE_POLICY[r.execution_mode]
            tp=ffloat(getattr(r,tcol)); rr=ffloat(getattr(r,rrcol))
            base["selected_target"]=policy
            base["target_level"]=tp
            base["target_rr"]=rr
            if not np.isfinite(tp) or not np.isfinite(rr):
                base["forward_status"]="NO_POLICY_TARGET"
            else:
                status,rt=resolve_open(raw,r.entry_ts,float(r.sl_reference),tp,latest)
                base["forward_status"]=status
                base["resolution_ts"]=rt
                if status=="PAPER_WIN":base["realized_r"]=rr
                elif status=="PAPER_LOSS":base["realized_r"]=-1.0
        else:
            raise RuntimeError(f"unexpected source status {r.execution_status}")
        rows.append(base)
    return pd.DataFrame(rows)

def same_value(a,b):
    if pd.isna(a) and pd.isna(b): return True
    if isinstance(a,(float,np.floating,int,np.integer)) or isinstance(b,(float,np.floating,int,np.integer)):
        try:
            aa=float(a); bb=float(b)
            if np.isnan(aa) and np.isnan(bb): return True
            return abs(aa-bb)<=1e-10*max(1.0,abs(aa),abs(bb))
        except Exception:
            pass
    return str(a)==str(b)

def merge_ledger(old,cur,now):
    if cur.empty:
        return old.copy() if len(old) else cur.copy()
    keycols=["zone_id","first_touch_ts"]
    cur=cur.copy()
    cur["event_key"]=cur.zone_id.astype(str)+"|"+pd.to_datetime(cur.first_touch_ts,utc=True).astype(str)
    if len(old):
        old=old.copy()
        old["event_key"]=old.zone_id.astype(str)+"|"+pd.to_datetime(old.first_touch_ts,utc=True).astype(str)
    else:
        old=pd.DataFrame(columns=cur.columns)

    by_old={r.event_key:r for r in old.itertuples(index=False)}
    out=[]
    for r in cur.itertuples(index=False):
        d=r._asdict()
        prev=by_old.get(r.event_key)
        if prev is None:
            out.append(d)
            continue
        p=prev._asdict()
        terminal=str(p.get("forward_status","")) in {
            "CANCELLED_DEMAND_ACCEPTANCE","NO_POLICY_TARGET",
            "PAPER_WIN","PAPER_LOSS","PAPER_AMBIGUOUS_SAME_5M"
        }
        # Once entry exists, all execution geometry is immutable.
        if pd.notna(p.get("entry_ts")):
            for c in IMMUTABLE_ENTRY_FIELDS:
                if not same_value(p.get(c),d.get(c)):
                    raise RuntimeError(f"immutable forward geometry mutation {r.event_key} field={c}: {p.get(c)} -> {d.get(c)}")
        if terminal:
            # Terminal outcome cannot be rewritten.
            d=p
            d["last_checked_at_utc"]=now
        else:
            # Preserve first-seen timestamp while allowing PENDING -> ENTRY/CANCEL.
            d["first_seen_at_utc"]=p.get("first_seen_at_utc")
        out.append(d)

    # Old rows missing from a deterministic rebuild are forbidden.
    curkeys=set(cur.event_key)
    missing=set(by_old)-curkeys
    if missing:
        raise RuntimeError(f"previous forward events disappeared from rebuild: {sorted(missing)[:5]}")

    z=pd.DataFrame(out)
    if "event_key" in z.columns:z=z.drop(columns=["event_key"])
    return z.sort_values(["first_touch_ts","zone_id"]).reset_index(drop=True)

def stats(q):
    resolved=q[q.forward_status.isin(["PAPER_WIN","PAPER_LOSS"])].copy()
    wins=resolved[resolved.forward_status=="PAPER_WIN"]
    losses=resolved[resolved.forward_status=="PAPER_LOSS"]
    n=len(resolved)
    exp=float(resolved.realized_r.mean()) if n else np.nan
    total=float(resolved.realized_r.sum()) if n else np.nan
    pos=float(wins.realized_r.sum()) if len(wins) else 0.0
    neg=abs(float(losses.realized_r.sum())) if len(losses) else 0.0
    pf=pos/neg if neg>0 else (np.inf if pos>0 else np.nan)
    seq=resolved.sort_values(["entry_ts","zone_id"]).forward_status.tolist()
    maxl=cur=0
    for x in seq:
        if x=="PAPER_LOSS":cur+=1;maxl=max(maxl,cur)
        else:cur=0
    if n:
        rs=resolved.sort_values(["entry_ts","zone_id"]).realized_r.to_numpy(float)
        cum=np.cumsum(rs); peak=np.maximum.accumulate(np.concatenate([[0.0],cum]))[:-1]
        mdd=float(np.max(peak-cum))
    else:mdd=np.nan
    return {
        "events":len(q),"resolved":n,"wins":len(wins),"losses":len(losses),
        "hit_rate":len(wins)/n if n else np.nan,"expectancy_r":exp,
        "total_r":total,"profit_factor":pf,"max_loss_streak":maxl,"max_drawdown_r":mdd,
    }

def render(ledger,latest,created_seed,now):
    s=stats(ledger)
    elapsed=(now-FREEZE)/pd.Timedelta(days=1)
    support=elapsed>=28 and s["resolved"]>=30
    if not support:
        gate="COLLECTING_FORWARD_EVIDENCE"
    elif s["expectancy_r"]>0 and s["profit_factor"]>1 and s["total_r"]>0:
        gate="FORWARD_EDGE_GATE_PASS_PAPER_REVIEW"
    else:
        gate="FORWARD_EDGE_GATE_FAIL"

    modes=[]
    if len(ledger):
        e=ledger[ledger.execution_mode.astype(str)!="PENDING_RECLAIM"]
        for mode,q in e.groupby("execution_mode"):
            modes.append({"execution_mode":mode,**stats(q)})
    M=pd.DataFrame(modes)
    M.to_csv(SUMMARY,index=False)

    vc=ledger.forward_status.value_counts().to_dict() if len(ledger) else {}
    def n(x,d=3):
        if x==np.inf:return "∞"
        return "—" if x is None or not np.isfinite(x) else f"{x:.{d}f}"
    def p(x):
        return "—" if x is None or not np.isfinite(x) else f"{100*x:.1f}%"
    lines=[
        "# BNB B38-S6 — Prospective Forward Shadow","",
        f"**Status: {gate}**","",
        f"- S5 freeze: **{FREEZE}**",
        f"- Latest completed 5m close: **{latest}**",
        f"- Elapsed: **{elapsed:.2f} days**",
        f"- Historical seed created this run: **{'YES' if created_seed else 'NO'}**",
        "",
        "## Forward census",
        f"- Post-freeze parent interactions: **{len(ledger)}**",
        f"- Pending reclaim: **{vc.get('PENDING_RECLAIM',0)}**",
        f"- Cancelled before reclaim: **{vc.get('CANCELLED_DEMAND_ACCEPTANCE',0)}**",
        f"- No required policy target: **{vc.get('NO_POLICY_TARGET',0)}**",
        f"- Open paper entries: **{vc.get('PAPER_ENTRY_OPEN',0)}**",
        f"- Paper WIN / LOSS: **{vc.get('PAPER_WIN',0)} / {vc.get('PAPER_LOSS',0)}**",
        f"- Ambiguous same-5m: **{vc.get('PAPER_AMBIGUOUS_SAME_5M',0)}**","",
        "## Resolved forward performance",
        f"- Resolved WIN+LOSS: **{s['resolved']} / 30 required**",
        f"- Hit rate: **{p(s['hit_rate'])}**",
        f"- Expectancy: **{n(s['expectancy_r'])}R/trade**",
        f"- Total R: **{n(s['total_r'])}R**",
        f"- Profit factor: **{n(s['profit_factor'])}**",
        f"- Max loss streak: **{s['max_loss_streak']}**",
        f"- Max cumulative-R drawdown: **{n(s['max_drawdown_r'])}R**","",
        "## Frozen gate",
        "- support: >=28 days AND >=30 resolved paper trades",
        "- edge: expectancy >0R AND PF >1.0 AND total R >0",
        f"- support gate: **{'PASS' if support else 'WAIT'}**",
        f"- composite gate: **{gate}**","",
        "Public market data only. No Binance order endpoint is called."
    ]
    STATUS.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return gate,s,M

def main():
    verify_manifest()
    now=utc_now()
    raw,created_seed,latest=build_market_cache()
    if latest<=FREEZE:
        raise RuntimeError(f"no completed post-freeze 5m bar yet: latest={latest}")
    fwd,_,_=rebuild_plans(raw,latest)
    cur=current_rows(fwd,raw,latest,now)
    old=read_ledger()
    merged=merge_ledger(old,cur,now)
    merged.to_csv(LEDGER,index=False)
    gate,s,M=render(merged,latest,created_seed,now)

    audit={
        "identity":"BNB_B38_S6_PROSPECTIVE_FORWARD_V1",
        "run_at_utc":now.isoformat(),
        "freeze_utc":FREEZE.isoformat(),
        "latest_complete_5m_close_utc":latest.isoformat(),
        "raw_rows":len(raw),
        "raw_first":str(raw.index.min()),
        "raw_last":str(raw.index.max()),
        "seed_created":created_seed,
        "post_freeze_parent_events":len(merged),
        "resolved_win_loss":s["resolved"],
        "gate":gate,
        "no_order_endpoints":True,
    }
    AUDIT.write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    print(STATUS.read_text(),flush=True)

if __name__=="__main__":
    main()
