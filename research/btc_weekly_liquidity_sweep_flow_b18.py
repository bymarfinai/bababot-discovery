#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd

import btc_weekly_volume_memory_b13 as vm
import btc_weekly_volume_memory_b13_fast as vmfast
import btc_weekly_w1_vah_false_break_b17 as b17

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_WEEKLY_LIQUIDITY_SWEEP_FLOW_B18_Result.md'
OUT_JSON=ROOT/'BTC_WEEKLY_LIQUIDITY_SWEEP_FLOW_B18_Result.json'
OUT_RULES=ROOT/'BTC_WEEKLY_LIQUIDITY_SWEEP_FLOW_B18_Rules.csv'
OUT_ATLAS=ROOT/'BTC_WEEKLY_LIQUIDITY_SWEEP_FLOW_B18_Atlas.csv'
OUT_SEL=ROOT/'BTC_WEEKLY_LIQUIDITY_SWEEP_FLOW_B18_Selected.csv'
REVISION='B18_V1'
VARIANTS=['RAW','H1_FLOW','FLOW3','PERSIST','MICRO','MICRO_PERSIST']


def flow(qv,buy):
    qv=float(qv);buy=float(buy)
    return 2*buy/qv-1 if qv>0 else np.nan


def build_h1(x15):
    h=x15.resample('1h',label='left',closed='left').agg({
        'open':'first','high':'max','low':'min','close':'last','quote_volume':'sum','taker_buy_quote':'sum'
    }).dropna()
    pc=h.close.shift(1)
    tr=pd.concat([h.high-h.low,(h.high-pc).abs(),(h.low-pc).abs()],axis=1).max(axis=1)
    h['atr14']=tr.rolling(14,min_periods=14).mean()
    h['hour_flow']=np.where(h.quote_volume>0,2*h.taker_buy_quote/h.quote_volume-1,np.nan)
    for n in (3,6):
        q=h.quote_volume.rolling(n,min_periods=n).sum();b=h.taker_buy_quote.rolling(n,min_periods=n).sum()
        h[f'flow{n}h']=np.where(q>0,2*b/q-1,np.nan)
    return h


def prev_period_state(x15,kind):
    if kind=='D':
        keys=x15.index.floor('D');dur=pd.Timedelta(days=1);expected=96;hi='PDH';lo='PDL'
    elif kind=='W':
        keys=pd.DatetimeIndex([vm.b11.week_start(t) for t in x15.index]);dur=pd.Timedelta(days=7);expected=672;hi='PWH';lo='PWL'
    else:raise ValueError(kind)
    rows=[]
    for k,g in x15.groupby(keys,sort=True):
        if len(g)<int(expected*.95):continue
        rows.append({'avail_ts':pd.Timestamp(k)+dur,'instance':pd.Timestamp(k).isoformat(),hi:float(g.high.max()),lo:float(g.low.min())})
    return pd.DataFrame(rows).sort_values('avail_ts').set_index('avail_ts')


def cutoff(w):return w+pd.Timedelta(days=5,hours=12)
def week_key(t):return vm.b11.week_key(vm.b11.week_start(pd.Timestamp(t)))
def pool_family(level):return 'PD' if level.startswith('PD') else ('PW' if level.startswith('PW') else 'W1VA')
def in_research(t):
    t=pd.Timestamp(t)
    return (vm.b11.EXT0<=t<vm.b11.VAL1) or (vm.b11.AUG0<=t<vm.b11.AUG1)


def micro_flows(x15,signal_ts,level,is_upper):
    a=pd.Timestamp(signal_ts);z=a+pd.Timedelta(hours=1)
    q=x15[(x15.index>=a)&(x15.index<z)]
    if len(q)<4:return np.nan,np.nan
    breach=None
    for _,r in q.iterrows():
        if (is_upper and float(r.high)>level) or ((not is_upper) and float(r.low)<level):
            breach=r;break
    if breach is None:return np.nan,np.nan
    bf=flow(breach.quote_volume,breach.taker_buy_quote)
    last=q.iloc[-1];ff=flow(last.quote_volume,last.taker_buy_quote)
    return bf,ff


def structural_events(h1,x15,states):
    idx=h1.index;op=h1.open.to_numpy(float);hi=h1.high.to_numpy(float);lo=h1.low.to_numpy(float);cl=h1.close.to_numpy(float)
    hf=h1.hour_flow.to_numpy(float);f3=h1.flow3h.to_numpy(float);f6=h1.flow6h.to_numpy(float)
    exe=vm.execution(h1);rows=[]
    specs=[
      ('PDH',states['PD'],'UPPER'),('PDL',states['PD'],'LOWER'),
      ('PWH',states['PW'],'UPPER'),('PWL',states['PW'],'LOWER'),
      ('W1_VAH',states['W1'],'UPPER'),('W1_VAL',states['W1'],'LOWER')]
    for level_name,state,pos in specs:
        col={'W1_VAH':'VAH','W1_VAL':'VAL'}.get(level_name,level_name)
        lv=state[col].reindex(idx,method='ffill').to_numpy(float)
        inst=state['instance'].reindex(idx,method='ffill').to_numpy(object)
        valid=np.isfinite(lv)&np.array([x is not None and str(x)!='nan' for x in inst])
        seen=set()
        for i in range(len(idx)):
            if not valid[i] or not in_research(idx[i]):continue
            if idx[i]>cutoff(vm.b11.week_start(idx[i])):continue
            if pos=='UPPER':
                if not (op[i]<=lv[i] and hi[i]>lv[i]):continue
                if cl[i]<lv[i]:arch='REV';side='SHORT'
                elif cl[i]>lv[i]:arch='CONT';side='LONG'
                else:continue
                sweep_sign=1.0
            else:
                if not (op[i]>=lv[i] and lo[i]<lv[i]):continue
                if cl[i]>lv[i]:arch='REV';side='LONG'
                elif cl[i]<lv[i]:arch='CONT';side='SHORT'
                else:continue
                sweep_sign=-1.0
            key=(level_name,str(inst[i]),arch)
            if key in seen:continue
            seen.add(key)
            tr=exe(i,side)
            if tr is None:continue
            bf,ff=micro_flows(x15,idx[i],float(lv[i]),pos=='UPPER')
            ss=1.0 if side=='LONG' else -1.0
            base={'level_name':level_name,'pool_family':pool_family(level_name),'archetype':arch,'signal_i':i,'signal_ts':idx[i],
                  'week':week_key(idx[i]),'side':side,'level':float(lv[i]),'instance':str(inst[i]),
                  'hour_signed':ss*hf[i],'flow3_signed':ss*f3[i],'flow6_signed':ss*f6[i],
                  'breach_signed':sweep_sign*bf,'final15_signed':ss*ff,**tr}
            for v in VARIANTS:
                ok=(v=='RAW' or
                    (v=='H1_FLOW' and base['hour_signed']>0) or
                    (v=='FLOW3' and base['flow3_signed']>0) or
                    (v=='PERSIST' and base['hour_signed']>0 and base['flow3_signed']>0 and base['flow6_signed']>0) or
                    (v=='MICRO' and base['breach_signed']>0 and base['final15_signed']>0 and base['hour_signed']>0) or
                    (v=='MICRO_PERSIST' and base['breach_signed']>0 and base['final15_signed']>0 and base['hour_signed']>0 and base['flow3_signed']>0))
                if ok:
                    r=base.copy();r['variant']=v;r['rule']=f'{level_name}|{arch}|{v}';rows.append(r)
    q=pd.DataFrame(rows)
    if q.empty:raise RuntimeError('no B18 candidates')
    return q.sort_values(['signal_ts','rule']).reset_index(drop=True)


def route_rule(cand,rule,weeks):
    ws=vm.b11.week_set(weeks);q=cand[(cand.rule==rule)&cand.week.isin(ws)].sort_values('signal_ts')
    if q.empty:return q
    return q.groupby('week',as_index=False,sort=False).head(1).sort_values('signal_ts')


def rank_rules(cand,weeks):
    out=[]
    for rule in sorted(cand.rule.unique()):
        q=route_rule(cand,rule,weeks);s=vm.b11.stat(q,weeks)
        a=rule.split('|');out.append({'rule':rule,'level_name':a[0],'pool_family':pool_family(a[0]),'archetype':a[1],'variant':a[2],**s})
    r=pd.DataFrame(out);r['eligible']=(r.n>=20).astype(int);r['wr_sort']=r.wr.fillna(-1);r['pf_sort']=r.pf.fillna(-1)
    r=r.sort_values(['eligible','wilson','wr_sort','pf_sort','n','rule'],ascending=[False,False,False,False,False,True]).reset_index(drop=True);r['rank']=np.arange(1,len(r)+1)
    return r


def choose_primary(r):
    q=r[r.n>=20]
    return str((q.iloc[0] if len(q) else r.iloc[0]).rule)


def top4_rules(r):
    out=[];seen=set()
    for _,x in r.iterrows():
        if x.n<20:continue
        k=(x.pool_family,x.archetype)
        if k in seen:continue
        seen.add(k);out.append(str(x.rule))
        if len(out)>=4:break
    return out


def route_top(cand,rules,weeks):
    if not rules:return cand.iloc[:0].copy()
    ws=vm.b11.week_set(weeks);rank={r:i for i,r in enumerate(rules)}
    q=cand[cand.rule.isin(rules)&cand.week.isin(ws)].copy()
    if q.empty:return q
    q['rrank']=q.rule.map(rank)
    return q.sort_values(['signal_ts','rrank','rule']).groupby('week',as_index=False,sort=False).head(1).sort_values('signal_ts')


def atlas(cand):
    rows=[]
    for rule in sorted(cand.rule.unique()):
        for part in ('development','external','reference_validation','august'):
            weeks=vm.b11.partition_weeks(part);s=vm.b11.stat(route_rule(cand,rule,weeks),weeks)
            rows.append({'rule':rule,'partition':part,**s})
    return pd.DataFrame(rows)


def posblocks(bs):return sum(1 for b in bs if b.get('n',0)>0 and b.get('exp') is not None and b['exp']>0)
def gate_high(s,bs):return s['n']>=20 and s['wr'] is not None and s['wr']>=.70 and s['exp'] is not None and s['exp']>0 and s['pf'] is not None and s['pf']>1.5 and s['max_ls']<=2 and posblocks(bs)>=3
def gate100(s,weeks):return s['n']==len(weeks) and abs(s['coverage']-1)<1e-12 and s['sl']==0 and s['time']==0

def pct(v):return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{100*float(v):.2f}%'
def num(v):return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{float(v):.3f}'


def main():
    x15=b17.load_15m(b17.BASE_FUT,'klines','futures');print('15m',len(x15),x15.index.min(),x15.index.max(),flush=True)
    h1=build_h1(x15);print('H1',len(h1),flush=True)
    states={'PD':prev_period_state(x15,'D'),'PW':prev_period_state(x15,'W'),'W1':vmfast.build_level_state_fast(x15,'W1')}
    cand=structural_events(h1,x15,states);print('candidates',len(cand),flush=True)
    ranks=rank_rules(cand,vm.b11.partition_weeks('development'));primary=choose_primary(ranks);top4=top4_rules(ranks)
    ranks.to_csv(OUT_RULES,index=False);atlas(cand).to_csv(OUT_ATLAS,index=False)
    summary={};selected=[]
    for selector in ('PRIMARY','TOP4'):
        summary[selector]={}
        for part in ('development','external','reference_validation','august'):
            weeks=vm.b11.partition_weeks(part);q=route_rule(cand,primary,weeks) if selector=='PRIMARY' else route_top(cand,top4,weeks)
            s=vm.b11.stat(q,weeks);bs=vm.b11.block_stats(q,weeks);summary[selector][part]={'stat':s,'blocks':bs}
            if len(q):qq=q.copy();qq['selector']=selector;qq['partition']=part;selected.append(qq)
    if selected:pd.concat(selected,ignore_index=True).to_csv(OUT_SEL,index=False)
    ew=vm.b11.partition_weeks('external');vw=vm.b11.partition_weeks('reference_validation')
    high=False;rob=False;passing=[]
    for sel in ('PRIMARY','TOP4'):
        e=summary[sel]['external'];v=summary[sel]['reference_validation']
        if gate_high(e['stat'],e['blocks']) and gate_high(v['stat'],v['blocks']):high=True;passing.append(sel)
        if gate100(e['stat'],ew) and gate100(v['stat'],vw):rob=True
    result={'experiment':'B18_LIQUIDITY_SWEEP_FLOW','revision':REVISION,'primary_rule':primary,'top4_router':top4,
            'selectors':summary,'gates':{'B18_HIGH_PRECISION':'PASS' if high else 'FAIL','B18_ROBUST_WEEKLY_100':'PASS' if rob else 'FAIL','passing':passing},
            'data':{'m15_rows':len(x15),'h1_rows':len(h1),'first':str(h1.index.min()),'last':str(h1.index.max())},'live_bbc_untouched':True}
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    lines=['# BTC Weekly Liquidity Sweep + Order-Flow Resolution B18 — Result','',f"**Verdict: {'B18_HIGH_PRECISION_PASS' if high else 'B18_NO_HIGH_PRECISION_SWEEP_FLOW'}**",'',
           f"15m rows **{len(x15):,}**, H1 rows **{len(h1):,}**, {h1.index.min()} -> {h1.index.max()}.",'',f'Frozen development PRIMARY: **{primary}**','',f"Frozen TOP4: {', '.join(top4) if top4 else 'none'}",'',
           '| Selector | Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |','|---|---|---:|---:|---:|---:|---:|---:|']
    for sel in ('PRIMARY','TOP4'):
        for part in ('development','external','reference_validation','august'):
            s=summary[sel][part]['stat'];lines.append(f"| {sel} | {part} | {s['weeks']}/{s['n']}/{pct(s['coverage'])} | {s['tp']}/{s['sl']}/{s['time']} | {pct(s['wr'])} | {pct(s['exp'])} | {num(s['pf'])} | {s['max_ls']} |")
    lines += ['','## Development top rules','', '| Rank | Rule | N | Coverage | WR | Wilson LB | PF |','|---:|---|---:|---:|---:|---:|---:|']
    for _,x in ranks.head(18).iterrows():lines.append(f"| {int(x['rank'])} | `{x.rule}` | {int(x.n)} | {pct(x.coverage)} | {pct(x.wr)} | {pct(x.wilson)} | {num(x.pf)} |")
    lines += ['','## Gates','',f"- B18_HIGH_PRECISION: **{'PASS' if high else 'FAIL'}**",f"- B18_ROBUST_WEEKLY_100: **{'PASS' if rob else 'FAIL'}**",'',
              'No OOS retuning. No equal-high/low rescue. No flow-threshold sweep. Live BBC untouched.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('\n'.join(lines),flush=True)

if __name__=='__main__':main()
