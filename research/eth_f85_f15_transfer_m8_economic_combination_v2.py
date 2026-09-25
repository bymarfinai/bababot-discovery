from __future__ import annotations
import importlib.util
from pathlib import Path
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('m8base', HERE/'eth_f85_f15_transfer_m8_economic_combination.py')
b=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(b)

def main():
    b.synthetic_tests()
    x, coverage=b.m.load5(); assert coverage>=.995
    E=b.build_entries(x); assert not E.empty
    rows=[]
    for r in E.to_dict('records'):
        for mode,(dist,sf) in b.STOP_CANDIDATES[r['clock']].items():
            rows.append({**r,**b.simulate(x,pd.Series(r),mode,dist,sf)})
    T=pd.DataFrame(rows); assert len(T)==len(E)*2
    T.to_csv(b.OUT_DETAIL,index=False)
    sums=[]
    for clock in b.LOCKED:
        for mode in b.STOP_CANDIDATES[clock]:
            for part in (*b.PARTS,'POOLED_MAJOR'):
                g=T[(T['clock']==clock)&(T['mode']==mode)]
                g=g[g['partition'].isin(b.MAJOR)] if part=='POOLED_MAJOR' else g[g['partition']==part]
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
    CH=pd.DataFrame(chosen); chosen_path=Path(str(b.OUT_SEL).replace('_Selection.csv','_FinalSelection.csv')); CH.to_csv(chosen_path,index=False)
    lines=['# ETH Transfer — M8 Economic Combination Backtest — Result','','Raw ETH 5m coverage: **%.4f%%**.'%(coverage*100),'',f'Illustrative notional: **${b.NOTIONAL:.0f}**; round-trip fee: **${b.FEE:.2f}**.','','Frozen entries/targets: ALT F95→E30; RAW0530 F90→E30; LONDON F90→E25; RAW2330 F95→E15.','','| Habitat | Entry→Target | Hard stop | Close invalidation | Economic selection |','|---|---|---|---|---|']
    for r in CH.itertuples(index=False):
        hs=SEL[(SEL['clock']==r.clock)&(SEL['mode']=='HARD_TOUCH')].iloc[0]; cs=SEL[(SEL['clock']==r.clock)&(SEL['mode']=='CLOSE_NEXT_OPEN')].iloc[0]
        hsx=f"{'PASS' if hs.screen_pass else 'FAIL'} D{int(hs.stop_distance*100):02d}/F{int(hs.stop_fraction*100):02d}"; csx=f"{'PASS' if cs.screen_pass else 'FAIL'} D{int(cs.stop_distance*100):02d}/F{int(cs.stop_fraction*100):02d}"
        lines.append(f'| {r.clock} | {r.level}→{r.target} | {hsx} | {csx} | **{r.status}**: {r.mode} |')
    lines += ['', 'Screen = each major partition has ≥30 resolved trades, WR ≥70%, positive net expectancy, PF ≥1.20. August is telemetry only.','', '**Status: ETH_M8_ECONOMIC_COMBINATION_COMPLETED**']
    Path(str(b.OUT_MD).replace('_Result.md','_Result_v2.md')).write_text('\n'.join(lines)+'\n')
    Path(str(b.OUT_STATUS).replace('_Status.txt','_Status_v2.txt')).write_text('ETH_M8_ECONOMIC_COMBINATION_COMPLETED\n')
    print('\n'.join(lines))
if __name__=='__main__': main()
