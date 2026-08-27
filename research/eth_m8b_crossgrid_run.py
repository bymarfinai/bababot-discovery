#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent.parent
HERE=Path(__file__).resolve().parent
PFX='ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M8B'
OUT_DETAIL=ROOT/f'{PFX}_Detail.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_TARGETS=ROOT/f'{PFX}_M7PassingTargets.csv'; OUT_SEL=ROOT/f'{PFX}_Selection.csv'; OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
spec=importlib.util.spec_from_file_location('m8base',HERE/'eth_f85_f15_transfer_m8_economic_combination.py'); b=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(b)
spec2=importlib.util.spec_from_file_location('m8v3',HERE/'eth_f85_f15_transfer_m8_economic_combination_v3.py'); v3=importlib.util.module_from_spec(spec2); assert spec2.loader is not None; spec2.loader.exec_module(v3)
EXTS=[.05,.10,.15,.20,.25,.30,.40,.50]; MAJOR=('external','development','reference_validation')
LOCKED={'ALT_0330':('F95',.95),'RAW_0530':('F90',.90),'LONDON':('F90',.90),'RAW_2330':('F95',.95)}
STOP_CANDIDATES={'ALT_0330':{'HARD_TOUCH':(.45,.50),'CLOSE_NEXT_OPEN':(.40,.55)},'RAW_0530':{'HARD_TOUCH':(.55,.35),'CLOSE_NEXT_OPEN':(.40,.50)},'LONDON':{'HARD_TOUCH':(.55,.35),'CLOSE_NEXT_OPEN':(.35,.55)},'RAW_2330':{'HARD_TOUCH':(.40,.55),'CLOSE_NEXT_OPEN':(.30,.65)}}

def synthetic_tests():
 idx=pd.date_range('2026-01-02 13:30',periods=5,freq='5min',tz='UTC'); x=pd.DataFrame({'open':[98.5,98,100,101,100],'high':[99,99,100.2,101.5,101],'low':[98,95,99.5,100,100],'close':[98.5,96,99.9,101,100.5]},index=idx); r=pd.Series({'entry_ts':idx[0],'entry_px':98.5,'H':100.,'L':90.,'R':10.,'target_px':101.,'target_name':'E10','session_end':idx[-1]+b.BAR5,'h2_ts':idx[2]}); assert v3.simulate_pre_h2(x,r,'CLOSE_NEXT_OPEN',.40,.55)['exit_reason']=='TP_E10'; x2=x.copy(); x2.loc[idx[1],'close']=95.; assert v3.simulate_pre_h2(x2,r,'CLOSE_NEXT_OPEN',.40,.55)['exit_reason']=='CLOSE_INVALIDATION'; x3=x.copy(); x3.loc[idx[1],'low']=95.; assert v3.simulate_pre_h2(x3,r,'HARD_TOUCH',.40,.55)['exit_reason']=='HARD_STOP'

def build_m7_targets(E,x):
 rows=[]
 for r in E.itertuples(index=False):
  if r.m2_outcome!='H2': continue
  h2=pd.Timestamp(r.h2_ts); end=pd.Timestamp(r.session_end); post=x.iloc[int(x.index.searchsorted(h2,'left')):int(x.index.searchsorted(end,'left'))]
  if post.empty or post.index[0]!=h2: raise AssertionError('missing H2 post path')
  for e in EXTS:
   tag=f'E{int(round(e*100)):02d}'; px=float(r.H)+e*float(r.R); rows.append({'clock':r.clock,'level':r.level,'target':tag,'extension':e,'partition':r.partition,'wick_reach_n':int((post.high>=px).any()),'close_accept_n':int((post.close>=px).any())})
 D=pd.DataFrame(rows); assert not D.empty
 out=[]
 for clock,(lvl,_) in LOCKED.items():
  for e in EXTS:
   tag=f'E{int(round(e*100)):02d}'
   for p in (*MAJOR,'POOLED_MAJOR'):
    allg=E[(E.clock==clock)&(E.level==lvl)];
    if p=='POOLED_MAJOR': allg=allg[allg.partition.isin(MAJOR)]
    g=D[(D.clock==clock)&(D.target==tag)&(D.partition.isin(MAJOR))] if p=='POOLED_MAJOR' else D[(D.clock==clock)&(D.target==tag)&(D.partition==p)]
    fills=len(allg); h2n=int((allg.m2_outcome=='H2').sum()); wr=int(g.wick_reach_n.sum()) if len(g) else 0; cr=int(g.close_accept_n.sum()) if len(g) else 0
    out.append({'clock':clock,'level':lvl,'target':tag,'extension':e,'partition':p,'fills':fills,'h2_n':h2n,'h2_rate':h2n/fills if fills else np.nan,'wick_reach_all':wr/fills if fills else np.nan,'wick_reach_given_h2':wr/h2n if h2n else np.nan,'close_accept_given_h2':cr/h2n if h2n else np.nan})
 S=pd.DataFrame(out); passing=[]
 for clock,(lvl,_) in LOCKED.items():
  for e in EXTS:
   tag=f'E{int(round(e*100)):02d}'; major=S[(S.clock==clock)&(S.level==lvl)&(S.target==tag)&S.partition.isin(MAJOR)]; pooled=S[(S.clock==clock)&(S.level==lvl)&(S.target==tag)&(S.partition=='POOLED_MAJOR')]
   if len(pooled)!=1: continue
   p=pooled.iloc[0]; ok=(len(major)==3 and (major.h2_n>=20).all() and (major.wick_reach_given_h2>=.60).all() and float(p.wick_reach_given_h2)>=.70 and float(p.wick_reach_all)>=.55 and float(p.close_accept_given_h2)>=.50)
   if ok: passing.append({'clock':clock,'level':lvl,'target':tag,'extension':e,'pooled_h2_rate':float(p.h2_rate),'pooled_wick_given_h2':float(p.wick_reach_given_h2),'pooled_wick_all':float(p.wick_reach_all),'pooled_close_given_h2':float(p.close_accept_given_h2)})
 P=pd.DataFrame(passing); P.to_csv(OUT_TARGETS,index=False); return P

def summarize(g):
 x=pd.to_numeric(g.net_pnl_usd,errors='coerce').dropna(); pos=x[x>0]; neg=x[x<=0]; gp=float(pos.sum()); gl=float(-neg.sum()); pf=np.inf if gl==0 and gp>0 else (gp/gl if gl>0 else np.nan); reasons=g.exit_reason.astype(str); return {'trades':len(x),'wins':int((x>0).sum()),'losses':int((x<=0).sum()),'wr':float((x>0).mean()) if len(x) else np.nan,'pf':pf,'net_exp':float(x.mean()) if len(x) else np.nan,'total_net':float(x.sum()) if len(x) else np.nan,'tp_rate':float(reasons.str.startswith('TP_').mean()) if len(x) else np.nan,'stop_count':int(reasons.str.contains('STOP|INVALIDATION').sum()),'time_exit_count':int((reasons=='TIME_EXIT_SESSION_END').sum()),'median_hold_minutes':float(g.hold_minutes.median()) if len(g) else np.nan}

def main():
 synthetic_tests(); x,coverage=b.m.load5(); assert coverage>=.995; E=b.build_entries(x); assert not E.empty; P=build_m7_targets(E,x); assert not P.empty
 rows=[]
 for r0 in E.to_dict('records'):
  for t in P[P.clock==r0['clock']].to_dict('records'):
   rr=dict(r0); rr['target_name']=t['target']; rr['target_extension']=float(t['extension']); rr['target_px']=float(rr['H'])+float(t['extension'])*float(rr['R'])
   for mode,(dist,sf) in STOP_CANDIDATES[rr['clock']].items(): rows.append({**rr,**v3.simulate_pre_h2(x,pd.Series(rr),mode,dist,sf)})
 T=pd.DataFrame(rows); assert not T.empty; T.to_csv(OUT_DETAIL,index=False)
 sums=[]
 for clock,(lvl,_) in LOCKED.items():
  for target in P[P.clock==clock].target.unique():
   for mode in STOP_CANDIDATES[clock]:
    for part in (*b.PARTS,'POOLED_MAJOR'):
     g=T[(T.clock==clock)&(T.target_name==target)&(T.mode==mode)]; g=g[g.partition.isin(b.MAJOR)] if part=='POOLED_MAJOR' else g[g.partition==part]; z=summarize(g); z.update({'clock':clock,'level':lvl,'target':target,'mode':mode,'stop_distance':STOP_CANDIDATES[clock][mode][0],'stop_fraction':STOP_CANDIDATES[clock][mode][1],'partition':part}); sums.append(z)
 S=pd.DataFrame(sums); S.to_csv(OUT_SUM,index=False); selections=[]
 for clock,(lvl,_) in LOCKED.items():
  for target in P[P.clock==clock].target.unique():
   for mode in STOP_CANDIDATES[clock]:
    maj=S[(S.clock==clock)&(S.target==target)&(S.mode==mode)&S.partition.isin(b.MAJOR)]; pooled=S[(S.clock==clock)&(S.target==target)&(S.mode==mode)&(S.partition=='POOLED_MAJOR')]; ok=(len(maj)==3 and (maj.trades>=30).all() and (maj.wr>=.70).all() and (maj.net_exp>0).all() and (maj.pf>=1.20).all()); selections.append({'clock':clock,'level':lvl,'target':target,'mode':mode,'screen_pass':bool(ok),'min_wr_major':float(maj.wr.min()) if len(maj) else np.nan,'min_pf_major':float(maj.pf.min()) if len(maj) else np.nan,'min_net_exp_major':float(maj.net_exp.min()) if len(maj) else np.nan,'pooled_wr':float(pooled.wr.iloc[0]) if len(pooled) else np.nan,'pooled_pf':float(pooled.pf.iloc[0]) if len(pooled) else np.nan,'pooled_net_exp':float(pooled.net_exp.iloc[0]) if len(pooled) else np.nan})
 SEL=pd.DataFrame(selections); SEL.to_csv(OUT_SEL,index=False); chosen=[]
 for clock,(lvl,_) in LOCKED.items():
  c=SEL[SEL.clock==clock]; p=c[c.screen_pass]; q=(p if len(p) else c).sort_values(['min_net_exp_major','min_pf_major','min_wr_major'],ascending=False).iloc[0]; chosen.append({**q.to_dict(),'status':'LOCKED_CANDIDATE' if len(p) else 'NONE_PASS'})
 CH=pd.DataFrame(chosen); lines=['# ETH Transfer — M8B Economic Stop×Target Cross-Grid','',f'Raw ETH 5m coverage: **{coverage:.4%}**.','','Only M7-passing target candidates and M6 stop candidates were tested. M6 invalidation applies only through H2; after H2 only target/session-end remains active.',f'Notional: **${b.NOTIONAL:.0f}**; round-trip fee: **${b.FEE:.2f}**.','','| Habitat | M7-passing targets | Best economic candidate |','|---|---|---|']
 for clock in LOCKED:
  targets=', '.join(P[P.clock==clock].target.tolist()) or 'NONE'; cc=CH[CH.clock==clock]; econ=f"{cc.iloc[0].status}: {cc.iloc[0].target} + {cc.iloc[0].mode}" if len(cc) else 'NONE'; lines.append(f'| {clock} | {targets} | **{econ}** |')
 lines += ['','Economic screen: each major partition >=30 resolved trades, WR >=70%, positive net expectancy, PF >=1.20.','','**Status: ETH_M8B_ECONOMIC_CROSSGRID_COMPLETED**']; OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text('ETH_M8B_ECONOMIC_CROSSGRID_COMPLETED\n'); print(OUT_MD.read_text())
if __name__=='__main__': main()
