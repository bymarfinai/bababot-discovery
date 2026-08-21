#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd

import btc_weekly_volume_memory_b13 as vm
import btc_weekly_volume_memory_b13_fast as vmfast
import btc_weekly_w1_vah_false_break_b17 as b17
import btc_weekly_liquidity_sweep_flow_b18 as b18

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_WEEKLY_AUCTION_QUALITY_B19_Result.md'
OUT_JSON=ROOT/'BTC_WEEKLY_AUCTION_QUALITY_B19_Result.json'
OUT_RULES=ROOT/'BTC_WEEKLY_AUCTION_QUALITY_B19_Rules.csv'
OUT_ATLAS=ROOT/'BTC_WEEKLY_AUCTION_QUALITY_B19_Atlas.csv'
OUT_SEL=ROOT/'BTC_WEEKLY_AUCTION_QUALITY_B19_Selected.csv'
OUT_BASE=ROOT/'BTC_WEEKLY_AUCTION_QUALITY_B19_Baseline.csv'
REVISION='B19_V1'

AQ_VARIANTS=[('AQ10_NIR1',0.10,1),('AQ25_NIR1',0.25,1),('AQ10_NIR2',0.10,2)]
SWEEP_LEVELS=['PDH','PDL','PWH','PWL']


def cutoff(w):return w+pd.Timedelta(days=5,hours=12)
def week_key(t):return vm.b11.week_key(vm.b11.week_start(pd.Timestamp(t)))
def in_research(t):
    x=pd.Timestamp(t)
    return ((vm.b11.EXT0<=x<vm.b11.EXT1) or (vm.b11.DEV0<=x<vm.b11.DEV1) or
            (vm.b11.VAL0<=x<vm.b11.VAL1) or (vm.b11.AUG0<=x<vm.b11.AUG1))


def signed_persist(h1,i,side):
    if i<5:return False
    ss=1.0 if side=='LONG' else -1.0
    vals=[float(h1.hour_flow.iloc[i]),float(h1.flow3h.iloc[i]),float(h1.flow6h.iloc[i])]
    return all(np.isfinite(v) and ss*v>0 for v in vals)


def build_w1_quality(h1,w1):
    idx=h1.index;op=h1.open.to_numpy(float);cl=h1.close.to_numpy(float);atr=h1.atr14.to_numpy(float)
    inst=w1['instance'].reindex(idx,method='ffill').to_numpy(object)
    vah=w1['VAH'].reindex(idx,method='ffill').to_numpy(float);val=w1['VAL'].reindex(idx,method='ffill').to_numpy(float)
    valid=np.isfinite(vah)&np.isfinite(val)&np.array([x is not None and str(x)!='nan' for x in inst])
    exe=vm.execution(h1);rows=[]
    for i in range(3,len(idx)-3):
        if not in_research(idx[i]) or not valid[i] or not np.isfinite(atr[i]) or atr[i]<=0:continue
        if idx[i]>cutoff(vm.b11.week_start(idx[i])):continue
        if not (op[i]<=vah[i] and cl[i]>vah[i]):continue
        prev=cl[i-3:i]
        if not (np.all(prev<=vah[i]) and int(np.sum(prev>=val[i]))>=2):continue
        disp=(cl[i]-vah[i])/atr[i]
        for name,min_disp,nir in AQ_VARIANTS:
            if disp<min_disp:continue
            ci=i+nir
            if ci>=len(idx) or idx[ci]>cutoff(vm.b11.week_start(idx[ci])):continue
            if any((not valid[j]) or inst[j]!=inst[i] or cl[j]<=vah[i] for j in range(i+1,ci+1)):continue
            tr=exe(ci,'LONG')
            if tr is None:continue
            base={'family':'W1_VAH','event':name,'signal_i':ci,'breakout_i':i,'breakout_ts':idx[i],'signal_ts':idx[ci],
                  'week':week_key(idx[ci]),'side':'LONG','level':float(vah[i]),'instance':str(inst[i]),
                  'displacement_atr':float(disp),'persist':signed_persist(h1,ci,'LONG'),**tr}
            for flowname,ok in [('RAW',True),('PERSIST',base['persist'])]:
                if ok:
                    r=base.copy();r['flow_variant']=flowname;r['rule']=f'W1_VAH|{name}|{flowname}';rows.append(r)
    return rows


def build_first_touch_sweeps(h1,states):
    idx=h1.index;op=h1.open.to_numpy(float);hi=h1.high.to_numpy(float);lo=h1.low.to_numpy(float);cl=h1.close.to_numpy(float);atr=h1.atr14.to_numpy(float)
    exe=vm.execution(h1);rows=[]
    specs=[('PDH',states['PD'],'UPPER'),('PDL',states['PD'],'LOWER'),('PWH',states['PW'],'UPPER'),('PWL',states['PW'],'LOWER')]
    for level_name,state,pos in specs:
        lv=state[level_name].reindex(idx,method='ffill').to_numpy(float)
        inst=state['instance'].reindex(idx,method='ffill').to_numpy(object)
        valid=np.isfinite(lv)&np.array([x is not None and str(x)!='nan' for x in inst])
        touched=set()
        for i in range(len(idx)-2):
            if not valid[i]:continue
            iid=str(inst[i])
            touch=(hi[i]>=lv[i]) if pos=='UPPER' else (lo[i]<=lv[i])
            if not touch:continue
            if iid in touched:continue
            touched.add(iid)  # first touch consumes the level even if it fails the sweep definition
            if not in_research(idx[i]) or idx[i]>cutoff(vm.b11.week_start(idx[i])):continue
            if not np.isfinite(atr[i]) or atr[i]<=0:continue
            if pos=='UPPER':
                if not (op[i]<=lv[i] and hi[i]>lv[i] and cl[i]<lv[i]):continue
                pen=(hi[i]-lv[i])/atr[i];side='SHORT';sweep_flow=float(h1.hour_flow.iloc[i]);sweep_aggr=sweep_flow>0
            else:
                if not (op[i]>=lv[i] and lo[i]<lv[i] and cl[i]>lv[i]):continue
                pen=(lv[i]-lo[i])/atr[i];side='LONG';sweep_flow=float(h1.hour_flow.iloc[i]);sweep_aggr=sweep_flow<0
            if not (0.10<=pen<=0.50):continue
            ci=i+1
            if not valid[ci] or inst[ci]!=inst[i] or idx[ci]>cutoff(vm.b11.week_start(idx[ci])):continue
            held=(cl[ci]<lv[i]) if side=='SHORT' else (cl[ci]>lv[i])
            if not held:continue
            confirm_flow=float(h1.hour_flow.iloc[ci]);takeover=(confirm_flow<0) if side=='SHORT' else (confirm_flow>0)
            tr=exe(ci,side)
            if tr is None:continue
            base={'family':level_name,'event':'FAILED_AUCTION','signal_i':ci,'sweep_i':i,'sweep_ts':idx[i],'signal_ts':idx[ci],
                  'week':week_key(idx[ci]),'side':side,'level':float(lv[i]),'instance':iid,'penetration_atr':float(pen),
                  'sweep_aggression':bool(sweep_aggr),'takeover':bool(takeover),**tr}
            for flowname,ok in [('RAW',True),('FLOW',bool(sweep_aggr and takeover))]:
                if ok:
                    r=base.copy();r['flow_variant']=flowname;r['rule']=f'{level_name}|FAILED_AUCTION|{flowname}';rows.append(r)
    return rows


def build_candidates(h1,states):
    rows=build_w1_quality(h1,states['W1'])+build_first_touch_sweeps(h1,states)
    q=pd.DataFrame(rows)
    if q.empty:raise RuntimeError('no B19 candidates')
    return q.sort_values(['signal_ts','rule']).reset_index(drop=True)


def route_rule(cand,rule,weeks):
    ws=vm.b11.week_set(weeks);q=cand[(cand.rule==rule)&cand.week.isin(ws)].sort_values('signal_ts')
    if q.empty:return q
    return q.groupby('week',as_index=False,sort=False).head(1).sort_values('signal_ts')


def rank_rules(cand,weeks):
    rows=[]
    for rule in sorted(cand.rule.unique()):
        q=route_rule(cand,rule,weeks);s=vm.b11.stat(q,weeks)
        rows.append({'rule':rule,**s})
    r=pd.DataFrame(rows);r['eligible']=(r.n>=20).astype(int);r['wr_sort']=r.wr.fillna(-1);r['pf_sort']=r.pf.fillna(-1)
    r=r.sort_values(['eligible','wilson','wr_sort','pf_sort','n','rule'],ascending=[False,False,False,False,False,True]).reset_index(drop=True);r['rank']=np.arange(1,len(r)+1)
    return r


def atlas(cand):
    rows=[]
    for rule in sorted(cand.rule.unique()):
        for part in ('development','external','reference_validation','august'):
            weeks=vm.b11.partition_weeks(part);rows.append({'rule':rule,'partition':part,**vm.b11.stat(route_rule(cand,rule,weeks),weeks)})
    return pd.DataFrame(rows)


def gate(s):return s['n']>=15 and s['wr'] is not None and s['wr']>=.65 and s['exp'] is not None and s['exp']>0 and s['pf'] is not None and s['pf']>=1.30
def pct(v):return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{100*float(v):.2f}%'
def num(v):return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{float(v):.3f}'


def main():
    x15=b17.load_15m(b17.BASE_FUT,'klines','futures');print('15m',len(x15),x15.index.min(),x15.index.max(),flush=True)
    h1=b18.build_h1(x15);print('H1',len(h1),flush=True)
    states={'PD':b18.prev_period_state(x15,'D'),'PW':b18.prev_period_state(x15,'W'),'W1':vmfast.build_level_state_fast(x15,'W1')}

    # Exact B15/B18 direct-break baseline sanity before evaluating B19 quality rules.
    baseline=b17.build_baseline(h1,states['W1']);baseline['partition']=baseline.week_start.map(b17.partition_for_week)
    sanity=b17.sanity_baseline(baseline)
    base_rows=[]
    for part in ('development','external','reference_validation','august'):
        weeks=vm.b11.partition_weeks(part);q=baseline[baseline.partition==part];base_rows.append({'partition':part,**vm.b11.stat(q,weeks)})
    pd.DataFrame(base_rows).to_csv(OUT_BASE,index=False)

    cand=build_candidates(h1,states);print('B19 candidates',len(cand),flush=True)
    ranks=rank_rules(cand,vm.b11.partition_weeks('development'));primary=str(ranks.iloc[0].rule)
    ranks.to_csv(OUT_RULES,index=False);a=atlas(cand);a.to_csv(OUT_ATLAS,index=False)

    summary={};selected=[]
    for part in ('development','external','reference_validation','august'):
        weeks=vm.b11.partition_weeks(part);q=route_rule(cand,primary,weeks);s=vm.b11.stat(q,weeks);bs=vm.b11.block_stats(q,weeks)
        summary[part]={'stat':s,'blocks':bs}
        if len(q):qq=q.copy();qq['partition']=part;selected.append(qq)
    if selected:pd.concat(selected,ignore_index=True).to_csv(OUT_SEL,index=False)

    high=gate(summary['external']['stat']) and gate(summary['reference_validation']['stat'])
    robust=(summary['external']['stat']['n']>0 and summary['external']['stat']['sl']==0 and summary['external']['stat']['time']==0 and
            summary['reference_validation']['stat']['n']>0 and summary['reference_validation']['stat']['sl']==0 and summary['reference_validation']['stat']['time']==0)

    descriptive_passers=[]
    for rule in sorted(cand.rule.unique()):
        e=vm.b11.stat(route_rule(cand,rule,vm.b11.partition_weeks('external')),vm.b11.partition_weeks('external'))
        v=vm.b11.stat(route_rule(cand,rule,vm.b11.partition_weeks('reference_validation')),vm.b11.partition_weeks('reference_validation'))
        if gate(e) and gate(v):descriptive_passers.append(rule)

    result={'experiment':'B19_AUCTION_QUALITY','revision':REVISION,'baseline_sanity':sanity,'primary_rule':primary,'primary_summary':summary,
            'gates':{'B19_HIGH_QUALITY_PRIMARY':'PASS' if high else 'FAIL','B19_ROBUST_100_DIAGNOSTIC':'PASS' if robust else 'FAIL'},
            'atomic_oos_passers_descriptive_not_promoted':descriptive_passers,
            'data':{'m15_rows':len(x15),'h1_rows':len(h1),'first':str(h1.index.min()),'last':str(h1.index.max())},'live_bbc_untouched':True}
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')

    lines=['# BTC Weekly Auction-Quality Breakout / Sweep B19 — Result','',f"**Verdict: {'B19_HIGH_QUALITY_PRIMARY_PASS' if high else 'B19_NO_ROBUST_AUCTION_QUALITY'}**",'',
           f"Baseline sanity reproduced exactly: **{sanity}**.",f"15m rows **{len(x15):,}**, H1 rows **{len(h1):,}**, {h1.index.min()} -> {h1.index.max()}.",'',
           f'Frozen development PRIMARY: **{primary}**','',
           '| Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |','|---|---:|---:|---:|---:|---:|---:|']
    for part in ('development','external','reference_validation','august'):
        s=summary[part]['stat'];lines.append(f"| {part} | {s['weeks']}/{s['n']}/{pct(s['coverage'])} | {s['tp']}/{s['sl']}/{s['time']} | {pct(s['wr'])} | {pct(s['exp'])} | {num(s['pf'])} | {s['max_ls']} |")
    lines += ['','## Development ranking','', '| Rank | Rule | N | Coverage | WR | Wilson LB | PF |','|---:|---|---:|---:|---:|---:|---:|']
    for _,x in ranks.iterrows():lines.append(f"| {int(x['rank'])} | `{x.rule}` | {int(x.n)} | {pct(x.coverage)} | {pct(x.wr)} | {pct(x.wilson)} | {num(x.pf)} |")
    lines += ['','## Atomic OOS passers (descriptive only; not promotable unless selected on development)','',(', '.join(f'`{x}`' for x in descriptive_passers) if descriptive_passers else 'none'),'',
              '## Gates','',f"- B19_HIGH_QUALITY_PRIMARY: **{'PASS' if high else 'FAIL'}**",f"- B19_ROBUST_100_DIAGNOSTIC: **{'PASS' if robust else 'FAIL'}**",'',
              'No OOS retuning. No equal-high/low rescue. No regime filter. No threshold sweep. Live BBC untouched.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('\n'.join(lines),flush=True)

if __name__=='__main__':main()
