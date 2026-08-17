"""BTC Friday15 A6.36 — max drawdown forensics on A6.33 provisional champion.

No strategy changes. Reconstruct all 138 Friday15 occurrences under A6.33, identify the exact
peak-to-trough max drawdown episode, attribute each occurrence by management layer, and rank
all drawdown episodes. Research only; live untouched.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a613_giveback_rescue as a613
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_friday15_a620_parity_combined as a620
import btc_temporal_friday15_a630_conditional_tight_stop as a630
import btc_temporal_friday15_a632_ema_failure_structure as a632
import btc_temporal_friday15_a633_ema_early_warning_union as a633
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

HOLD=360
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,'pnl':rnd(sum(p),3),
  'exp':rnd(sum(p)/n,4) if n else None,'pf':rnd(pos/neg,3) if neg else None,
  'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def layer(r):
 if r['action']:
  return 'DAMAGE_'+str(r['source'])
 if r['wrongway']:
  return 'WRONGWAY_POSTSTOP' if r['prior_stop'] else 'WRONGWAY_STILLOPEN'
 if r['dist_active']:return 'DISTRIBUTION'
 return 'PARENT'

def build():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,2.,.7,HOLD);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'rows':rows,'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
  r['wrongway']=a620.confirmed(rows,r,e7,e20);r['prior_stop']=r['wrongway'] and a617b.exited_before_120(r)
  r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
  r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
  r['dist_active']=not r['wrongway'] and a620.distribution_active(r['sig'])
  r['baseline']=a630.baseline(rows,r)
  r['c60']=a69.checkpoint(rows,r,e7,e20,60)
  r['ema45']=a632.ema_state(rows,r,e7,e20,45)
  r['chosen'],r['action'],r['source']=a633.managed(rows,r,'EMA45_OR_FULL60')
  r['layer']=layer(r)
  rec.append(r)
 assert len(rec)==138
 return rows,rec

def episodes(rec):
 eq=0.;peak=0.;peak_i=-1;open_ep=None;eps=[]
 for i,r in enumerate(rec):
  before=eq;eq+=r['chosen']
  if eq>=peak-1e-12:
   if open_ep is not None:
    open_ep['recovery_i']=i;open_ep['recovery_eq']=eq;eps.append(open_ep);open_ep=None
   peak=eq;peak_i=i
  else:
   dd=peak-eq
   if open_ep is None:
    open_ep={'peak_i':peak_i,'peak_eq':peak,'start_i':i,'trough_i':i,'trough_eq':eq,'max_dd':dd}
   elif dd>open_ep['max_dd']:
    open_ep['trough_i']=i;open_ep['trough_eq']=eq;open_ep['max_dd']=dd
 if open_ep is not None:eps.append(open_ep)
 return sorted(eps,key=lambda e:e['max_dd'],reverse=True)

def ep_pack(rec,e):
 start=e['peak_i']+1;end=e['trough_i']+1;q=rec[start:end]
 layers={}
 for r in q:
  d=layers.setdefault(r['layer'],{'n':0,'pnl':0.,'loss_n':0,'loss_usd':0.,'win_n':0,'win_usd':0.})
  d['n']+=1;d['pnl']+=r['chosen']
  if r['chosen']<=0:d['loss_n']+=1;d['loss_usd']+=r['chosen']
  else:d['win_n']+=1;d['win_usd']+=r['chosen']
 for d in layers.values():
  for k in ('pnl','loss_usd','win_usd'):d[k]=rnd(d[k],3)
 cases=[]
 for j,r in enumerate(q,start=start):
  short=None
  if r['wrongway'] and r['prior_stop']:
   short=a611.short_leg(r['rows'],r['i']+24,r['i']+72,1.5,.5)
  cases.append({'idx':j,'date':str(ldt(r['ts']).date()),'layer':r['layer'],'pnl':rnd(r['chosen'],3),
   'parent_pnl':rnd(r['base'],3),'parent_reason':r['trade']['reason'],'label':r['label'],
   'wrongway':r['wrongway'],'prior_stop':r['prior_stop'],'dist':r['dist_active'],'damage_source':r['source'],
   'short_leg_if_poststop':rnd(short,3) if short is not None else None,'mfe':rnd(r['path']['mfe'],3),'mae':rnd(r['path']['mae'],3)})
 return {'peak_date':str(ldt(rec[e['peak_i']]['ts']).date()) if e['peak_i']>=0 else 'START',
  'start_date':str(ldt(rec[start]['ts']).date()),'trough_date':str(ldt(rec[e['trough_i']]['ts']).date()),
  'recovery_date':str(ldt(rec[e['recovery_i']]['ts']).date()) if e.get('recovery_i') is not None else None,
  'max_dd':rnd(e['max_dd'],3),'peak_eq':rnd(e['peak_eq'],3),'trough_eq':rnd(e['trough_eq'],3),
  'occurrences_to_trough':len(q),'episode_pnl':rnd(sum(r['chosen'] for r in q),3),'layers':layers,'cases':cases}

def main():
 rows,rec=build();eps=episodes(rec);packed=[ep_pack(rec,e) for e in eps[:8]]
 m=packed[0]
 all_layers={}
 for r in rec:
  all_layers.setdefault(r['layer'],[]).append(r['chosen'])
 layer_stats={k:econ(v) for k,v in all_layers.items()}
 # contribution ranking among negative cases inside max-DD descent
 neg=sorted([x for x in m['cases'] if x['pnl']<0],key=lambda x:x['pnl'])
 out={'status':'FRIDAY15_A636_MAXDD_FORENSICS','engine':econ([r['chosen'] for r in rec]),
  'max_dd_episode':m,'largest_negative_cases':neg[:12],'layer_stats_full':layer_stats,
  'top_drawdown_episodes':[{k:v for k,v in z.items() if k!='cases'} for z in packed],
  'notes':'Forensics only; no parameter or policy changes.'}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
