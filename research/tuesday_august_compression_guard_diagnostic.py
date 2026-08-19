#!/usr/bin/env python3
"""August-motivated Tuesday compression guard diagnostic.

IMPORTANT: candidate families are motivated by the three August failures, so this
is NOT untouched validation even if D/V historical slices look good. Purpose is
to identify a simple live-executable SHADOW guard worth freezing forward.

No TP/SL/management retuning. Volatility cutoffs are frozen discovery Q25 from
the prior forensic, not re-optimized numeric thresholds.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import tuesday_a511_true_oos_august as tue
import tuesday_august_failure_forensics as fa

OUT=Path(os.getenv('TUECOMPG_OUT','tuecompg_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=83


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:return {'n':0,'wins':0,'wr':None,'pnl':0.0,'pf':None,'exp':None}
    w=int((a>0).sum()); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':float(a.sum()),'pf':gp/gl if gl>0 else 999.0,'exp':float(a.mean())}


def build(k, es):
    rows=[]
    for t in es:
        tr=tue.simulate_parent(k,t); lr=tue.layered(k,tr); f=fa.feature_row(k,t)
        rows.append({'date':str((t+pd.Timedelta(hours=7)).date()),'mfe':tr['mfe'],'developed':tr['mfe']>=tue.HINGE,
                     'pnl':lr['a511_pnl'],**f})
    return pd.DataFrame(rows)


def eval_gate(hist, aug, name, fn):
    out={'gate':name}
    for lab,part in [('D',hist.iloc[:DISC_N]),('V',hist.iloc[DISC_N:]),('F',hist)]:
        m=fn(part).astype(bool); skip=part[m]; keep=part[~m]
        out[lab]={'skip':metrics(skip.pnl),'keep':metrics(keep.pnl),
                  'skip_develop':float(skip.developed.mean()) if len(skip) else None,
                  'keep_develop':float(keep.developed.mean()) if len(keep) else None,
                  'delta_wait':float(-skip.pnl.sum()),'coverage_keep':float(len(keep)/len(part))}
    am=fn(aug).astype(bool)
    out['august_hits']=int(am.sum()); out['august_dates']=aug.loc[am,'date'].tolist()
    out['cross_slice_improves']=bool(out['D']['delta_wait']>0 and out['V']['delta_wait']>0)
    out['cross_slice_lower_develop']=bool(
        out['D']['skip_develop'] is not None and out['V']['skip_develop'] is not None and
        out['D']['skip_develop']<out['D']['keep_develop'] and out['V']['skip_develop']<out['V']['keep_develop'])
    return out


def main():
    k=tue.load_extended(); parity=tue.historical_parity(k)
    if not parity['pass']: raise RuntimeError('parity fail')
    hist=build(k,tue.entries(k)); aug=build(k,tue.entries(k,pd.Timestamp('2026-08-01',tz='UTC'),pd.Timestamp('2026-08-19',tz='UTC')))
    D=hist.iloc[:DISC_N]
    q6=float(D.range6.quantile(.25)); q24=float(D.range24.quantile(.25))

    # Fixed, compact post-hoc family. No numeric sweep.
    gates=[
      ('LOW_RANGE6',lambda x:x.range6<=q6),
      ('LOW_RANGE24',lambda x:x.range24<=q24),
      ('DUAL_COMPRESSION',lambda x:(x.range6<=q6)&(x.range24<=q24)),
      ('BEARISH_SATURATION',lambda x:(~x.ema_bull)&(~x.ema20_rising)&(~x.taker1h_buy)),
      ('DUAL_COMP_PLUS_TAKER_SELL',lambda x:(x.range6<=q6)&(x.range24<=q24)&(~x.taker1h_buy)),
      ('DUAL_COMP_PLUS_EMA_BEAR',lambda x:(x.range6<=q6)&(x.range24<=q24)&(~x.ema_bull)),
      ('DUAL_COMP_PLUS_BEARISH_SATURATION',lambda x:(x.range6<=q6)&(x.range24<=q24)&(~x.ema_bull)&(~x.ema20_rising)&(~x.taker1h_buy)),
    ]
    res=[eval_gate(hist,aug,n,f) for n,f in gates]
    # Diagnostic champion: require all three August hits, then cross-slice PnL improvement, then max full improvement.
    elig=[r for r in res if r['august_hits']==3 and r['cross_slice_improves']]
    champ=max(elig,key=lambda r:r['F']['delta_wait']) if elig else None
    summary={'status':'COMPLETE_AUGUST_MOTIVATED_COMPRESSION_DIAGNOSTIC','historical_parity':parity,
             'frozen_discovery_thresholds':{'range6_q25':q6,'range24_q25':q24},'results':res,'diagnostic_champion':champ,
             'guardrail':'All compound gates are motivated after observing August, so they are post-hoc diagnostics. Even a D/V-positive result is only a shadow-guard candidate. Freeze without further tuning and require future Tuesdays before live use.'}
    (OUT/'tuesday_august_compression_guard_summary.json').write_text(json.dumps(summary,indent=2,default=str))
    md=['# Tuesday August Compression Guard Diagnostic','',
        '**Status: COMPLETE — post-hoc August-motivated diagnostic; live BBC untouched.**','',
        f'- Frozen D Q25 range6: **{100*q6:.3f}%**; range24: **{100*q24:.3f}%**.','',
        '| Candidate WAIT guard | Aug hits | D skip N | D delta | V skip N | V delta | Full skip N | Full delta | Keep coverage | Cross-slice? |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in res:
        md.append(f"| {r['gate']} | {r['august_hits']}/3 | {r['D']['skip']['n']} | ${r['D']['delta_wait']:+.2f} | {r['V']['skip']['n']} | ${r['V']['delta_wait']:+.2f} | {r['F']['skip']['n']} | ${r['F']['delta_wait']:+.2f} | {100*r['F']['coverage_keep']:.1f}% | {'YES' if r['cross_slice_improves'] else 'NO'} |")
    md += ['', '## Diagnostic interpretation']
    if champ:
        md += [f"- Best candidate that catches all three August failures and improves both historical chronology slices: **{champ['gate']}**.",
               f"- Historical WAIT delta: D **${champ['D']['delta_wait']:+.2f}**, V **${champ['V']['delta_wait']:+.2f}**, full **${champ['F']['delta_wait']:+.2f}**.",
               f"- Retains **{100*champ['F']['coverage_keep']:.1f}%** of Tuesday trades.",
               '- This is suitable only as a **frozen shadow guard** because August motivated the conjunction.']
    else:
        md += ['- **No compound candidate both catches all 3 August failures and improves D + V.**',
               '- Therefore there is no defensible new WAIT rule from the current evidence.']
    md += ['', '## Guardrail',summary['guardrail']]
    (OUT/'TUESDAY_AUGUST_COMPRESSION_GUARD_DIAGNOSTIC.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__':main()
