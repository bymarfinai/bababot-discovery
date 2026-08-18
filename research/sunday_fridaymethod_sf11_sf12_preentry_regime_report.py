#!/usr/bin/env python3
"""SF11-SF12 report runner. Preserves forensic output even when no natural WAIT gate is discovery-positive."""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sunday_fridaymethod_sf11_sf12_preentry_regime as b

OUT=Path(os.getenv('SUNFM1112_OUT','sunfm1112_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=b.DISC_N


def main():
    k=f517.load_klines(); f=s50.load_funding(); entries=b.sun17.entries(k)
    trs=[b.sun17.simulate_parent(k,f,t) for t in entries]
    rows=[]; sf68_p=[]; sf9_p=[]
    for i,tr in enumerate(trs):
        feat=b.pre_features(k,tr['entry_t']); base=b.frozen_sf68(k,f,tr); comb=b.combined_sf9(k,f,tr,base)
        sf68_p.append(float(base['pnl'])); sf9_p.append(float(comb['pnl']))
        rows.append({'i':i,'period':'D' if i<DISC_N else 'V','date':str(tr['entry_t'].date()),
                     'parent_pnl':float(tr['pnl']),'parent_win':bool(tr['pnl']>0),
                     'parent_mfe_r':float(tr['mfe']/b.R),'parent_mae_r':float(tr['mae']/b.R),
                     'failure_to_develop':bool(tr['pnl']<=0 and tr['mfe']<0.5*b.R),
                     'developed_05r':bool(tr['mfe']>=0.5*b.R),'sf68_pnl':float(base['pnl']),'sf9_pnl':float(comb['pnl']),**feat})
    df=pd.DataFrame(rows); sf68_p=np.asarray(sf68_p,float); sf9_p=np.asarray(sf9_p,float)
    if int(df.failure_to_develop.sum())!=51 or abs(sf68_p.sum()-75.25)>0.30 or abs(sf9_p.sum()-77.74)>0.35:
        raise RuntimeError('parity failed')

    cont=['ret30m','ret60m','ret120m','ret240m','ret480m','ret6h','ret12h','ret24h','sun_pre16_ret','sat_day_ret','fri_day_ret','thu_day_ret',
          'sat18_to_sun12_ret','sun12_to16_ret','prior24_range','prior24_close_loc','prior24_taker','pre_close_vs_ema7','pre_close_vs_ema20','pre_ema_spread',
          'taker30','taker60','taker120','taker240','range_pos2h','range_pos4h','range_pos8h','ema7_slope30','ema20_slope60','last_body_ratio','last_upper_wick_ratio','last_lower_wick_ratio']
    atlas=[]
    for col in cont:
        p={}
        for name,z in [('full',df),('D',df.iloc[:DISC_N]),('V',df.iloc[DISC_N:])]:
            p[name]=b.auc_target_high(z[z.failure_to_develop][col].to_numpy(float),z[z.developed_05r][col].to_numpy(float))
        same=p['D']['direction']==p['V']['direction'] and p['D']['direction']!='NA'
        strengths=[p['D']['strength'],p['V']['strength']]
        score=min(strengths) if same and all(x is not None for x in strengths) else 0.0
        atlas.append({'feature':col,'same_direction_DV':same,'min_DV_strength':score,**p})
    atlas.sort(key=lambda x:(x['same_direction_DV'],x['min_DV_strength']),reverse=True)

    gates={
      'SUN_PRE16_UP': df.sun_pre16_ret>=0,
      'LAST4H_UP': df.sun12_to16_ret>=0,
      'LAST2H_UP': df.ret120m>=0,
      'LAST1H_UP': df.ret60m>=0,
      'CLOSE_ABOVE_EMA20': df.pre_close_vs_ema20>=0,
      'EMA7_ABOVE_EMA20': df.pre_ema_spread>=0,
      'TAKER60_BUYER': df.taker60>=0,
      'TAKER30_BUYER': df.taker30>=0,
      'RANGE2H_UPPER_HALF': df.range_pos2h>0.5,
      'RANGE4H_UPPER_HALF': df.range_pos4h>0.5,
      'LAST_GREEN': df.last_green.astype(bool),
      'LAST3_UP': df.last3_up.astype(bool),
      'WICK_DOMINANT_GREEN': df.last_green.astype(bool)&df.last_wick_dominant.astype(bool),
      'EMA_BULL_AND_BUYER_FLOW': (df.pre_ema_spread>=0)&(df.taker60>=0),
      'ABOVE20_AND_BUYER_FLOW': (df.pre_close_vs_ema20>=0)&(df.taker60>=0),
      'LAST4H_UP_AND_ABOVE20': (df.sun12_to16_ret>=0)&(df.pre_close_vs_ema20>=0),
      'LAST4H_UP_AND_BUYER_FLOW': (df.sun12_to16_ret>=0)&(df.taker60>=0),
      'SUN_UP_AND_LAST4H_UP': (df.sun_pre16_ret>=0)&(df.sun12_to16_ret>=0),
      'RANGE4H_UPPER_AND_BUYER': (df.range_pos4h>0.5)&(df.taker60>=0),
      'LAST3_UP_AND_BUYER': df.last3_up.astype(bool)&(df.taker30>=0),
      'BULL_TRIPLE': (df.sun12_to16_ret>=0)&(df.pre_close_vs_ema20>=0)&(df.taker60>=0),
    }
    D=df.i<DISC_N; V=~D; gr=[]
    for name,m in gates.items():
        m=pd.Series(m,index=df.index).fillna(False).astype(bool); md=m&D; mv=m&V
        sd=float(df.loc[md,'sf68_pnl'].sum()); sv=float(df.loc[mv,'sf68_pnl'].sum())
        keep=~m
        gr.append({'gate':name,'support_ok':bool(8<=md.sum()<=30),'eligible_D':bool(8<=md.sum()<=30 and sd<0),
                   'skip_n':int(m.sum()),'skip_D':int(md.sum()),'skip_V':int(mv.sum()),
                   'failure_rate_skip_full':b.failure_rate(df,m),'failure_rate_keep_full':b.failure_rate(df,keep),
                   'skipped_sf68_pnl_D':sd,'skipped_sf68_pnl_V':sv,'sf68_delta_D':-sd,'sf68_delta_V':-sv,'sf68_delta_full':-(sd+sv),
                   'sf68_keep_full':b.metrics(sf68_p[keep]),'sf68_keep_D':b.metrics(sf68_p[D&keep]),'sf68_keep_V':b.metrics(sf68_p[V&keep]),
                   'sf9_keep_full':b.metrics(sf9_p[keep]),'sf9_delta_full':-float(df.loc[m,'sf9_pnl'].sum())})
    gr.sort(key=lambda x:x['sf68_delta_D'],reverse=True)
    eligible=[x for x in gr if x['eligible_D']]
    selected=max(eligible,key=lambda x:x['sf68_delta_D']) if eligible else None
    best_supported=max([x for x in gr if x['support_ok']],key=lambda x:x['sf68_delta_D'])

    status='NATURAL_GATE_FOUND' if selected else 'NO_DISCOVERY_POSITIVE_NATURAL_WAIT_GATE'
    out={'status':status,'failure_to_develop':{'n':51,'D':int((df.failure_to_develop&D).sum()),'V':int((df.failure_to_develop&V).sum())},
         'frozen_sf68':{'full':b.metrics(sf68_p),'D':b.metrics(sf68_p[:DISC_N]),'V':b.metrics(sf68_p[DISC_N:])},
         'sf9':{'full':b.metrics(sf9_p),'D':b.metrics(sf9_p[:DISC_N]),'V':b.metrics(sf9_p[DISC_N:])},
         'top_continuous_preentry':atlas[:12],'gate_results':gr,'selected_gate':selected,'best_supported_even_if_harmful':best_supported,
         'guardrail':'No fitted thresholds. If selected_gate is null, do not manufacture a pre-entry WAIT rule from this family. D/V are robustness slices only.'}
    df.to_csv(OUT/'sunfm1112_rows.csv',index=False); (OUT/'sunfm1112_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Sunday Friday-Method SF11-SF12 — Pre-entry Regime','',f"**Status: {status}. Live BBC untouched.**",'',
        '## Failure-to-develop',f"- **51** cases = D {out['failure_to_develop']['D']} / V {out['failure_to_develop']['V']}; definition: parent loss + total MFE <0.5R (<0.70%).",'',
        '## Strongest stable pre-entry separators (descriptive only)']
    for x in atlas[:8]:
        md.append(f"- `{x['feature']}`: min D/V strength **{x['min_DV_strength']:.3f}**, {x['D']['direction']}; D fail/develop med {x['D']['target_median']}/{x['D']['control_median']}; V {x['V']['target_median']}/{x['V']['control_median']}")
    md += ['', '## Natural WAIT family']
    if selected:
        md += [f"Selected D-only: **{selected['gate']}**; skips {selected['skip_n']} (D/V {selected['skip_D']}/{selected['skip_V']}).",
               f"SF6-SF8 delta D/V/full **${selected['sf68_delta_D']:+.2f} / ${selected['sf68_delta_V']:+.2f} / ${selected['sf68_delta_full']:+.2f}**."]
    else:
        x=best_supported
        md += ['**No predeclared natural gate both had acceptable discovery support and removed negative discovery economics.**',
               f"Least-bad supported gate was `{x['gate']}` but discovery delta was **${x['sf68_delta_D']:+.2f}**, so it is NOT promoted."]
    md += ['', '## Guardrail',out['guardrail']]
    (OUT/'SUNDAY_FRIDAY_METHOD_SF11_SF12_PREENTRY_REGIME.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
