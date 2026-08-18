#!/usr/bin/env python3
"""Sunday Friday-method SF14 — August replay of fixed SF13 pre-entry morphology.

This is NOT untouched OOS because the research path continued after observing August weakness.
However, SF13 rule parameters are fixed before this replay and August pre-entry morphology is not
used to change the rule.

Rule: if immediate completed 5m candle before Sunday16 is bullish AND body > total wicks, WAIT.
Otherwise trade frozen SF6-SF8; also report the same gate on SF9 (SF6-SF8 + fixed FastMR).
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import sun22_sunday16_frozen_router_true_oos as sun22
import sunday_fridaymethod_sf11_sf12_preentry_regime as sf11

OUT=Path(os.getenv('SUNFM14_OUT','sunfm14_out')); OUT.mkdir(parents=True,exist_ok=True)
EXPECTED=['2026-08-02','2026-08-09','2026-08-16']


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:return {'n':0,'wins':0,'wr':None,'pnl':0.0,'pf':None}
    wins=int((a>0).sum());gp=float(a[a>0].sum());gl=float(-a[a<=0].sum())
    return {'n':len(a),'wins':wins,'wr':wins/len(a),'pnl':float(a.sum()),'pf':gp/gl if gl>0 else 999.0}


def entries(k):
    idx=k.index; local=idx+pd.Timedelta(hours=7)
    m=(idx>=pd.Timestamp('2026-08-01',tz='UTC'))&(idx<pd.Timestamp('2026-08-18',tz='UTC'))&(local.dayofweek==6)&(local.hour==16)&(local.minute==0)
    return list(idx[m])


def main():
    k,f=sun22.load_extended(); es=entries(k); dates=[t.strftime('%Y-%m-%d') for t in es]
    if dates!=EXPECTED:raise RuntimeError(f'dates {dates}')
    rows=[]; p68=[];p9=[];g68=[];g9=[]
    for t in es:
        tr=sf11.sun17.simulate_parent(k,f,t); b=sf11.frozen_sf68(k,f,tr); c=sf11.combined_sf9(k,f,tr,b); feat=sf11.pre_features(k,t)
        body=float(feat['last_body_ratio']);risk=bool(feat['last_green'] and body>(1.0-body))
        rows.append({'date':t.strftime('%Y-%m-%d'),'entry_t':str(t),'entry':float(tr['entry']),
                     'parent_pnl':float(tr['pnl']),'parent_mfe_pct':100*float(tr['mfe']),
                     'last_green':bool(feat['last_green']),'last_body_ratio':body,'last_total_wick_ratio':1.0-body,
                     'morph_wait':risk,'sf68_layer':b['layer'],'sf68_pnl':float(b['pnl']),'sf9_layer':c['layer'],'sf9_pnl':float(c['pnl']),
                     'gated_sf68_pnl':None if risk else float(b['pnl']),'gated_sf9_pnl':None if risk else float(c['pnl'])})
        p68.append(float(b['pnl']));p9.append(float(c['pnl']))
        if not risk:g68.append(float(b['pnl']));g9.append(float(c['pnl']))
    df=pd.DataFrame(rows)
    out={'status':'COMPLETE_POSTHOC_AUGUST_REPLAY_FIXED_SF13','dates':dates,'opportunities':3,'waits':int(df.morph_wait.sum()),
         'trades':int((~df.morph_wait).sum()),'sf68_ungated':metrics(p68),'sf9_ungated':metrics(p9),
         'sf68_gated_trades':metrics(g68),'sf9_gated_trades':metrics(g9),'rows':rows,
         'guardrail':'The SF13 morphology rule is fixed for this replay, but August weakness had already been observed earlier in the research path. Therefore this is post-hoc holdout replay, not untouched OOS confirmation.'}
    df.to_csv(OUT/'sunfm14_rows.csv',index=False);(OUT/'sunfm14_summary.json').write_text(json.dumps(out,indent=2,default=str))
    md=['# Sunday Friday-Method SF14 — August Morphology Replay','', '**Status: COMPLETE — fixed-rule post-hoc August replay; NOT untouched OOS.**','',
        '## Fixed SF13 gate','- bullish immediate pre-entry 5m candle + body > total wicks => WAIT.','',
        f"- Opportunities **3**; WAIT **{out['waits']}**; traded **{out['trades']}**.",
        f"- Ungated SF6-SF8 PnL **${out['sf68_ungated']['pnl']:+.2f}**; gated traded PnL **${out['sf68_gated_trades']['pnl']:+.2f}**.",
        f"- Ungated SF9 PnL **${out['sf9_ungated']['pnl']:+.2f}**; gated traded PnL **${out['sf9_gated_trades']['pnl']:+.2f}**.",'',
        '| Date | Green | Body | Wick | WAIT | SF6-SF8 | SF9 |','|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:md.append(f"| {r['date']} | {r['last_green']} | {r['last_body_ratio']:.3f} | {r['last_total_wick_ratio']:.3f} | {r['morph_wait']} | ${r['sf68_pnl']:+.2f} | ${r['sf9_pnl']:+.2f} |")
    md+=['','## Guardrail',out['guardrail']]
    (OUT/'SUNDAY_FRIDAY_METHOD_SF14_AUGUST_REPLAY.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
