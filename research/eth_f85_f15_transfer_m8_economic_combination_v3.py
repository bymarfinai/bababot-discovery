from __future__ import annotations
import importlib.util
from pathlib import Path
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('m8base', HERE/'eth_f85_f15_transfer_m8_economic_combination.py')
b=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(b)

def simulate_pre_h2(x, r, mode, dist, stop_fraction):
    entry_ts=pd.Timestamp(r.entry_ts); session_end=pd.Timestamp(r.session_end)
    H,L,R=float(r.H),float(r.L),float(r.R); entry=float(r.entry_px); target=float(r.target_px)
    boundary=L+float(stop_fraction)*R
    q=x.iloc[int(x.index.searchsorted(entry_ts)):int(x.index.searchsorted(session_end))]
    if q.empty or q.index[0]!=entry_ts: raise AssertionError('missing entry bar')
    assert L<boundary<entry<H<target
    h2=pd.Timestamp(r.h2_ts) if pd.notna(r.h2_ts) else pd.NaT
    exit_bar=exit_ts=pd.NaT; exit_px=np.nan; reason=''; h2_seen=False; accept=False
    for ts,bbar in q.iterrows():
        high,low,close=float(bbar.high),float(bbar.low),float(bbar.close)
        is_h2_bar=pd.notna(h2) and ts==h2
        after_h2=pd.notna(h2) and ts>h2
        if pd.notna(h2) and ts>=h2: h2_seen=True
        tp=high>=target
        if mode=='HARD_TOUCH':
            st=(low<=boundary) and not after_h2
            if tp and st:
                reason='HARD_STOP_AMBIGUOUS_SAME_BAR'; exit_bar=ts; exit_ts=ts; exit_px=boundary; break
            if st:
                reason='HARD_STOP'; exit_bar=ts; exit_ts=ts; exit_px=boundary; break
            if tp:
                reason=f'TP_{r.target_name}'; exit_bar=ts; exit_ts=ts; exit_px=target; break
        else:
            if tp:
                reason=f'TP_{r.target_name}'; exit_bar=ts; exit_ts=ts; exit_px=target; break
            if not after_h2 and not is_h2_bar and close<boundary:
                nxt=ts+b.BAR5
                if nxt<=session_end:
                    op=b.next_open(x,nxt)
                    if op is not None and op[0]==nxt:
                        reason='CLOSE_INVALIDATION'; exit_bar=ts; exit_ts=op[0]; exit_px=op[1]; break
        if close>H: accept=True
    if not reason:
        op=b.next_open(x,session_end)
        if op is None: raise AssertionError('missing session-end open')
        exit_ts,exit_px=op; exit_bar=exit_ts; reason='TIME_EXIT_SESSION_END'
    gross=exit_px/entry-1.0; net=gross*b.NOTIONAL-b.FEE
    hold=(pd.Timestamp(exit_ts)-entry_ts)/pd.Timedelta(minutes=1)
    return {'mode':mode,'stop_distance':dist,'stop_fraction':stop_fraction,'stop_px':boundary,'exit_bar_start':exit_bar,'exit_ts':exit_ts,'exit_px':exit_px,'exit_reason':reason,'gross_return':gross,'net_pnl_usd':net,'hold_minutes':float(hold),'h2_before_exit':bool(h2_seen),'close_above_H_before_exit':bool(accept),'nominal_rr':(target-entry)/(entry-boundary)}

def main():
    b.synthetic_tests(); x,coverage=b.m.load5(); assert coverage>=.995
    E=b.build_entries(x); assert not E.empty
    rows=[]
    for r in E.to_dict('records'):
        for mode,(dist,sf) in b.STOP_CANDIDATES[r['clock']].items(): rows.append({**r,**simulate_pre_h2(x,pd.Series(r),mode,dist,sf)})
    T=pd.DataFrame(rows); assert len(T)==len(E)*2; T.to_csv(b.OUT_DETAIL,index=False)
    sums=[]
    for clock in b.LOCKED:
        for mode in b.STOP_CANDIDATES[clock]:
            for part in (*b.PARTS,'POOLED_MAJOR'):
                g=T[(T['clock']==clock)&(T['mode']==mode)]; g=g[g['partition'].isin(b.MAJOR)] if part=='POOLED_MAJOR' else g[g['partition']==part]
                z=b.summarize(g); z.update({'clock':clock,'level':b.LOCKED[clock][0],'target':b.LOCKED[clock][2],'target_extension':b.LOCKED[clock][3],'mode':mode,'partition':part,'stop_distance':b.STOP_CANDIDATES[clock][mode][0],'stop_fraction':b.STOP_CANDIDATES[clock][mode][1]}); sums.append(z)
    S=pd.DataFrame(sums); S.to_csv(b.OUT_SUM,index=False)
    sel=[]
    for clock in b.LOCKED:
        for mode in b.STOP_CANDIDATES[clock]:
            maj=S[(S['clock']==clock)&(S['mode']==mode)&(S['partition'].isin(b.MAJOR))]
            ok=(len(maj)==3 and (maj['trades']>=30).all() and (maj['wr']>=.70).all() and (maj['net_exp']>0).all() and (maj['pf']>=1.20).all())
            pooled=S[(S['clock']==clock)&(S['mode']==mode)&(S['partition']=='POOLED_MAJOR')]
            sel.append({'clock':clock,'level':b.LOCKED[clock][0],'target':b.LOCKED[clock][2],'mode':mode,'stop_distance':b.STOP_CANDIDATES[clock][mode][0],'stop_fraction':b.STOP_CANDIDATES[clock][mode][1],'screen_pass':bool(ok),'min_wr_major':float(maj['wr'].min()) if len(maj) else np.nan,'min_pf_major':float(maj['pf'].min()) if len(maj) else np.nan,'min_net_exp_major':float(maj['net_exp'].min()) if len(maj) else np.nan,'pooled_net_exp':float(pooled['net_exp'].iloc[0]) if len(pooled) else np.nan})
    SEL=pd.DataFrame(sel); SEL.to_csv(b.OUT_SEL,index=False)
    chosen=[]
    for clock in b.LOCKED:
        c=SEL[SEL['clock']==clock]; p=c[c['screen_pass']]
        if len(p): q=p.sort_values(['min_net_exp_major','min_pf_major','min_wr_major'],ascending=False).iloc[0]; status='LOCKED'
        else: q=c.sort_values(['min_net_exp_major','min_pf_major','min_wr_major'],ascending=False).iloc[0]; status='NONE_PASS'
        chosen.append({**q.to_dict(),'status':status})
    CH=pd.DataFrame(chosen); CH.to_csv(Path(str(b.OUT_SEL).replace('_Selection.csv','_FinalSelection.csv')),index=False)
    lines=['# ETH Transfer — M8 Economic Combination Backtest — Corrected Pre-H2 Invalidation Scope','','Raw ETH 5m coverage: **%.4f%%**.'%(coverage*100),'',f'Illustrative notional: **${b.NOTIONAL:.0f}**; round-trip fee: **${b.FEE:.2f}**.','','M6 invalidation is applied only through the H2 terminal boundary: HARD_TOUCH includes the H2 bar; CLOSE_NEXT_OPEN excludes the H2 bar. After H2, only the frozen target or session-end time exit remains active.','','| Habitat | Entry→Target | Hard stop | Close invalidation | Economic selection |','|---|---|---|---|---|']
    for r in CH.itertuples(index=False):
        hs=SEL[(SEL['clock']==r.clock)&(SEL['mode']=='HARD_TOUCH')].iloc[0]; cs=SEL[(SEL['clock']==r.clock)&(SEL['mode']=='CLOSE_NEXT_OPEN')].iloc[0]
        hsx=f"{'PASS' if hs.screen_pass else 'FAIL'} D{int(hs.stop_distance*100):02d}/F{int(hs.stop_fraction*100):02d}"; csx=f"{'PASS' if cs.screen_pass else 'FAIL'} D{int(cs.stop_distance*100):02d}/F{int(cs.stop_fraction*100):02d}"
        lines.append(f'| {r.clock} | {r.level}→{r.target} | {hsx} | {csx} | **{r.status}**: {r.mode} |')
    lines += ['', 'Screen = each major partition has ≥30 resolved trades, WR ≥70%, positive net expectancy, PF ≥1.20. August is telemetry only.','', '**Status: ETH_M8_ECONOMIC_COMBINATION_COMPLETED**']
    Path(str(b.OUT_MD).replace('_Result.md','_Result_v3.md')).write_text('\n'.join(lines)+'\n'); Path(str(b.OUT_STATUS).replace('_Status.txt','_Status_v3.txt')).write_text('ETH_M8_ECONOMIC_COMBINATION_COMPLETED\n'); print('\n'.join(lines))
if __name__=='__main__': main()
