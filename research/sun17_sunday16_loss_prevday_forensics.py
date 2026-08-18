#!/usr/bin/env python3
"""SUN1.7 — Sunday 16:00 SELL loss + previous-day causal forensics.

Research only; live BBC untouched.
Frozen parent under study:
- Sunday 16:00 WIB SELL
- TP 2.5%, SL 1.4%, max hold 18h
- $500 notional, 0.15% round-trip fee, historical funding
- adverse-first same-5m ambiguity

Purpose:
1) Reproduce the frozen Sunday16 parent exactly.
2) Describe loser anatomy and earliest post-entry separation using completed 5m bars only.
3) Test whether purely PRE-entry context from Friday/Saturday/Sunday-before-16:00
   shows stable winner/loss separation in discovery and validation.
4) No threshold optimization and no adaptive rule promotion in this step.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50

OUT=Path(os.getenv('SUN17_OUT','sun17_out')); OUT.mkdir(parents=True,exist_ok=True)
NOTIONAL=500.0; FEE=0.0015*NOTIONAL
START=pd.Timestamp('2023-12-02',tz='UTC'); END=pd.Timestamp('2026-07-30',tz='UTC')
DISC_N=83; TP=0.025; SL=0.014; HOLD_MIN=18*60
CHECKPOINTS=[15,30,60,120,240,360,720]


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0: return {'n':0,'wins':0,'wr':np.nan,'pnl':0.0,'pf':np.nan,'exp':np.nan}
    gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    return {'n':int(len(a)),'wins':int((a>0).sum()),'wr':float((a>0).mean()),
            'pnl':float(a.sum()),'pf':float(gp/gl) if gl>0 else 999.0,'exp':float(a.mean())}


def entries(k):
    idx=k.index; local=idx+pd.Timedelta(hours=7)
    m=(idx>=START)&(idx<END)&(local.dayofweek==6)&(local.hour==16)&(local.minute==0)
    e=list(idx[m])
    if len(e)!=139: raise RuntimeError(f'entry parity {len(e)}')
    return e


def funding_short(k,f,entry_t,exit_t,entry_px):
    rows=f[(f.ts>entry_t)&(f.ts<=exit_t)]
    qty=NOTIONAL/entry_px; cost=0.0; n=0
    for r in rows.itertuples(index=False):
        px=float(k.loc[r.ts,'open']) if r.ts in k.index else entry_px
        # signed cost for short: positive funding rate is received => negative cost
        cost += -qty*px*float(r.rate); n+=1
    return float(cost),int(n)


def simulate_parent(k,f,t):
    ep=float(k.loc[t,'open']); tp_px=ep*(1-TP); sl_px=ep*(1+SL)
    bars=k[(k.index>=t)&(k.index<t+pd.Timedelta(minutes=HOLD_MIN))]
    if len(bars)!=HOLD_MIN//5: raise RuntimeError(f'incomplete {t}: {len(bars)}')
    reason='TIMEOUT'; exit_t=t+pd.Timedelta(minutes=HOLD_MIN); exit_px=float(bars.iloc[-1].close); exit_i=len(bars)-1
    mfe=0.0; mae=0.0
    for i,b in enumerate(bars.itertuples(index=False)):
        mfe=max(mfe,1.0-float(b.low)/ep)      # favorable for SELL
        mae=max(mae,float(b.high)/ep-1.0)     # adverse for SELL
        hit_sl=float(b.high)>=sl_px; hit_tp=float(b.low)<=tp_px
        if hit_sl:                            # adverse-first if same 5m
            reason='SL'; exit_t=b.ts+pd.Timedelta(minutes=5); exit_px=sl_px; exit_i=i; break
        if hit_tp:
            reason='TP'; exit_t=b.ts+pd.Timedelta(minutes=5); exit_px=tp_px; exit_i=i; break
    gross=1.0-exit_px/ep
    fc,fn=funding_short(k,f,t,exit_t,ep)
    pnl=NOTIONAL*gross-FEE-fc
    return {'entry_t':t,'entry':ep,'exit_t':exit_t,'exit_px':exit_px,'exit_i':exit_i,'reason':reason,
            'pnl':float(pnl),'gross_ret':float(gross),'mfe':float(mfe),'mae':float(mae),
            'funding':float(fc),'funding_events':fn,'win':bool(pnl>0)}


def last_completed(k,t):
    x=k[k.index<t]
    return None if x.empty else x.iloc[-1]


def exact_close_before(k,t):
    r=last_completed(k,t)
    return np.nan if r is None else float(r.close)


def window(k,a,b):
    return k[(k.index>=a)&(k.index<b)]


def pre_context(k,t):
    last=last_completed(k,t)
    if last is None: return {}
    lc=float(last.close)
    out={}
    for h in [6,12,24,48,72]:
        pc=exact_close_before(k,t-pd.Timedelta(hours=h))
        out[f'ret{h}h']=lc/pc-1.0 if np.isfinite(pc) and pc>0 else np.nan
    # Calendar-day context in WIB. Sunday 16 WIB entry => Sunday 09 UTC.
    local_t=t+pd.Timedelta(hours=7)
    sun0_utc=(local_t.normalize()-pd.Timedelta(hours=7))
    sat0_utc=sun0_utc-pd.Timedelta(days=1)
    fri0_utc=sat0_utc-pd.Timedelta(days=1)
    thu0_utc=fri0_utc-pd.Timedelta(days=1)
    p_sun0=exact_close_before(k,sun0_utc); p_sat0=exact_close_before(k,sat0_utc)
    p_fri0=exact_close_before(k,fri0_utc); p_thu0=exact_close_before(k,thu0_utc)
    out['sun_pre16_ret']=lc/p_sun0-1.0 if np.isfinite(p_sun0) else np.nan
    out['sat_day_ret']=p_sun0/p_sat0-1.0 if np.isfinite(p_sun0) and np.isfinite(p_sat0) else np.nan
    out['fri_day_ret']=p_sat0/p_fri0-1.0 if np.isfinite(p_sat0) and np.isfinite(p_fri0) else np.nan
    out['thu_day_ret']=p_fri0/p_thu0-1.0 if np.isfinite(p_fri0) and np.isfinite(p_thu0) else np.nan
    # Saturday 18 WIB -> Sunday 12 WIB handoff, and final 4h pre-entry move.
    sat18=t-pd.Timedelta(hours=22)  # Sunday16 minus 22h = Saturday18 WIB
    sun12=t-pd.Timedelta(hours=4)
    p_sat18=exact_close_before(k,sat18); p_sun12=exact_close_before(k,sun12)
    out['sat18_to_sun12_ret']=p_sun12/p_sat18-1.0 if np.isfinite(p_sat18) and np.isfinite(p_sun12) else np.nan
    out['sun12_to16_ret']=lc/p_sun12-1.0 if np.isfinite(p_sun12) else np.nan
    # Causal price/flow state over prior 24h.
    w24=window(k,t-pd.Timedelta(hours=24),t)
    if len(w24):
        lo=float(w24.low.min()); hi=float(w24.high.max())
        out['prior24_range']=hi/lo-1.0 if lo>0 else np.nan
        out['prior24_close_loc']=(lc-lo)/(hi-lo) if hi>lo else 0.5
        out['prior24_taker']=float(np.nanmean(w24.taker_imb.to_numpy(float))) if 'taker_imb' in w24 else np.nan
    else:
        out['prior24_range']=out['prior24_close_loc']=out['prior24_taker']=np.nan
    out['pre_close_vs_ema7']=lc/float(last.ema7)-1.0
    out['pre_close_vs_ema20']=lc/float(last.ema20)-1.0
    out['pre_ema_spread']=float(last.ema7)/float(last.ema20)-1.0
    return out


def checkpoint(k,tr,m):
    t=tr['entry_t']; cp=t+pd.Timedelta(minutes=m)
    # Only evaluate if parent is still alive at the checkpoint decision open.
    if tr['exit_t']<=cp: return None
    bars=window(k,t,cp)
    if len(bars)!=m//5: return None
    ep=tr['entry']; last=bars.iloc[-1]; prev=bars.iloc[-2] if len(bars)>=2 else last
    half=max(1,len(bars)//2); a=bars.iloc[:half]; b=bars.iloc[half:]
    return {
      'progress':1.0-float(last.close)/ep,
      'mfe':1.0-float(bars.low.min())/ep,
      'mae':float(bars.high.max())/ep-1.0,
      'taker_mean':float(np.nanmean(bars.taker_imb.to_numpy(float))),
      'close_vs_ema7':float(last.ema7)/float(last.close)-1.0,   # positive = close below EMA7, good for SELL
      'close_vs_ema20':float(last.ema20)/float(last.close)-1.0,
      'ema_spread':float(last.ema7)/float(last.ema20)-1.0,
      'last_lower_close':float(last.close)<float(prev.close),
      'last_lower_high':float(last.high)<float(prev.high),
      'last_higher_low':float(last.low)>float(prev.low),
      'secondhalf_new_adverse_high':float(b.high.max())>float(a.high.max()) if len(b) else False,
      'secondhalf_new_fav_low':float(b.low.min())<float(a.low.min()) if len(b) else False,
    }


def auc_loss_higher(df,feature):
    z=df[['win',feature]].dropna()
    w=z[z.win][feature].to_numpy(float); l=z[~z.win][feature].to_numpy(float)
    if len(w)==0 or len(l)==0: return {'auc':np.nan,'strength':np.nan,'direction':'NA','nW':len(w),'nL':len(l)}
    # Pairwise probability loss value > winner value; ties count 0.5.
    cmp=l[:,None]-w[None,:]
    auc=float((np.sum(cmp>0)+0.5*np.sum(cmp==0))/cmp.size)
    return {'auc':auc,'strength':max(auc,1-auc),'direction':'higher=loss' if auc>=0.5 else 'lower=loss','nW':len(w),'nL':len(l),
            'W_median':float(np.median(w)),'L_median':float(np.median(l))}


def auc_slices(df,feature):
    return {'full':auc_loss_higher(df,feature),'D':auc_loss_higher(df.iloc[:DISC_N],feature),'V':auc_loss_higher(df.iloc[DISC_N:],feature)}


def state_metrics(df,mask):
    z=df[mask]
    if len(z)==0: return {'n':0,'wr':np.nan,'pnl':0.0,'pf':np.nan}
    m=metrics(z.pnl.to_numpy(float)); return {'n':m['n'],'wr':m['wr'],'pnl':m['pnl'],'pf':m['pf']}


def bool_report(df,name,mask):
    mask=pd.Series(mask,index=df.index).fillna(False).astype(bool)
    out={}
    for label,z in [('full',df),('D',df.iloc[:DISC_N]),('V',df.iloc[DISC_N:])]:
        mm=mask.loc[z.index]
        out[label]={'true':state_metrics(z,mm),'false':state_metrics(z,~mm)}
    return {'feature':name,**out}


def main():
    k=f517.load_klines(); f=s50.load_funding(); es=entries(k)
    trades=[simulate_parent(k,f,t) for t in es]
    rows=[]
    for tr in trades:
        r={**tr,**pre_context(k,tr['entry_t'])}; rows.append(r)
    df=pd.DataFrame(rows)

    # Hard reproduction gate against SUN1.6 reference.
    base=metrics(df.pnl.to_numpy(float))
    gate={'n':len(df)==139,'wins':base['wins']==66,'wr':abs(base['wr']-0.4748201438848921)<1e-9,'pnl':abs(base['pnl']-63.599379132074105)<0.25}
    if not all(gate.values()): raise RuntimeError(f'SUN1.7 parent reproduction failed: {base} gate={gate}')

    win=df[df.win]; loss=df[~df.win]
    reason_cross={}
    for reason in ['TP','SL','TIMEOUT']:
        z=df[df.reason==reason]
        reason_cross[reason]={'n':int(len(z)),'wins':int(z.win.sum()),'losses':int((~z.win).sum()),'pnl':float(z.pnl.sum())}

    anatomy={
      'base':base,
      'reason_cross':reason_cross,
      'winner_mfe_median':float(win.mfe.median()),'winner_mae_median':float(win.mae.median()),
      'loser_mfe_median':float(loss.mfe.median()),'loser_mae_median':float(loss.mae.median()),
      'loser_mfe_reached':{str(x):int((loss.mfe>=x).sum()) for x in [0.003,0.005,0.008,0.010,0.015,0.020]},
      'winner_mae_reached':{str(x):int((win.mae>=x).sum()) for x in [0.003,0.005,0.008,0.010,0.012]},
    }

    # Post-entry separation among trades still alive at each checkpoint.
    cp_summary={}
    cp_features=['progress','mfe','mae','taker_mean','close_vs_ema7','close_vs_ema20','ema_spread']
    for m in CHECKPOINTS:
        rr=[]
        for tr in trades:
            st=checkpoint(k,tr,m)
            if st is not None: rr.append({'win':tr['win'],'pnl':tr['pnl'],**st})
        z=pd.DataFrame(rr)
        item={'alive_n':int(len(z)),'alive_w':int(z.win.sum()) if len(z) else 0,'alive_l':int((~z.win).sum()) if len(z) else 0,
              'exited_before_or_at':int(len(df)-len(z)),'continuous':{},'booleans':{}}
        for feat in cp_features:
            item['continuous'][feat]=auc_loss_higher(z,feat) if len(z) else {}
        for feat in ['last_lower_close','last_lower_high','last_higher_low','secondhalf_new_adverse_high','secondhalf_new_fav_low']:
            if len(z):
                b=z[feat].astype(bool); item['booleans'][feat]={'W_true_rate':float(b[z.win].mean()) if z.win.any() else np.nan,'L_true_rate':float(b[~z.win].mean()) if (~z.win).any() else np.nan}
        cp_summary[str(m)]=item

    # Purely pre-entry continuous features. Rank by weakest D/V strength, requiring direction agreement.
    pre_feats=['ret6h','ret12h','ret24h','ret48h','ret72h','sun_pre16_ret','sat_day_ret','fri_day_ret','thu_day_ret',
               'sat18_to_sun12_ret','sun12_to16_ret','prior24_range','prior24_close_loc','prior24_taker',
               'pre_close_vs_ema7','pre_close_vs_ema20','pre_ema_spread']
    pre_auc={f:auc_slices(df,f) for f in pre_feats}
    ranked=[]
    for feat,a in pre_auc.items():
        dirs=[a[x]['direction'] for x in ['D','V']]
        agree=dirs[0]==dirs[1] and dirs[0]!='NA'
        score=min(a['D']['strength'],a['V']['strength']) if agree else 0.0
        ranked.append({'feature':feat,'direction_agree':agree,'robust_strength':float(score),**a})
    ranked=sorted(ranked,key=lambda x:x['robust_strength'],reverse=True)

    # Natural threshold-free states only: sign / EMA side / range half.
    bools=[]
    for ftr in ['ret24h','ret48h','ret72h','sun_pre16_ret','sat_day_ret','fri_day_ret','sat18_to_sun12_ret','sun12_to16_ret','prior24_taker','pre_close_vs_ema20','pre_ema_spread']:
        bools.append(bool_report(df,f'{ftr}>0',df[ftr]>0))
    bools.append(bool_report(df,'prior24_close_loc>0.5',df.prior24_close_loc>0.5))

    # Three-stage previous-day sign state: Friday / Saturday / Sunday pre16.
    patterns=[]
    pattern=(np.where(df.fri_day_ret>0,'F+','F-')+'|'+np.where(df.sat_day_ret>0,'S+','S-')+'|'+np.where(df.sun_pre16_ret>0,'U+','U-'))
    df['prevday_pattern']=pattern
    for p,z in df.groupby('prevday_pattern'):
        fm=metrics(z.pnl.to_numpy(float)); zd=z[z.index<DISC_N]; zv=z[z.index>=DISC_N]
        dm=metrics(zd.pnl.to_numpy(float)); vm=metrics(zv.pnl.to_numpy(float))
        patterns.append({'pattern':p,'n':fm['n'],'wr':fm['wr'],'pnl':fm['pnl'],'D_n':dm['n'],'D_wr':dm['wr'],'D_pnl':dm['pnl'],'V_n':vm['n'],'V_wr':vm['wr'],'V_pnl':vm['pnl']})
    patterns=sorted(patterns,key=lambda x:x['n'],reverse=True)

    # Compact assessment: identify genuinely reproducible pre-entry candidates, but do not promote.
    reproducible=[x for x in ranked if x['direction_agree'] and x['robust_strength']>=0.60]
    assessment={
      'preentry_reproducible_ge_060':[{'feature':x['feature'],'robust_strength':x['robust_strength'],'direction':x['D']['direction'],
                                      'D_strength':x['D']['strength'],'V_strength':x['V']['strength']} for x in reproducible],
      'interpretation':'If this list is empty or weak, previous-day context is not yet strong enough for a causal adaptive router. Post-entry path separation may still be stronger.',
      'guardrail':'Forensic only. No threshold was tuned and no state is promoted to a trading rule on this same sample.'
    }

    out={'status':'COMPLETE_LOSS_PREVDAY_FORENSICS','definition':{'parent':'Sunday16 WIB SELL TP2.5 SL1.4 hold18h','n':139,'discovery_n':83,'validation_n':56,
         'fee_rt_pct':0.15,'notional':500,'funding':'historical','ambiguity':'adverse-first'},
         'anatomy':anatomy,'postentry_checkpoints':cp_summary,'preentry_ranked':ranked,'preentry_natural_states':bools,
         'prevday_patterns':patterns,'assessment':assessment}
    (OUT/'sun17_summary.json').write_text(json.dumps(out,indent=2,default=str))
    df.to_csv(OUT/'sun17_trades.csv',index=False)

    md=['# SUN1.7 — Sunday16 Loss + Previous-Day Forensics','',
        '**Status: COMPLETE — forensic only; no adaptive rule promoted; live BBC untouched.**','',
        '## Parent reproduction',
        f"- N **{base['n']}**, wins **{base['wins']}**, WR **{100*base['wr']:.2f}%**, PnL **${base['pnl']:+.2f}**, PF **{base['pf']:.2f}**.",
        f"- TP: {reason_cross['TP']['n']} ({reason_cross['TP']['wins']}W/{reason_cross['TP']['losses']}L); SL: {reason_cross['SL']['n']}; timeout: {reason_cross['TIMEOUT']['n']} ({reason_cross['TIMEOUT']['wins']}W/{reason_cross['TIMEOUT']['losses']}L).",'',
        '## Loss anatomy',
        f"- Winner median MFE/MAE: **{100*anatomy['winner_mfe_median']:.2f}% / {100*anatomy['winner_mae_median']:.2f}%**.",
        f"- Loser median MFE/MAE: **{100*anatomy['loser_mfe_median']:.2f}% / {100*anatomy['loser_mae_median']:.2f}%**.",
        '- Losers that first reached favorable excursion: '+', '.join([f">={100*float(k):.1f}%: {v}" for k,v in anatomy['loser_mfe_reached'].items()])+'.','',
        '## Post-entry checkpoint strongest continuous separators']
    for m in CHECKPOINTS:
        z=cp_summary[str(m)]; feats=sorted(z['continuous'].items(),key=lambda kv:kv[1].get('strength',0),reverse=True)[:3]
        desc=', '.join([f"{f} {a.get('strength',np.nan):.3f} ({a.get('direction','')})" for f,a in feats])
        md.append(f"- +{m}m alive {z['alive_n']} ({z['alive_w']}W/{z['alive_l']}L): {desc}")
    md += ['', '## Previous-day / pre-entry strongest reproducible features']
    for x in ranked[:8]:
        md.append(f"- {x['feature']}: robust {x['robust_strength']:.3f}; D {x['D']['strength']:.3f} {x['D']['direction']}; V {x['V']['strength']:.3f} {x['V']['direction']}")
    md += ['', '## Friday / Saturday / Sunday-pre16 sign patterns']
    for x in patterns:
        md.append(f"- {x['pattern']}: N{x['n']}, WR {100*x['wr']:.1f}%, PnL {x['pnl']:+.2f}; D {x['D_n']} / {100*x['D_wr']:.1f}% / {x['D_pnl']:+.2f}; V {x['V_n']} / {100*x['V_wr']:.1f}% / {x['V_pnl']:+.2f}")
    md += ['', '## Assessment',
           '- Reproducible pre-entry features >=0.60 robust strength: '+(', '.join([x['feature'] for x in reproducible]) if reproducible else '**none**')+'.',
           '- '+assessment['interpretation'],
           '- '+assessment['guardrail']]
    (OUT/'SUN1.7_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
