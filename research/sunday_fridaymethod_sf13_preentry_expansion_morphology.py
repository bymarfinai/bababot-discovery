#!/usr/bin/env python3
"""Sunday Friday-method SF13 — pre-entry bullish expansion morphology.

Single natural morphology motivated by SF11, mirroring Friday's geometry-first approach.
No fitted magnitude threshold and no timing sweep.

Risk state at the immediate completed 5m candle before Sunday16 entry:
- candle is bullish (close > open), AND
- body length > total wick length (body-dominant expansion).

Primary action under test: WAIT (skip entry) on this state; otherwise retain the exact frozen SF6-SF8 entry/management.
The identical gate is also reported on SF9 (SF6-SF8 + fixed FastMR).
Discovery/validation are report slices only; no re-selection.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sunday_fridaymethod_sf11_sf12_preentry_regime as sf11

OUT=Path(os.getenv('SUNFM13_OUT','sunfm13_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=83


def pack(a):
    a=np.asarray(a,float)
    return {'full':sf11.metrics(a),'D':sf11.metrics(a[:DISC_N]),'V':sf11.metrics(a[DISC_N:])}


def main():
    k=f517.load_klines(); f=s50.load_funding(); trs=[sf11.sun17.simulate_parent(k,f,t) for t in sf11.sun17.entries(k)]
    rows=[]; base=[]; sf9=[]
    for i,tr in enumerate(trs):
        feat=sf11.pre_features(k,tr['entry_t']); b=sf11.frozen_sf68(k,f,tr); c=sf11.combined_sf9(k,f,tr,b)
        body=float(feat['last_body_ratio']); wicks=1.0-body
        risk=bool(feat['last_green'] and body>wicks)
        rows.append({'i':i,'period':'D' if i<DISC_N else 'V','date':str(tr['entry_t'].date()),
                     'parent_pnl':float(tr['pnl']),'parent_mfe_r':float(tr['mfe']/sf11.R),
                     'failure_to_develop':bool(tr['pnl']<=0 and tr['mfe']<0.5*sf11.R),
                     'last_green':bool(feat['last_green']),'body_ratio':body,'total_wick_ratio':wicks,
                     'bull_body_dominant':risk,'sf68_pnl':float(b['pnl']),'sf9_pnl':float(c['pnl'])})
        base.append(float(b['pnl'])); sf9.append(float(c['pnl']))
    df=pd.DataFrame(rows); base=np.asarray(base); sf9=np.asarray(sf9)
    if abs(base.sum()-75.25)>0.30 or abs(sf9.sum()-77.74)>0.35:raise RuntimeError('parity')
    risk=df.bull_body_dominant.to_numpy(bool); keep=~risk
    D=np.arange(139)<DISC_N; V=~D
    def report(p):
        return {'base':pack(p),'kept_full':sf11.metrics(p[keep]),'kept_D':sf11.metrics(p[D&keep]),'kept_V':sf11.metrics(p[V&keep]),
                'delta_full':float(-p[risk].sum()),'delta_D':float(-p[D&risk].sum()),'delta_V':float(-p[V&risk].sum())}
    rb=report(base); r9=report(sf9)
    r=df[risk]
    out={'status':'COMPLETE_SF13_SINGLE_NATURAL_MORPHOLOGY','rule':'WAIT if immediate pre-entry 5m candle is bullish AND body > total wicks',
         'signals':int(risk.sum()),'signals_D':int((risk&D).sum()),'signals_V':int((risk&V).sum()),
         'signal_failure_rate':float(r.failure_to_develop.mean()) if len(r) else None,
         'keep_failure_rate':float(df[keep].failure_to_develop.mean()),
         'signal_failure_n':int(r.failure_to_develop.sum()),'signal_nonfailure_n':int((~r.failure_to_develop).sum()),
         'sf68':rb,'sf9':r9,
         'screen_pass':bool(rb['delta_D']>0 and rb['delta_V']>=0 and len(r)>=8),
         'guardrail':'One geometry rule only, motivated by SF11 stable body/lower-wick separation. No magnitude threshold or alternate morphology selection.'}
    df.to_csv(OUT/'sunfm13_rows.csv',index=False); (OUT/'sunfm13_summary.json').write_text(json.dumps(out,indent=2,default=str))
    md=['# Sunday Friday-Method SF13 — Pre-entry Bullish Expansion Morphology','',
        f"**Screen: {'PASS' if out['screen_pass'] else 'FAIL'} — same-sample diagnostic; live BBC untouched.**",'',
        '## Rule','- Immediate completed 5m candle before Sunday16 is bullish.','- Candle body > total wick length.','- If true: WAIT; otherwise use frozen strategy unchanged.','',
        '## Signal anatomy',f"- signals **{out['signals']}** (D/V {out['signals_D']}/{out['signals_V']})",f"- failure-to-develop among signal **{100*out['signal_failure_rate']:.1f}%** vs kept **{100*out['keep_failure_rate']:.1f}%**",f"- signal failure/non-failure **{out['signal_failure_n']}/{out['signal_nonfailure_n']}**",'',
        '## Frozen SF6-SF8',f"- baseline ${rb['base']['full']['pnl']:+.2f}; WAIT-gated traded N **{rb['kept_full']['n']}**, WR **{100*rb['kept_full']['wr']:.2f}%**, PnL **${rb['kept_full']['pnl']:+.2f}**.",f"- delta D/V/full **${rb['delta_D']:+.2f} / ${rb['delta_V']:+.2f} / ${rb['delta_full']:+.2f}**.",'',
        '## SF6-SF8 + FastMR',f"- WAIT-gated traded N **{r9['kept_full']['n']}**, WR **{100*r9['kept_full']['wr']:.2f}%**, PnL **${r9['kept_full']['pnl']:+.2f}**.",f"- delta D/V/full **${r9['delta_D']:+.2f} / ${r9['delta_V']:+.2f} / ${r9['delta_full']:+.2f}**.",'',
        '## Guardrail',out['guardrail']]
    (OUT/'SUNDAY_FRIDAY_METHOD_SF13_PREENTRY_MORPH.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
