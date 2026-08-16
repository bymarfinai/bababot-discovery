"""BTC Friday15 A6.21 — parity-correct validation loss attribution.

Diagnostic only. Do not tune thresholds on validation.
Uses frozen A6.20 canonical engine (all 138 Friday15 BUY occurrences):
- parent BUY TP2.0 / SL0.7 / max6h
- failed-thesis detector 60m + 120m
- parity-correct sequential SHORT TP1.3 / SL0.7
- selective distribution giveback protection on non-wrongway trades.

Goal: explain why last56 validation is still net-negative after A6.20.
"""
import json, statistics
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a613_giveback_rescue as a613
import btc_temporal_friday15_a617b_wrongway_parity_repair as a617b
import btc_temporal_friday15_a620_parity_combined as a620
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

TP_SHORT=1.3; SL_SHORT=.7; H=120; HOLD=360; NOTIONAL=500.; FEE_USD=.75
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')

def med(xs): return rnd(statistics.median(xs),4) if xs else None

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wins':sum(x>0 for x in p),'losses':sum(x<=0 for x in p),
         'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,'pnl':rnd(sum(p),3),
         'exp':rnd(sum(p)/n,4) if n else None,'pf':rnd(pos/neg,3) if neg else None}

def route(r):
 if r['wrongway']:
  return 'WRONGWAY_REENTRY_AFTER_STOP' if a617b.exited_before_120(r) else 'WRONGWAY_FLIP_WHILE_OPEN'
 if r['dist_active']: return 'DISTRIBUTION_PROTECT'
 return 'NORMAL_PARENT'

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,2.,.7,HOLD);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'rows':rows,'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
  r['wrongway']=a620.confirmed(rows,r,e7,e20)
  r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
  r['sig']=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None
  r['dist_active']=not r['wrongway'] and a620.distribution_active(r['sig'])
  r['ww']=a620.wrongway_action(rows,r,TP_SHORT)
  r['new']=r['ww'] if r['wrongway'] else (a613.protect_pnl(rows,r,r['sig'],a620.LOCK) if r['dist_active'] else r['base'])
  r['route']=route(r)
  r['c60']=a69.checkpoint(rows,r,e7,e20,60);r['c120']=a69.checkpoint(rows,r,e7,e20,120)
  # Decompose sequential short economics where applicable.
  if r['wrongway']:
   j=i+H//5;end=i+HOLD//5;r['short_leg']=a611.short_leg(rows,j,end,TP_SHORT,SL_SHORT)
   if a617b.exited_before_120(r):r['long_component']=r['base']
   else:
    px=rows[j][1];r['long_component']=(px-r['entry'])/r['entry']*NOTIONAL-FEE_USD
  else:r['short_leg']=None;r['long_component']=None
  rec.append(r)
 assert len(rec)==138
 val=rec[82:];disc=rec[:82]
 def by_route(q):
  out={}
  for rt in ('NORMAL_PARENT','WRONGWAY_REENTRY_AFTER_STOP','WRONGWAY_FLIP_WHILE_OPEN','DISTRIBUTION_PROTECT'):
   z=[r for r in q if r['route']==rt]
   out[rt]={'final':econ([r['new'] for r in z]),'parent':econ([r['base'] for r in z]),
            'delta':rnd(sum(r['new']-r['base'] for r in z),3),
            'original_labels':{lab:sum(r['label']==lab for r in z) for lab in ('WIN','A_WRONG_WAY_LT_03','B_WEAK_POP_03_05','C_GIVEBACK_05_10','D_DEEP_GIVEBACK_GE_10')}}
   if 'WRONGWAY' in rt and z:
    out[rt]['short_leg']=econ([r['short_leg'] for r in z])
    out[rt]['short_tp_like_positive']=sum(r['short_leg']>0 for r in z)
  out[rt]['final_negative']=sum(r['new']<=0 for r in z)
  out[rt]['final_positive']=sum(r['new']>0 for r in z)
  return out
 losses=[r for r in val if r['new']<=0]
 # Attribution among final validation losses.
 loss_routes={rt:{'n':len(z),'pnl':rnd(sum(r['new'] for r in z),3),'parent_pnl':rnd(sum(r['base'] for r in z),3),
                  'mfe_med':med([r['path']['mfe'] for r in z]),'mae_med':med([r['path']['mae'] for r in z]),
                  'labels':{lab:sum(r['label']==lab for r in z) for lab in ('WIN','A_WRONG_WAY_LT_03','B_WEAK_POP_03_05','C_GIVEBACK_05_10','D_DEEP_GIVEBACK_GE_10')},
                  'exit_reasons':{reason:sum(r['trade']['reason']==reason for r in z) for reason in ('TP','SL','AMB_SL','TIMEOUT')}}
             for rt in ('NORMAL_PARENT','WRONGWAY_REENTRY_AFTER_STOP','WRONGWAY_FLIP_WHILE_OPEN','DISTRIBUTION_PROTECT')
             for z in [[r for r in losses if r['route']==rt]]}
 # Normal-parent validation losses deserve separate mechanism taxonomy because management never touched them.
 normal_losses=[r for r in losses if r['route']=='NORMAL_PARENT']
 normal_tax={lab:{'n':len(z),'pnl':rnd(sum(r['new'] for r in z),3),'mfe_med':med([r['path']['mfe'] for r in z]),
                  'mae_med':med([r['path']['mae'] for r in z]),'peak_min_med':med([r['path']['peak_min'] for r in z]),
                  'c60_progress_med':med([r['c60']['progress'] for r in z if r['c60']]),
                  'c120_progress_med':med([r['c120']['progress'] for r in z if r['c120']])}
             for lab in ('A_WRONG_WAY_LT_03','B_WEAK_POP_03_05','C_GIVEBACK_05_10','D_DEEP_GIVEBACK_GE_10')
             for z in [[r for r in normal_losses if r['label']==lab]]}
 # Wrongway validation loss decomposition: did the short leg itself lose, or did it win but fail to offset first leg?
 wwloss=[r for r in losses if r['wrongway']]
 ww_decomp={'n':len(wwloss),'short_leg_positive':sum(r['short_leg']>0 for r in wwloss),
            'short_leg_nonpositive':sum(r['short_leg']<=0 for r in wwloss),
            'prior_stop':sum(a617b.exited_before_120(r) for r in wwloss),
            'still_open_at120':sum(not a617b.exited_before_120(r) for r in wwloss),
            'long_component_pnl':rnd(sum(r['long_component'] for r in wwloss),3),
            'short_component_pnl':rnd(sum(r['short_leg'] for r in wwloss),3),
            'combined_pnl':rnd(sum(r['new'] for r in wwloss),3)}
 cases=[{'date':ldt(r['ts']).strftime('%Y-%m-%d'),'route':r['route'],'label':r['label'],'reason':r['trade']['reason'],
         'base':rnd(r['base'],3),'final':rnd(r['new'],3),'mfe':rnd(r['path']['mfe'],4),'mae':rnd(r['path']['mae'],4),
         'short_leg':rnd(r['short_leg'],3) if r['short_leg'] is not None else None,
         'c60_progress':rnd(r['c60']['progress'],4) if r['c60'] else None,'c120_progress':rnd(r['c120']['progress'],4) if r['c120'] else None}
        for r in losses]
 out={'status':'FRIDAY15_A621_VALIDATION_LOSS_ATTRIBUTION','frozen_engine':'A6.20 canonical TP1.3',
      'discovery':econ([r['new'] for r in disc]),'validation':econ([r['new'] for r in val]),
      'validation_parent':econ([r['base'] for r in val]),'validation_by_route':by_route(val),
      'validation_final_losses':{'n':len(losses),'pnl':rnd(sum(r['new'] for r in losses),3),'by_route':loss_routes,
                                 'normal_parent_taxonomy':normal_tax,'wrongway_loss_decomposition':ww_decomp},
      'validation_cases':cases}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
