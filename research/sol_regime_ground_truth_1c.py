"""SOL Regime Stage 1C — empirical ground-truth discovery.

Ground-truth labels MAY use future information. They are targets for later
causal detector research, never live signals.

Discovery thresholds are fitted ONLY on 2023-2024 and then frozen for
2025 validation and 2026 final OOS reporting.
"""
import os, sqlite3, json
from datetime import datetime, timezone
import numpy as np

DB_PATH=os.environ.get("DB_PATH","market_data.db")
HORIZONS=(4,8,12,24)

def load_sol_1h(db_path=DB_PATH):
    con=sqlite3.connect(f"file:{db_path}?mode=ro",uri=True)
    rows=con.execute("""SELECT open_time,open,high,low,close,volume FROM klines
        WHERE symbol='SOLUSDT' AND timeframe='1h' ORDER BY open_time""").fetchall()
    con.close()
    a=np.asarray(rows,dtype=float)
    if len(a)<100:return None
    return {"t":a[:,0].astype(np.int64),"o":a[:,1],"h":a[:,2],"l":a[:,3],"c":a[:,4],"v":a[:,5]}

def year(ts): return datetime.fromtimestamp(int(ts)/1000,tz=timezone.utc).year

def future_metrics(d):
    t,H,L,C=d["t"],d["h"],d["l"],d["c"]; n=len(C); out=[]
    for i in range(n):
        rec={"i":i,"t":int(t[i]),"year":year(t[i])}
        for hz in HORIZONS:
            if i+hz>=n: continue
            ep=C[i]; hs=H[i+1:i+hz+1]; ls=L[i+1:i+hz+1]; cs=C[i+1:i+hz+1]
            ret=(C[i+hz]/ep-1)*100
            up=(np.max(hs)/ep-1)*100
            dn=(ep/np.min(ls)-1)*100
            steps=np.diff(np.r_[ep,cs])
            efficiency=abs(C[i+hz]-ep)/(np.sum(np.abs(steps))+1e-12)
            signs=np.sign(np.diff(np.r_[ep,cs]))
            persistence=abs(np.sum(signs))/len(signs)
            rec[f"r{hz}"]=ret;rec[f"up{hz}"]=up;rec[f"dn{hz}"]=dn
            rec[f"eff{hz}"]=efficiency;rec[f"pers{hz}"]=persistence
        out.append(rec)
    return out

def fit_thresholds(recs):
    dev=[r for r in recs if r["year"] in (2023,2024) and "r24" in r]
    # Multi-horizon directional score: median standardized forward returns.
    scales={hz:max(np.median(np.abs([r[f"r{hz}"] for r in dev])),1e-9) for hz in HORIZONS}
    scores=[]
    for r in dev:
        z=np.median([r[f"r{hz}"]/scales[hz] for hz in HORIZONS])
        path=np.mean([r[f"eff{hz}"] for hz in HORIZONS])
        scores.append((z,path))
    zabs=np.asarray([abs(z) for z,_ in scores]); paths=np.asarray([p for _,p in scores])
    # Quantiles are discovery-only; frozen thereafter.
    return {
      "scales":scales,
      "direction_abs_q60":float(np.quantile(zabs,.60)),
      "direction_abs_q30":float(np.quantile(zabs,.30)),
      "path_eff_q55":float(np.quantile(paths,.55)),
      "path_eff_q35":float(np.quantile(paths,.35)),
    }

def label(r,th):
    if "r24" not in r:return None
    z=float(np.median([r[f"r{hz}"]/th["scales"][hz] for hz in HORIZONS]))
    pe=float(np.mean([r[f"eff{hz}"] for hz in HORIZONS]))
    # Strong coherent directional future = directional ground truth.
    if abs(z)>=th["direction_abs_q60"] and pe>=th["path_eff_q55"]:
        return "BULL" if z>0 else "BEAR"
    # Low directional displacement + inefficient path = sideways.
    if abs(z)<=th["direction_abs_q30"] and pe<=th["path_eff_q35"]:
        return "SIDEWAYS"
    # Everything between stable directional and stable sideways is transition.
    return "TRANSITION"

def summarize(rs,th,years):
    x=[r for r in rs if r["year"] in years and label(r,th)]
    labs=["BULL","BEAR","SIDEWAYS","TRANSITION"]; out={"n":len(x)}
    for lab in labs:
        q=[r for r in x if label(r,th)==lab]
        o={"n":len(q),"pct":round(100*len(q)/len(x),2) if x else 0}
        for hz in HORIZONS:
            if q:
                o[f"r{hz}_med"]=round(float(np.median([r[f"r{hz}"] for r in q])),4)
                o[f"up{hz}_med"]=round(float(np.median([r[f"up{hz}"] for r in q])),4)
                o[f"dn{hz}_med"]=round(float(np.median([r[f"dn{hz}"] for r in q])),4)
                o[f"eff{hz}_med"]=round(float(np.median([r[f"eff{hz}"] for r in q])),4)
        out[lab]=o
    seq=[label(r,th) for r in x]
    out["persistence_pct"]=round(100*sum(a==b for a,b in zip(seq,seq[1:]))/max(1,len(seq)-1),2)
    return out

def acceptance(summary):
    # Ground truth must order forward returns correctly, not hit a trading WR.
    b=summary["BULL"]; s=summary["SIDEWAYS"]; br=summary["BEAR"]
    return {
      "bull_positive_all_horizons":all(b.get(f"r{h}_med",0)>0 for h in HORIZONS),
      "bear_negative_all_horizons":all(br.get(f"r{h}_med",0)<0 for h in HORIZONS),
      "ordered_24h":b.get("r24_med",0)>s.get("r24_med",0)>br.get("r24_med",0),
      "nonempty_all_states":all(summary[k]["n"]>0 for k in ("BULL","BEAR","SIDEWAYS","TRANSITION"))
    }

def run(db_path=DB_PATH):
    d=load_sol_1h(db_path)
    if d is None:return {"error":"not enough SOLUSDT 1h data"}
    rs=future_metrics(d); th=fit_thresholds(rs)
    periods={"DEV_2023_2024":(2023,2024),"VAL_2025":(2025,),"OOS_2026":(2026,)}
    result={"method":"future multi-horizon empirical ground truth; NOT a live detector",
            "thresholds_frozen_from":"2023-2024","thresholds":th,"periods":{}}
    for name,yrs in periods.items():
        sm=summarize(rs,th,yrs); sm["acceptance"]=acceptance(sm); result["periods"][name]=sm
    return result

if __name__=="__main__": print(json.dumps(run(),indent=2))
