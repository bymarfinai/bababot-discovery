"""Saturday18 A7.12 — deep loss taxonomy before any new management rule.

Frozen parent remains unchanged:
Saturday 18:00 WIB BUY / TP2.6 / SL1.2 / max18h / canonical historical funding.

Goal: decompose the 74 funding-adjusted negative trades into mutually exclusive path families,
then compare each family across discovery first83 and validation last56. No trading intervention
is optimized in this file.
"""
import json, statistics
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.6; SL=1.2; HOLD=1080
CHECKPOINTS=(15,30,60,120,240,360)

def med(xs): return rnd(statistics.median(xs),4) if xs else None

def first_touch(rows,i,level,side):
    e=rows[i][1]; end=min(len(rows),i+HOLD//5)
    for j in range(i,end):
        x=rows[j]
        if x[0] != rows[i][0]+(j-i)*TF: return None
        if side=='UP' and x[2] >= e*(1+level/100): return (j-i+1)*5
        if side=='DOWN' and x[3] <= e*(1-level/100): return (j-i+1)*5
    return None

def path_stats(rows,i):
    e=rows[i][1]; end=min(len(rows),i+HOLD//5); q=rows[i:end]
    hi=max(x[2] for x in q); lo=min(x[3] for x in q)
    hi_j=max(range(len(q)), key=lambda k:q[k][2]); lo_j=min(range(len(q)), key=lambda k:q[k][3])
    return {
      'mfe':100*(hi-e)/e,'mae':100*(e-lo)/e,
      't_peak':(hi_j+1)*5,'t_trough':(lo_j+1)*5,
      'u03':first_touch(rows,i,.3,'UP'),'u05':first_touch(rows,i,.5,'UP'),'u08':first_touch(rows,i,.8,'UP'),
      'd03':first_touch(rows,i,.3,'DOWN'),'d05':first_touch(rows,i,.5,'DOWN'),'d08':first_touch(rows,i,.8,'DOWN'),
    }

def earlier(a,b):
    if a is None:return False
    if b is None:return True
    return a < b

def taxonomy(p,reason):
    # Mutually exclusive, ordered by economically meaningful path shape.
    if p['mfe'] >= .8:
        return 'D_DEEP_GIVEBACK_GE_0.8'
    if p['mfe'] >= .5:
        return 'C_GIVEBACK_0.5_TO_0.8'
    if p['mfe'] >= .3:
        return 'B_WEAK_POP_0.3_TO_0.5'
    # Never even made +0.3. Separate immediate adverse movement from slow/no-edge drift.
    if earlier(p['d03'],p['u03']):
        return 'A1_WRONG_WAY_BEFORE_0.3'
    return 'A2_NO_FAVORABLE_IMPULSE_LT_0.3'

def state_summary(z,cp):
    q=[r['states'].get(cp) for r in z if r['states'].get(cp)]
    if not q:return None
    return {
      'n':len(q),
      'progress_med':med([x['progress'] for x in q]),
      'mfe_med':med([x['mfe'] for x in q]),
      'mae_med':med([x['mae'] for x in q]),
      'taker_med':med([x['taker'] for x in q]),
      'd7_med':med([x['d7'] for x in q]),
      'd20_med':med([x['d20'] for x in q]),
      's7_3_med':med([x['s7_3'] for x in q]),
      's20_3_med':med([x['s20_3'] for x in q]),
      'above7_pct':rnd(100*sum(x['above7'] for x in q)/len(q),2),
      'above20_pct':rnd(100*sum(x['above20'] for x in q)/len(q),2),
    }

def summarize(z):
    if not z:return {'n':0}
    return {
      'n':len(z),
      'pnl':rnd(sum(r['base'] for r in z),3),
      'mfe_med':med([r['path']['mfe'] for r in z]),
      'mae_med':med([r['path']['mae'] for r in z]),
      't_peak_med':med([r['path']['t_peak'] for r in z]),
      't_trough_med':med([r['path']['t_trough'] for r in z]),
      'sl':sum(r['reason'] in ('SL','AMB_SL') for r in z),
      'timeout':sum(r['reason']=='TIMEOUT' for r in z),
      'u03_before_d03_pct':rnd(100*sum(earlier(r['path']['u03'],r['path']['d03']) for r in z)/len(z),2),
      'u05_before_d05_pct':rnd(100*sum(earlier(r['path']['u05'],r['path']['d05']) for r in z)/len(z),2),
      'pre':{
        'day_pos_med':med([r['pre']['day_pos'] for r in z if r['pre']]),
        'pre1_med':med([r['pre']['pre1'] for r in z if r['pre']]),
        'pre4_med':med([r['pre']['pre4'] for r in z if r['pre']]),
        'd20_med':med([r['pre']['d20'] for r in z if r['pre']]),
        'to_hod_med':med([r['pre']['to_hod'] for r in z if r['pre']]),
      },
      'states':{str(cp):state_summary(z,cp) for cp in CHECKPOINTS},
    }

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; tsmap={x[0]:x for x in rows}
    e7=a74.ema_series(rows,7); e20=a74.ema_series(rows,20); funding,_,miss=load_funding()
    idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==5 and d.hour==18 and d.minute==0:idx.append(im[x[0]])
    rec=[]
    for i in idx:
        t=trade(rows,i,TP,SL,HOLD)
        if t is None:continue
        base,fp,fe=a74.funding_adjust(rows,t,funding,tsmap)
        p=path_stats(rows,i)
        r={'i':i,'ts':rows[i][0],'base':base,'reason':t['reason'],'path':p,
           'pre':a74.prectx(rows,i,e7,e20),'states':{cp:a74.state(rows,i,cp,e7,e20) for cp in CHECKPOINTS}}
        r['tax']=taxonomy(p,t['reason']) if base<=0 else 'WIN'
        rec.append(r)
    neg=[r for r in rec if r['base']<=0]; disc=[r for r in rec[:83] if r['base']<=0]; val=[r for r in rec[83:] if r['base']<=0]
    families=('A1_WRONG_WAY_BEFORE_0.3','A2_NO_FAVORABLE_IMPULSE_LT_0.3','B_WEAK_POP_0.3_TO_0.5','C_GIVEBACK_0.5_TO_0.8','D_DEEP_GIVEBACK_GE_0.8')
    out={
      'status':'SATURDAY18_A712_LOSS_TAXONOMY',
      'parent':{'n':len(rec),'losses':len(neg),'wr':rnd(100*(len(rec)-len(neg))/len(rec),2),'pnl':rnd(sum(r['base'] for r in rec),3)},
      'funding_missing':miss,
      'families':{}
    }
    for f in families:
        full=[r for r in neg if r['tax']==f]; d=[r for r in disc if r['tax']==f]; v=[r for r in val if r['tax']==f]
        out['families'][f]={
          'full':summarize(full),'discovery':summarize(d),'validation':summarize(v),
          'share_full_pct':rnd(100*len(full)/len(neg),2) if neg else None,
          'share_discovery_pct':rnd(100*len(d)/len(disc),2) if disc else None,
          'share_validation_pct':rnd(100*len(v)/len(val),2) if val else None,
        }
    # Also report broad mechanism buckets, still descriptive only.
    out['mechanism_counts']={
      'never_reach_plus_0.3':sum(r['path']['mfe']<.3 for r in neg),
      'reach_plus_0.3_not_0.5':sum(.3<=r['path']['mfe']<.5 for r in neg),
      'reach_plus_0.5_not_0.8':sum(.5<=r['path']['mfe']<.8 for r in neg),
      'reach_plus_0.8_or_more':sum(r['path']['mfe']>=.8 for r in neg),
      'sl_losses':sum(r['reason'] in ('SL','AMB_SL') for r in neg),
      'timeout_losses':sum(r['reason']=='TIMEOUT' for r in neg),
    }
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
