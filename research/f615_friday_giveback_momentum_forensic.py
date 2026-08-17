#!/usr/bin/env python3
from __future__ import annotations
import json, os, math
from pathlib import Path
import numpy as np, pandas as pd
import f517_regime_attribution as f517
import f611_friday_fibonacci_forensic as f611
import f612_friday_fib_early5_cut as f612
import f69_friday_early_sink_candidate_robustness as f69

OUT=Path(os.getenv('F615_OUT','f615_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL

def fib5_state(k,t,tr):
    f2=f611.fib_features(k,t,float(tr.entry),120); baseline=f612.rolling_2h_range_baseline(k,t)
    if f2 is None or not np.isfinite(baseline): return False
    return bool(float(k.loc[t].close)<tr.entry and tr.exit_t>t+pd.Timedelta(minutes=5) and float(f2['retr_depth'])<=0.382 and float(f2['range_pct'])>baseline)

def candle_feat(b):
    rng=max(float(b.high-b.low),1e-12); body=abs(float(b.close-b.open)); uw=float(b.high-max(b.open,b.close)); lw=float(min(b.open,b.close)-b.low)
    return {'bear':bool(b.close<b.open),'upper_wick_ratio':uw/rng,'lower_wick_ratio':lw/rng,'body_ratio':body/rng,'close_pos':(float(b.close-b.low))/rng,'upper_wick_gt_body':bool(uw>body),'taker':float(b.taker_imb),'ema7_dist':float(b.close/b.ema7-1),'ema20_dist':float(b.close/b.ema20-1)}

def first_hit(k,tr,thr):
    px=tr.entry*(1+thr)
    bars=k[(k.index>=tr.entry_t)&(k.index<tr.exit_t)]
    z=bars[bars.high>=px]
    return None if z.empty else z.iloc[0].ts

def pre_fib_resistance(k,t,event_px,hours):
    w=k[(k.index<t)&(k.index>=t-pd.Timedelta(hours=hours))]
    if w.empty: return None
    hi=float(w.high.max()); lo=float(w.low.min()); thi=w.high.idxmax(); tlo=w.low.idxmin(); span=hi-lo
    if span<=0:return None
    candidates=[]
    if thi<tlo:
        for r in [0.382,0.5,0.618,0.786,1.0]: candidates.append((f'retr_{r}',lo+r*span))
    for x in [1.272,1.618]: candidates.append((f'ext_{x}',lo+x*span))
    if not candidates:return None
    name,level=min(candidates,key=lambda z:abs(event_px-z[1])/event_px)
    return {'name':name,'level':level,'dist_pct':abs(event_px-level)/event_px,'downswing':bool(thi<tlo)}

def post_event(k,tr,hit_t,minutes):
    end=min(hit_t+pd.Timedelta(minutes=minutes+5),tr.exit_t)
    w=k[(k.index>=hit_t)&(k.index<end)]
    if w.empty:return {}
    feats=[candle_feat(b) for _,b in w.iterrows()]
    close=float(w.iloc[-1].close); best=float(w.high.max())
    return {
      f'post{minutes}_progress':close/tr.entry-1,
      f'post{minutes}_drawdown_from_best':close/best-1,
      f'post{minutes}_bear_frac':float(np.mean([x['bear'] for x in feats])),
      f'post{minutes}_upperwick_med':float(np.median([x['upper_wick_ratio'] for x in feats])),
      f'post{minutes}_wickgtbody_frac':float(np.mean([x['upper_wick_gt_body'] for x in feats])),
      f'post{minutes}_taker_med':float(np.median([x['taker'] for x in feats])),
      f'post{minutes}_ema7_dist':float(w.iloc[-1].close/w.iloc[-1].ema7-1),
      f'post{minutes}_below_ema7':bool(w.iloc[-1].close<w.iloc[-1].ema7),
    }

def summarize(df,label):
    def med(c): return float(df[c].median()) if c in df and len(df[c].dropna()) else np.nan
    return {'n':int(len(df)),'label':label,
      'event_bear_rate':float(df.event_bear.mean()),'event_upperwick_med':med('event_upper_wick_ratio'),'event_wickgtbody_rate':float(df.event_upper_wick_gt_body.mean()),'event_taker_med':med('event_taker'),'event_ema7_dist_med':med('event_ema7_dist'),
      'fib2h_near_0p10_rate':float((df.fib2h_dist_pct<=0.001).mean()),'fib4h_near_0p10_rate':float((df.fib4h_dist_pct<=0.001).mean()),'fib2h_dist_med':med('fib2h_dist_pct'),'fib4h_dist_med':med('fib4h_dist_pct'),
      **{f'{c}_med':med(c) for c in ['post5_progress','post10_progress','post15_progress','post30_progress','post10_drawdown_from_best','post15_drawdown_from_best','post30_drawdown_from_best','post10_taker_med','post15_taker_med','post30_taker_med','post10_upperwick_med','post15_upperwick_med','post30_upperwick_med']},
      'post10_below_ema7_rate':float(df.post10_below_ema7.mean()),'post15_below_ema7_rate':float(df.post15_below_ema7.mean()),'post30_below_ema7_rate':float(df.post30_below_ema7.mean())}

def main():
    k=f517.load_klines(); days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8); tr=f517.simulate_parent(k,t)
        a5=fib5_state(k,t,tr); a10=f69.early_state(k,t,tr); a60=f69.f65_state(k,t,tr); intercepted=a5 or a10 or a60
        for tag,thr in [('R05',0.5*R),('R10',1.0*R)]:
            ht=first_hit(k,tr,thr)
            if ht is None: continue
            is_giveback=bool(tr.pnl<=0 and not intercepted and tr.mfe>=thr and tr.mfe<2*R)
            is_control=bool(tr.pnl>0)
            if not (is_giveback or is_control): continue
            b=k.loc[ht]; cf=candle_feat(b); event_px=float(b.high)
            f2=pre_fib_resistance(k,t,event_px,2); f4=pre_fib_resistance(k,t,event_px,4)
            row={'i':i,'period':'discovery' if i<f517.SPLIT_N else 'validation','date':tr.date,'tag':tag,'group':'GIVEBACK' if is_giveback else 'WINNER_CONTROL','parent_pnl':tr.pnl,'mfe_r':tr.mfe/R,'hit_t':str(ht),**{f'event_{kk}':vv for kk,vv in cf.items()}}
            for pref,fv in [('fib2h',f2),('fib4h',f4)]:
                row[f'{pref}_dist_pct']=np.nan if fv is None else fv['dist_pct']; row[f'{pref}_level']=None if fv is None else fv['name']; row[f'{pref}_downswing']=False if fv is None else fv['downswing']
            for m in [5,10,15,30]: row.update(post_event(k,tr,ht,m))
            rows.append(row)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f615_events.csv',index=False)
    out={}
    for tag in ['R05','R10']:
        sub=df[df.tag==tag]; out[tag]={}
        for g in ['GIVEBACK','WINNER_CONTROL']: out[tag][g]=summarize(sub[sub.group==g],g)
        counts=sub.groupby(['group','period']).size()
        out[tag]['counts_by_period']={f'{g}|{p}':int(n) for (g,p),n in counts.items()}
    payload=json.dumps(out,indent=2,default=str)
    (OUT/'f615_summary.json').write_text(payload)
    (OUT/'F6.15_CHECKPOINT.md').write_text('# Friday F6.15 — Giveback Momentum Forensic\n\n**Status: FORENSIC ONLY — no management rule tuned.**\n\nAnchors are causal first-hit milestones (+0.5R and +1R), not hindsight peaks.\n\n```json\n'+payload+'\n```\n')
    print(payload,flush=True)
if __name__=='__main__': main()
