#!/usr/bin/env python3
"""Sunday Friday-method SF11-SF12 — pre-entry failure-to-develop forensic + natural WAIT gate.

Research only; live BBC untouched.

Motivation:
- Frozen Sunday16 Friday-method SF6-SF8 improves historical loss severity but did not act usefully
  on the first three August observations.
- Those August trades mostly failed to develop SELL at all, so the next Friday-style question is
  whether failure-to-develop can be recognized BEFORE the Sunday 16:00 WIB entry.

Method:
SF11 forensic:
- target = parent loss whose total favorable MFE <0.5R (R=1.4%, so MFE <0.70%).
- controls = trades that develop >=0.5R, plus parent winners as a second comparison.
- features use strictly completed pre-entry 5m bars only.
- continuous features are descriptive only (AUC); no fitted cutoffs.

SF12 natural gate:
- predeclare a compact family of BOOLEAN/natural geometry gates only: zero-crosses, EMA ordering,
  buyer/seller flow sign, half-range split, and simple candle geometry.
- a WAIT gate means skip the Sunday16 entry when the bad-regime condition is true.
- select on DISCOVERY only using frozen SF6-SF8 economics.
- eligibility: 8..30 discovery skips, skipped discovery PnL <0; maximize discovery PnL uplift.
- validation is report-only and never influences the selection.
- the selected gate is also applied unchanged to SF9 (frozen SF6-SF8 + fixed FastMR) for comparison.

Important: Sunday history has already been inspected in prior research. D/V are robustness slices,
not untouched OOS. No August data is loaded or used here.
"""
from __future__ import annotations
import json, os, math
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sun17b_sunday16_loss_prevday_forensics_exactfunding as sun17b
import sunday_fridaymethod_sf6_sf8_confirmed_failure as sf68
import sunday_fridaymethod_sf9_fastmr_overlay as sf9

sun17 = sun17b.base
sun17.funding_short = sun17b.exact_sun16_funding
OUT=Path(os.getenv('SUNFM1112_OUT','sunfm1112_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=83
R=0.014


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:
        return {'n':0,'wins':0,'losses':0,'wr':None,'pnl':0.0,'pf':None,'exp':None,'dd':0.0,'ls':0}
    wins=int((a>0).sum()); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.,eq]); dd=float(np.max(peak[1:]-eq)); cur=ls=0
    for x in a:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':int(len(a)),'wins':wins,'losses':int(len(a)-wins),'wr':float(wins/len(a)),
            'pnl':float(a.sum()),'pf':float(gp/gl) if gl>0 else 999.0,'exp':float(a.mean()),'dd':dd,'ls':ls}


def auc_target_high(target,control):
    a=np.asarray(target,float); b=np.asarray(control,float)
    a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if len(a)==0 or len(b)==0:return {'auc':None,'strength':None,'direction':'NA','target_median':None,'control_median':None,'n_target':len(a),'n_control':len(b)}
    cmp=a[:,None]-b[None,:]
    auc=float((np.sum(cmp>0)+0.5*np.sum(cmp==0))/cmp.size)
    return {'auc':auc,'strength':max(auc,1-auc),'direction':'higher=failure' if auc>=0.5 else 'lower=failure',
            'target_median':float(np.median(a)),'control_median':float(np.median(b)),
            'n_target':int(len(a)),'n_control':int(len(b))}


def w(k,t,minutes):
    return k[(k.index>=t-pd.Timedelta(minutes=minutes))&(k.index<t)]


def ret_window(k,t,minutes):
    x=w(k,t,minutes)
    if len(x)<2:return np.nan
    return float(x.iloc[-1].close)/float(x.iloc[0].open)-1.0


def taker(x):
    if x.empty:return np.nan
    q=float(x.quote_volume.sum()); b=float(x.taker_buy_quote.sum())
    return 2*b/q-1.0 if q>0 else np.nan


def range_pos(x,px):
    if x.empty:return np.nan
    lo=float(x.low.min()); hi=float(x.high.max())
    return (px-lo)/(hi-lo) if hi>lo else 0.5


def slope_sign_value(x,col):
    if len(x)<2:return np.nan
    a=float(x.iloc[0][col]); b=float(x.iloc[-1][col])
    return b/a-1.0 if a>0 else np.nan


def pre_features(k,t):
    # t is entry open; every value below uses rows with index < t only.
    last=k.loc[t-pd.Timedelta(minutes=5)]
    lc=float(last.close)
    base=sun17.pre_context(k,t)
    x30=w(k,t,30);x60=w(k,t,60);x120=w(k,t,120);x240=w(k,t,240);x480=w(k,t,480)
    rng=max(float(last.high-last.low),1e-12)
    body=abs(float(last.close-last.open)); upper=float(last.high-max(last.open,last.close)); lower=float(min(last.open,last.close)-last.low)
    x3=w(k,t,15)
    last3_up=bool(len(x3)==3 and float(x3.iloc[-1].close)>float(x3.iloc[0].open))
    return {
      **base,
      'ret30m':ret_window(k,t,30),'ret60m':ret_window(k,t,60),'ret120m':ret_window(k,t,120),
      'ret240m':ret_window(k,t,240),'ret480m':ret_window(k,t,480),
      'taker30':taker(x30),'taker60':taker(x60),'taker120':taker(x120),'taker240':taker(x240),
      'range_pos2h':range_pos(x120,lc),'range_pos4h':range_pos(x240,lc),'range_pos8h':range_pos(x480,lc),
      'ema7_slope30':slope_sign_value(x30,'ema7'),'ema20_slope60':slope_sign_value(x60,'ema20'),
      'last_green':bool(float(last.close)>float(last.open)),
      'last_body_ratio':body/rng,'last_upper_wick_ratio':upper/rng,'last_lower_wick_ratio':lower/rng,
      'last_wick_dominant':bool((upper+lower)>body),'last_upper_gt_lower':bool(upper>lower),
      'last3_up':last3_up,
    }


def frozen_sf68(k,f,tr):
    return sf9.frozen_baseline(k,f,tr)


def combined_sf9(k,f,tr,base):
    return sf9.overlay_outcome(k,f,tr,base)


def failure_rate(df,mask):
    z=df[mask]
    return None if len(z)==0 else float(z.failure_to_develop.mean())


def apply_wait(pnls,mask):
    a=np.asarray(pnls,float).copy(); a[np.asarray(mask,bool)]=0.0
    return a


def main():
    k=f517.load_klines(); f=s50.load_funding(); entries=sun17.entries(k)
    trs=[sun17.simulate_parent(k,f,t) for t in entries]
    rows=[]; sf68_p=[]; sf9_p=[]
    for i,tr in enumerate(trs):
        feat=pre_features(k,tr['entry_t'])
        b=frozen_sf68(k,f,tr); c=combined_sf9(k,f,tr,b)
        sf68_p.append(float(b['pnl'])); sf9_p.append(float(c['pnl']))
        rows.append({'i':i,'period':'D' if i<DISC_N else 'V','date':str(tr['entry_t'].date()),
                     'parent_pnl':float(tr['pnl']),'parent_win':bool(tr['pnl']>0),
                     'parent_mfe_r':float(tr['mfe']/R),'parent_mae_r':float(tr['mae']/R),
                     'failure_to_develop':bool(tr['pnl']<=0 and tr['mfe']<0.5*R),
                     'developed_05r':bool(tr['mfe']>=0.5*R),
                     'sf68_pnl':float(b['pnl']),'sf9_pnl':float(c['pnl']),**feat})
    df=pd.DataFrame(rows); sf68_p=np.asarray(sf68_p,float); sf9_p=np.asarray(sf9_p,float)
    if len(df)!=139 or int(df.parent_win.sum())!=66:raise RuntimeError('parent count parity')
    if abs(sf68_p.sum()-75.25)>0.30 or int((sf68_p>0).sum())!=66:raise RuntimeError(f'SF68 parity {metrics(sf68_p)}')
    if abs(sf9_p.sum()-77.74)>0.35:raise RuntimeError(f'SF9 parity {metrics(sf9_p)}')
    if int(df.failure_to_develop.sum())!=51:raise RuntimeError(f'failure cohort parity {df.failure_to_develop.sum()}')

    # SF11 continuous atlas: target failure-to-develop vs developed >=0.5R.
    cont=['ret30m','ret60m','ret120m','ret240m','ret480m','ret6h','ret12h','ret24h',
          'sun_pre16_ret','sat_day_ret','fri_day_ret','thu_day_ret','sat18_to_sun12_ret','sun12_to16_ret',
          'prior24_range','prior24_close_loc','prior24_taker','pre_close_vs_ema7','pre_close_vs_ema20','pre_ema_spread',
          'taker30','taker60','taker120','taker240','range_pos2h','range_pos4h','range_pos8h',
          'ema7_slope30','ema20_slope60','last_body_ratio','last_upper_wick_ratio','last_lower_wick_ratio']
    atlas=[]
    for col in cont:
        pack={}
        for name,z in [('full',df),('D',df.iloc[:DISC_N]),('V',df.iloc[DISC_N:])]:
            tgt=z[z.failure_to_develop][col].to_numpy(float)
            ctl=z[z.developed_05r][col].to_numpy(float)
            pack[name]=auc_target_high(tgt,ctl)
        dirs=[pack['D']['direction'],pack['V']['direction']]
        same=dirs[0]==dirs[1] and dirs[0]!='NA'
        strengths=[pack['D']['strength'],pack['V']['strength']]
        minstr=min(strengths) if same and all(v is not None for v in strengths) else 0.0
        atlas.append({'feature':col,'same_direction_DV':same,'min_DV_strength':minstr,**pack})
    atlas.sort(key=lambda x:(x['same_direction_DV'],x['min_DV_strength']),reverse=True)

    # Natural, predeclared bad-regime boolean gates. True means WAIT.
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

    gate_rows=[]
    Dmask=df.i<DISC_N; Vmask=~Dmask
    baseD=float(sf68_p[Dmask].sum()); baseV=float(sf68_p[Vmask].sum())
    for name,mask in gates.items():
        mask=pd.Series(mask,index=df.index).fillna(False).astype(bool)
        md=mask&Dmask; mv=mask&Vmask
        nD=int(md.sum()); nV=int(mv.sum()); n=int(mask.sum())
        skippedD=float(df.loc[md,'sf68_pnl'].sum()); skippedV=float(df.loc[mv,'sf68_pnl'].sum())
        sf68_wait=apply_wait(sf68_p,mask); sf9_wait=apply_wait(sf9_p,mask)
        eligible=bool(8<=nD<=30 and skippedD<0)
        gate_rows.append({
          'gate':name,'eligible_D':eligible,'skip_n':n,'skip_D':nD,'skip_V':nV,
          'failure_rate_skip_full':failure_rate(df,mask),'failure_rate_keep_full':failure_rate(df,~mask),
          'failure_rate_skip_D':failure_rate(df,md),'failure_rate_keep_D':failure_rate(df,Dmask&~mask),
          'failure_rate_skip_V':failure_rate(df,mv),'failure_rate_keep_V':failure_rate(df,Vmask&~mask),
          'skipped_sf68_pnl_D':skippedD,'skipped_sf68_pnl_V':skippedV,
          'sf68_delta_D':-skippedD,'sf68_delta_V':-skippedV,'sf68_delta_full':float(sf68_wait.sum()-sf68_p.sum()),
          'sf68_wait_full':metrics(sf68_wait[~mask]), # metrics on actually traded observations only
          'sf68_wait_D':metrics(sf68_p[Dmask&~mask]),'sf68_wait_V':metrics(sf68_p[Vmask&~mask]),
          'sf9_delta_full':float(sf9_wait.sum()-sf9_p.sum()),
          'sf9_wait_full':metrics(sf9_p[~mask]),'sf9_wait_D':metrics(sf9_p[Dmask&~mask]),'sf9_wait_V':metrics(sf9_p[Vmask&~mask]),
        })
    eligible=[x for x in gate_rows if x['eligible_D']]
    if not eligible: raise RuntimeError('no eligible natural gate')
    selected=max(eligible,key=lambda x:x['sf68_delta_D'])
    selmask=pd.Series(gates[selected['gate']],index=df.index).fillna(False).astype(bool)

    # Eight chronology blocks for selected traded SF68 only; skipped observations contribute no trade.
    block_out=[]
    for bi,idx in enumerate(np.array_split(np.arange(len(df)),8),1):
        idx=np.asarray(idx,int); keep=~selmask.iloc[idx].to_numpy(bool)
        block_out.append({'block':bi,'opportunities':len(idx),'trades':int(keep.sum()),
                          'sf68':metrics(sf68_p[idx][keep]),'sf9':metrics(sf9_p[idx][keep])})

    out={
      'status':'COMPLETE_SF11_FORENSIC_SF12_D_ONLY_NATURAL_GATE',
      'parent':metrics(df.parent_pnl),'failure_to_develop':{'n':int(df.failure_to_develop.sum()),'D':int((df.failure_to_develop&Dmask).sum()),'V':int((df.failure_to_develop&Vmask).sum())},
      'frozen_sf68':{'full':metrics(sf68_p),'D':metrics(sf68_p[:DISC_N]),'V':metrics(sf68_p[DISC_N:])},
      'sf9':{'full':metrics(sf9_p),'D':metrics(sf9_p[:DISC_N]),'V':metrics(sf9_p[DISC_N:])},
      'top_continuous_preentry':atlas[:12],
      'gate_family_n':len(gate_rows),'gate_results':gate_rows,'selected_gate':selected,
      'selected_blocks':block_out,
      'selected_positive_sf68_blocks':int(sum(b['sf68']['pnl']>0 for b in block_out if b['sf68']['n']>0)),
      'selected_positive_sf9_blocks':int(sum(b['sf9']['pnl']>0 for b in block_out if b['sf9']['n']>0)),
      'guardrail':'Selected from a predeclared natural boolean family using discovery SF6-SF8 economics only. Validation is report-only. Sunday history has prior research exposure, so this remains same-sample research and is not production-ready.'
    }
    df['selected_wait']=selmask
    df.to_csv(OUT/'sunfm1112_rows.csv',index=False)
    (OUT/'sunfm1112_summary.json').write_text(json.dumps(out,indent=2,default=str))

    s=selected
    md=['# Sunday Friday-Method SF11-SF12 — Pre-entry Regime','',
        '**Status: COMPLETE — pre-entry forensic + discovery-only natural WAIT gate; live BBC untouched.**','',
        '## SF11 failure-to-develop cohort',
        f"- failure-to-develop **{int(df.failure_to_develop.sum())}** = D {int((df.failure_to_develop&Dmask).sum())} / V {int((df.failure_to_develop&Vmask).sum())}",
        '- definition: eventual parent loss AND total favorable MFE <0.5R (<0.70%).','',
        '## Strongest continuous pre-entry separators (descriptive only)']
    for x in atlas[:8]:
        md.append(f"- `{x['feature']}`: min D/V strength **{x['min_DV_strength']:.3f}**, direction {x['D']['direction']}; D med fail/develop {x['D']['target_median']}/{x['D']['control_median']}, V {x['V']['target_median']}/{x['V']['control_median']}")
    md += ['', '## SF12 selected natural WAIT gate',
           f"**{s['gate']}**",f"- skips **{s['skip_n']}** / 139 (D {s['skip_D']} / V {s['skip_V']}).",
           f"- failure-to-develop rate skipped vs kept: **{100*s['failure_rate_skip_full']:.1f}% vs {100*s['failure_rate_keep_full']:.1f}%**.",
           f"- SF6-SF8 discovery uplift **${s['sf68_delta_D']:+.2f}**; validation uplift **${s['sf68_delta_V']:+.2f}**; full uplift **${s['sf68_delta_full']:+.2f}**.",
           f"- SF6-SF8 traded full: **{s['sf68_wait_full']['n']} trades**, WR **{100*s['sf68_wait_full']['wr']:.2f}%**, PnL **${s['sf68_wait_full']['pnl']:+.2f}**, PF **{s['sf68_wait_full']['pf']:.2f}**.",
           f"- SF9 traded full: **{s['sf9_wait_full']['n']} trades**, WR **{100*s['sf9_wait_full']['wr']:.2f}%**, PnL **${s['sf9_wait_full']['pnl']:+.2f}**, PF **{s['sf9_wait_full']['pf']:.2f}**.",
           f"- selected SF6-SF8 positive chronology blocks **{out['selected_positive_sf68_blocks']}/8**; SF9 **{out['selected_positive_sf9_blocks']}/8**.",'',
           '## Guardrail',out['guardrail']]
    (OUT/'SUNDAY_FRIDAY_METHOD_SF11_SF12_PREENTRY_REGIME.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
