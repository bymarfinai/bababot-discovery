"""BTC Friday15 A6.6 — strict-causal winner/loss atlas.

Friday has a strong full-sample raw directional tendency but unstable executable economics.
A6.5 showed the frozen Saturday pre-pump gate does NOT generalize to Friday validation.
This file therefore does not tune a new rule. It maps Friday's own causal pre-entry state:
- raw 240m directional winner vs loser
- fixed A6.0 TP2.0/SL0.7/6h net winner vs loser
- discovery first82 vs validation last56
- quartile monotonicity for interpretable pre-entry features
- 6h MFE/MAE path medians

EMA/pre-entry features end at completed candle i-1. Research only.
"""
import json, statistics
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a724_preentry_wrongway_atlas as a724
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

TP=2.0; SL=.7; HOLD=360
FEATURES=('pre1','pre4','pre24','day_pos','vs_dopen','to_hod','to_lod','to_ph','to_pl','d7','d20','s7_15','s20_15','s7_60','s20_60','taker30','taker60','taker120','range_ratio_1h_vs_prev','vol_ratio_1h_vs_prev')


def med(xs): return rnd(statistics.median(xs),4) if xs else None

def raw240(rows,i):
    j=i+48
    if j>=len(rows) or rows[j][0]!=rows[i][0]+48*TF:return None
    return 100*(rows[j][1]-rows[i][1])/rows[i][1]

def path360(rows,i):
    end=i+HOLD//5
    if end>len(rows):return None
    q=[]
    for j in range(i,end):
        if rows[j][0]!=rows[i][0]+(j-i)*TF:return None
        q.append(rows[j])
    e=rows[i][1]
    return {'mfe':100*(max(x[2] for x in q)-e)/e,'mae':100*(e-min(x[3] for x in q))/e}

def atlas(q,label_key,label):
    z=[r for r in q if r[label_key]==label]
    out={'n':len(z)}
    for f in FEATURES:out[f+'_med']=med([r['prex'][f] for r in z])
    out['raw240_avg']=rnd(statistics.mean(r['raw240'] for r in z),4) if z else None
    out['exec_pnl']=rnd(sum(r['trade']['net_usd'] for r in z),3)
    out['mfe360_med']=med([r['path']['mfe'] for r in z]);out['mae360_med']=med([r['path']['mae'] for r in z])
    return out

def quartiles(q,f):
    ordered=sorted(q,key=lambda r:r['prex'][f]); n=len(ordered); out=[]
    for k in range(4):
        lo=k*n//4; hi=(k+1)*n//4; z=ordered[lo:hi]
        if not z:continue
        vals=[r['prex'][f] for r in z]; p=[r['trade']['net_usd'] for r in z]
        out.append({'q':k+1,'n':len(z),'lo':rnd(min(vals),4),'hi':rnd(max(vals),4),'med':med(vals),
          'raw240_wr':rnd(100*sum(r['raw240']>0 for r in z)/len(z),2),
          'raw240_avg':rnd(statistics.mean(r['raw240'] for r in z),4),
          'exec_wr':rnd(100*sum(x>0 for x in p)/len(p),2),'exec_pnl':rnd(sum(p),3),'exec_exp':rnd(sum(p)/len(p),4)})
    return out

def mechanism(q):
    # Capacity only: what fraction of executable losses had useful favorable excursion first?
    neg=[r for r in q if r['trade']['net_usd']<=0]
    return {'exec_losses':len(neg),
      'loss_mfe_ge_0.3':sum(r['path']['mfe']>=.3 for r in neg),
      'loss_mfe_ge_0.5':sum(r['path']['mfe']>=.5 for r in neg),
      'loss_mfe_ge_0.7':sum(r['path']['mfe']>=.7 for r in neg),
      'loss_mfe_ge_1.0':sum(r['path']['mfe']>=1.0 for r in neg),
      'loss_mae_ge_0.7':sum(r['path']['mae']>=.7 for r in neg)}

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
        i=im[x[0]];px=a724.pre_features(rows,i,e7,e20);rw=raw240(rows,i);t=a60.trade(rows,i,TP,SL,HOLD);p=path360(rows,i)
        if px is None or rw is None or t is None or p is None:continue
        rec.append({'i':i,'ts':x[0],'prex':px,'raw240':rw,'trade':t,'path':p,
          'raw_lab':'WIN' if rw>0 else 'LOSS','exec_lab':'WIN' if t['net_usd']>0 else 'LOSS'})
    split=int(len(rec)*.60);disc=rec[:split];val=rec[split:]
    out={'status':'FRIDAY15_A66_WINNER_LOSS_ATLAS','n':len(rec),'discovery_n':split,'validation_n':len(rec)-split,
      'raw240_atlas':{},'exec_atlas':{},'quartiles':{},'mechanism':{}}
    for scope,q in (('full',rec),('discovery',disc),('validation',val)):
        out['raw240_atlas'][scope]={'WIN':atlas(q,'raw_lab','WIN'),'LOSS':atlas(q,'raw_lab','LOSS')}
        out['exec_atlas'][scope]={'WIN':atlas(q,'exec_lab','WIN'),'LOSS':atlas(q,'exec_lab','LOSS')}
        out['mechanism'][scope]=mechanism(q)
    for f in FEATURES:
        out['quartiles'][f]={'full':quartiles(rec,f),'discovery':quartiles(disc,f),'validation':quartiles(val,f)}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
