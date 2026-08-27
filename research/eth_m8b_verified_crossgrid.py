#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
spec=importlib.util.spec_from_file_location('m8base',HERE/'eth_f85_f15_transfer_m8_economic_combination.py'); b=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(b)
spec2=importlib.util.spec_from_file_location('m8v3',HERE/'eth_f85_f15_transfer_m8_economic_combination_v3.py'); v3=importlib.util.module_from_spec(spec2); assert spec2.loader is not None; spec2.loader.exec_module(v3)
LOCKED={'ALT_0330':('F95',.95),'RAW_0530':('F90',.90),'LONDON':('F90',.90),'RAW_2330':('F95',.95)}
STOPS={'ALT_0330':{'HARD_TOUCH':(.45,.50),'CLOSE_NEXT_OPEN':(.40,.55)},'RAW_0530':{'HARD_TOUCH':(.55,.35),'CLOSE_NEXT_OPEN':(.40,.50)},'LONDON':{'HARD_TOUCH':(.55,.35),'CLOSE_NEXT_OPEN':(.35,.55)},'RAW_2330':{'HARD_TOUCH':(.40,.55),'CLOSE_NEXT_OPEN':(.30,.65)}}
TARGETS={'ALT_0330':['E05','E10','E15','E20','E25','E30'],'RAW_0530':['E05','E10','E15','E20','E25','E30'],'LONDON':['E05','E10','E15','E20','E25'],'RAW_2330':['E05','E10','E15']}
PFX='ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M8B_VERIFIED'; DETAIL=ROOT/f'{PFX}_Detail.csv'; SUM=ROOT/f'{PFX}_Summary.csv'; SEL=ROOT/f'{PFX}_Selection.csv'; MD=ROOT/f'{PFX}_Result.md'; STATUS=ROOT/f'{PFX}_Status.txt'

def synth():
 idx=pd.date_range('2026-01-02 13:30',periods=5,freq='5min',tz='UTC'); x=pd.DataFrame({'open':[98.5,98,100,101,100],'high':[99,99,100.2,101.5,101],'low':[98,95,99.5,100,100],'close':[98.5,96,99.9,101,100.5]},index=idx); r=pd.Series({'entry_ts':idx[0],'entry_px':98.5,'H':100.,'L':90.,'R':10.,'target_px':101.,'target_name':'E10','session_end':idx[-1]+b.BAR5,'h2_ts':idx[2]}); assert v3.simulate_pre_h2(x,r,'CLOSE_NEXT_OPEN',.40,.55)['exit_reason']=='TP_E10'; x2=x.copy(); x2.loc[idx[1],'close']=95.; assert v3.simulate_pre_h2(x2,r,'CLOSE_NEXT_OPEN',.40,.55)['exit_reason']=='CLOSE_INVALIDATION'; x3=x.copy(); x3.loc[idx[1],'low']=95.; assert v3.simulate_pre_h2(x3,r,'HARD_TOUCH',.40,.55)['exit_reason']=='HARD_STOP'

def metrics(g):
 p=pd.to_numeric(g.net_pnl_usd,errors='coerce').dropna(); pos=p[p>0]; neg=p[p<=0]; gp=float(pos.sum()); gl=float(-neg.sum()); pf=np.inf if gl==0 and gp>0 else (gp/gl if gl>0 else np.nan); return {'trades':len(p),'wr':float((p>0).mean()) if len(p) else np.nan,'pf':pf,'net_exp':float(p.mean()) if len(p) else np.nan,'total_net':float(p.sum()) if len(p) else np.nan,'wins':int((p>0).sum()),'losses':int((p<=0).sum()),'tp_rate':float(g.exit_reason.astype(str).str.startswith('TP_').mean()) if len(g) else np.nan,'stop_rate':float(g.exit_reason.astype(str).str.contains('STOP|INVALIDATION').mean()) if len(g) else np.nan,'time_exit_rate':float((g.exit_reason.astype(str)=='TIME_EXIT_SESSION_END').mean()) if len(g) else np.nan,'median_hold_min':float(g.hold_minutes.median()) if len(g) else np.nan}

def main():
 synth(); x,cov=b.m.load5(); assert cov>=.995; E=b.build_entries(x); assert not E.empty
 rows=[]
 for r0 in E.to_dict('records'):
  clock=r0['clock']
  for target in TARGETS[clock]:
   ext=int(target[1:])/100.0; rr=dict(r0); rr['target_name']=target; rr['target_extension']=ext; rr['target_px']=float(rr['H'])+ext*float(rr['R'])
   for mode,(dist,sf) in STOPS[clock].items(): rows.append({**rr,**v3.simulate_pre_h2(x,pd.Series(rr),mode,dist,sf)})
 T=pd.DataFrame(rows); assert len(T)>0; T.to_csv(DETAIL,index=False)
 out=[]
 for clock,(lvl,_) in LOCKED.items():
  for target in TARGETS[clock]:
   for mode,(dist,sf) in STOPS[clock].items():
    for part in (*b.MAJOR,'POOLED_MAJOR'):
     g=T[(T.clock==clock)&(T.target_name==target)&(T.mode==mode)]; g=g[g.partition.isin(b.MAJOR)] if part=='POOLED_MAJOR' else g[g.partition==part]; z=metrics(g); z.update({'clock':clock,'level':lvl,'target':target,'mode':mode,'stop_distance':dist,'stop_fraction':sf,'partition':part}); out.append(z)
 S=pd.DataFrame(out); S.to_csv(SUM,index=False)
 sel=[]
 for clock,(lvl,_) in LOCKED.items():
  for target in TARGETS[clock]:
   for mode,(dist,sf) in STOPS[clock].items():
    maj=S[(S.clock==clock)&(S.target==target)&(S.mode==mode)&S.partition.isin(b.MAJOR)]; pooled=S[(S.clock==clock)&(S.target==target)&(S.mode==mode)&(S.partition=='POOLED_MAJOR')]; ok=(len(maj)==3 and (maj.trades>=30).all() and (maj.wr>=.70).all() and (maj.net_exp>0).all() and (maj.pf>=1.20).all()); pr=pooled.iloc[0] if len(pooled) else None; sel.append({'clock':clock,'level':lvl,'target':target,'mode':mode,'stop_distance':dist,'stop_fraction':sf,'screen_pass':bool(ok),'min_wr_major':float(maj.wr.min()) if len(maj) else np.nan,'min_pf_major':float(maj.pf.min()) if len(maj) else np.nan,'min_net_exp_major':float(maj.net_exp.min()) if len(maj) else np.nan,'pooled_wr':float(pr.wr) if pr is not None else np.nan,'pooled_pf':float(pr.pf) if pr is not None else np.nan,'pooled_net_exp':float(pr.net_exp) if pr is not None else np.nan})
 SELD=pd.DataFrame(sel); SELD.to_csv(SEL,index=False)
 lines=['# ETH Transfer — M8B Verified Economic Stop×Target Cross-Grid','','Raw ETH 5m coverage: **%.4f%%**.'%(cov*100),'','Frozen inputs: verified M6 stop candidates and verified M7-passing target candidates. No new entry/stop/target levels.','M6 invalidation applies only through H2; after H2 only the tested target or session-end time exit remains active.','','| Habitat | M7-passing targets | Economic pass count | Best pooled candidate |','|---|---|---:|---|']
 for clock in LOCKED:
  c=SELD[SELD.clock==clock]; p=c[c.screen_pass]; best=(p if len(p) else c).sort_values(['pooled_net_exp','pooled_pf','pooled_wr'],ascending=False).iloc[0]; lines.append(f"| {clock} | {', '.join(TARGETS[clock])} | {len(p)} | **{best.target} + {best.mode}** ({'PASS' if best.screen_pass else 'NO PASS'}, pooled WR {best.pooled_wr:.1%}, PF {best.pooled_pf:.2f}, exp ${best.pooled_net_exp:.3f}) |")
 lines += ['','Economic screen: each major partition >=30 resolved trades, WR >=70%, positive net expectancy, PF >=1.20.','', '**Status: ETH_M8B_VERIFIED_ECONOMIC_CROSSGRID_COMPLETED**']; MD.write_text('\n'.join(lines)+'\n'); STATUS.write_text('ETH_M8B_VERIFIED_ECONOMIC_CROSSGRID_COMPLETED\n'); print(MD.read_text())
if __name__=='__main__': main()
