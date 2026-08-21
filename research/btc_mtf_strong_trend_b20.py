#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json, math
import numpy as np
import pandas as pd

import btc_weekly_w1_vah_false_break_b17 as b17
import btc_weekly_mtf_level_atlas_b11 as b11

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_MTF_STRONG_TREND_B20_Result.md'
OUT_JSON=ROOT/'BTC_MTF_STRONG_TREND_B20_Result.json'
OUT_ATLAS=ROOT/'BTC_MTF_STRONG_TREND_B20_Atlas.csv'
OUT_EP=ROOT/'BTC_MTF_STRONG_TREND_B20_Episodes.csv'
OUT_TR=ROOT/'BTC_MTF_STRONG_TREND_B20_Trades.csv'
OUT_SIDE=ROOT/'BTC_MTF_STRONG_TREND_B20_Sides.csv'
REVISION='B20_V1'
FAV=0.0115
ADV=0.0085
FEE=0.0015
VARIANTS=['S1_STACK','S2_STACK_SLOPE','S3_STACK_MOMENTUM','S4_STACK_MOMENTUM_FLOW']
PARTS={
 'external':(pd.Timestamp('2020-01-01',tz='UTC'),pd.Timestamp('2022-01-01',tz='UTC')),
 'development':(pd.Timestamp('2022-01-01',tz='UTC'),pd.Timestamp('2025-01-01',tz='UTC')),
 'reference_validation':(pd.Timestamp('2025-01-01',tz='UTC'),pd.Timestamp('2026-07-30',tz='UTC')),
 'august':(pd.Timestamp('2026-08-01',tz='UTC'),pd.Timestamp('2026-08-20',tz='UTC')),
}


def sma_features(src:pd.DataFrame, lag:int, duration:pd.Timedelta)->pd.DataFrame:
    z=src[['open','high','low','close']].copy()
    for n in (7,25,99):z[f'ma{n}']=z.close.rolling(n,min_periods=n).mean()
    z['ma25_lag']=z.ma25.shift(lag);z['ma99_lag']=z.ma99.shift(lag);z['close_lag']=z.close.shift(lag)
    z.index=z.index+duration
    return z


def source_frames(x15):
    m15=x15[['open','high','low','close']].copy()
    h1=m15.resample('1h',label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    h4=m15.resample('4h',origin='start_day',label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    return {
      'm15':sma_features(m15,4,pd.Timedelta(minutes=15)),
      'h1':sma_features(h1,3,pd.Timedelta(hours=1)),
      'h4':sma_features(h4,2,pd.Timedelta(hours=4)),
    }


def map_features(avail:pd.DataFrame, target:pd.DatetimeIndex, prefix:str)->pd.DataFrame:
    cols=['close','ma7','ma25','ma99','ma25_lag','ma99_lag','close_lag']
    q=avail[cols].reindex(target,method='ffill').copy()
    q.columns=[f'{prefix}_{c}' for c in q.columns]
    return q


def build_state_table(x15:pd.DataFrame)->pd.DataFrame:
    src=source_frames(x15);idx=x15.index
    q=pd.DataFrame(index=idx)
    for tf in ('m15','h1','h4'):
        q=q.join(map_features(src[tf],idx,tf))

    # Completed 1h/3h taker flow known at this 15m open: rolling windows end on the prior 15m bar.
    fq=x15.quote_volume.rolling(4,min_periods=4).sum();fb=x15.taker_buy_quote.rolling(4,min_periods=4).sum()
    gq=x15.quote_volume.rolling(12,min_periods=12).sum();gb=x15.taker_buy_quote.rolling(12,min_periods=12).sum()
    f1=(2*fb/fq-1);f3=(2*gb/gq-1)
    f1.index=f1.index+pd.Timedelta(minutes=15);f3.index=f3.index+pd.Timedelta(minutes=15)
    q['flow1h']=f1.reindex(idx,method='ffill');q['flow3h']=f3.reindex(idx,method='ffill')

    for side,ss in [('LONG',1.0),('SHORT',-1.0)]:
        stack=np.ones(len(q),dtype=bool);slope=np.ones(len(q),dtype=bool);mom=np.ones(len(q),dtype=bool)
        for tf in ('m15','h1','h4'):
            c=q[f'{tf}_close'];m7=q[f'{tf}_ma7'];m25=q[f'{tf}_ma25'];m99=q[f'{tf}_ma99']
            if side=='LONG':core=(m7>m25)&(m25>m99)&(c>m25)
            else:core=(m7<m25)&(m25<m99)&(c<m25)
            stack &= core.fillna(False).to_numpy(bool)
            sl=((q[f'{tf}_ma25']-q[f'{tf}_ma25_lag'])*ss>0)&((q[f'{tf}_ma99']-q[f'{tf}_ma99_lag'])*ss>0)
            mo=((q[f'{tf}_close']/q[f'{tf}_close_lag']-1)*ss>0)
            slope &= sl.fillna(False).to_numpy(bool);mom &= mo.fillna(False).to_numpy(bool)
        q[f'{side}_S1_STACK']=stack
        q[f'{side}_S2_STACK_SLOPE']=stack&slope
        q[f'{side}_S3_STACK_MOMENTUM']=stack&slope&mom
        flowok=((q.flow1h*ss)>0)&((q.flow3h*ss)>0)
        q[f'{side}_S4_STACK_MOMENTUM_FLOW']=stack&slope&mom&flowok.fillna(False).to_numpy(bool)

    for v in VARIANTS:
        lo=q[f'LONG_{v}'].to_numpy(bool);sh=q[f'SHORT_{v}'].to_numpy(bool)
        q[f'state_{v}']=np.where(lo&~sh,'LONG',np.where(sh&~lo,'SHORT','OFF'))
    return q


def partition_weeks(part):
    a,z=PARTS[part]
    return b11.complete_weeks(a,z)


def week_key(t):return b11.week_key(b11.week_start(pd.Timestamp(t)))


def build_episodes(state:pd.Series,part:str)->pd.DataFrame:
    a,z=PARTS[part];s=state[(state.index>=a)&(state.index<z)]
    rows=[];cur='OFF';start=None
    for t,val in s.items():
        val=str(val)
        if val==cur:continue
        if cur in ('LONG','SHORT') and start is not None:
            rows.append({'partition':part,'side':cur,'start_ts':start,'end_ts':t,'duration_h':float((t-start)/pd.Timedelta(hours=1)),'week':week_key(start)})
        cur=val;start=t if val in ('LONG','SHORT') else None
    if cur in ('LONG','SHORT') and start is not None:
        rows.append({'partition':part,'side':cur,'start_ts':start,'end_ts':z,'duration_h':float((z-start)/pd.Timedelta(hours=1)),'week':week_key(start)})
    return pd.DataFrame(rows)


def episode_outcomes(ep:pd.DataFrame,bars:pd.DataFrame)->pd.DataFrame:
    if ep.empty:return ep.assign(outcome=pd.Series(dtype=str),entry=pd.Series(dtype=float))
    rows=[]
    for r in ep.itertuples(index=False):
        q=bars[(bars.index>=r.start_ts)&(bars.index<r.end_ts)]
        if q.empty:continue
        entry=float(q.iloc[0].open);side=r.side
        tp=entry*(1+FAV) if side=='LONG' else entry*(1-FAV)
        sl=entry*(1-ADV) if side=='LONG' else entry*(1+ADV)
        outcome='OFF';exit_ts=r.end_ts;hours=float((r.end_ts-r.start_ts)/pd.Timedelta(hours=1))
        for j,(t,b) in enumerate(q.iterrows(),1):
            if side=='LONG':hit_sl=float(b.low)<=sl;hit_tp=float(b.high)>=tp
            else:hit_sl=float(b.high)>=sl;hit_tp=float(b.low)<=tp
            if hit_sl:outcome='SL';exit_ts=t;hours=j*.25;break
            if hit_tp:outcome='TP';exit_ts=t;hours=j*.25;break
        x=dict(r._asdict());x.update({'entry':entry,'tp':tp,'sl':sl,'outcome':outcome,'first_exit_ts':exit_ts,'first_hours':hours});rows.append(x)
    return pd.DataFrame(rows)


def close_return(entry,px,side):return (px/entry-1)*(1 if side=='LONG' else -1)-FEE


def simulate(state:pd.Series,bars:pd.DataFrame,part:str)->pd.DataFrame:
    a,z=PARTS[part];q=bars[(bars.index>=a)&(bars.index<z)].copy();s=state.reindex(q.index).fillna('OFF')
    rows=[];pos=None
    for k,(t,b) in enumerate(q.iterrows()):
        st=str(s.iloc[k]);op=float(b.open);hi=float(b.high);lo=float(b.low)
        # State for this open is based only on bars completed before this open.
        if pos is not None and st!=pos['side']:
            net=close_return(pos['entry'],op,pos['side'])
            rows.append({**pos,'exit_ts':t,'exit':op,'reason':'OFF','net_ret':net,'bars_held':k-pos['entry_k']})
            pos=None
        if pos is None and st in ('LONG','SHORT'):
            entry=op;tp=entry*(1+FAV) if st=='LONG' else entry*(1-FAV);sl=entry*(1-ADV) if st=='LONG' else entry*(1+ADV)
            pos={'partition':part,'side':st,'entry_ts':t,'entry':entry,'tp':tp,'sl':sl,'entry_k':k,'week':week_key(t)}
        if pos is not None:
            if pos['side']=='LONG':hit_sl=lo<=pos['sl'];hit_tp=hi>=pos['tp']
            else:hit_sl=hi>=pos['sl'];hit_tp=lo<=pos['tp']
            if hit_sl:
                rows.append({**pos,'exit_ts':t,'exit':pos['sl'],'reason':'SL','net_ret':-0.0100000000000000,'bars_held':k-pos['entry_k']+1});pos=None
            elif hit_tp:
                rows.append({**pos,'exit_ts':t,'exit':pos['tp'],'reason':'TP','net_ret':0.0100000000000000,'bars_held':k-pos['entry_k']+1});pos=None
    if pos is not None and len(q):
        t=q.index[-1];px=float(q.iloc[-1].close);net=close_return(pos['entry'],px,pos['side'])
        rows.append({**pos,'exit_ts':t,'exit':px,'reason':'EOP','net_ret':net,'bars_held':len(q)-pos['entry_k']})
    out=pd.DataFrame(rows)
    if len(out):out=out.drop(columns=['entry_k'])
    return out


def pf(a):
    a=np.asarray(a,float);gp=float(a[a>0].sum());gl=float(-a[a<0].sum())
    return gp/gl if gl>0 else (999. if gp>0 else 0.)


def max_ls(a):
    m=c=0
    for x in np.asarray(a,float):
        if x<=0:c+=1;m=max(m,c)
        else:c=0
    return int(m)


def summarize(variant,part,state,epdiag,trades):
    weeks=partition_weeks(part);wkset={week_key(w) for w in weeks};a,z=PARTS[part]
    ss=state[(state.index>=a)&(state.index<z)]
    sw={week_key(t) for t,v in ss.items() if v!='OFF'} & wkset
    e=epdiag.copy();tr=trades.copy()
    n=len(tr);arr=tr.net_ret.to_numpy(float) if n else np.array([])
    tradeweeks=set(tr.week.tolist())&wkset if n else set()
    wp={w:float(g.net_ret.sum()) for w,g in tr[tr.week.isin(wkset)].groupby('week')} if n else {}
    posweeks=sum(v>0 for v in wp.values());pt=int((arr>0).sum()) if n else 0
    tp=int((tr.reason=='TP').sum()) if n else 0;sl=int((tr.reason=='SL').sum()) if n else 0;off=int((tr.reason=='OFF').sum()) if n else 0;eop=int((tr.reason=='EOP').sum()) if n else 0
    etp=int((e.outcome=='TP').sum()) if len(e) else 0;esl=int((e.outcome=='SL').sum()) if len(e) else 0;eoff=int((e.outcome=='OFF').sum()) if len(e) else 0
    return {
      'variant':variant,'partition':part,'weeks':len(weeks),'episodes':len(e),'long_episodes':int((e.side=='LONG').sum()) if len(e) else 0,'short_episodes':int((e.side=='SHORT').sum()) if len(e) else 0,
      'median_episode_h':float(e.duration_h.median()) if len(e) else None,'mean_episode_h':float(e.duration_h.mean()) if len(e) else None,
      'state_weeks':len(sw),'state_week_coverage':len(sw)/len(weeks) if weeks else None,
      'episode_tp':etp,'episode_sl':esl,'episode_off':eoff,'episode_tp_rate':etp/len(e) if len(e) else None,
      'trades':n,'long_trades':int((tr.side=='LONG').sum()) if n else 0,'short_trades':int((tr.side=='SHORT').sum()) if n else 0,
      'tp':tp,'sl':sl,'off':off,'eop':eop,'positive_trades':pt,'positive_trade_rate':pt/n if n else None,'tp_hit_rate':tp/n if n else None,
      'mean_net_ret':float(arr.mean()) if n else None,'total_net_ret':float(arr.sum()) if n else 0.0,'pf':pf(arr) if n else None,'max_ls':max_ls(arr) if n else 0,
      'trade_weeks':len(tradeweeks),'trade_week_coverage':len(tradeweeks)/len(weeks) if weeks else None,
      'positive_weeks':posweeks,'positive_week_rate':posweeks/len(wp) if wp else None,
    }


def side_stats(variant,part,tr):
    out=[]
    for side in ('LONG','SHORT'):
        q=tr[tr.side==side] if len(tr) else tr;n=len(q);a=q.net_ret.to_numpy(float) if n else np.array([])
        out.append({'variant':variant,'partition':part,'side':side,'trades':n,'positive_rate':float((a>0).mean()) if n else None,'tp_rate':float((q.reason=='TP').mean()) if n else None,'mean_net_ret':float(a.mean()) if n else None,'total_net_ret':float(a.sum()) if n else 0.,'pf':pf(a) if n else None})
    return out


def eligible_dev(r):return r['trades']>=100 and r['episodes']>=50

def useful(r):
    vals=[r['mean_net_ret'],r['pf'],r['positive_trade_rate'],r['positive_week_rate'],r['episode_tp_rate']]
    if any(v is None or not np.isfinite(v) for v in vals):return False
    return r['trades']>=100 and r['mean_net_ret']>0 and r['pf']>1.20 and r['positive_trade_rate']>=.60 and r['positive_week_rate']>=.65 and r['episode_tp_rate']>=.65

def highp(r):
    return r['trades']>=75 and r['positive_trade_rate'] is not None and r['positive_trade_rate']>=.75 and r['pf'] is not None and r['pf']>1.50

def weekly100(r):return r['trade_week_coverage'] is not None and abs(r['trade_week_coverage']-1)<1e-12 and r['positive_week_rate'] is not None and abs(r['positive_week_rate']-1)<1e-12

def pct(v):return '-' if v is None or not np.isfinite(v) else f'{100*v:.2f}%'
def num(v):return '-' if v is None or not np.isfinite(v) else f'{v:.3f}'


def main():
    x15=b17.load_15m(b17.BASE_FUT,'klines','futures').copy()
    print('15m',len(x15),x15.index.min(),x15.index.max(),flush=True)
    states=build_state_table(x15);print('state table ready',len(states),flush=True)
    bars=x15[['open','high','low','close']].astype(float)
    atlas=[];all_ep=[];all_tr=[];sides=[];lookup={}
    for v in VARIANTS:
        state=states[f'state_{v}']
        for part in ('development','external','reference_validation','august'):
            ep=build_episodes(state,part);ed=episode_outcomes(ep,bars)
            tr=simulate(state,bars,part)
            if len(ed):ed=ed.copy();ed['variant']=v;all_ep.append(ed)
            if len(tr):tr=tr.copy();tr['variant']=v;all_tr.append(tr)
            row=summarize(v,part,state,ed,tr);atlas.append(row);lookup[(v,part)]=row
            sides.extend(side_stats(v,part,tr))
            print(v,part,'episodes',row['episodes'],'trades',row['trades'],'pos',row['positive_trade_rate'],'pf',row['pf'],flush=True)
    adf=pd.DataFrame(atlas);adf.to_csv(OUT_ATLAS,index=False);pd.DataFrame(sides).to_csv(OUT_SIDE,index=False)
    if all_ep:pd.concat(all_ep,ignore_index=True).to_csv(OUT_EP,index=False)
    if all_tr:pd.concat(all_tr,ignore_index=True).to_csv(OUT_TR,index=False)

    dev=[lookup[(v,'development')] for v in VARIANTS]
    elig=[r for r in dev if eligible_dev(r)]
    pool=elig if elig else dev
    def sk(r):
        return (-(r['positive_trade_rate'] if r['positive_trade_rate'] is not None else -1),-(r['pf'] if r['pf'] is not None else -1),-(r['episode_tp_rate'] if r['episode_tp_rate'] is not None else -1),-(r['trade_week_coverage'] if r['trade_week_coverage'] is not None else -1),r['variant'])
    primary=sorted(pool,key=sk)[0]['variant']
    ext=lookup[(primary,'external')];val=lookup[(primary,'reference_validation')]
    g_use=useful(ext) and useful(val);g_high=highp(ext) and highp(val);g_100=weekly100(ext) and weekly100(val)
    result={'experiment':'B20_MTF_STRONG_TREND_STATE','revision':REVISION,'primary_variant':primary,'development_eligible':[r['variant'] for r in elig],
            'gates':{'B20_STRONG_STATE_USEFUL':'PASS' if g_use else 'FAIL','B20_HIGH_PRECISION':'PASS' if g_high else 'FAIL','B20_WEEKLY_100_DIAGNOSTIC':'PASS' if g_100 else 'FAIL'},
            'atlas':atlas,'data':{'rows_15m':len(x15),'first':str(x15.index.min()),'last':str(x15.index.max())},'live_bbc_untouched':True}
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')

    verdict='B20_STRONG_STATE_USEFUL_PASS' if g_use else 'B20_NO_ROBUST_STRONG_STATE'
    lines=['# BTC Multi-Timeframe Strong Trend State B20 — Result','',f'**Verdict: {verdict}**','',
           f"15m rows **{len(x15):,}**, {x15.index.min()} -> {x15.index.max()}.",'',
           'Frozen detector: **SMA 7/25/99 on 15m + H1 + H4, causal completed bars only.**',
           'Execution: **one position at a time; immediately re-enter next 15m open while the same STRONG state remains ON.**','',
           f'Frozen development PRIMARY: **{primary}**','',
           '| Variant | Partition | Episodes | Med dur | State-week cov | Trades | TP/SL/OFF | Positive WR | TP rate | Exp/trade | PF | Trade-week cov | Positive weeks | Episode TP |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in VARIANTS:
        for part in ('development','external','reference_validation','august'):
            r=lookup[(v,part)]
            dur='-' if r['median_episode_h'] is None else f"{r['median_episode_h']:.2f}h"
            lines.append(f"| {v} | {part} | {r['episodes']} | {dur} | {pct(r['state_week_coverage'])} | {r['trades']} | {r['tp']}/{r['sl']}/{r['off']} | {pct(r['positive_trade_rate'])} | {pct(r['tp_hit_rate'])} | {pct(r['mean_net_ret'])} | {num(r['pf'])} | {pct(r['trade_week_coverage'])} | {pct(r['positive_week_rate'])} | {pct(r['episode_tp_rate'])} |")
    lines += ['','## PRIMARY side breakdown','', '| Partition | Side | Trades | Positive WR | TP rate | Exp/trade | PF |','|---|---|---:|---:|---:|---:|---:|']
    sdf=pd.DataFrame(sides)
    for part in ('development','external','reference_validation','august'):
        for side in ('LONG','SHORT'):
            r=sdf[(sdf.variant==primary)&(sdf.partition==part)&(sdf.side==side)].iloc[0]
            lines.append(f"| {part} | {side} | {int(r.trades)} | {pct(r.positive_rate)} | {pct(r.tp_rate)} | {pct(r.mean_net_ret)} | {num(r.pf)} |")
    lines += ['','## Gates','',f"- B20_STRONG_STATE_USEFUL: **{'PASS' if g_use else 'FAIL'}**",f"- B20_HIGH_PRECISION: **{'PASS' if g_high else 'FAIL'}**",f"- B20_WEEKLY_100_DIAGNOSTIC: **{'PASS' if g_100 else 'FAIL'}**",'',
              'No post-result MA/timeframe/slope/momentum/flow threshold rescue. Live BBC untouched. Historical performance is not a guarantee of future performance.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('\n'.join(lines),flush=True)

if __name__=='__main__':main()
