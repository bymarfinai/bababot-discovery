"""BTC Friday15 A6.7 — compact causal pullback selector.

A6.6 found a stable qualitative difference in both chronological halves:
Friday15 BUY winners tend to enter after a pullback, below/falling EMA20, whereas losses
are nearer/above flat-to-rising EMA20. Test ONLY sign-based interpretable rules here.
No non-zero threshold sweep, no money-geometry retune.

Fixed executable diagnostic remains A6.0 TP2.0 / SL0.7 / 6h / 0.15% fee.
Research only; same Friday sample means this is exploratory, not fresh OOS proof.
"""
import json, statistics
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a724_preentry_wrongway_atlas as a724
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

TP=2.0;SL=.7;HOLD=360
HORIZONS=(30,60,120,240,360)
RULES=(
 ('D20_BELOW',lambda x:x['d20']<0),
 ('EMA20_PULLBACK',lambda x:x['d20']<0 and x['s20_60']<0),
 ('PRICE_EMA_PULLBACK',lambda x:x['pre1']<0 and x['d20']<0 and x['s20_60']<0),
 ('MULTI_HORIZON_PULLBACK',lambda x:x['pre1']<0 and x['pre4']<0 and x['d20']<0 and x['s20_60']<0),
 ('PULLBACK_SELLFLOW',lambda x:x['pre1']<0 and x['d20']<0 and x['s20_60']<0 and x['taker30']<0),
 ('EMA7_20_PULLBACK',lambda x:x['d7']<0 and x['d20']<0 and x['s7_15']<0 and x['s20_15']<0),
)

def raw(rows,r,h):
    j=r['i']+h//5
    if j>=len(rows) or rows[j][0]!=rows[r['i']][0]+(h//5)*TF:return None
    return 100*(rows[j][1]-rows[r['i']][1])/rows[r['i']][1]

def raws(rows,q):
    out={}
    for h in HORIZONS:
        z=[raw(rows,r,h) for r in q];z=[x for x in z if x is not None]
        out[str(h)]={'n':len(z),'wr':rnd(100*sum(x>0 for x in z)/len(z),2) if z else None,
          'avg':rnd(statistics.mean(z),4) if z else None,'median':rnd(statistics.median(z),4) if z else None}
    return out

def econ(q):
    p=[r['trade']['net_usd'] for r in q];n=len(p)
    if not p:return {'n':0}
    pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),
      'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p),
      'tp':sum(r['trade']['reason']=='TP' for r in q),'sl':sum(r['trade']['reason'] in ('SL','AMB_SL') for r in q),
      'timeout':sum(r['trade']['reason']=='TIMEOUT' for r in q)}

def pack(rows,q,total):
    return {'coverage_pct':rnd(100*len(q)/total,2) if total else 0,'raw':raws(rows,q),'exec':econ(q)}

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
        i=im[x[0]];px=a724.pre_features(rows,i,e7,e20);t=a60.trade(rows,i,TP,SL,HOLD)
        if px is not None and t is not None:rec.append({'i':i,'ts':x[0],'prex':px,'trade':t})
    split=int(len(rec)*.60);disc=rec[:split];val=rec[split:]
    base={'full':pack(rows,rec,len(rec)),'discovery':pack(rows,disc,len(disc)),'validation':pack(rows,val,len(val))}
    rr=[]
    for name,fn in RULES:
        fq=[r for r in rec if fn(r['prex'])];dq=[r for r in disc if fn(r['prex'])];vq=[r for r in val if fn(r['prex'])]
        rr.append({'rule':name,'full':pack(rows,fq,len(rec)),'discovery':pack(rows,dq,len(disc)),'validation':pack(rows,vq,len(val))})
    print('RESULT_JSON',json.dumps({'status':'FRIDAY15_A67_PULLBACK_SELECTOR','method':'sign-only rules; no threshold/geometry optimization',
      'parent':'Friday15 BUY TP2.0 SL0.7 hold360 fee0.15','base':base,'rules':rr},separators=(',',':')),flush=True)
if __name__=='__main__':main()
