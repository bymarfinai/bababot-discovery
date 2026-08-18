#!/usr/bin/env python3
"""F6.41 — Friday F6.38 frozen true-OOS replay into August 2026.

Research only; live BBC untouched.

No retuning. Replays the exact F6.38 architecture on post-cutoff Fridays:
- 2026-07-31 (post-cutoff context observation)
- 2026-08-07
- 2026-08-14

Headline August score uses Aug 7 and Aug 14 only.
"""
from __future__ import annotations

import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f610_friday_early_sink_true_oos as f610
import f616_friday_post1r_profit_protection as f616
import f624_friday_context_repair_failure_management as f624
import f626_friday_failed_launch10_management as f626
import f629_friday_context_recovery_fail20_management as f629
import f631_friday_flow_reversal_recovery_guard as f631
import f636_friday_preentry_rejection_morphology_management as f636
import f637_friday_relative_upper_rejection_forensic as f637

OUT=Path(os.getenv('F641_OUT','f641_out')); OUT.mkdir(parents=True,exist_ok=True)
DATES=['2026-07-31','2026-08-07','2026-08-14']
AUG={'2026-08-07','2026-08-14'}


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0: return {'n':0,'wins':0,'wr':None,'pnl':0.0,'pf':None,'exp':None}
    gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    return {'n':int(len(a)),'wins':int((a>0).sum()),'wr':float((a>0).mean()),'pnl':float(a.sum()),
            'pf':float(gp/gl) if gl>0 else 999.0,'exp':float(a.mean())}


def apply_f638(k,t,tr):
    # Exact frozen five-layer base used by F6.38.
    bst=f624.state(k,tr)
    base_pnl,base_layer,base_dt=f624.apply(k,t,tr,bst)

    watch=f626.failed_launch_state(k,t,tr)
    watch_active=False
    if watch is not None and watch[f626.RULE]:
        watch_active=bool(base_dt is None or watch['decision_t']<pd.Timestamp(base_dt))

    st=f629.candidate_state(k,t,tr) if watch_active else None
    gs=f631.guard_state(k,t,tr) if watch_active else None

    f629_action=False; f629_pnl=float(base_pnl); guarded20=False
    if st is not None and st[f629.RULE] and (base_dt is None or st['decision_t']<pd.Timestamp(base_dt)):
        f629_action=True
        f629_pnl=float(f616.cut_pnl(float(tr.entry),float(st['decision_open'])))
        guarded20=bool(gs is not None and gs[f631.RULE])

    lf=f637.local_features(k,t)
    upper=float(lf['rel_last_upper']) if lf is not None else float('nan')
    body_exp=float(lf['rel_body_delta_prev3median']) if lf is not None else float('nan')
    balance=bool(upper>body_exp) if lf is not None else False

    managed=float(base_pnl); action='BASE'; route35='NONE'; c35=None
    if f629_action:
        if guarded20:
            route35='FLOW_DIVERGENCE'
            managed,action,c35=f636.resolve35(k,t,tr,base_pnl,base_dt)
        elif balance:
            route35='REJECTION_GT_BODY_EXPANSION'
            managed,action,c35=f636.resolve35(k,t,tr,base_pnl,base_dt)
        else:
            managed=f629_pnl; action='CUT20'

    return {
        'base_pnl':float(base_pnl),'base_layer':str(base_layer),'base_dt':None if base_dt is None else str(base_dt),
        'watch_active':bool(watch_active),'f629_action':bool(f629_action),'guarded20':bool(guarded20),
        'rel_last_upper':upper,'rel_body_delta_prev3median':body_exp,
        'balance_margin':upper-body_exp if lf is not None else float('nan'),'balance_gate':bool(balance),
        'route35':route35,'action':action,'managed_pnl':float(managed),
        'higher_close35':None if c35 is None else bool(c35['higher_close']),
    }


def main():
    k=f610.load_extended(); rows=[]
    for ds in DATES:
        t=pd.Timestamp(ds,tz='UTC')+pd.Timedelta(hours=8)  # Friday 15:00 WIB
        tr=f517.simulate_parent(k,t)
        m=apply_f638(k,t,tr)
        rows.append({
            'date':ds,'period':'AUGUST' if ds in AUG else 'POST_CUTOFF_JULY',
            'entry':float(tr.entry),'parent_reason':tr.reason,'parent_pnl':float(tr.pnl),
            'parent_mfe_pct':100*float(tr.mfe),'parent_mae_pct':100*float(tr.mae),
            **m,'delta_vs_parent':float(m['managed_pnl']-tr.pnl),'delta_vs_base':float(m['managed_pnl']-m['base_pnl'])
        })

    df=pd.DataFrame(rows); df.to_csv(OUT/'f641_oos_rows.csv',index=False)
    aug=df[df.period=='AUGUST'].copy(); allp=df.copy()
    out={
        'status':'COMPLETE_TRUE_OOS_F638_REPLAY',
        'research_last_same_sample_friday':'2026-07-24',
        'dates':DATES,
        'august_dates':['2026-08-07','2026-08-14'],
        'august':{
            'parent':metrics(aug.parent_pnl.to_numpy(float)),
            'five_layer':metrics(aug.base_pnl.to_numpy(float)),
            'f638':metrics(aug.managed_pnl.to_numpy(float)),
            'f638_delta_vs_five_layer':float((aug.managed_pnl-aug.base_pnl).sum()),
            'f638_delta_vs_parent':float((aug.managed_pnl-aug.parent_pnl).sum()),
            'watch_active':int(aug.watch_active.sum()),'f629_actions':int(aug.f629_action.sum()),
            'route35_actions':int((aug.route35!='NONE').sum()),
        },
        'post_cutoff_all3':{
            'parent':metrics(allp.parent_pnl.to_numpy(float)),
            'five_layer':metrics(allp.base_pnl.to_numpy(float)),
            'f638':metrics(allp.managed_pnl.to_numpy(float)),
            'f638_delta_vs_five_layer':float((allp.managed_pnl-allp.base_pnl).sum()),
        },
        'rows':df.to_dict('records'),
        'guardrail':'Only two August Fridays are available as of 2026-08-18. Rule is replayed unchanged; N=2 cannot confirm or reject the edge.'
    }
    (OUT/'f641_summary.json').write_text(json.dumps(out,indent=2,default=str))

    a=out['august']; am=a['f638']
    def wr(m): return '-' if m['wr'] is None else f"{100*m['wr']:.1f}%"
    md=['# Friday F6.41 — F6.38 Frozen True-OOS August Replay','',
        '**Status: COMPLETE — TRUE-OOS OBSERVATION; F6.38 unchanged; live BBC untouched.**','',
        '## August headline',
        f"- August Fridays available: **2** (2026-08-07, 2026-08-14).",
        f"- Parent: {a['parent']['wins']}/{a['parent']['n']} wins, WR **{wr(a['parent'])}**, PnL **${a['parent']['pnl']:+.3f}**.",
        f"- Frozen five-layer: WR **{wr(a['five_layer'])}**, PnL **${a['five_layer']['pnl']:+.3f}**.",
        f"- F6.38: {am['wins']}/{am['n']} wins, WR **{wr(am)}**, PnL **${am['pnl']:+.3f}**, PF **{'-' if am['pf'] is None else f'{am['pf']:.3f}'}**.",
        f"- F6.38 delta vs five-layer: **${a['f638_delta_vs_five_layer']:+.3f}**; vs parent **${a['f638_delta_vs_parent']:+.3f}**.",
        f"- WATCH active {a['watch_active']}; F6.29 actions {a['f629_actions']}; routed +35 {a['route35_actions']}.",'',
        '## Trade by trade','',
        '| Date | Parent | Five-layer | F6.38 | Watch? | F629? | Route | Action |','|---|---:|---:|---:|---:|---:|---|---|']
    for r in rows:
        md.append(f"| {r['date']} | ${r['parent_pnl']:+.3f} | ${r['base_pnl']:+.3f} | ${r['managed_pnl']:+.3f} | {r['watch_active']} | {r['f629_action']} | {r['route35']} | {r['action']} |")
    md += ['', '## Guardrail',out['guardrail']]
    (OUT/'F6.41_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
