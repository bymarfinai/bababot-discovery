#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd

import btc_weekly_volume_memory_b13 as vm
import btc_weekly_volume_memory_b13_fast as vmfast

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_WEEKLY_W1_VAH_RETEST_B16_Result.md'
OUT_JSON = ROOT / 'BTC_WEEKLY_W1_VAH_RETEST_B16_Result.json'
OUT_RULES = ROOT / 'BTC_WEEKLY_W1_VAH_RETEST_B16_Rules.csv'
OUT_SEL = ROOT / 'BTC_WEEKLY_W1_VAH_RETEST_B16_Selected.csv'
OUT_BASE = ROOT / 'BTC_WEEKLY_W1_VAH_RETEST_B16_Baseline.csv'
REVISION = 'B16_V1'

VARIANTS = [
    ('A1_HOLD', 1, False),
    ('A1_BODY', 1, True),
    ('A2_HOLD', 2, False),
    ('A2_BODY', 2, True),
]


def scan_cutoff(w):
    return w + pd.Timedelta(days=5, hours=12)


def week_key(ts):
    return vm.b11.week_key(vm.b11.week_start(pd.Timestamp(ts)))


def build_sequences(h1: pd.DataFrame, state: pd.DataFrame) -> pd.DataFrame:
    idx=h1.index
    op=h1.open.to_numpy(float); hi=h1.high.to_numpy(float); lo=h1.low.to_numpy(float); cl=h1.close.to_numpy(float)
    inst=state['instance'].reindex(idx,method='ffill').to_numpy(object)
    vah=state['VAH'].reindex(idx,method='ffill').to_numpy(float)
    valid=np.array([x is not None and str(x)!='nan' for x in inst],dtype=bool) & np.isfinite(vah)
    exe=vm.execution(h1)
    rows=[]

    # Iterate complete research weeks using B11 partition union; this also keeps logic causal and deterministic.
    all_weeks=[]
    for part in ('external','development','reference_validation','august'):
        all_weeks.extend(vm.b11.partition_weeks(part))
    all_weeks=sorted(set(all_weeks))

    for w in all_weeks:
        a=int(idx.searchsorted(w,'left')); z=int(idx.searchsorted(scan_cutoff(w),'right'))
        if a>=z: continue
        # First literal W1 VAH breakout in the week.
        bidx=None
        for i in range(a,z):
            if not valid[i]: continue
            if op[i] <= vah[i] and cl[i] > vah[i]:
                bidx=i; break
        if bidx is None: continue
        base_inst=inst[bidx]; base_vah=float(vah[bidx])

        for name,naccept,need_body in VARIANTS:
            consec=0; accept_i=None; invalid=False
            j=bidx+1
            while j<z:
                if not valid[j] or inst[j] != base_inst:
                    invalid=True; break
                if cl[j] < base_vah:
                    invalid=True; break
                if cl[j] > base_vah:
                    consec += 1
                else:
                    consec = 0
                if consec >= naccept:
                    accept_i=j; break
                j += 1
            if invalid or accept_i is None:
                continue

            # First retest only after acceptance. Failed first retest cannot be rescued.
            retest_i=None; retest_valid=False
            j=accept_i+1
            while j<z:
                if not valid[j] or inst[j] != base_inst:
                    break
                if lo[j] <= base_vah:
                    retest_i=j
                    retest_valid = (cl[j] >= base_vah) and ((cl[j] > op[j]) if need_body else True)
                    break
                j += 1
            if retest_i is None or not retest_valid:
                continue

            tr=exe(int(retest_i),'LONG')
            if tr is None: continue
            rows.append({
                'rule':name,'week':week_key(idx[retest_i]),'week_start':w,
                'breakout_ts':idx[bidx],'accept_ts':idx[accept_i],'signal_ts':idx[retest_i],
                'signal_i':int(retest_i),'side':'LONG','level':base_vah,
                'instance':str(base_inst),'accept_closes':naccept,'body_required':need_body,
                **tr
            })
    q=pd.DataFrame(rows)
    if q.empty: raise RuntimeError('no B16 acceptance-retest candidates')
    return q.sort_values(['signal_ts','rule']).reset_index(drop=True)


def build_direct_baseline(h1: pd.DataFrame, state: pd.DataFrame) -> pd.DataFrame:
    idx=h1.index; op=h1.open.to_numpy(float); cl=h1.close.to_numpy(float)
    inst=state['instance'].reindex(idx,method='ffill').to_numpy(object)
    vah=state['VAH'].reindex(idx,method='ffill').to_numpy(float)
    valid=np.array([x is not None and str(x)!='nan' for x in inst],dtype=bool) & np.isfinite(vah)
    exe=vm.execution(h1); rows=[]
    all_weeks=[]
    for part in ('external','development','reference_validation','august'):
        all_weeks.extend(vm.b11.partition_weeks(part))
    for w in sorted(set(all_weeks)):
        a=int(idx.searchsorted(w,'left'));z=int(idx.searchsorted(scan_cutoff(w),'right'))
        for i in range(a,z):
            if valid[i] and op[i] <= vah[i] and cl[i] > vah[i]:
                tr=exe(int(i),'LONG')
                if tr is not None:
                    rows.append({'rule':'B15_W1_VAH_BREAK_LONG','week':week_key(idx[i]),'signal_ts':idx[i],**tr})
                break
    return pd.DataFrame(rows)


def route_rule(cand,rule,weeks):
    ws=vm.b11.week_set(weeks)
    q=cand[(cand.rule==rule)&cand.week.isin(ws)].sort_values('signal_ts')
    if q.empty:return q
    return q.groupby('week',as_index=False,sort=False).head(1).sort_values('signal_ts')


def rank_rules(cand,weeks):
    rows=[]
    for rule in [v[0] for v in VARIANTS]:
        q=route_rule(cand,rule,weeks);s=vm.b11.stat(q,weeks)
        rows.append({'rule':rule,**s})
    r=pd.DataFrame(rows)
    r['wr_sort']=r.wr.fillna(-1);r['pf_sort']=r.pf.fillna(-1)
    r=r.sort_values(['coverage','wr_sort','wilson','pf_sort','rule'],ascending=[False,False,False,False,True]).reset_index(drop=True)
    r['rank']=np.arange(1,len(r)+1)
    return r


def gate(s,bs,wrmin,require_full=False):
    if require_full and abs(s['coverage']-1)>1e-12:return False
    return (s['wr'] is not None and s['wr']>=wrmin and s['exp'] is not None and s['exp']>0 and
            s['pf'] is not None and s['pf']>1 and (s['max_ls']==0 if wrmin>=1 else s['max_ls']<=2) and
            sum(1 for b in bs if b['exp'] is not None and b['exp']>0)>=(4 if wrmin>=1 else 3))

def pct(v):return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{100*float(v):.2f}%'
def num(v):return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{float(v):.3f}'


def main():
    x15=vm.load_15m();print('15m',len(x15),x15.index.min(),x15.index.max(),flush=True)
    h1=vm.build_h1(x15);print('H1',len(h1),flush=True)
    w1=vmfast.build_level_state_fast(x15,'W1');print('W1 states',len(w1),flush=True)
    cand=build_sequences(h1,w1)
    baseline=build_direct_baseline(h1,w1)
    cand=cand[cand.signal_ts>=vm.b11.EXT0].copy()
    baseline=baseline[baseline.signal_ts>=vm.b11.EXT0].copy()

    dw=vm.b11.partition_weeks('development');ranks=rank_rules(cand,dw);primary=str(ranks.iloc[0].rule)
    ranks.to_csv(OUT_RULES,index=False)

    summary={};sels=[];base_summary={}
    for part in ('development','external','reference_validation','august'):
        weeks=vm.b11.partition_weeks(part)
        q=route_rule(cand,primary,weeks);s=vm.b11.stat(q,weeks);bs=vm.b11.block_stats(q,weeks)
        summary[part]={'stat':s,'blocks':bs}
        if len(q):
            qq=q.copy();qq['partition']=part;qq['selector']='PRIMARY_RULE';sels.append(qq)
        b=baseline[baseline.week.isin(vm.b11.week_set(weeks))].sort_values('signal_ts')
        if len(b):b=b.groupby('week',as_index=False,sort=False).head(1)
        base_summary[part]=vm.b11.stat(b,weeks)
    if sels:pd.concat(sels,ignore_index=True).to_csv(OUT_SEL,index=False)
    pd.DataFrame([{'partition':p,**s} for p,s in base_summary.items()]).to_csv(OUT_BASE,index=False)

    e=summary['external'];v=summary['reference_validation']
    robust=gate(e['stat'],e['blocks'],1.0,True) and gate(v['stat'],v['blocks'],1.0,True)
    highp=gate(e['stat'],e['blocks'],.8,False) and gate(v['stat'],v['blocks'],.8,False)

    result={
        'experiment':'B16_W1_VAH_ACCEPTANCE_RETEST','revision':REVISION,
        'coverage':{'first':str(h1.index.min()),'last':str(h1.index.max()),'h1_rows':len(h1),'m15_rows':len(x15)},
        'primary_rule':primary,'development_rules':ranks.replace({np.nan:None}).to_dict('records'),
        'primary_summary':summary,'b15_direct_baseline':base_summary,
        'gates':{'B16_ROBUST_WEEKLY_100':'PASS' if robust else 'FAIL','B16_HIGH_PRECISION':'PASS' if highp else 'FAIL'},
        'live_bbc_untouched':True
    }
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')

    lines=['# BTC Weekly W1 VAH Acceptance-Retest B16 — Result','',
           f"**Verdict: {'B16_ROBUST_WEEKLY_100_PASS' if robust else 'B16_NO_ROBUST_WEEKLY_100'}**",'',
           f"15m rows **{len(x15):,}**, H1 rows **{len(h1):,}**, {h1.index.min()} -> {h1.index.max()}.",'',
           'Frozen sequence: **W1 VAH breakout -> additional acceptance close(s) above -> first retest -> hold -> LONG next H1 open.**','',
           f'Frozen development PRIMARY_RULE: **{primary}**','',
           '## Primary rule','',
           '| Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |','|---|---:|---:|---:|---:|---:|---:|']
    for part in ('development','external','reference_validation','august'):
        s=summary[part]['stat'];lines.append(f"| {part} | {s['weeks']}/{s['n']}/{pct(s['coverage'])} | {s['tp']}/{s['sl']}/{s['time']} | {pct(s['wr'])} | {pct(s['exp'])} | {num(s['pf'])} | {s['max_ls']} |")
    lines += ['','## B15 direct W1 VAH breakout baseline','',
              '| Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF |','|---|---:|---:|---:|---:|---:|']
    for part in ('development','external','reference_validation','august'):
        s=base_summary[part];lines.append(f"| {part} | {s['weeks']}/{s['n']}/{pct(s['coverage'])} | {s['tp']}/{s['sl']}/{s['time']} | {pct(s['wr'])} | {pct(s['exp'])} | {num(s['pf'])} |")
    lines += ['','## Development ranking','',
              '| Rank | Rule | Coverage | WR | Wilson LB | PF | N |','|---:|---|---:|---:|---:|---:|---:|']
    for _,x in ranks.iterrows():lines.append(f"| {int(x['rank'])} | `{x.rule}` | {pct(x.coverage)} | {pct(x.wr)} | {pct(x.wilson)} | {num(x.pf)} | {int(x.n)} |")
    lines += ['','## Gates','',f"- B16_ROBUST_WEEKLY_100: **{'PASS' if robust else 'FAIL'}**",f"- B16_HIGH_PRECISION: **{'PASS' if highp else 'FAIL'}**",'', 'No OOS retuning. Live BBC untouched.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)

if __name__=='__main__':main()
