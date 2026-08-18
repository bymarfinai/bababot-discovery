#!/usr/bin/env python3
from __future__ import annotations
import json, os
from pathlib import Path
import pandas as pd
import numpy as np
import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sun12_sunday_hold_exit_and_allhour_surface as s12

OUT=Path(os.getenv('SUN13_OUT','sun13_out')); OUT.mkdir(parents=True,exist_ok=True)

def pack(r):
    return s12.pack(r)

def main():
    k=f517.load_klines(); f=s50.load_funding(); fmap=s12.funding_map(k,f)
    entries,entry,highs,lows,closes,fund=s12.prepare_hour(k,fmap,9)
    df=pd.DataFrame(s12.evaluate_hour(9,entry,highs,lows,closes,fund))
    sell=df[df.direction=='SELL'].copy()
    sell['D_robust']=(sell.D_pnl>0)&(sell.D_pf>1.10)&(sell.D_pos_blocks>=4)
    sell['V_pass']=(sell.V_pnl>0)&(sell.V_pf>1.0)

    eq=sell[(sell.tp_pct==0.4)&(sell.sl_pct==0.4)].sort_values('hold_h')
    tp04_18=sell[(sell.hold_h==18)&(sell.tp_pct==0.4)].sort_values('sl_pct')
    sl04_18=sell[(sell.hold_h==18)&(sell.sl_pct==0.4)].sort_values('tp_pct')
    topD=sell.sort_values(['D_pnl','D_pf','D_wr'],ascending=False).head(20)
    topWR=sell.sort_values(['D_wr','D_pnl'],ascending=False).head(20)
    robust=sell[sell.D_robust].sort_values(['D_pnl','D_pf'],ascending=False)

    # Exact trade-outcome counts for the two focal 18h cells.
    def exact_cell(tp,sl,hh=18):
        it=int(np.where(np.isclose(s12.TP_GRID,tp))[0][0]); js=int(np.where(np.isclose(s12.SL_GRID,sl))[0][0])
        fav,adv=s12.precompute_indices(entry,highs,lows,-1)
        pnl,tp_m,sl_m,to_m=s12.outcome(entry,closes,fund,fav[:,it],adv[:,js],tp,sl,hh,-1)
        d=pnl[:s12.DISC_N]; v=pnl[s12.DISC_N:]
        return {
          'cell':f'{tp:.1f}/{sl:.1f}/{hh}h','D':s12.metrics(d),'V':s12.metrics(v),'full':s12.metrics(pnl),
          'full_tp_n':int(tp_m.sum()),'full_sl_n':int(sl_m.sum()),'full_timeout_n':int(to_m.sum()),
          'D_tp_n':int(tp_m[:s12.DISC_N].sum()),'D_sl_n':int(sl_m[:s12.DISC_N].sum()),'D_timeout_n':int(to_m[:s12.DISC_N].sum()),
          'V_tp_n':int(tp_m[s12.DISC_N:].sum()),'V_sl_n':int(sl_m[s12.DISC_N:].sum()),'V_timeout_n':int(to_m[s12.DISC_N:].sum())
        }

    out={
      'status':'COMPLETE_SUNDAY09_DEEPDIVE','definition':{'hour_wib':9,'direction':'SELL','n':139,'discovery_n':83,'validation_n':56,
        'holds_h':s12.HOLDS_H,'tp_grid':[0.3,2.5,0.1],'sl_grid':[0.3,1.5,0.1],'all_sell_cells':int(len(sell)),
        'fee_rt_pct':0.15,'notional':500,'funding':'historical','ambiguity':'adverse-first'},
      'all_combinations_were_tested':True,
      'equal_04_by_hold':[pack(r) for _,r in eq.iterrows()],
      'tp04_sl_sweep_18h':[pack(r) for _,r in tp04_18.iterrows()],
      'sl04_tp_sweep_18h':[pack(r) for _,r in sl04_18.iterrows()],
      'top20_discovery_pnl':[pack(r) for _,r in topD.iterrows()],
      'top20_discovery_wr':[pack(r) for _,r in topWR.iterrows()],
      'discovery_robust_cells':[pack(r) for _,r in robust.head(20).iterrows()],
      'exact_04_04_18h':exact_cell(0.4,0.4,18),
      'exact_04_15_18h':exact_cell(0.4,1.5,18),
    }
    (OUT/'sun13_summary.json').write_text(json.dumps(out,indent=2,default=str))

    e04=out['exact_04_04_18h']; e15=out['exact_04_15_18h']
    md=['# Sunday 09:00 WIB SELL — SUN1.3 TP/SL Deep Dive','',
        '**All TP/SL combinations from SUN1.2 were retested for this hour only. Live BBC untouched.**','',
        f"- SELL cells tested: **{len(sell)}** = 7 holds × 23 TP values × 13 SL values.",
        '- TP grid 0.3–2.5 step 0.1; SL grid 0.3–1.5 step 0.1; holds 1/2/4/6/8/12/18h.','',
        '## Exact TP0.4 / SL0.4 by hold']
    for _,r in eq.iterrows():
        md.append(f"- {int(r.hold_h)}h: D {r.D_pnl:+.2f}, WR {100*r.D_wr:.1f}%, PF {r.D_pf:.2f}; V {r.V_pnl:+.2f}, WR {100*r.V_wr:.1f}%, PF {r.V_pf:.2f}; Full {r.full_pnl:+.2f}")
    md += ['', '## 18h: TP fixed 0.4, SL sweep']
    for _,r in tp04_18.iterrows():
        md.append(f"- SL {r.sl_pct:.1f}: D {r.D_pnl:+.2f}, WR {100*r.D_wr:.1f}%, PF {r.D_pf:.2f}; V {r.V_pnl:+.2f}, PF {r.V_pf:.2f}; Full {r.full_pnl:+.2f}")
    md += ['', '## Outcome anatomy, 18h',
      f"- 0.4/0.4: full TP/SL/timeout **{e04['full_tp_n']}/{e04['full_sl_n']}/{e04['full_timeout_n']}**, full PnL **{e04['full']['pnl']:+.2f}**, WR **{100*e04['full']['wr']:.1f}%**, PF **{e04['full']['pf']:.2f}**.",
      f"- 0.4/1.5: full TP/SL/timeout **{e15['full_tp_n']}/{e15['full_sl_n']}/{e15['full_timeout_n']}**, full PnL **{e15['full']['pnl']:+.2f}**, WR **{100*e15['full']['wr']:.1f}%**, PF **{e15['full']['pf']:.2f}**.",'',
      '## Guardrail','Selection remains discovery-only; validation is shown only as a robustness check.']
    (OUT/'SUN1.3_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
