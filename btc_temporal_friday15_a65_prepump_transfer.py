"""BTC Friday15 A6.5 — frozen Saturday pre-pump exhaustion transfer.

Purpose
-------
Test whether the exact strict-causal Saturday18 pre-entry low-quality BUY state transfers
WITHOUT tuning to the independent BTC Friday15 BUY temporal cluster.

Frozen gate copied exactly from Saturday A7.25 primary PUMP_TREND_NEAR_PH:
- pre1 > 0
- pre4 > 0
- entry open > EMA20 computed through completed bar i-1
- EMA20 60m slope > 0 through i-1
- distance to previous completed 1h high <= 0.10%

Two tests:
1) Raw directional separation at 30/60/120/240/360m.
2) Executable A6.0 diagnostic parent fixed at TP2.0 / SL0.7 / 360m, fee-only,
   same-bar ambiguity adverse-first. Compare all Friday15 occurrences vs SKIP gate.

No Friday threshold tuning. No live mutation.
"""
import json, statistics
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a724_preentry_wrongway_atlas as a724
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

TP=2.0
SL=0.7
HOLD=360
HORIZONS=(30,60,120,240,360)


def gate(x):
    return bool(x and x['pre1']>0 and x['pre4']>0 and x['d20']>0 and x['s20_60']>0 and x['to_ph']<=.10)


def block_id(ts):
    return min(7,max(0,int((ts-EVAL_START)*8/(EVAL_END-EVAL_START))))


def raw_one(rows,r,h):
    i=r['i']; k=h//5; j=i+k
    if j>=len(rows) or rows[j][0] != rows[i][0]+k*TF:
        return None
    e=rows[i][1]; px=rows[j][1]
    return 100.0*(px-e)/e


def raw_summary(rows,recs,h):
    vals=[raw_one(rows,r,h) for r in recs]
    vals=[x for x in vals if x is not None]
    if not vals:return {'n':0}
    return {
      'n':len(vals),
      'wr':rnd(100*sum(x>0 for x in vals)/len(vals),2),
      'avg':rnd(statistics.mean(vals),4),
      'median':rnd(statistics.median(vals),4),
    }


def econ_summary(recs):
    p=[r['trade']['net_usd'] for r in recs]; n=len(p)
    if not p:return {'n':0}
    pos=sum(x for x in p if x>0); neg=-sum(x for x in p if x<0)
    blocks=[rnd(sum(r['trade']['net_usd'] for r in recs if block_id(r['ts'])==b),3) for b in range(8)]
    return {
      'n':n,
      'wr':rnd(100*sum(x>0 for x in p)/n,2),
      'pnl':rnd(sum(p),3),
      'exp':rnd(sum(p)/n,4),
      'pf':rnd(pos/neg,3) if neg else None,
      'mdd':rnd(a60.max_dd(p),3),
      'ls':a60.loss_streak(p),
      'positive_blocks':sum(x>0 for x in blocks),
      'blocks':blocks,
      'tp':sum(r['trade']['reason']=='TP' for r in recs),
      'sl':sum(r['trade']['reason'] in ('SL','AMB_SL') for r in recs),
      'timeout':sum(r['trade']['reason']=='TIMEOUT' for r in recs),
    }


def directional_pack(rows,q):
    return {str(h):raw_summary(rows,q,h) for h in HORIZONS}


def split_pack(rows,q):
    sig=[r for r in q if r['skip']]; keep=[r for r in q if not r['skip']]
    return {
      'all':directional_pack(rows,q),
      'signaled_skip':directional_pack(rows,sig),
      'retained':directional_pack(rows,keep),
      'counts':{'all':len(q),'signaled_skip':len(sig),'retained':len(keep)},
    }


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}
    e7=a74.ema_series(rows,7); e20=a74.ema_series(rows,20)
    rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
        i=im[x[0]]
        px=a724.pre_features(rows,i,e7,e20)
        t=a60.trade(rows,i,TP,SL,HOLD)
        if px is None or t is None:continue
        rec.append({'i':i,'ts':x[0],'prex':px,'skip':gate(px),'trade':t})
    split=int(len(rec)*.60)
    disc=rec[:split]; val=rec[split:]
    sig=[r for r in rec if r['skip']]; keep=[r for r in rec if not r['skip']]
    ds=[r for r in disc if r['skip']]; dk=[r for r in disc if not r['skip']]
    vs=[r for r in val if r['skip']]; vk=[r for r in val if not r['skip']]

    out={
      'status':'FRIDAY15_A65_FROZEN_PREPUMP_TRANSFER',
      'frozen_gate':'pre1>0 & pre4>0 & d20>0 & s20_60>0 & to_ph<=0.10',
      'methodology':{
        'entry':'Friday 15:00 WIB exact 5m open','direction':'BUY',
        'parent':'A6.0 fee-only diagnostic','tp_pct':TP,'sl_pct':SL,'hold_min':HOLD,
        'fee_roundtrip_pct':a60.FEE_PCT,'notional_usd':a60.NOTIONAL,
        'same_bar_policy':'SL/adverse first','fridays':len(rec),'discovery_n':split,'validation_n':len(rec)-split,
        'threshold_tuning_on_friday':False,
      },
      'raw_directional':{
        'full':split_pack(rows,rec),
        'discovery':split_pack(rows,disc),
        'validation':split_pack(rows,val),
      },
      'executable':{
        'full':{
          'parent_all':econ_summary(rec),'retained_after_skip':econ_summary(keep),'skipped_subset':econ_summary(sig),
          'skip_count':len(sig),'coverage_pct':rnd(100*len(keep)/len(rec),2),
        },
        'discovery':{
          'parent_all':econ_summary(disc),'retained_after_skip':econ_summary(dk),'skipped_subset':econ_summary(ds),
          'skip_count':len(ds),'coverage_pct':rnd(100*len(dk)/len(disc),2),
        },
        'validation':{
          'parent_all':econ_summary(val),'retained_after_skip':econ_summary(vk),'skipped_subset':econ_summary(vs),
          'skip_count':len(vs),'coverage_pct':rnd(100*len(vk)/len(val),2),
        },
      },
      'signals':[{
        'ts':r['ts'],'pre1':rnd(r['prex']['pre1'],4),'pre4':rnd(r['prex']['pre4'],4),
        'd20':rnd(r['prex']['d20'],4),'s20_60':rnd(r['prex']['s20_60'],4),'to_ph':rnd(r['prex']['to_ph'],4),
        'pnl':rnd(r['trade']['net_usd'],3),'reason':r['trade']['reason']
      } for r in sig],
    }
    # Explicit deltas for decision reading.
    for scope in ('full','discovery','validation'):
        z=out['executable'][scope]; b=z['parent_all']; k=z['retained_after_skip']
        z['delta_pnl']=rnd(k['pnl']-b['pnl'],3)
        z['delta_wr_pp']=rnd(k['wr']-b['wr'],2)
        z['delta_exp']=rnd(k['exp']-b['exp'],4)
        z['delta_pf']=rnd(k['pf']-b['pf'],3) if k['pf'] is not None and b['pf'] is not None else None
        z['delta_mdd']=rnd(k['mdd']-b['mdd'],3)
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
