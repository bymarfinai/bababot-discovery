"""BTC Friday15 A6.11 — recovery confirmation after frozen A6.10 60m failure state.

All 138 Friday entries remain. Initial failure state at 60m is frozen from A6.10:
MFE<+0.30, progress<0, taker<0, d20<0, s20_15<0.
Do NOT act immediately. Test whether persistence at 90/120/150m removes delayed winners.
Confirmation selection uses discovery only. Then evaluate CUT / fixed FLIP geoms on validation.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

TP=2.0;SL=.7;HOLD=360;NOTIONAL=500.;FEE_USD=.75
FOLLOW=(90,120,150)
SHORT_GEOMS=((.7,.7),(1.0,.7),(1.0,1.0))

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4) if n else None,'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def initial(c):return c['mfe']<.3 and c['progress']<0 and c['taker']<0 and c['d20']<0 and c['s20_15']<0

def conf_defs(h):
 return (
  (f'{h}_STILL_NO03_NEG',lambda c:c['mfe']<.3 and c['progress']<0),
  (f'{h}_STILL_NO03_NEG_FLOW',lambda c:c['mfe']<.3 and c['progress']<0 and c['taker']<0),
  (f'{h}_STILL_NO03_NEG_D20',lambda c:c['mfe']<.3 and c['progress']<0 and c['d20']<0),
  (f'{h}_STILL_NO03_NEG_FLOW_D20',lambda c:c['mfe']<.3 and c['progress']<0 and c['taker']<0 and c['d20']<0),
 )

def short_leg(rows,j,end,tp,sl):
 e=rows[j][1];tp_px=e*(1-tp/100);sl_px=e*(1+sl/100)
 for k in range(j,end):
  x=rows[k];ht=x[3]<=tp_px;hs=x[2]>=sl_px
  if ht and hs:return -sl/100*NOTIONAL-FEE_USD
  if hs:return -sl/100*NOTIONAL-FEE_USD
  if ht:return tp/100*NOTIONAL-FEE_USD
 px=rows[end][1];return (e-px)/e*NOTIONAL-FEE_USD

def action(rows,r,h,mode,g=None):
 if not r['confirmed']:return r['trade']['net_usd']
 j=r['i']+h//5;e=r['entry'];px=rows[j][1];ln=(px-e)/e*NOTIONAL-FEE_USD
 if mode=='CUT':return ln
 return ln+short_leg(rows,j,r['i']+HOLD//5,g[0],g[1])

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,TP,SL,HOLD);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p};r['label']=a69.label(r)
  r['c60']=a69.checkpoint(rows,r,e7,e20,60);r['follow']={str(h):a69.checkpoint(rows,r,e7,e20,h) for h in FOLLOW}
  if r['c60'] and all(r['follow'].values()):r['initial']=initial(r['c60']);rec.append(r)
 disc=rec[:82];val=rec[82:];init_disc=[r for r in disc if r['initial']];init_val=[r for r in val if r['initial']];init_full=[r for r in rec if r['initial']]
 cand=[]
 for h in FOLLOW:
  for name,fn in conf_defs(h):
   def pack(q):
    z=[r for r in q if r['initial'] and fn(r['follow'][str(h)])];n=len(z);loss=sum(r['trade']['net_usd']<=0 for r in z);w=n-loss;a=sum(r['label']=='A_WRONG_WAY_LT_03' for r in z)
    return {'signals':n,'losses':loss,'false_winner':w,'A_wrongway':a,'loss_precision':rnd(100*loss/n,2) if n else None}
   ds=pack(disc);vs=pack(val);fs=pack(rec);score=-1e9 if ds['signals']<8 else ds['loss_precision']*100+ds['A_wrongway']-ds['false_winner']
   cand.append({'name':name,'h':h,'score_disc':score,'discovery':ds,'validation':vs,'full':fs})
 chosen=max(cand,key=lambda z:z['score_disc']);h=chosen['h'];fn=dict(conf_defs(h))[chosen['name']]
 for r in rec:r['confirmed']=r['initial'] and fn(r['follow'][str(h)])
 base={'full':econ([r['trade']['net_usd'] for r in rec]),'discovery':econ([r['trade']['net_usd'] for r in disc]),'validation':econ([r['trade']['net_usd'] for r in val])}
 acts=[]
 for mode,g in [('CUT',None)]+[('FLIP',x) for x in SHORT_GEOMS]:
  pd=[action(rows,r,h,mode,g) for r in disc];pv=[action(rows,r,h,mode,g) for r in val];pf=[action(rows,r,h,mode,g) for r in rec]
  acts.append({'mode':mode,'geom':g,'discovery':econ(pd),'validation':econ(pv),'full':econ(pf),'delta_disc':rnd(sum(pd)-base['discovery']['pnl'],3),'delta_val':rnd(sum(pv)-base['validation']['pnl'],3),'delta_full':rnd(sum(pf)-base['full']['pnl'],3)})
 out={'status':'FRIDAY15_A611_RECOVERY_CONFIRMATION','initial60':{'full':len(init_full),'discovery':len(init_disc),'validation':len(init_val),'labels_full':{lab:sum(r['label']==lab for r in init_full) for lab in ('WIN','A_WRONG_WAY_LT_03','B_WEAK_POP_03_05','C_GIVEBACK_05_10','D_DEEP_GIVEBACK_GE_10')}},'candidates':cand,'chosen_confirmation':chosen,'base':base,'actions':acts,'selected_action_discovery_only':max(acts,key=lambda z:z['discovery']['pnl'])}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
