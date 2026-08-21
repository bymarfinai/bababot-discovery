#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd

import btc_weekly_volume_memory_b13 as vm
import btc_weekly_volume_memory_b13_fast as vmfast

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_WEEKLY_VALUE_AREA_BREAKOUT_B15_Result.md'
OUT_JSON = ROOT / 'BTC_WEEKLY_VALUE_AREA_BREAKOUT_B15_Result.json'
OUT_RULES = ROOT / 'BTC_WEEKLY_VALUE_AREA_BREAKOUT_B15_Rules.csv'
OUT_SEL = ROOT / 'BTC_WEEKLY_VALUE_AREA_BREAKOUT_B15_Selected.csv'
OUT_ATLAS = ROOT / 'BTC_WEEKLY_VALUE_AREA_BREAKOUT_B15_Atlas.csv'
REVISION = 'B15_V1'

TFS = ['H1','H4','D1','W1']
BOUNDARIES = [('VAH','LONG'),('VAL','SHORT')]


def build_candidates(h1: pd.DataFrame, states: dict[str,pd.DataFrame]) -> pd.DataFrame:
    idx = h1.index
    op = h1.open.to_numpy(float)
    cl = h1.close.to_numpy(float)
    exe = vm.execution(h1)
    rows=[]
    for tf,state in states.items():
        print('breakout scan',tf,flush=True)
        inst=state['instance'].reindex(idx,method='ffill').to_numpy(object)
        valid=np.array([x is not None and str(x)!='nan' for x in inst],dtype=bool)
        for boundary,side in BOUNDARIES:
            lv=state[boundary].reindex(idx,method='ffill').to_numpy(float)
            if side=='LONG':
                mask=valid & np.isfinite(lv) & (op <= lv) & (cl > lv)
                kind='VAH_BREAK_LONG'
            else:
                mask=valid & np.isfinite(lv) & (op >= lv) & (cl < lv)
                kind='VAL_BREAK_SHORT'
            inds=np.flatnonzero(mask)
            if not len(inds):
                continue
            # First qualifying breakout for each active source-period level instance and side.
            qi=inst[inds]
            keep=np.r_[True,qi[1:]!=qi[:-1]]
            first_inds=inds[keep]
            rule=f'{tf}|{kind}'
            for i in first_inds:
                tr=exe(int(i),side)
                if tr is None:
                    continue
                rows.append({
                    'rule':rule,'source_tf':tf,'boundary':boundary,'setup':kind,
                    'signal_i':int(i),'signal_ts':idx[i],'side':side,'level':float(lv[i]),
                    'instance':f'{tf}|{boundary}|{inst[i]}|{side}',
                    'week':vm.b11.week_key(vm.b11.week_start(idx[i])),**tr
                })
        print('candidates so far',len(rows),flush=True)
    q=pd.DataFrame(rows)
    if q.empty:
        raise RuntimeError('no B15 candidates')
    return q.sort_values(['signal_ts','rule']).reset_index(drop=True)


def scan_ok(ts):
    t=pd.Timestamp(ts)
    return t <= vm.b11.week_start(t)+pd.Timedelta(days=5,hours=12)


def route_rule(cand,rule,weeks):
    ws=vm.b11.week_set(weeks)
    q=cand[(cand.rule==rule)&cand.week.isin(ws)&cand.signal_ts.map(scan_ok)].sort_values('signal_ts')
    if q.empty:return q
    q=q.groupby('week',as_index=False,sort=False).head(1).copy()
    q['route']='PRIMARY_RULE'
    return q.sort_values('signal_ts')


def rank_rules(cand,weeks):
    rows=[]
    for rule in sorted(cand.rule.unique()):
        q=route_rule(cand,rule,weeks)
        s=vm.b11.stat(q,weeks)
        tf,setup=rule.split('|',1)
        boundary='VAH' if setup.startswith('VAH') else 'VAL'
        rows.append({'rule':rule,'source_tf':tf,'boundary':boundary,'setup':setup,**s})
    r=pd.DataFrame(rows)
    r['fullcov']=(r.coverage>=1-1e-12).astype(int)
    r['wr_sort']=r.wr.fillna(-1)
    r['pf_sort']=r.pf.fillna(-1)
    r=r.sort_values(['fullcov','wr_sort','wilson','pf_sort','n','rule'],ascending=[False,False,False,False,False,True]).reset_index(drop=True)
    r['rank']=np.arange(1,len(r)+1)
    return r


def top4(r):
    out=[];seen=set()
    for _,x in r.iterrows():
        k=(x.source_tf,x.boundary)
        if k in seen:continue
        seen.add(k);out.append(str(x.rule))
        if len(out)==4:break
    return out


def route_top4(cand,rules,weeks):
    ws=vm.b11.week_set(weeks);rank={r:i for i,r in enumerate(rules)}
    q=cand[cand.rule.isin(rules)&cand.week.isin(ws)&cand.signal_ts.map(scan_ok)].copy()
    if q.empty:return q
    q['rrank']=q.rule.map(rank)
    q=q.sort_values(['signal_ts','rrank','rule']).groupby('week',as_index=False,sort=False).head(1).copy()
    q['route']='TOP4_ROUTER'
    return q.sort_values('signal_ts')


def atlas(cand):
    rows=[];q=cand[cand.signal_ts.map(scan_ok)]
    for rule,g in q.groupby('rule'):
        for part in ('development','external','reference_validation','august'):
            weeks=vm.b11.partition_weeks(part);ws=vm.b11.week_set(weeks)
            x=g[g.week.isin(ws)].sort_values('signal_ts')
            routed=x.groupby('week',as_index=False,sort=False).head(1) if len(x) else x
            s=vm.b11.stat(routed,weeks)
            rows.append({'rule':rule,'partition':part,'candidate_n':len(x),'coverage':s['coverage'],'weekly_wr':s['wr'],'pf':s['pf'],'exp':s['exp'],'n':s['n']})
    return pd.DataFrame(rows)


def gate(s,bs,weeks,wrmin):
    return (s['n']==len(weeks) and abs(s['coverage']-1)<1e-12 and s['wr'] is not None and s['wr']>=wrmin and s['exp'] is not None and s['exp']>0 and s['pf'] is not None and s['pf']>1 and (s['max_ls']==0 if wrmin>=1 else s['max_ls']<=2) and sum(1 for b in bs if b['exp'] is not None and b['exp']>0)>=(4 if wrmin>=1 else 3))

def pct(v):return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{100*float(v):.2f}%'
def num(v):return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{float(v):.3f}'


def main():
    x15=vm.load_15m();print('15m',len(x15),x15.index.min(),x15.index.max(),flush=True)
    h1=vm.build_h1(x15);print('H1',len(h1),flush=True)
    states={tf:vmfast.build_level_state_fast(x15,tf) for tf in TFS}
    for tf,s in states.items():print('state',tf,len(s),flush=True)
    cand=build_candidates(h1,states)
    cand=cand[cand.signal_ts>=vm.b11.EXT0].copy()

    dw=vm.b11.partition_weeks('development')
    ranks=rank_rules(cand,dw)
    primary=str(ranks.iloc[0].rule)
    t4=top4(ranks)
    ranks.to_csv(OUT_RULES,index=False)
    aa=atlas(cand);aa.to_csv(OUT_ATLAS,index=False)

    summary={};sels=[]
    for selector in ('PRIMARY_RULE','TOP4_ROUTER'):
        summary[selector]={}
        for part in ('development','external','reference_validation','august'):
            weeks=vm.b11.partition_weeks(part)
            q=route_rule(cand,primary,weeks) if selector=='PRIMARY_RULE' else route_top4(cand,t4,weeks)
            s=vm.b11.stat(q,weeks);bs=vm.b11.block_stats(q,weeks)
            if len(q):
                qq=q.copy();qq['selector']=selector;qq['partition']=part;sels.append(qq)
            summary[selector][part]={'stat':s,'blocks':bs}
    if sels:pd.concat(sels,ignore_index=True).to_csv(OUT_SEL,index=False)

    ew=vm.b11.partition_weeks('external');vw=vm.b11.partition_weeks('reference_validation')
    robust=False;highp=False;passing=None
    for sel in ('PRIMARY_RULE','TOP4_ROUTER'):
        e=summary[sel]['external'];v=summary[sel]['reference_validation']
        if gate(e['stat'],e['blocks'],ew,1.0) and gate(v['stat'],v['blocks'],vw,1.0):robust=True;passing=sel
        if gate(e['stat'],e['blocks'],ew,.8) and gate(v['stat'],v['blocks'],vw,.8):highp=True

    result={
        'experiment':'B15_VALUE_AREA_BREAKOUT','revision':REVISION,
        'coverage':{'first':str(h1.index.min()),'last':str(h1.index.max()),'h1_rows':len(h1),'m15_rows':len(x15)},
        'primary_rule':primary,'top4_router':t4,
        'development_rules':ranks.replace({np.nan:None}).to_dict('records'),
        'selectors':summary,
        'gates':{'B15_ROBUST_WEEKLY_100':'PASS' if robust else 'FAIL','B15_HIGH_PRECISION_WEEKLY':'PASS' if highp else 'FAIL','passing_selector':passing},
        'live_bbc_untouched':True
    }
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')

    lines=['# BTC Weekly Value-Area Breakout B15 — Result','',f"**Verdict: {'B15_ROBUST_WEEKLY_100_PASS' if robust else 'B15_NO_ROBUST_WEEKLY_100'}**",'',
           f"15m rows **{len(x15):,}**, H1 execution rows **{len(h1):,}**, {h1.index.min()} -> {h1.index.max()}.",'',
           'Frozen setup: **VAH break -> LONG; VAL break -> SHORT; entry next H1 open.**','',
           f'Frozen development PRIMARY_RULE: **{primary}**','', 'Frozen TOP4_ROUTER:']+[f'- {i+1}. `{x}`' for i,x in enumerate(t4)]+['',
           '| Selector | Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |','|---|---|---:|---:|---:|---:|---:|---:|']
    for sel in ('PRIMARY_RULE','TOP4_ROUTER'):
        for part in ('development','external','reference_validation','august'):
            s=summary[sel][part]['stat']
            lines.append(f"| {sel} | {part} | {s['weeks']}/{s['n']}/{pct(s['coverage'])} | {s['tp']}/{s['sl']}/{s['time']} | {pct(s['wr'])} | {pct(s['exp'])} | {num(s['pf'])} | {s['max_ls']} |")
    lines += ['','## All atomic rules — development ranking','', '| Rank | Rule | Coverage | WR | PF | N |','|---:|---|---:|---:|---:|---:|']
    for _,x in ranks.iterrows():
        lines.append(f"| {int(x['rank'])} | `{x.rule}` | {pct(x.coverage)} | {pct(x.wr)} | {num(x.pf)} | {int(x.n)} |")
    lines += ['','## Gates','',f"- B15_ROBUST_WEEKLY_100: **{'PASS' if robust else 'FAIL'}**",f"- B15_HIGH_PRECISION_WEEKLY: **{'PASS' if highp else 'FAIL'}**",'', 'No OOS retuning. Live BBC untouched.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)

if __name__=='__main__':
    main()
