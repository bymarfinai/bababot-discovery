"""BTC Friday15 A6.14 — discriminate shallow giveback from healthy runner.

Builds on A6.13. Frozen broad deterioration event for study:
- actionable +0.5% hinge while BUY still open
- within 60m after hinge, completed 5m close progress <= +0.30%
- next 5m open decision
A6.13 showed broad +0.20 lock raises WR but destroys PnL by clipping runners.
A6.14 tests a mechanistic strength cap using cumulative MFE known at signal time.
No pre-entry filter. All 138 Fridays still enter. A6.12 wrong-way layer remains baseline.
"""
import json, statistics
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a613_giveback_rescue as a613
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END
import btc_temporal_saturday18_a74_loss_forensics as a74

CAPS=(.70,.80,1.00)
LOCK=.20
RULE=next(r for r in a613.RULES if r[0]=='GB30_60')

def econ(p):
 n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
 return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}

def med(xs):return rnd(statistics.median(xs),4) if xs else None

def sig_features(rows,r,sig):
 j=sig['bar'];e=r['entry'];q=rows[r['i']:j+1]
 mfe=max(100*(x[2]-e)/e for x in q);mae=max(100*(e-x[3])/e for x in q)
 return {'cum_mfe':mfe,'cum_mae':mae,'hinge_from_entry_min':(r['hinge']-r['i'])*5,
         'signal_from_entry_min':(j-r['i']+1)*5,'mins_after_hinge':sig['mins_after_hinge'],
         'progress':sig['state']['progress'],'taker':sig['state']['taker'],'d20':sig['state']['d20'],'s20':sig['state']['s20']}

def pack(q):
 out={}
 for lab in ('WIN','LOSS'):
  z=[x for x in q if x['outcome']==lab];d={'n':len(z)}
  for f in ('cum_mfe','cum_mae','hinge_from_entry_min','signal_from_entry_min','mins_after_hinge','progress','taker','d20','s20'):
   d[f+'_med']=med([x[f] for x in z])
  out[lab]=d
 return out

def main():
 rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[];atlas=[]
 for x in rows:
  if not(EVAL_START<=x[0]<EVAL_END):continue
  d=ldt(x[0])
  if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
  i=im[x[0]];t=a60.trade(rows,i,2.,.7,360);p=a69.path_stats(rows,i,x[1])
  if t is None or p is None:continue
  r={'rows':rows,'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a69.label(r)
  r['wrongway']=a613.wrongway_signal(rows,r,e7,e20);r['a612']=a613.wrongway_pnl(rows,r)
  r['hinge']=None if r['wrongway'] else a613.actionable_hinge(rows,r)
  sig=a613.find_signal(rows,r,e20,RULE) if r['hinge'] is not None else None;r['sig']=sig
  if sig:
   sf=sig_features(rows,r,sig);sf['ts']=r['ts'];sf['outcome']='WIN' if r['base']>0 else 'LOSS';sf['label']=r['label'];atlas.append(sf);r['sf']=sf
  else:r['sf']=None
  rec.append(r)
 assert len(rec)==138
 disc_at=[z for z in atlas if z['ts']<rec[82]['ts']];val_at=[z for z in atlas if z['ts']>=rec[82]['ts']]
 variants=[]
 for cap in CAPS:
  for r in rec:
   active=(not r['wrongway'] and r['sig'] is not None and r['sf']['cum_mfe']<cap)
   r['active']=active
   r['new']=a613.protect_pnl(rows,r,r['sig'],LOCK) if active else r['a612']
  def subset(q):
   a=[r for r in q if r['active']];return {'stats':econ([r['new'] for r in q]),'baseline':econ([r['a612'] for r in q]),
    'delta':rnd(sum(r['new']-r['a612'] for r in q),3),'actions':len(a),
    'loss_to_win':sum(r['base']<=0 and r['new']>0 for r in a),'win_to_loss':sum(r['base']>0 and r['new']<=0 for r in a),
    'win_clipped':sum(r['base']>0 and 0<r['new']<r['base'] for r in a)}
  variants.append({'cap':cap,'discovery':subset(rec[:82]),'validation':subset(rec[82:]),'full':subset(rec)})
 # choose discovery PnL delta only; threshold family predeclared above
 chosen=max(variants,key=lambda z:z['discovery']['delta']);cap=chosen['cap']
 for r in rec:
  r['active']=not r['wrongway'] and r['sig'] is not None and r['sf']['cum_mfe']<cap
  r['new']=a613.protect_pnl(rows,r,r['sig'],LOCK) if r['active'] else r['a612']
 blocks=[]
 for b in range(8):
  lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
  blocks.append({'block':b+1,'delta':rnd(sum(r['new']-r['a612'] for r in q),3),'actions':sum(r['active'] for r in q)})
 out={'status':'FRIDAY15_A614_SHALLOW_GIVEBACK','broad_signal_atlas':{'full':pack(atlas),'discovery':pack(disc_at),'validation':pack(val_at)},
  'variants':variants,'chosen':chosen,'parent':econ([r['base'] for r in rec]),'a612':econ([r['a612'] for r in rec]),
  'combined':econ([r['new'] for r in rec]),'combined_delta_vs_a612':rnd(sum(r['new']-r['a612'] for r in rec),3),
  'blocks':blocks,'positive_delta_blocks':sum(x['delta']>0 for x in blocks)}
 print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
