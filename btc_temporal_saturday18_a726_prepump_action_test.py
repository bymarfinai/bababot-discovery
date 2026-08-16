"""Saturday18 A7.26 — economic action test for frozen A7.25 pre-pump exhaustion state.

Frozen pre-entry state (no threshold sweep here):
PUMP_TREND_NEAR_PH = pre1>0 & pre4>0 & d20>0 & EMA20 60m slope>0 & distance to prior-1h high <=0.10%.

Compare against A7.19 provisional management champion:
1) SKIP the pre-pump occurrence (coverage cost made explicit).
2) DELAY BUY by 15/30/60m on those occurrences, using TP2.6/SL1.2 and the remaining
   original 18h temporal horizon. Non-signaled trades keep A7.19 management.

Strict causal pre-entry features end at i-1, with only actual 18:00 open known at decision.
Historical funding + 0.15% roundtrip fee retained. Research only; no live mutation.
"""
import json
import btc_temporal_saturday18_a717_lockable_profit_protection as a717
import btc_temporal_saturday18_a723_a719_robustness as a723
import btc_temporal_saturday18_a724_preentry_wrongway_atlas as a724
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_saturday18_a70_money_geometry import FEE_PCT,NOTIONAL
from btc_temporal_a34_5m_events import TF,rnd

TPSL=(2.6,1.2); DELAYS=(15,30,60)

def signal(x):
    return bool(x and x['pre1']>0 and x['pre4']>0 and x['d20']>0 and x['s20_60']>0 and x['to_ph']<=.10)

def delayed_trade(rows,i,delay,funding,tsmap):
    j=i+delay//5; end=min(len(rows),i+1080//5)
    if j>=end or j>=len(rows):return None
    if rows[j][0]!=rows[i][0]+(j-i)*TF:return None
    e=rows[j][1];tp=e*(1+TPSL[0]/100);sl=e*(1-TPSL[1]/100);ex=None;reason='TIMEOUT';exit_i=None
    for k in range(j,end):
        if rows[k][0]!=rows[j][0]+(k-j)*TF:return None
        x=rows[k];ht=x[2]>=tp;hs=x[3]<=sl
        if ht and hs:ex=sl;reason='AMB_SL';exit_i=k;break
        if hs:ex=sl;reason='SL';exit_i=k;break
        if ht:ex=tp;reason='TP';exit_i=k;break
    if ex is None:
        exit_i=end-1;ex=rows[exit_i][4]
    gross=100*(ex-e)/e;raw=NOTIONAL*(gross-FEE_PCT)/100
    fp=a717.funding_long(funding,tsmap,rows[j][0],rows[exit_i][0],NOTIONAL/e,e)
    return {'pnl':raw+fp,'reason':reason,'entry_i':j,'exit_i':exit_i,'entry':e,'exit':ex}

def summary(vals,key):return a717.summarize(vals,key)

def split_stats(vals,key):
    return {'full':summary(vals,key),'discovery':summary(vals[:83],key),'validation':summary(vals[83:],key)}

def main():
    rows,tsmap,funding,miss,recs=a717.build();e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20)
    # A7.19 final values for the frozen comparison base.
    a719_vals,_=a723.eval_recs(rows,recs,funding,tsmap,0.80)
    for r in recs:r['prex']=a724.pre_features(rows,r['i'],e7,e20)
    sigidx={k for k,r in enumerate(recs) if signal(r['prex'])}
    base=[{'ts':x['ts'],'a719':x['final']} for x in a719_vals]
    base_stats=split_stats(base,'a719')

    # SKIP: summarize retained trades only, and expose occurrence coverage.
    kept=[x for k,x in enumerate(base) if k not in sigidx]
    kd=sum(k<83 for k in sigidx);kv=sum(k>=83 for k in sigidx)
    skip={
      'signals':len(sigidx),'coverage_pct':rnd(100*len(kept)/len(base),2),
      'full':summary(kept,'a719'),
      'discovery':summary([x for k,x in enumerate(base[:83]) if k not in sigidx],'a719'),
      'validation':summary([x for k,x in enumerate(base[83:],start=83) if k not in sigidx],'a719'),
      'skipped_discovery':kd,'skipped_validation':kv,
    }

    delays=[]
    for delay in DELAYS:
        vals=[];details=[]
        for k,r in enumerate(recs):
            if k not in sigidx:
                final=a719_vals[k]['final'];reason='A719_OR_PARENT'
            else:
                t=delayed_trade(rows,r['i'],delay,funding,tsmap)
                if t is None:
                    final=a719_vals[k]['final'];reason='DELAY_DATA_FAIL'
                else:
                    final=t['pnl'];reason='DELAY_'+t['reason']
                    details.append({'idx':k,'ts':r['ts'],'a719':a719_vals[k]['final'],'delayed':final,'delta':final-a719_vals[k]['final'],'reason':t['reason']})
            vals.append({'ts':r['ts'],'final':final})
        st=split_stats(vals,'final')
        delays.append({'delay_min':delay,'signals':len(sigidx),'full':st['full'],'discovery':st['discovery'],'validation':st['validation'],
          'delta_full':rnd(st['full']['pnl']-base_stats['full']['pnl'],3),
          'delta_discovery':rnd(st['discovery']['pnl']-base_stats['discovery']['pnl'],3),
          'delta_validation':rnd(st['validation']['pnl']-base_stats['validation']['pnl'],3),
          'details':details})
    out={'status':'SATURDAY18_A726_PREPUMP_ACTION_TEST','funding_missing':miss,
      'signal':'PUMP_TREND_NEAR_PH','signal_count':len(sigidx),'base_a719':base_stats,'skip':skip,'delays':delays}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
