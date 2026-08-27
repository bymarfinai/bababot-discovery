#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
spec=importlib.util.spec_from_file_location('m8base',HERE/'eth_f85_f15_transfer_m8_economic_combination.py')
b=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(b)

LOCKED=b.LOCKED
STOPS=b.STOP_CANDIDATES
MECHS=('H2_FULL_EXIT','H2_HALF_M7_HALF','BE_AFTER_H2_M7','H_CLOSE_FAILURE_M7')
PFX='ETH_M8C_EXIT_MECHANISM'
DETAIL=ROOT/f'{PFX}_Detail.csv'; SUMMARY=ROOT/f'{PFX}_Summary.csv'; SELECTION=ROOT/f'{PFX}_Selection.csv'; RESULT=ROOT/f'{PFX}_Result.md'; STATUS=ROOT/f'{PFX}_Status.txt'


def next_open(x,ts):
    i=int(x.index.searchsorted(ts,side='left'))
    if i>=len(x): return None
    return x.index[i],float(x.iloc[i].open)


def leg_pnl(exit_px, entry_px, notional, fee):
    return (float(exit_px)/float(entry_px)-1.0)*float(notional)-float(fee)


def pre_h2_state(x,r,mode,dist,sf):
    entry_ts=pd.Timestamp(r.entry_ts); end=pd.Timestamp(r.session_end)
    H,L,R=float(r.H),float(r.L),float(r.R); entry=float(r.entry_px)
    boundary=L+float(sf)*R
    h2=pd.Timestamp(r.h2_ts) if pd.notna(r.h2_ts) else pd.NaT
    q=x.iloc[int(x.index.searchsorted(entry_ts)):int(x.index.searchsorted(end))]
    if q.empty or q.index[0]!=entry_ts: raise AssertionError('missing entry bar')
    assert L<boundary<entry<H
    for ts,bar in q.iterrows():
        low,close=float(bar.low),float(bar.close)
        is_h2=pd.notna(h2) and ts==h2
        after_h2=pd.notna(h2) and ts>h2
        if mode=='HARD_TOUCH':
            if not after_h2 and low<=boundary:
                return {'terminated':True,'exit_ts':ts,'exit_px':boundary,'exit_reason':'PRE_H2_HARD_STOP','h2_reached':False,'boundary':boundary}
        else:
            if not after_h2 and not is_h2 and close<boundary:
                nxt=ts+b.BAR5
                if nxt<=end:
                    op=next_open(x,nxt)
                    if op is not None and op[0]==nxt:
                        return {'terminated':True,'exit_ts':op[0],'exit_px':op[1],'exit_reason':'PRE_H2_CLOSE_INVALIDATION','h2_reached':False,'boundary':boundary}
        if is_h2:
            return {'terminated':False,'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'','h2_reached':True,'boundary':boundary}
    op=next_open(x,end)
    if op is None: raise AssertionError('missing session end open')
    return {'terminated':True,'exit_ts':op[0],'exit_px':op[1],'exit_reason':'NO_H2_TIME_EXIT','h2_reached':False,'boundary':boundary}


def post_h2(x,r,mechanism):
    entry_ts=pd.Timestamp(r.entry_ts); h2=pd.Timestamp(r.h2_ts); end=pd.Timestamp(r.session_end)
    H=float(r.H); entry=float(r.entry_px); target=float(r.target_px)
    q=x.iloc[int(x.index.searchsorted(h2)):int(x.index.searchsorted(end))]
    if q.empty or q.index[0]!=h2: raise AssertionError('missing h2 bar')

    if mechanism=='H2_FULL_EXIT':
        net=leg_pnl(H,entry,b.NOTIONAL,b.FEE)
        return {'exit_ts':h2,'exit_px_equiv':H,'exit_reason':'H2_FULL_EXIT','net_pnl_usd':net,'hold_minutes':float((h2-entry_ts)/pd.Timedelta(minutes=1))}

    if mechanism=='H2_HALF_M7_HALF':
        first=leg_pnl(H,entry,b.NOTIONAL/2,b.FEE/2)
        for ts,bar in q.iterrows():
            if float(bar.high)>=target:
                second=leg_pnl(target,entry,b.NOTIONAL/2,b.FEE/2)
                net=first+second
                return {'exit_ts':ts,'exit_px_equiv':(H+target)/2,'exit_reason':'H2_HALF_M7_HALF_TP','net_pnl_usd':net,'hold_minutes':float((ts-entry_ts)/pd.Timedelta(minutes=1))}
        op=next_open(x,end); assert op is not None
        second=leg_pnl(op[1],entry,b.NOTIONAL/2,b.FEE/2); net=first+second
        return {'exit_ts':op[0],'exit_px_equiv':(H+op[1])/2,'exit_reason':'H2_HALF_M7_HALF_TIME','net_pnl_usd':net,'hold_minutes':float((op[0]-entry_ts)/pd.Timedelta(minutes=1))}

    if mechanism=='BE_AFTER_H2_M7':
        for ts,bar in q.iterrows():
            if ts==h2:
                if float(bar.high)>=target:
                    net=leg_pnl(target,entry,b.NOTIONAL,b.FEE)
                    return {'exit_ts':ts,'exit_px_equiv':target,'exit_reason':'M7_TARGET_ON_H2_BAR','net_pnl_usd':net,'hold_minutes':float((ts-entry_ts)/pd.Timedelta(minutes=1))}
                continue
            hit_be=float(bar.low)<=entry; hit_tp=float(bar.high)>=target
            if hit_be:
                net=leg_pnl(entry,entry,b.NOTIONAL,b.FEE)
                return {'exit_ts':ts,'exit_px_equiv':entry,'exit_reason':'POST_H2_BREAK_EVEN','net_pnl_usd':net,'hold_minutes':float((ts-entry_ts)/pd.Timedelta(minutes=1))}
            if hit_tp:
                net=leg_pnl(target,entry,b.NOTIONAL,b.FEE)
                return {'exit_ts':ts,'exit_px_equiv':target,'exit_reason':'M7_TARGET','net_pnl_usd':net,'hold_minutes':float((ts-entry_ts)/pd.Timedelta(minutes=1))}
        op=next_open(x,end); assert op is not None
        net=leg_pnl(op[1],entry,b.NOTIONAL,b.FEE)
        return {'exit_ts':op[0],'exit_px_equiv':op[1],'exit_reason':'POST_H2_TIME_EXIT','net_pnl_usd':net,'hold_minutes':float((op[0]-entry_ts)/pd.Timedelta(minutes=1))}

    if mechanism=='H_CLOSE_FAILURE_M7':
        for ts,bar in q.iterrows():
            if float(bar.high)>=target:
                net=leg_pnl(target,entry,b.NOTIONAL,b.FEE)
                return {'exit_ts':ts,'exit_px_equiv':target,'exit_reason':'M7_TARGET','net_pnl_usd':net,'hold_minutes':float((ts-entry_ts)/pd.Timedelta(minutes=1))}
            if float(bar.close)<H:
                nxt=ts+b.BAR5
                if nxt<=end:
                    op=next_open(x,nxt)
                    if op is not None and op[0]==nxt:
                        net=leg_pnl(op[1],entry,b.NOTIONAL,b.FEE)
                        return {'exit_ts':op[0],'exit_px_equiv':op[1],'exit_reason':'POST_H2_CLOSE_BELOW_H','net_pnl_usd':net,'hold_minutes':float((op[0]-entry_ts)/pd.Timedelta(minutes=1))}
        op=next_open(x,end); assert op is not None
        net=leg_pnl(op[1],entry,b.NOTIONAL,b.FEE)
        return {'exit_ts':op[0],'exit_px_equiv':op[1],'exit_reason':'POST_H2_TIME_EXIT','net_pnl_usd':net,'hold_minutes':float((op[0]-entry_ts)/pd.Timedelta(minutes=1))}
    raise AssertionError(mechanism)


def simulate(x,r,mode,dist,sf,mechanism):
    pre=pre_h2_state(x,r,mode,dist,sf)
    entry=float(r.entry_px); entry_ts=pd.Timestamp(r.entry_ts)
    if pre['terminated']:
        net=leg_pnl(pre['exit_px'],entry,b.NOTIONAL,b.FEE)
        return {'mode':mode,'mechanism':mechanism,'stop_distance':dist,'stop_fraction':sf,'exit_ts':pre['exit_ts'],'exit_px_equiv':pre['exit_px'],'exit_reason':pre['exit_reason'],'net_pnl_usd':net,'hold_minutes':float((pd.Timestamp(pre['exit_ts'])-entry_ts)/pd.Timedelta(minutes=1)),'h2_reached':False}
    z=post_h2(x,r,mechanism); z.update({'mode':mode,'mechanism':mechanism,'stop_distance':dist,'stop_fraction':sf,'h2_reached':True}); return z


def metrics(g):
    p=pd.to_numeric(g.net_pnl_usd,errors='coerce').dropna(); pos=p[p>0]; neg=p[p<=0]
    gp=float(pos.sum()); gl=float(-neg.sum()); pf=np.inf if gl==0 and gp>0 else (gp/gl if gl>0 else np.nan)
    return {'trades':len(p),'wins':int((p>0).sum()),'losses':int((p<=0).sum()),'wr':float((p>0).mean()) if len(p) else np.nan,'pf':pf,'net_exp':float(p.mean()) if len(p) else np.nan,'total_net':float(p.sum()) if len(p) else np.nan,'h2_rate':float(g.h2_reached.mean()) if len(g) else np.nan,'median_hold_min':float(g.hold_minutes.median()) if len(g) else np.nan}


def synthetic_tests():
    idx=pd.date_range('2026-01-02 00:00',periods=7,freq='5min',tz='UTC')
    x=pd.DataFrame({'open':[98,98,100,101,100,100,100],'high':[99,99,100.2,103,101,101,101],'low':[97,97,99,100,98,98,98],'close':[98,98,100,102,99,100,100]},index=idx)
    r=pd.Series({'entry_ts':idx[0],'entry_px':98.,'H':100.,'L':90.,'R':10.,'target_px':103.,'target_name':'E30','session_end':idx[-1]+b.BAR5,'h2_ts':idx[2]})
    z=simulate(x,r,'CLOSE_NEXT_OPEN',.40,.55,'H2_FULL_EXIT'); assert z['exit_reason']=='H2_FULL_EXIT'
    z=simulate(x,r,'CLOSE_NEXT_OPEN',.40,.55,'H2_HALF_M7_HALF'); assert z['exit_reason']=='H2_HALF_M7_HALF_TP'
    z=simulate(x,r,'CLOSE_NEXT_OPEN',.40,.55,'BE_AFTER_H2_M7'); assert z['exit_reason']=='M7_TARGET'
    x2=x.copy(); x2.loc[idx[3],'high']=101.; x2.loc[idx[3],'low']=97.; z=simulate(x2,r,'CLOSE_NEXT_OPEN',.40,.55,'BE_AFTER_H2_M7'); assert z['exit_reason']=='POST_H2_BREAK_EVEN'
    x3=x.copy(); x3.loc[idx[2],'close']=99.; x3.loc[idx[2],'high']=100.2; z=simulate(x3,r,'CLOSE_NEXT_OPEN',.40,.55,'H_CLOSE_FAILURE_M7'); assert z['exit_reason']=='POST_H2_CLOSE_BELOW_H'


def main():
    synthetic_tests(); x,cov=b.m.load5(); assert cov>=.995
    E=b.build_entries(x); assert not E.empty
    rows=[]
    for r0 in E.to_dict('records'):
        for mode,(dist,sf) in STOPS[r0['clock']].items():
            for mech in MECHS:
                rows.append({**r0,**simulate(x,pd.Series(r0),mode,dist,sf,mech)})
    T=pd.DataFrame(rows); assert len(T)==len(E)*2*len(MECHS); T.to_csv(DETAIL,index=False)
    sums=[]
    for clock in LOCKED:
        for mode in STOPS[clock]:
            for mech in MECHS:
                for part in (*b.PARTS,'POOLED_MAJOR'):
                    g=T[(T.clock==clock)&(T['mode']==mode)&(T.mechanism==mech)]
                    g=g[g.partition.isin(b.MAJOR)] if part=='POOLED_MAJOR' else g[g.partition==part]
                    z=metrics(g); z.update({'clock':clock,'level':LOCKED[clock][0],'target':LOCKED[clock][2],'mode':mode,'mechanism':mech,'partition':part,'stop_distance':STOPS[clock][mode][0],'stop_fraction':STOPS[clock][mode][1]}); sums.append(z)
    S=pd.DataFrame(sums); S.to_csv(SUMMARY,index=False)
    sel=[]
    for clock in LOCKED:
        for mode in STOPS[clock]:
            for mech in MECHS:
                maj=S[(S.clock==clock)&(S['mode']==mode)&(S.mechanism==mech)&S.partition.isin(b.MAJOR)]
                pooled=S[(S.clock==clock)&(S['mode']==mode)&(S.mechanism==mech)&(S.partition=='POOLED_MAJOR')]
                ok=(len(maj)==3 and (maj.trades>=30).all() and (maj.wr>=.70).all() and (maj.net_exp>0).all() and (maj.pf>=1.20).all())
                pr=pooled.iloc[0]
                sel.append({'clock':clock,'level':LOCKED[clock][0],'target':LOCKED[clock][2],'mode':mode,'mechanism':mech,'screen_pass':bool(ok),'min_wr_major':float(maj.wr.min()),'min_pf_major':float(maj.pf.min()),'min_net_exp_major':float(maj.net_exp.min()),'pooled_wr':float(pr.wr),'pooled_pf':float(pr.pf),'pooled_net_exp':float(pr.net_exp),'pooled_total_net':float(pr.total_net)})
    SEL=pd.DataFrame(sel); SEL.to_csv(SELECTION,index=False)
    lines=['# ETH Transfer — M8C Exit Mechanism Discovery','','Raw ETH 5m coverage: **%.4f%%**.'%(cov*100),'','Frozen: M5 entries, M6 pre-H2 protections, M7 primary targets. Only post-H2 exit mechanism changes.','','| Habitat | Economic pass count | Best by frozen selection rule |','|---|---:|---|']
    for clock in LOCKED:
        c=SEL[SEL.clock==clock]; p=c[c.screen_pass]
        if len(p): best=p.sort_values(['min_net_exp_major','min_pf_major','min_wr_major'],ascending=False).iloc[0]; status='PASS'
        else: best=c.sort_values(['pooled_net_exp','pooled_pf','pooled_wr'],ascending=False).iloc[0]; status='NONE_PASS'
        lines.append(f"| {clock} | {len(p)} | **{best.mechanism} + {best['mode']}** ({status}; pooled WR {best.pooled_wr:.1%}, PF {best.pooled_pf:.2f}, exp ${best.pooled_net_exp:.3f}) |")
    lines += ['','Promotion screen: each major partition >=30 trades, WR >=70%, positive net expectancy, PF >=1.20. August telemetry only.','','**Status: ETH_M8C_EXIT_MECHANISM_COMPLETED**']
    RESULT.write_text('\n'.join(lines)+'\n'); STATUS.write_text('ETH_M8C_EXIT_MECHANISM_COMPLETED\n'); print(RESULT.read_text())

if __name__=='__main__': main()
