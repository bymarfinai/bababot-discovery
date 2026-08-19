#!/usr/bin/env python3
"""AOH2 — optimize PRE_UP60 + previous-day range location for Asia Open HIGH immediate reclaim."""
from __future__ import annotations

import json, math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_aoh1_asia_open_high_failed_acceptance as base

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_AOH2_AsiaOpen_Context_Optimization_Result.md"
OUT_JSON = ROOT / "BTC_AOH2_AsiaOpen_Context_Optimization_Result.json"
OUT_GRID = ROOT / "BTC_AOH2_AsiaOpen_Context_Optimization_Grid.csv"
OUT_AUG = ROOT / "BTC_AOH2_AsiaOpen_Context_Optimization_August.csv"

EXTERNAL_START = pd.Timestamp("2022-01-01T00:00:00Z")
EXTERNAL_END = pd.Timestamp("2023-12-02T00:00:00Z")
REFERENCE_START = pd.Timestamp("2023-12-02T00:00:00Z")
REFERENCE_END = pd.Timestamp("2026-07-30T00:00:00Z")
AUG_START = pd.Timestamp("2026-08-01T00:00:00Z")
AUG_END = pd.Timestamp("2026-08-20T00:00:00Z")

PRE_GRID = [0.0, 0.0005, 0.0010, 0.0015, 0.0020, 0.0030, 0.0050]
LOC_GRID = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
MIN_DEV_N = 12


def wilson(w: int, n: int, z: float = 1.959963984540054) -> tuple[float|None,float|None]:
    if n <= 0:
        return None, None
    p = w/n
    den = 1 + z*z/n
    center = (p + z*z/(2*n))/den
    half = z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return center-half, center+half


def detect_core(x5: pd.DataFrame, x15: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows=[]
    x5_by_ts={t:i for i,t in enumerate(x5.ts)}
    day=start.normalize()
    while day < end.normalize():
        prev=x5[(x5.ts>=day-pd.Timedelta(days=1)) & (x5.ts<day)]
        if len(prev)!=288:
            day += pd.Timedelta(days=1); continue
        pdh=float(prev.high.max()); pdl=float(prev.low.min())
        if pdh<=pdl:
            day += pd.Timedelta(days=1); continue
        ai=x5_by_ts.get(day); p60i=x5_by_ts.get(day-pd.Timedelta(minutes=60))
        if ai is None or p60i is None:
            day += pd.Timedelta(days=1); continue
        anchor=float(x5.open.iloc[int(ai)]); p60=float(x5.open.iloc[int(p60i)])
        pre60=anchor/p60-1.0
        loc=(anchor-pdl)/(pdh-pdl)
        z=x15[(x15.ts>=day)&(x15.ts<day+pd.Timedelta(minutes=90))]
        reclaim=None
        for _,r in z.iterrows():
            if float(r.high)>pdh and float(r.close)<=pdh:
                reclaim=r; break
        if reclaim is None:
            day += pd.Timedelta(days=1); continue
        reclaim_ts=pd.Timestamp(reclaim.ts)
        entry_ts=reclaim_ts+pd.Timedelta(minutes=15)
        ei=x5_by_ts.get(entry_ts)
        if ei is None:
            day += pd.Timedelta(days=1); continue
        tr=base.resolve_trade(x5,int(ei),float(reclaim.high))
        if tr is None:
            day += pd.Timedelta(days=1); continue
        d60=base.forward_diag(x5,int(ei),60); d120=base.forward_diag(x5,int(ei),120); d240=base.forward_diag(x5,int(ei),240)
        if d60 is None or d120 is None or d240 is None:
            day += pd.Timedelta(days=1); continue
        rows.append({
            "utc_date":day.strftime("%Y-%m-%d"),"anchor_ts":day,"anchor_price":anchor,"previous_day_high":pdh,"previous_day_low":pdl,
            "pre60_ret":pre60,"range_location":loc,"reclaim_ts":reclaim_ts,"reclaim_high":float(reclaim.high),"reclaim_close":float(reclaim.close),
            "entry_ts":entry_ts,"entry_wib":entry_ts+pd.Timedelta(hours=7),**tr,
            "ret60":d60["ret"],"ret120":d120["ret"],"ret240":d240["ret"]})
        day += pd.Timedelta(days=1)
    return pd.DataFrame(rows)


def filt(z: pd.DataFrame, pre: float, loc: float) -> pd.DataFrame:
    if z.empty: return z
    return z[(z.pre60_ret>=pre)&(z.range_location>=loc)].copy()


def stats(z: pd.DataFrame) -> dict:
    if z is None or z.empty:
        return {"n":0,"tp":0,"sl":0,"time":0,"wins":0,"wr":None,"wilson_lo":None,"wilson_hi":None,"net_positive_rate":None,
                "pnl":0.0,"expectancy":None,"median_risk_pct":None,"avg_target_pct":None,"avg_ret60":None,"avg_ret120":None,"avg_ret240":None}
    dec=z[z.outcome.isin(["TP","SL"])]
    w=int((dec.outcome=="TP").sum()); n=int(len(dec)); lo,hi=wilson(w,n)
    return {"n":int(len(z)),"tp":int((z.outcome=="TP").sum()),"sl":int((z.outcome=="SL").sum()),"time":int((z.outcome=="TIME").sum()),
            "wins":w,"wr":float(w/n) if n else None,"wilson_lo":lo,"wilson_hi":hi,"net_positive_rate":float(z.net_positive.mean()),
            "pnl":float(z.pnl.sum()),"expectancy":float(z.pnl.mean()),"median_risk_pct":float(z.risk_pct.median()),
            "avg_target_pct":float(z.raw_target_pct.mean()),"avg_ret60":float(z.ret60.mean()),"avg_ret120":float(z.ret120.mean()),"avg_ret240":float(z.ret240.mean())}


def blocks(z: pd.DataFrame) -> list[dict]:
    if z.empty: return []
    y=z.sort_values("entry_ts").reset_index(drop=True); bounds=np.linspace(0,len(y),5,dtype=int); out=[]
    for i in range(4):
        p=y.iloc[bounds[i]:bounds[i+1]].copy(); out.append({"block":f"B{i+1}",**stats(p)})
    return out


def rank_key(r: dict):
    # descending Wilson, WR, N, expectancy; then less restrictive thresholds.
    return (-(r["wilson_lo"] if r["wilson_lo"] is not None else -1),-(r["wr"] if r["wr"] is not None else -1),-r["n"],-(r["expectancy"] if r["expectancy"] is not None else -1e9),r["pre_min"],r["loc_min"])


def pct(v): return "-" if v is None else f"{100*v:.2f}%"


def main():
    x5=base.load_data(); x15=base.aggregate_15m(x5)
    ext=detect_core(x5,x15,EXTERNAL_START,EXTERNAL_END)
    ref=detect_core(x5,x15,REFERENCE_START,REFERENCE_END)
    aug=detect_core(x5,x15,AUG_START,AUG_END)
    ref=ref.sort_values("entry_ts").reset_index(drop=True); cut=int(math.floor(len(ref)*0.70)); dev=ref.iloc[:cut].copy(); val=ref.iloc[cut:].copy()

    grid=[]
    for pre in PRE_GRID:
        for loc in LOC_GRID:
            s=stats(filt(dev,pre,loc))
            grid.append({"pre_min":pre,"loc_min":loc,**s,"eligible_for_selection":bool(s["n"]>=MIN_DEV_N)})
    eligible=[r for r in grid if r["eligible_for_selection"]]
    if not eligible: raise RuntimeError("no grid cell meets development N>=12")
    eligible.sort(key=rank_key); selected=eligible[0]
    grid_sorted=sorted(grid,key=lambda r:(not r["eligible_for_selection"],rank_key(r)))
    pd.DataFrame(grid_sorted).to_csv(OUT_GRID,index=False)

    pre=float(selected["pre_min"]); loc=float(selected["loc_min"])
    cohorts={
        "development_selected":stats(filt(dev,pre,loc)),"reference_validation_selected":stats(filt(val,pre,loc)),
        "external_selected":stats(filt(ext,pre,loc)),"august_selected":stats(filt(aug,pre,loc)),
        "development_control":stats(dev),"reference_validation_control":stats(val),"external_control":stats(ext),"august_control":stats(aug)}
    ext_sel=filt(ext,pre,loc); ext_blocks=blocks(ext_sel); aug_sel=filt(aug,pre,loc)
    if aug_sel.empty: pd.DataFrame(columns=["utc_date"]).to_csv(OUT_AUG,index=False)
    else: aug_sel.to_csv(OUT_AUG,index=False)

    rs=cohorts["reference_validation_selected"]; es=cohorts["external_selected"]
    nonneg=sum(1 for b in ext_blocks if b["n"]==0 or (b["expectancy"] is not None and b["expectancy"]>=0))
    supported=bool(rs["n"]>=8 and rs["wr"] is not None and rs["wr"]>=.60 and es["n"]>=12 and es["wr"] is not None and es["wr"]>=.60 and es["pnl"]>0 and nonneg>=3)
    c80=bool(rs["n"]>=8 and rs["wr"] is not None and rs["wr"]>=.80 and rs["pnl"]>0 and es["n"]>=12 and es["wr"] is not None and es["wr"]>=.80 and es["pnl"]>0)

    result={"protocol":"AOH2_CONTEXT_OPT_V1","coverage":{"first":str(x5.ts.min()),"last":str(x5.ts.max())},"core_counts":{"external":len(ext),"reference":len(ref),"development":len(dev),"reference_validation":len(val),"august":len(aug)},
            "selected":{"pre60_min":pre,"location_min":loc,"development_selector":selected},"cohorts":cohorts,"external_blocks":ext_blocks,
            "AOH2_CONTEXT_SUPPORTED":supported,"AOH2_80_CANDIDATE":c80,"grid_count":len(grid)}
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str)+"\n")

    md=["# BTC AOH2 — Asia Open Context Optimization Result","",
        "Core setup unchanged: previous-day HIGH sweep -> immediate 15m reclaim -> SHORT next 15m open; structural SL; TP sized for **net 1:1 after 0.15% fee**.","",
        f"Core events: external **{len(ext)}**, reference **{len(ref)}** (development {len(dev)}, validation {len(val)}), August **{len(aug)}**.","",
        "## Frozen selected thresholds","",
        f"- PRE_UP 60m minimum: **{100*pre:.2f}%**",
        f"- Asia-open location in previous-day range: **>= {100*loc:.0f}%**",
        f"- Development selected N **{selected['n']}**, WR **{pct(selected['wr'])}**, Wilson lower **{pct(selected['wilson_lo'])}**, expectancy **${selected['expectancy']:.3f}/trade**.","",
        "## Exact selected rule vs unfiltered control","",
        "| Partition | Rule | N | TP | SL | WR | Wilson 95% low | PnL | Exp/trade | Median risk | Avg raw TP |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for part in ["development","reference_validation","external","august"]:
        for rule in ["selected","control"]:
            s=cohorts[f"{part}_{rule}"]
            md.append(f"| {part} | {rule} | {s['n']} | {s['tp']} | {s['sl']} | {pct(s['wr'])} | {pct(s['wilson_lo'])} | ${s['pnl']:.2f} | {('-' if s['expectancy'] is None else f'${s[\"expectancy\"]:.3f}')} | {pct(s['median_risk_pct'])} | {pct(s['avg_target_pct'])} |")
    md += ["","## External selected-rule blocks","","| Block | N | TP | SL | WR | PnL | Exp/trade |","|---|---:|---:|---:|---:|---:|---:|"]
    for b in ext_blocks:
        md.append(f"| {b['block']} | {b['n']} | {b['tp']} | {b['sl']} | {pct(b['wr'])} | ${b['pnl']:.2f} | {('-' if b['expectancy'] is None else f'${b[\"expectancy\"]:.3f}')} |")
    md += ["","## Top development grid cells","","| Rank | PRE60 min | Location min | N | WR | Wilson low | PnL | Exp/trade |","|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for i,r in enumerate(eligible[:10],1):
        md.append(f"| {i} | {100*r['pre_min']:.2f}% | {100*r['loc_min']:.0f}% | {r['n']} | {pct(r['wr'])} | {pct(r['wilson_lo'])} | ${r['pnl']:.2f} | ${r['expectancy']:.3f} |")
    md += ["",f"**AOH2_CONTEXT_SUPPORTED: {'PASS' if supported else 'FAIL'}**",f"**AOH2_80_CANDIDATE: {'PASS' if c80 else 'FAIL'}**","",
           "Thresholds were selected only from development data; validation, external, and August were not used to choose them. No post-result rescue."]
    OUT_MD.write_text("\n".join(md)+"\n")
    print(json.dumps(result,indent=2,default=str))

if __name__=="__main__": main()
