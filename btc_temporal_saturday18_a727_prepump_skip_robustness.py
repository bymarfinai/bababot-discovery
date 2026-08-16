"""Saturday18 A7.27 — robustness audit for A7.26 pre-pump SKIP candidate.

Primary candidate is frozen from A7.25/A7.26:
pre1>0 & pre4>0 & d20>0 & EMA20 60m slope>0 & to prior-1h high <=0.10%.

No new rule family is selected here. Audit:
- local prior-hour-high cap perturbation (.08/.10/.12/.15)
- pre1 floor perturbation (0/.03/.05) one dimension at a time with PH=.10
- leave-one-skip-out (restore one skipped occurrence)
- year distribution
All retained trades use A7.19 frozen management.
"""
import json,datetime as dt
import btc_temporal_saturday18_a717_lockable_profit_protection as a717
import btc_temporal_saturday18_a723_a719_robustness as a723
import btc_temporal_saturday18_a724_preentry_wrongway_atlas as a724
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import rnd

PH_CAPS=(.08,.10,.12,.15); PRE1_FLOORS=(0,.03,.05)

def sig(x,ph=.10,pre1=0):
    return bool(x and x['pre1']>pre1 and x['pre4']>0 and x['d20']>0 and x['s20_60']>0 and x['to_ph']<=ph)

def summarize_kept(base,recs,ph=.10,pre1=0,restore=None):
    kept=[];sk=[]
    for k,(x,r) in enumerate(zip(base,recs)):
        s=sig(r['prex'],ph,pre1)
        if restore is not None and k==restore:s=False
        if s:sk.append(k)
        else:kept.append({'ts':x['ts'],'p':x['final']})
    return a717.summarize(kept,'p'),sk,kept

def split_summary(base,recs,ph=.10,pre1=0):
    f,sk,_=summarize_kept(base,recs,ph,pre1)
    db=base[:83];dr=recs[:83]; vb=base[83:];vr=recs[83:]
    d,dsk,_=summarize_kept(db,dr,ph,pre1);v,vsk,_=summarize_kept(vb,vr,ph,pre1)
    return {'full':f,'discovery':d,'validation':v,'skips':len(sk),'skip_discovery':len(dsk),'skip_validation':len(vsk),'coverage_pct':rnd(100*f['n']/len(base),2)}

def main():
    rows,tsmap,funding,miss,recs=a717.build();e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20)
    base,_=a723.eval_recs(rows,recs,funding,tsmap,.80)
    for r in recs:r['prex']=a724.pre_features(rows,r['i'],e7,e20)
    primary=split_summary(base,recs,.10,0)
    primary_idx=[k for k,r in enumerate(recs) if sig(r['prex'],.10,0)]
    loo=[]
    for k in primary_idx:
        s,_,_=summarize_kept(base,recs,.10,0,restore=k)
        loo.append({'restored_idx':k,'ts':recs[k]['ts'],'restored_a719':rnd(base[k]['final'],3),'pnl':s['pnl'],'wr':s['wr'],'pf':s['pf'],'mdd':s['mdd'],'n':s['n']})
    ph=[]
    for x in PH_CAPS:
        z=split_summary(base,recs,x,0);z['ph_cap']=x;ph.append(z)
    pre=[]
    for x in PRE1_FLOORS:
        z=split_summary(base,recs,.10,x);z['pre1_floor']=x;pre.append(z)
    # Primary year stats on retained occurrences.
    _,_,kept=summarize_kept(base,recs,.10,0)
    years={}
    for y in (2023,2024,2025,2026):
        q=[x for x in kept if dt.datetime.fromtimestamp(x['ts']/1000,dt.timezone.utc).year==y]
        if q:years[str(y)]=a717.summarize(q,'p')
    out={'status':'SATURDAY18_A727_PREPUMP_SKIP_ROBUSTNESS','funding_missing':miss,
      'a719_base':a717.summarize([{'ts':x['ts'],'p':x['final']} for x in base],'p'),
      'primary':primary,'ph_cap_sensitivity':ph,'pre1_floor_sensitivity':pre,
      'leave_one_skip_out':loo,'year_stats':years}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
