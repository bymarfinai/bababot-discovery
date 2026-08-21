#!/usr/bin/env python3
from pathlib import Path
import json, numpy as np, pandas as pd
import btc_orb_b0_baseline as b0

ROOT=Path(__file__).resolve().parent.parent
OUTJ=ROOT/'BTC_WEEKLY_BEST_B7_Result.json'
OUTM=ROOT/'BTC_WEEKLY_BEST_B7_Result.md'
OUTC=ROOT/'BTC_WEEKLY_BEST_B7_Selected.csv'
FEE=b0.FEE
RRS={'R100':1.0,'R150':1.5}
THRS=[0.90,0.95,0.975]

def rs(k,tf):
    x=k[['open','high','low','close']].resample(tf,origin='start_day',label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    pc=x.close.shift(1)
    tr=pd.concat([(x.high-x.low),(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    x['atr']=tr.rolling(14,min_periods=14).mean().shift(1)
    x['hi20']=x.high.shift(1).rolling(20,min_periods=20).max()
    x['lo20']=x.low.shift(1).rolling(20,min_periods=20).min()
    x['mid20']=(x.hi20+x.lo20)/2
    x['mom3']=(x.close/x.close.shift(3)-1)/(x.atr/x.close)
    x['body']=((x.close-x.open).abs()/(x.high-x.low).replace(0,np.nan)).clip(0,1)
    x['rangeexp']=((x.high-x.low)/x.atr).clip(0,10)
    x['up_break']=((x.close-x.hi20)/x.atr).clip(-10,10)
    x['dn_break']=((x.lo20-x.close)/x.atr).clip(-10,10)
    half=((x.hi20-x.lo20)/2).replace(0,np.nan)
    x['range_loc']=((x.close-x.mid20)/half).clip(-3,3)
    return x.dropna()

def opportunities(k):
    out=[]
    for tf,hold in [('1h',6),('4h',3)]:
        x=rs(k,tf)
        for i in range(3,len(x)-hold-1):
            t=x.index[i]; b=x.iloc[i]
            mom_signed=float(b['mom3']) + float(b['range_loc'])
            mom_side='LONG' if mom_signed>=0 else 'SHORT'
            mom_score=abs(mom_signed)
            up=float(b['up_break']); dn=float(b['dn_break']); body=float(b['body'])
            if up>=dn:
                br_side='LONG'; br_raw=up
            else:
                br_side='SHORT'; br_raw=dn
            br_score=max(0.0,br_raw)*(0.5+body)
            signed_break=up-dn
            comb_signed=float(b['mom3'])+float(b['range_loc'])+signed_break*(0.5+body)
            comb_side='LONG' if comb_signed>=0 else 'SHORT'
            comb_score=abs(comb_signed)*(0.5+min(float(b['rangeexp']),3.0)/3.0)
            iso=t.isocalendar(); week=f'{int(iso.year):04d}-W{int(iso.week):02d}'
            for sel,side,score in [('MOMENTUM',mom_side,mom_score),('BREAKOUT',br_side,br_score),('COMBINED',comb_side,comb_score)]:
                out.append({'tf':tf,'signal_ts':t,'entry_idx':i+1,'hold':hold,'selector':sel,'side':side,'score':float(score),'week':week})
    return pd.DataFrame(out)

def trade_for(op,xmap,rr):
    x=xmap[op['tf']]; idx=int(op['entry_idx'])
    if idx>=len(x): return None
    e=float(x.iloc[idx].open); atr=float(x.iloc[idx].atr); side=op['side']
    if not np.isfinite(atr) or atr<=0:return None
    tp=e+rr*atr if side=='LONG' else e-rr*atr
    sl=e-atr if side=='LONG' else e+atr
    fut=x.iloc[idx:idx+int(op['hold'])]
    if fut.empty:return None
    px=float(fut.iloc[-1].close); reason='TIME'; xt=fut.index[-1]
    for t,b in fut.iterrows():
        hs=float(b.low)<=sl if side=='LONG' else float(b.high)>=sl
        ht=float(b.high)>=tp if side=='LONG' else float(b.low)<=tp
        if hs: px=sl; reason='SL'; xt=t; break
        if ht: px=tp; reason='TP'; xt=t; break
    gross=(px/e-1)*(1 if side=='LONG' else -1)
    return {'net_ret':gross-FEE,'reason':reason,'exit_ts':xt,'entry':e}

def stat(z):
    if len(z)==0:return {'n':0,'wins':0,'losses':0,'wr':None,'exp':None,'pf':None,'max_losing_streak':0}
    a=np.array(z.net_ret,float); wins=int((a>0).sum()); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    streak=mx=0
    for v in a:
        if v<=0: streak+=1; mx=max(mx,streak)
        else: streak=0
    return {'n':len(a),'wins':wins,'losses':len(a)-wins,'wr':wins/len(a),'exp':float(a.mean()),'pf':float(gp/gl if gl>0 else 999.0),'max_losing_streak':mx}

def blocks(z):
    z=z.sort_values('signal_ts').reset_index(drop=True)
    ed=np.linspace(0,len(z),5,dtype=int)
    return [stat(z.iloc[ed[i]:ed[i+1]]) for i in range(4)]

def select_weekly(ops,selector,threshold):
    z=ops[(ops.selector==selector)&(ops.score>=threshold)].copy()
    if z.empty:return z
    z=z.sort_values(['week','score','signal_ts'],ascending=[True,False,True])
    return z.groupby('week',as_index=False).head(1).sort_values('signal_ts')

def main():
    k=b0.load(); xmap={'1h':rs(k,'1h'),'4h':rs(k,'4h')}
    ops=opportunities(k).sort_values('signal_ts').reset_index(drop=True)
    weeks=sorted(ops.week.unique()); cut=int(len(weeks)*0.70); d_weeks=set(weeks[:cut]); v_weeks=set(weeks[cut:])
    disc_ops=ops[ops.week.isin(d_weeks)]
    results=[]; selected_rows=[]
    for sel in ['MOMENTUM','BREAKOUT','COMBINED']:
        base=disc_ops[disc_ops.selector==sel].score
        for q in THRS:
            thr=float(base.quantile(q)); chosen=select_weekly(ops,sel,thr)
            for rn,rr in RRS.items():
                rows=[]
                for _,op in chosen.iterrows():
                    tr=trade_for(op,xmap,rr)
                    if tr is None:continue
                    r=op.to_dict(); r.update(tr); r['rr']=rn; r['threshold_q']=q; rows.append(r)
                df=pd.DataFrame(rows)
                if df.empty: continue
                d=df[df.week.isin(d_weeks)].copy(); v=df[df.week.isin(v_weeks)].copy()
                results.append({'selector':sel,'threshold_q':q,'threshold':thr,'rr':rn,'disc':stat(d),'val':stat(v),'pooled':stat(df),'val_no_trade_weeks':len(v_weeks)-v.week.nunique(),'blocks':blocks(df)})
                selected_rows.extend(rows)
    ranked=sorted(results,key=lambda r:((r['val']['wr'] or 0),(r['val']['n'] or 0),(r['val']['exp'] or -9),(r['val']['pf'] or 0)),reverse=True)
    perfect=[r for r in ranked if r['val']['n']>=20 and r['val']['wr']==1.0]
    verdict='PERFECT_VALIDATION_CANDIDATE_B7' if perfect else 'NO_PERFECT_VALIDATION_CANDIDATE_B7'
    out={'protocol':'BTC_WEEKLY_BEST_B7','verdict':verdict,'weeks_total':len(weeks),'weeks_disc':len(d_weeks),'weeks_val':len(v_weeks),'perfect':perfect,'top20':ranked[:20]}
    OUTJ.write_text(json.dumps(out,indent=2,default=str)+'\n')
    if selected_rows: pd.DataFrame(selected_rows).to_csv(OUTC,index=False)
    md=['# BTC Weekly Best-State B7 — Result','',f'**Verdict: {verdict}**','',f'Weeks: {len(weeks)} total / {len(d_weeks)} discovery / {len(v_weeks)} validation.','', '| Selector | Q | RR | Disc N/W/WR | Val N/W/L/WR | Val Exp | PF | No-trade val weeks | Max LS |','|---|---:|---|---:|---:|---:|---:|---:|---:|']
    for r in ranked[:20]:
        d,v=r['disc'],r['val']; md.append(f"| {r['selector']} | {100*r['threshold_q']:.1f}% | {r['rr']} | {d['n']} / {d['wins']} / {100*d['wr']:.2f}% | {v['n']} / {v['wins']} / {v['losses']} / {100*v['wr']:.2f}% | {100*v['exp']:.3f}% | {v['pf']:.3f} | {r['val_no_trade_weeks']} | {v['max_losing_streak']} |")
    md += ['','Thresholds were derived from discovery only. Maximum one trade per week. NO TRADE allowed. Live BBC untouched.']
    OUTM.write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str))
if __name__=='__main__': main()
