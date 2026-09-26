"""SOL Regime Stage 4B — dedicated BEAR robustness audit.

Research-only. Uses frozen Stage 1C ground truth and fixed Stage 4B candidates.
The goal is to reproduce the key Stage 4B validation result, not to emit a
live trading signal.

Expected DB schema: klines(symbol,timeframe,open_time,open,high,low,close,
volume,trades,taker_buy_volume,...)
"""

from __future__ import annotations
import math, os, sqlite3
from collections import defaultdict
from datetime import datetime, timezone
import numpy as np

DB_PATH = os.environ.get("DB_PATH", "market_data.db")
EVAL_START = int(datetime(2023,12,2,tzinfo=timezone.utc).timestamp()*1000)
END_TS = int(datetime(2026,9,25,11,tzinfo=timezone.utc).timestamp()*1000)
HORIZONS=(4,8,12,24)

GT_SCALES={4:0.9839058824328062,8:1.4145306027761706,12:1.794720362676172,24:2.62972781641872}
GT={"q60":1.1008168495902722,"q30":0.4730911846778754,
    "p55":0.32397842902877055,"p35":0.24712535346635553}

CANDIDATES={
    "V1_BEAR": lambda f: f["acc"] >= 1.101215540095295 and f["close_loc"] >= 0.6260779194779318,
    "STAGE4B_PRIMARY_NEW": lambda f: f["r8_atr"] >= 1.1599460108703312 and f["taker_imb8"] <= -0.02489891287682621,
    "STAGE4B_BROAD_EXHAUSTION": lambda f: f["ret4"] >= 1.0538685953763893 and f["acc"] >= 0.8770846111536335 and f["dist_low8"] >= 3.0464801954845857,
    "STAGE4B_NEAR_HIGH_VOL": lambda f: f["rv24"] >= 1.1633509828632893 and f["dist_high8"] >= -1.1720800325883762,
}

def load():
    con=sqlite3.connect(f"file:{DB_PATH}?mode=ro",uri=True)
    rows=con.execute("""
      SELECT open_time,open,high,low,close,volume,trades,taker_buy_volume
      FROM klines
      WHERE symbol='SOLUSDT' AND timeframe='1h' AND open_time<=?
      ORDER BY open_time
    """,(END_TS,)).fetchall()
    con.close()
    a=np.asarray(rows,dtype=float)
    return {
      "t":a[:,0].astype(np.int64),"o":a[:,1],"h":a[:,2],"l":a[:,3],
      "c":a[:,4],"v":a[:,5],"trades":a[:,6],"tb":a[:,7]
    }

def med(xs): return float(np.median(xs))
def mean(xs): return float(np.mean(xs))

def gt_label(d,i):
    if i+24>=len(d["c"]): return None
    zs=[]; eff=[]
    ep=d["c"][i]
    for hz in HORIZONS:
        ret=(d["c"][i+hz]/ep-1)*100
        zs.append(ret/GT_SCALES[hz])
        cs=d["c"][i+1:i+hz+1]
        path=np.sum(np.abs(np.diff(np.r_[ep,cs])))
        eff.append(abs(d["c"][i+hz]-ep)/(path+1e-12))
    z=med(zs); e=mean(eff)
    if abs(z)>=GT["q60"] and e>=GT["p55"]: return "BULL" if z>0 else "BEAR"
    if abs(z)<=GT["q30"] and e<=GT["p35"]: return "SIDEWAYS"
    return "TRANSITION"

def tr(d,i):
    if i==0:return d["h"][i]-d["l"][i]
    return max(d["h"][i]-d["l"][i],abs(d["h"][i]-d["c"][i-1]),abs(d["l"][i]-d["c"][i-1]))

def feat(d,i):
    trs=[tr(d,j) for j in range(i-13,i+1)]
    atr=mean(trs); atrp=100*atr/d["c"][i]
    ret=lambda h:100*(d["c"][i]/d["c"][i-h]-1)
    r4=ret(4); r8=ret(8); r12=ret(12)
    hi8=max(d["h"][i-7:i+1]); lo8=min(d["l"][i-7:i+1])
    lr24=[math.log(d["c"][j]/d["c"][j-1]) for j in range(i-23,i+1)]
    taker=[(2*d["tb"][j]/d["v"][j]-1) if d["v"][j] else 0 for j in range(i-7,i+1)]
    rng=d["h"][i]-d["l"][i]+1e-12
    return {
      "ret4":r4,
      "r8_atr":r8/(atrp+1e-12),
      "acc":r4-r12/3,
      "dist_low8":100*(d["c"][i]/lo8-1),
      "dist_high8":100*(d["c"][i]/hi8-1),
      "rv24":100*np.std(lr24),
      "close_loc":2*(d["c"][i]-d["l"][i])/rng-1,
      "taker_imb8":mean(taker),
    }

def period(ts):
    y=datetime.fromtimestamp(ts/1000,tz=timezone.utc).year
    if y in (2023,2024): return "DEV"
    if y==2025:return "VAL"
    if y==2026:return "OOS"
    return None

def quarter(ts):
    z=datetime.fromtimestamp(ts/1000,tz=timezone.utc)
    return f"{z.year} Q{(z.month-1)//3+1}"

def metric(rows,name):
    fn=CANDIDATES[name]
    base=sum(r["gt"]=="BEAR" for r in rows)/len(rows)
    q=[r for r in rows if fn(r["f"])]
    tp=sum(r["gt"]=="BEAR" for r in q)
    trans=sum(r["gt"]=="TRANSITION" for r in q)
    opp=sum(r["gt"]=="BULL" for r in q)
    p=tp/len(q) if q else 0
    return {
      "n":len(q),"precision":p,"lift":p/base if base else 0,
      "transition":trans/len(q) if q else 0,
      "opposite":opp/len(q) if q else 0,
    }

def run():
    d=load(); rows=[]
    for i in range(24,len(d["c"])-24):
        ts=int(d["t"][i])
        if ts<EVAL_START: continue
        p=period(ts)
        if not p: continue
        # Boundary safety: last 24h of DEV/VAL excluded.
        if p=="DEV" and ts>=int(datetime(2024,12,31,tzinfo=timezone.utc).timestamp()*1000): continue
        if p=="VAL" and ts>=int(datetime(2025,12,31,tzinfo=timezone.utc).timestamp()*1000): continue
        rows.append({"t":ts,"period":p,"gt":gt_label(d,i),"f":feat(d,i)})

    out={}
    for name in CANDIDATES:
        out[name]={}
        for p in ("DEV","VAL","OOS"):
            out[name][p]=metric([r for r in rows if r["period"]==p],name)
        out[name]["quarters"]={}
        groups=defaultdict(list)
        for r in rows:
            if r["period"] in ("VAL","OOS"): groups[quarter(r["t"])].append(r)
        for q,rs in groups.items(): out[name]["quarters"][q]=metric(rs,name)
    return out

if __name__=="__main__":
    import json
    print(json.dumps(run(),indent=2))
