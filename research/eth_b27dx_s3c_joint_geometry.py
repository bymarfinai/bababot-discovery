#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
BASE_PATH=HERE/'eth_b27dx_pair_calibration_v2.py'
spec=importlib.util.spec_from_file_location('eth_v2_base',BASE_PATH); b=importlib.util.module_from_spec(spec)
assert spec.loader is not None; spec.loader.exec_module(b)

PFX='ETH_B27DX_S3C_JOINT_GEOMETRY'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_SCORES=ROOT/f'{PFX}_Scores.csv'; OUT_CELLS=ROOT/f'{PFX}_CellSummary.csv'; OUT_COMPONENTS=ROOT/f'{PFX}_Components.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'; OUT_REP=ROOT/f'{PFX}_Representative.csv'
REF_MIN=300; HORIZON_MIN=360
CLOCKS=(300,540,600,960)
ENTRIES=(0.85,0.80,0.75,0.70)
TARGETS=(0.10,0.15,0.20,0.25,0.30,0.35,0.40)
STOPS=(0.20,0.15)
PARTS=('development','external','reference_validation')
BTC_WR=0.719298; BTC_PF=2.223193; BTC_EXP=1.26; BTC_MAX_LS=3

def clock_label(v): return f'{(v//60)%24:02d}:{v%60:02d}'
def f_label(v): return f'F{int(round(v*100)):02d}'
def t_label(v): return f'E{int(round(v*100)):02d}'
def finite(v):
    if pd.isna(v): return np.nan
    return 999999.0 if math.isinf(float(v)) else float(v)
def positive(part,r):
    if part=='development': return bool(r['n']>=30 and r['pf']>=1.10 and r['expectancy']>0 and r['net']>0)
    return bool(r['n']>=15 and r['pf']>1.00 and r['expectancy']>0 and r['net']>0)

def run_scores(x):
    rows=[]
    cache={}
    for ef in ENTRIES:
        for ex in CLOCKS:
            for p in PARTS:
                cache[(ef,ex,p)]=b.sessions_for(x,p,ex,REF_MIN,HORIZON_MIN,'LONG',ef)
    for ef in ENTRIES:
        for te in TARGETS:
            for sf in STOPS:
                for ex in CLOCKS:
                    for p in PARTS:
                        r=b.score_config(x=x,part_name=p,side='LONG',exec_min=ex,ref_min=REF_MIN,horizon_min=HORIZON_MIN,
                                         entry_f=ef,target_ext=te,stop_f=sf,stress_bps=0.0,cached=cache[(ef,ex,p)])
                        r['execution_utc']=clock_label(ex); r['entry']=f_label(ef); r['target']=t_label(te); r['stop']=f_label(sf); r['positive']=positive(p,r); rows.append(r)
    return pd.DataFrame(rows)

def summarize(scores):
    robust_rows=[]; cell_rows=[]
    for ef in ENTRIES:
        for te in TARGETS:
            for sf in STOPS:
                q=scores[(scores.entry_f==ef)&(scores.target_ext==te)&(scores.stop_f==sf)]
                robust_clocks=[]
                for ex in CLOCKS:
                    z=q[q.exec_min==ex]
                    if len(z)==3 and all(bool(z.loc[z.partition==p,'positive'].iloc[0]) for p in PARTS): robust_clocks.append(ex)
                rz=q[q.exec_min.isin(robust_clocks)] if robust_clocks else q.iloc[0:0]
                wr=pd.to_numeric(rz.wr,errors='coerce').dropna(); pf=[finite(v) for v in rz.pf if not pd.isna(v)]; exp=pd.to_numeric(rz.expectancy,errors='coerce').dropna(); ls=pd.to_numeric(rz.max_ls,errors='coerce').dropna(); n=pd.to_numeric(rz.n,errors='coerce').dropna()
                rwr=float(wr.median()) if len(wr) else np.nan; rpf=float(np.median(pf)) if pf else np.nan; rexp=float(exp.median()) if len(exp) else np.nan; rls=float(ls.median()) if len(ls) else np.nan
                supported=len(robust_clocks)>=2
                btcq=bool(supported and rwr>=BTC_WR and rpf>=BTC_PF and rexp>=BTC_EXP)
                cell_rows.append({'entry_f':ef,'entry':f_label(ef),'target_ext':te,'target':t_label(te),'stop_f':sf,'stop':f_label(sf),
                                  'robust_clock_count':len(robust_clocks),'robust_clocks':','.join(clock_label(x) for x in robust_clocks),
                                  'robust_major_median_wr':rwr,'robust_major_median_pf':rpf,'robust_major_median_exp':rexp,'robust_major_median_max_ls':rls,
                                  'robust_major_median_n':float(n.median()) if len(n) else np.nan,'btc_wr_gap_pp':100*(rwr-BTC_WR) if len(wr) else np.nan,
                                  'btc_pf_gap':rpf-BTC_PF if pf else np.nan,'btc_exp_gap':rexp-BTC_EXP if len(exp) else np.nan,
                                  'btc_quality_diagnostic_pass':btcq,'supported':supported})
                for ex in robust_clocks: robust_rows.append({'entry_f':ef,'entry':f_label(ef),'target_ext':te,'target':t_label(te),'stop_f':sf,'stop':f_label(sf),'exec_min':ex,'execution_utc':clock_label(ex)})
    return pd.DataFrame(cell_rows),pd.DataFrame(robust_rows)

def components(cells):
    ei={v:i for i,v in enumerate(ENTRIES)}; ti={v:i for i,v in enumerate(TARGETS)}; si={v:i for i,v in enumerate(STOPS)}
    coord={(ei[e],ti[t],si[s]):(e,t,s) for e,t,s in cells}; unseen=set(coord); comps=[]
    while unseen:
        seed=min(unseen); stack=[seed]; unseen.remove(seed); comp=[]
        while stack:
            c=stack.pop(); comp.append(coord[c]);
            for axis in range(3):
                for d in (-1,1):
                    n=list(c); n[axis]+=d; n=tuple(n)
                    if n in unseen: unseen.remove(n); stack.append(n)
        comps.append(comp)
    return comps

def qualifying(comp):
    return len(comp)>=6 and len({e for e,_,_ in comp})>=2 and len({t for _,t,_ in comp})>=2 and len({s for _,_,s in comp})==2

def representative(comp):
    ei={v:i for i,v in enumerate(ENTRIES)}; ti={v:i for i,v in enumerate(TARGETS)}; si={v:i for i,v in enumerate(STOPS)}
    med=np.array([np.median([ei[e] for e,_,_ in comp]),np.median([ti[t] for _,t,_ in comp]),np.median([si[s] for _,_,s in comp])],dtype=float)
    def key(cell):
        e,t,s=cell; idx=np.array([ei[e],ti[t],si[s]],dtype=float); dist=float(np.abs(idx-med).sum())
        return (dist,-e,t,-s)
    return min(comp,key=key),med

def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=b.m.m.load5(); scores=run_scores(x); scores.to_csv(OUT_SCORES,index=False); cells,robust=summarize(scores); cells.to_csv(OUT_CELLS,index=False)
    supported=cells[cells.supported].copy(); tuples=[(float(r.entry_f),float(r.target_ext),float(r.stop_f)) for r in supported.itertuples(index=False)]; comps=components(tuples) if tuples else []
    comp_rows=[]; quals=[]
    for i,c in enumerate(sorted(comps,key=lambda z:(-len(z),sorted(z))),1):
        q=qualifying(c); quals.append((i,c)) if q else None
        comp_rows.append({'component':i,'cells':len(c),'entries':','.join(f_label(v) for v in sorted({e for e,_,_ in c},reverse=True)),
                          'targets':','.join(t_label(v) for v in sorted({t for _,t,_ in c})),'stops':','.join(f_label(v) for v in sorted({s for _,_,s in c},reverse=True)),'qualifying':q})
    pd.DataFrame(comp_rows).to_csv(OUT_COMPONENTS,index=False)
    rep_row=None
    if quals:
        # largest qualifying component; component ordering above is deterministic
        cid,comp=quals[0]; rep,_=representative(comp); e,t,s=rep
        rep_row=cells[(cells.entry_f==e)&(cells.target_ext==t)&(cells.stop_f==s)].iloc[0].to_dict(); rep_row['component']=cid
        pd.DataFrame([rep_row]).to_csv(OUT_REP,index=False)
        status='ETH_S3C_JOINT_GEOMETRY_SUPPORTED'
    elif len(supported):
        pd.DataFrame().to_csv(OUT_REP,index=False); status='ETH_S3C_SUPPORTED_CELLS_NO_3D_FAMILY'
    else:
        pd.DataFrame().to_csv(OUT_REP,index=False); status='ETH_S3C_NO_SUPPORTED_JOINT_CELL'

    lines=['# ETH B27DX — S3C Joint Native Trade Geometry — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',
           'Frozen structural layer: **R300/X360**, clocks **05:00, 09:00, 10:00, 16:00 UTC**. S3C crosses only previously supported families: entry F85–F70, target E10–E40, invalidation F20–F15.','',
           f'- Total joint cells: **{len(cells)}**.','- Supported joint cells: **%d**.'%len(supported),'- BTC-quality diagnostic supported cells: **%d**.'%int(supported.btc_quality_diagnostic_pass.sum() if len(supported) else 0),'',
           '## Supported joint cells','',
           '| Entry | Target | Stop | Robust clocks | Labels | Robust WR | Robust PF | Robust Exp | Max LS | BTC-quality diag |',
           '|---:|---:|---:|---:|---|---:|---:|---:|---:|---|']
    if supported.empty: lines.append('| - | - | - | - | - | - | - | - | - | - |')
    else:
        for r in supported.sort_values(['entry_f','target_ext','stop_f'],ascending=[False,True,False]).itertuples(index=False):
            lines.append(f'| {r.entry} | {r.target} | {r.stop} | {r.robust_clock_count}/4 | {r.robust_clocks} | {pct(r.robust_major_median_wr)} | {fmt(r.robust_major_median_pf)} | {fmt(r.robust_major_median_exp)} | {fmt(r.robust_major_median_max_ls,1)} | {"PASS" if r.btc_quality_diagnostic_pass else "NO"} |')
    lines += ['','## 3D connected components','']
    if not comp_rows: lines.append('None.')
    else:
        lines += ['| Component | Cells | Entries | Targets | Stops | Qualifying |','|---:|---:|---|---|---|---|']
        for r in comp_rows: lines.append(f'| {r["component"]} | {r["cells"]} | {r["entries"]} | {r["targets"]} | {r["stops"]} | {"YES" if r["qualifying"] else "NO"} |')
    lines += ['','## Deterministic representative','']
    if rep_row is None: lines.append('None.')
    else:
        lines += [f'- Component: **{rep_row["component"]}**.',f'- Geometry: **{f_label(rep_row["entry_f"])} / {t_label(rep_row["target_ext"])} / {f_label(rep_row["stop_f"])}**.',
                  f'- Robust clocks: **{rep_row["robust_clocks"]}**.',f'- Robust-major WR: **{pct(rep_row["robust_major_median_wr"])}**.',f'- Robust-major PF: **{fmt(rep_row["robust_major_median_pf"])}**.',f'- Robust-major expectancy: **{fmt(rep_row["robust_major_median_exp"])}**.',f'- BTC-quality diagnostic: **{"PASS" if rep_row["btc_quality_diagnostic_pass"] else "NO"}**.']
    lines += ['','## BTC benchmark','',f'- BTC B27DX LONG: WR **71.9%**, PF **2.22**, expectancy **+$1.26/trade**, max loss streak **3**.','- S3C benchmark labels are diagnostic only until global one-position portfolio locking removes overlapping clock candidates.','',
              '## Decision','',f'**Status: {status}**','', '- No runner, leverage, lifecycle, clock, fee, or live-code changes were made.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text(status+'\n'); print(OUT_MD.read_text())
if __name__=='__main__': main()
