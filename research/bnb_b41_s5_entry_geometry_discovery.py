#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b41_s2_wall_importance_audit as s2

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY"
S4B_SIG="acab9ae7928bdcbebc3608a1f5818a6b5eaa6a4a782f446a2cc418e8e50adcbc"

CLASSES=[
    ("UPPER","C1_CLEAN_REJECTION","SHORT","TF05"),
    ("LOWER","C2_RECLAIM_AFTER_CLOSE","LONG","TF60"),
]
CANDS=[
    ("E0_MARKET",0.0),
    ("E1_R25",0.25),
    ("E2_R50",0.50),
    ("E3_WALL",1.0),
]
LIMIT_WAIT_MIN=60
EVAL_MIN=180

def verify_parent():
    p=ROOT/"results/bnb_b41_s4b/BNB_B41_S4B_MTF_DIRECTION_TIMING_ANATOMY_Freeze.txt"
    txt=p.read_text(encoding="utf-8")
    if f"S4B_SIGNATURE_SHA256={S4B_SIG}" not in txt:
        raise RuntimeError("S4B parent signature mismatch")

def build_signal_ledger():
    E=pd.read_csv(
        ROOT/"results/bnb_b41_s4b/BNB_B41_S4B_MTF_DIRECTION_TIMING_ANATOMY_Ledger.csv.gz",
        compression="gzip",parse_dates=["session_day","first_touch_ts","detector_ts"]
    )
    parts=[]
    for side,char,direction,tf in CLASSES:
        z=E[
            (E.eligible_tf==True)&
            (E.side==side)&(E.character==char)&
            (E.direction==direction)&(E.tf==tf)
        ].copy()
        z["class_id"]=f"{side}_{char}_{direction}_{tf}"
        parts.append(z)
    S=pd.concat(parts,ignore_index=True)
    if len(S)==0: raise RuntimeError("no S4B validated signals")
    return S

def one_candidate(daybars,r,name,frac):
    det=pd.Timestamp(r.detector_ts)
    if det not in daybars.index:
        raise RuntimeError(f"missing detector {det}")
    D=float(r.detector_close)
    W=float(r.level)
    wd=abs(W-float(r.session_open))
    if wd<=0: raise RuntimeError("nonpositive wall distance")
    price=D+frac*(W-D)

    if name=="E0_MARKET":
        fill=True; fill_ts=det; fill_price=D; wait=0.0
    else:
        after=daybars[(daybars.index>det)&(daybars.index<=det+pd.Timedelta(minutes=LIMIT_WAIT_MIN))]
        if str(r.direction)=="SHORT":
            hits=after[after.high>=price]
        else:
            hits=after[after.low<=price]
        if len(hits):
            fill=True; fill_ts=hits.index[0]; fill_price=price
            wait=float((fill_ts-det)/pd.Timedelta(minutes=1))
        else:
            fill=False; fill_ts=pd.NaT; fill_price=np.nan; wait=np.nan

    endpoint=det+pd.Timedelta(minutes=EVAL_MIN)
    valid_endpoint=endpoint in daybars.index

    out={
        "candidate":name,"fraction":frac,"fill":fill,
        "fill_ts":fill_ts,"fill_price":fill_price,"fill_wait_min":wait,
        "endpoint_ts":endpoint,"valid180":bool(fill and valid_endpoint),
    }
    if not (fill and valid_endpoint):
        out.update({"aligned180":np.nan,"hit180":False,"mfe180":np.nan,"mae180":np.nan,"favdom":False})
        return out

    close180=float(daybars.loc[endpoint,"close"])
    sign=1.0 if str(r.direction)=="LONG" else -1.0
    a180=sign*(close180-fill_price)/wd

    path=daybars[(daybars.index>fill_ts)&(daybars.index<=endpoint)]
    if len(path):
        hi=float(path.high.max()); lo=float(path.low.min())
        if str(r.direction)=="LONG":
            mfe=max(0.0,hi-fill_price)/wd
            mae=max(0.0,fill_price-lo)/wd
        else:
            mfe=max(0.0,fill_price-lo)/wd
            mae=max(0.0,hi-fill_price)/wd
    else:
        mfe=mae=0.0

    out.update({
        "aligned180":float(a180),"hit180":bool(a180>0),
        "mfe180":float(mfe),"mae180":float(mae),"favdom":bool(mfe>mae)
    })
    return out

def stats(z, baseline_win_keys=None):
    signals=z.signal_key.nunique()
    filled=z[z.fill]
    v=z[z.valid180]
    row={
        "signals":signals,
        "filled_n":len(filled),
        "fill_rate":len(filled)/signals if signals else np.nan,
        "median_fill_wait":float(filled.fill_wait_min.median()) if len(filled) else np.nan,
        "n180":len(v),
        "median180":float(v.aligned180.median()) if len(v) else np.nan,
        "hit180":float(v.hit180.mean()) if len(v) else np.nan,
        "median_mfe":float(v.mfe180.median()) if len(v) else np.nan,
        "median_mae":float(v.mae180.median()) if len(v) else np.nan,
        "favdom":float(v.favdom.mean()) if len(v) else np.nan,
    }
    if baseline_win_keys is not None:
        filled_keys=set(filled.signal_key)
        missed=len(set(baseline_win_keys)-filled_keys)
        row["missed_baseline_wins"]=missed
        row["baseline_wins"]=len(baseline_win_keys)
        row["missed_win_fraction"]=missed/len(baseline_win_keys) if baseline_win_keys else np.nan
    else:
        row["missed_baseline_wins"]=0
        row["baseline_wins"]=0
        row["missed_win_fraction"]=0.0
    return row

def main():
    verify_parent()
    S=build_signal_ledger()

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    xb=s2.session_bars(raw)
    grouped={k:v.copy() for k,v in xb.groupby("session_day",sort=False)}

    rows=[]
    for idx,r in enumerate(S.itertuples(index=False)):
        day=pd.Timestamp(r.session_day)
        bars=grouped[day]
        key=f"{r.class_id}|{day.isoformat()}|{pd.Timestamp(r.detector_ts).isoformat()}"
        for name,frac in CANDS:
            a=one_candidate(bars,r,name,frac)
            rows.append({
                "signal_key":key,"class_id":r.class_id,
                "session_day":day,"year":int(r.year),"period":str(r.period),
                "side":str(r.side),"character":str(r.character),"direction":str(r.direction),"tf":str(r.tf),
                "wall":float(r.level),"session_open":float(r.session_open),
                "detector_ts":pd.Timestamp(r.detector_ts),"detector_close":float(r.detector_close),
                **a
            })
    L=pd.DataFrame(rows)

    summary=[]
    for period in ["DEV","REF","ALL"]:
        p=L if period=="ALL" else L[L.period==period]
        for side,char,direction,tf in CLASSES:
            q=p[(p.side==side)&(p.character==char)&(p.direction==direction)&(p.tf==tf)]
            base=q[q.candidate=="E0_MARKET"]
            baseline_win_keys=set(base[(base.valid180)&(base.hit180)].signal_key)
            for name,_ in CANDS:
                z=q[q.candidate==name]
                row=stats(z,baseline_win_keys if name!="E0_MARKET" else None)
                summary.append({
                    "period":period,"side":side,"character":char,"direction":direction,"tf":tf,
                    "candidate":name,**row
                })
    A=pd.DataFrame(summary)

    selections=[]
    final_entries=[]
    for side,char,direction,tf in CLASSES:
        dbase=A[(A.period=="DEV")&(A.side==side)&(A.character==char)&(A.direction==direction)&(A.tf==tf)&(A.candidate=="E0_MARKET")].iloc[0]
        eligible=[]
        dev_diag=[]
        for name,_ in CANDS[1:]:
            z=A[(A.period=="DEV")&(A.side==side)&(A.character==char)&(A.direction==direction)&(A.tf==tf)&(A.candidate==name)].iloc[0]
            ok=bool(
                z.fill_rate>=0.70 and z.n180>=30 and
                z.median180>dbase.median180 and
                z.median_mae<dbase.median_mae and
                z.hit180>=dbase.hit180-0.03 and
                z.missed_win_fraction<=0.30
            )
            dev_diag.append((name,ok))
            if ok: eligible.append(name)

        nom=eligible[0] if eligible else "E0_MARKET"
        if nom=="E0_MARKET":
            ref_valid=True
            final="E0_MARKET"
        else:
            rbase=A[(A.period=="REF")&(A.side==side)&(A.character==char)&(A.direction==direction)&(A.tf==tf)&(A.candidate=="E0_MARKET")].iloc[0]
            rz=A[(A.period=="REF")&(A.side==side)&(A.character==char)&(A.direction==direction)&(A.tf==tf)&(A.candidate==nom)].iloc[0]
            ref_valid=bool(
                rz.fill_rate>=0.60 and rz.n180>=20 and
                rz.median180>rbase.median180 and
                rz.median_mae<rbase.median_mae and
                rz.hit180>=rbase.hit180-0.03 and
                rz.missed_win_fraction<=0.30
            )
            final=nom if ref_valid else "E0_MARKET"

        def pick(period,cand):
            return A[(A.period==period)&(A.side==side)&(A.character==char)&(A.direction==direction)&(A.tf==tf)&(A.candidate==cand)].iloc[0]
        dn=pick("DEV",nom); rn=pick("REF",nom)
        selections.append({
            "side":side,"character":char,"direction":direction,"tf":tf,
            "dev_nomination":nom,"ref_limit_validated":ref_valid if nom!="E0_MARKET" else np.nan,
            "final_entry":final,
            "dev_fill":dn.fill_rate,"dev_n180":int(dn.n180),"dev_med180":dn.median180,"dev_hit180":dn.hit180,
            "dev_mae":dn.median_mae,"dev_missed_win":dn.missed_win_fraction,
            "ref_fill":rn.fill_rate,"ref_n180":int(rn.n180),"ref_med180":rn.median180,"ref_hit180":rn.hit180,
            "ref_mae":rn.median_mae,"ref_missed_win":rn.missed_win_fraction,
        })
        final_entries.append((side,char,direction,tf,final))

    SEL=pd.DataFrame(selections)

    # Final-entry pooled evidence, using the frozen class-specific final geometry.
    chosen=[]
    for side,char,direction,tf,entry in final_entries:
        chosen.append(L[
            (L.side==side)&(L.character==char)&(L.direction==direction)&(L.tf==tf)&(L.candidate==entry)
        ].copy())
    F=pd.concat(chosen,ignore_index=True)

    pooled=[]
    for period in ["DEV","REF","ALL"]:
        z=F if period=="ALL" else F[F.period==period]
        basekeys=None
        pooled.append({"period":period,**stats(z,basekeys)})
    P=pd.DataFrame(pooled)

    yearly=[]
    for y in [2022,2023,2024,2025,2026]:
        z=F[F.year==y]
        yearly.append({"year":y,**stats(z,None)})
    Y=pd.DataFrame(yearly)

    status="BNB_B41_S5_READY_FOR_S6"
    sig=hashlib.sha256(json.dumps({
        "parent":S4B_SIG,
        "classes":["UPPER_C1_SHORT_TF05","LOWER_C2_LONG_TF60"],
        "entries":{"MARKET":0.0,"R25":0.25,"R50":0.50,"WALL":1.0},
        "limit_wait_min":LIMIT_WAIT_MIN,
        "endpoint":"DETECTOR_PLUS_180M",
        "selection":"DEV_SHALLOWEST_ELIGIBLE",
        "dev_gate":{"fill":0.70,"n180":30,"median180":"gt_market","mae":"lt_market","hit_delta_min":-0.03,"missed_win_max":0.30},
        "ref_gate":{"fill":0.60,"n180":20,"median180":"gt_market","mae":"lt_market","hit_delta_min":-0.03,"missed_win_max":0.30},
        "fallback":"MARKET",
        "no_sl_tp_pnl":True,
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    A.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    SEL.to_csv(ROOT/f"{PFX}_Selections.csv",index=False)
    P.to_csv(ROOT/f"{PFX}_FinalPooled.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_FinalByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_S4B_SIGNATURE_SHA256={S4B_SIG}\nS5_SIGNATURE_SHA256={sig}\n"
        "SHORT_CLASS=UPPER_C1_TF05\nLONG_CLASS=LOWER_C2_TF60\n"
        "ENTRY_CANDIDATES=MARKET,R25,R50,WALL\nLIMIT_WAIT_MIN=60\nEVAL_ENDPOINT=SIGNAL_PLUS_180M\n"
        "SELECTION=DEV_SHALLOWEST_ELIGIBLE_REF_HOLDOUT\nNO_SL_TP_PNL=TRUE\n",
        encoding="utf-8"
    )
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}x"

    lines=[
        "# BNB B41-S5 — Entry Geometry Discovery","",
        f"**Status: {status}**","",f"S5 signature: `{sig}`","",
        "Direction and timeframe are frozen from S4B. Limit candidates are judged against market-at-detector with a fixed detector+180m endpoint.","",
        "## Candidate geometry","",
        "| Period | Side | Dir | TF | Candidate | Fill | N180 | 180m | Hit180 | MFE | MAE | Fav-dom | Missed baseline wins |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in A.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.side} | {r.direction} | {r.tf} | {r.candidate} | {pct(r.fill_rate)} | {r.n180} | "
            f"{num(r.median180)} | {pct(r.hit180)} | {num(r.median_mfe)} | {num(r.median_mae)} | "
            f"{pct(r.favdom)} | {pct(r.missed_win_fraction)} |"
        )

    lines += ["","## DEV nomination -> REF holdout -> final entry","",
        "| Side | Dir | TF | DEV nomination | DEV fill | DEV 180m | DEV hit | DEV MAE | DEV missed wins | REF fill | REF 180m | REF hit | REF MAE | REF missed wins | Final |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in SEL.itertuples(index=False):
        lines.append(
            f"| {r.side} | {r.direction} | {r.tf} | {r.dev_nomination} | {pct(r.dev_fill)} | {num(r.dev_med180)} | "
            f"{pct(r.dev_hit180)} | {num(r.dev_mae)} | {pct(r.dev_missed_win)} | {pct(r.ref_fill)} | "
            f"{num(r.ref_med180)} | {pct(r.ref_hit180)} | {num(r.ref_mae)} | {pct(r.ref_missed_win)} | **{r.final_entry}** |"
        )

    lines += ["","## Final frozen-entry pooled evidence","",
        "| Period | Signals | Filled | Fill | N180 | 180m | Hit180 | MFE | MAE | Fav-dom |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in P.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.signals} | {r.filled_n} | {pct(r.fill_rate)} | {r.n180} | {num(r.median180)} | "
            f"{pct(r.hit180)} | {num(r.median_mfe)} | {num(r.median_mae)} | {pct(r.favdom)} |"
        )

    lines += ["","## Gate",
        "Each validated S4B direction class now has a frozen final entry geometry.",
        "**READY FOR B41-S6 STRUCTURAL INVALIDATION / SL DISCOVERY.**",
        "",
        "S5 did not optimize stop, target, trade WR, PF, expectancy, leverage, or PnL."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
