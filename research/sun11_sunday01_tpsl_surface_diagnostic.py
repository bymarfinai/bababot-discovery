#!/usr/bin/env python3
"""SUN1.1 — Persist full Sunday 01:00 TP/SL surface after SUN1.0 strict-gate miss.

No validation-based retuning. Same frozen grid/entry/hold/costs as SUN1.0.
This run is descriptive: identify discovery-only raw and plateau champions, report validation,
and explain exactly why SUN1.0 found no strict-eligible cell.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import sun10_sunday01_tpsl_surface as s10

OUT=Path(os.getenv('SUN11_OUT','sun11_out')); OUT.mkdir(parents=True,exist_ok=True)


def pack(s):
    keys=['tp_pct','sl_pct','rr','D_pnl','D_wr','D_pf','D_dd','D_expectancy','D_positive_blocks_5',
          'V_pnl','V_wr','V_pf','V_dd','V_expectancy','full_pnl','full_wr','full_pf','full_dd',
          'full_expectancy','full_positive_blocks_8','tp_count','sl_count','timeout_count','ambiguous_count',
          'neighbor_n','neighbor_D_pnl_median','neighbor_D_pnl_min','neighbor_D_positive_share']
    out={}
    for k in keys:
        v=s[k]
        if isinstance(v,(np.integer,)): v=int(v)
        elif isinstance(v,(np.floating,)): v=float(v)
        out[k]=v
    return out


def main():
    k=f517.load_klines(); entries=s10.sunday_entries(k)
    if len(entries)!=139: raise RuntimeError(f'entry parity {len(entries)}')
    rows=[]
    for tp in s10.TP_GRID:
        for sl in s10.SL_GRID:
            outs=[s10.simulate(k,t,tp,sl) for t in entries]
            pnls=np.array([o['pnl'] for o in outs],float)
            d=pnls[:s10.DISC_N]; v=pnls[s10.DISC_N:]
            dm=s10.metrics(d); vm=s10.metrics(v); fm=s10.metrics(pnls)
            db=s10.block_pnls(d,5); fb=s10.block_pnls(pnls,8)
            rc=pd.Series([o['reason'] for o in outs]).value_counts().to_dict()
            rows.append({
              'tp_pct':tp,'sl_pct':sl,'rr':tp/sl,
              'D_pnl':dm['pnl'],'D_wr':dm['wr'],'D_pf':dm['pf'],'D_dd':dm['dd'],'D_expectancy':dm['expectancy'],
              'D_positive_blocks_5':sum(x>0 for x in db),
              'V_pnl':vm['pnl'],'V_wr':vm['wr'],'V_pf':vm['pf'],'V_dd':vm['dd'],'V_expectancy':vm['expectancy'],
              'full_pnl':fm['pnl'],'full_wr':fm['wr'],'full_pf':fm['pf'],'full_dd':fm['dd'],'full_expectancy':fm['expectancy'],
              'full_positive_blocks_8':sum(x>0 for x in fb),
              'tp_count':int(rc.get('TP',0)),'sl_count':int(rc.get('SL',0)),'timeout_count':int(rc.get('TIMEOUT',0)),
              'ambiguous_count':sum(bool(o['ambiguous']) for o in outs),
            })
    df=pd.DataFrame(rows)
    for i,r in df.iterrows():
        n=df[(df.tp_pct.sub(r.tp_pct).abs()<=.1000001)&(df.sl_pct.sub(r.sl_pct).abs()<=.1000001)]
        df.loc[i,'neighbor_n']=len(n)
        df.loc[i,'neighbor_D_pnl_median']=float(n.D_pnl.median())
        df.loc[i,'neighbor_D_pnl_min']=float(n.D_pnl.min())
        df.loc[i,'neighbor_D_positive_share']=float((n.D_pnl>0).mean())
    df['strict_eligible']=(df.D_pnl>0)&(df.D_pf>1.10)&(df.D_positive_blocks_5>=4)
    df.to_csv(OUT/'sun11_surface.csv',index=False)

    rawD=df.sort_values(['D_pnl','D_pf'],ascending=False).iloc[0]
    pos=df[df.D_pnl>0].copy()
    plateau=(pos.sort_values(['neighbor_D_pnl_median','D_pnl'],ascending=False).iloc[0] if len(pos) else rawD)
    rawFull=df.sort_values('full_pnl',ascending=False).iloc[0]
    max_blocks=int(df.D_positive_blocks_5.max())
    best_pf=df.sort_values('D_pf',ascending=False).iloc[0]
    strict_n=int(df.strict_eligible.sum())
    positive_n=int((df.D_pnl>0).sum())
    pf110_n=int((df.D_pf>1.10).sum())
    blocks4_n=int((df.D_positive_blocks_5>=4).sum())

    out={
      'status':'DESCRIPTIVE_DISCOVERY_ONLY_SELECTION_VALIDATION_REPORTED',
      'definition':{'entry':'Sunday 01:00 WIB BUY','hold_min':240,'grid_cells':len(df),'tp_grid_pct':[0.3,2.5,0.1],'sl_grid_pct':[0.3,1.5,0.1],
                    'discovery_n':83,'validation_n':56,'notional':500,'fee_rt_pct':0.15,'ambiguity':'adverse-first'},
      'strict_gate':{'strict_eligible_cells':strict_n,'D_positive_cells':positive_n,'D_pf_gt_1_10_cells':pf110_n,'D_blocks_ge4_cells':blocks4_n,'max_D_positive_blocks_5':max_blocks},
      'raw_discovery_pnl_champion':pack(rawD),
      'discovery_plateau_champion':pack(plateau),
      'raw_full_sample_champion_reference_only':pack(rawFull),
      'best_discovery_pf_cell':pack(best_pf),
      'top20_discovery_pnl':[pack(r) for _,r in df.sort_values('D_pnl',ascending=False).head(20).iterrows()],
      'top20_plateau':[pack(r) for _,r in df.sort_values(['neighbor_D_pnl_median','D_pnl'],ascending=False).head(20).iterrows()],
      'guardrail':'Validation was not used to select rawD or plateau. Raw full-sample champion is reference only and must not be promoted.'}
    (OUT/'sun11_summary.json').write_text(json.dumps(out,indent=2,default=str))

    rd=out['raw_discovery_pnl_champion']; pl=out['discovery_plateau_champion']; rf=out['raw_full_sample_champion_reference_only']
    md=['# BTC Sunday 01:00 WIB — SUN1.1 TP/SL Surface Diagnostic','',
        '**Status: COMPLETE — descriptive discovery selection; validation reported; live BBC untouched.**','',
        '## Why SUN1.0 strict gate had no champion',
        f"- grid cells: **{len(df)}**",
        f"- discovery-PnL-positive cells: **{positive_n}**",
        f"- discovery PF >1.10 cells: **{pf110_n}**",
        f"- >=4/5 discovery-positive-block cells: **{blocks4_n}**",
        f"- all three simultaneously: **{strict_n}**",
        f"- maximum discovery-positive blocks achieved by any cell: **{max_blocks}/5**",'',
        '## Raw discovery PnL champion (selected without validation)',
        f"- **TP {rd['tp_pct']:.1f}% / SL {rd['sl_pct']:.1f}% (RR {rd['rr']:.2f})**",
        f"- D: PnL **${rd['D_pnl']:+.3f}**, WR **{100*rd['D_wr']:.2f}%**, PF **{rd['D_pf']:.3f}**, DD **${rd['D_dd']:.3f}**, blocks **{int(rd['D_positive_blocks_5'])}/5**",
        f"- V: PnL **${rd['V_pnl']:+.3f}**, WR **{100*rd['V_wr']:.2f}%**, PF **{rd['V_pf']:.3f}**, DD **${rd['V_dd']:.3f}**",
        f"- Full: PnL **${rd['full_pnl']:+.3f}**, WR **{100*rd['full_wr']:.2f}%**, PF **{rd['full_pf']:.3f}**, DD **${rd['full_dd']:.3f}**, blocks **{int(rd['full_positive_blocks_8'])}/8**",'',
        '## Discovery plateau champion',
        f"- **TP {pl['tp_pct']:.1f}% / SL {pl['sl_pct']:.1f}%**; neighborhood median D PnL **${pl['neighbor_D_pnl_median']:+.3f}**",
        f"- D **${pl['D_pnl']:+.3f}** / V **${pl['V_pnl']:+.3f}** / Full **${pl['full_pnl']:+.3f}** / PF full **{pl['full_pf']:.3f}**",'',
        '## Full-sample max reference only',
        f"- TP {rf['tp_pct']:.1f}% / SL {rf['sl_pct']:.1f}% → full **${rf['full_pnl']:+.3f}** (NOT eligible for selection because it sees validation)",'',
        '## Guardrail','Do not choose a different TP/SL because it looks better in validation. If discovery-selected settings fail validation, the correct conclusion is that 4h static TP/SL is not yet robust enough.']
    (OUT/'SUN1.1_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
