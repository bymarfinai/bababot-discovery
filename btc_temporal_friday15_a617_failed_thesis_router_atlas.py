"""BTC Friday15 A6.17 — forensic atlas for the 27 A6.12 confirmed failed-thesis cases.

All 138 Friday15 BUY entries remain unchanged. A6.17 only studies cases where the frozen
A6.12 state is confirmed at 120m:
- initial 60m: MFE<+.3, progress<0, taker<0, d20<0, EMA20 slope<0
- persistent at 120m: MFE<+.3 and progress<0

Outcome labels are descriptive only:
- SHORT_SUCCESS: original BUY loss, A6.12 flip result net positive
- SHORT_FAILURE: original BUY loss, A6.12 flip result non-positive
- DELAYED_BUY_WIN: original BUY would eventually finish net positive

Features are causal checkpoints at 120/150/180/210m and interval state after 120m.
Research only; no live code touched.
"""
import json, statistics
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a612_wrongway_robustness as a612
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

CHECKS=(120,150,180,210)
NOTIONAL=500.0

def med(xs): return rnd(statistics.median(xs),4) if xs else None

def interval_state(rows,r,e7,e20,h):
    i=r['i']; j0=i+120//5; j=i+h//5
    if j<=j0 or j>=len(rows): return None
    if rows[j][0]!=rows[i][0]+(h//5)*TF:return None
    q=rows[j0:j]
    if not q:return None
    e=r['entry']; op120=rows[j0][1]; oph=rows[j][1]; last=j-1; prev=max(0,last-3)
    tak=sum((x[9]/x[6] if x[6] else .5) for x in q)/len(q)-.5
    hi=max(x[2] for x in q); lo=min(x[3] for x in q)
    return {
      'delta_progress':100*(oph-op120)/op120,
      'progress':100*(oph-e)/e,
      'post120_up':100*(hi-op120)/op120,
      'post120_dn':100*(op120-lo)/op120,
      'taker_new':tak,
      'd7':100*(oph-e7[last])/e7[last],
      'd20':100*(oph-e20[last])/e20[last],
      's7_15':100*(e7[last]-e7[prev])/e7[prev] if e7[prev] else 0,
      's20_15':100*(e20[last]-e20[prev])/e20[prev] if e20[prev] else 0,
      'reclaim_entry':oph>=e,
      'further_down':oph<op120,
    }

def category(r):
    if r['base']>0:return 'DELAYED_BUY_WIN'
    if r['flip']>0:return 'SHORT_SUCCESS'
    return 'SHORT_FAILURE'

def pack(q):
    out={}
    for cat in ('SHORT_SUCCESS','SHORT_FAILURE','DELAYED_BUY_WIN'):
        z=[r for r in q if r['cat']==cat]; d={'n':len(z)}
        if z:
            d['base_pnl_med']=med([r['base'] for r in z]); d['flip_pnl_med']=med([r['flip'] for r in z])
            for h in CHECKS:
                zz=[r['checks'][str(h)] for r in z if r['checks'][str(h)]]
                for f in ('progress','mfe','mae','taker','d7','d20','s7_15','s20_15'):
                    d[f'{h}_{f}_med']=med([x[f] for x in zz])
                if h>120:
                    ii=[r['interval'][str(h)] for r in z if r['interval'][str(h)]]
                    for f in ('delta_progress','progress','post120_up','post120_dn','taker_new','d7','d20','s7_15','s20_15'):
                        d[f'{h}_new_{f}_med']=med([x[f] for x in ii])
                    d[f'{h}_reclaim_entry_pct']=rnd(100*sum(x['reclaim_entry'] for x in ii)/len(ii),2) if ii else None
                    d[f'{h}_further_down_pct']=rnd(100*sum(x['further_down'] for x in ii)/len(ii),2) if ii else None
        out[cat]=d
    return out

def simple_rules(rec,h):
    rules=(
      ('CONT_FLOW',lambda s:s['further_down'] and s['taker_new']<0),
      ('CONT_EMA20',lambda s:s['further_down'] and s['d20']<0 and s['s20_15']<0),
      ('CONT_FLOW_EMA20',lambda s:s['further_down'] and s['taker_new']<0 and s['d20']<0 and s['s20_15']<0),
      ('RECOVER_FLOW',lambda s:(not s['further_down']) and s['taker_new']>0),
      ('RECOVER_EMA7',lambda s:s['d7']>0 and s['s7_15']>0),
      ('RECOVER_ENTRY',lambda s:s['reclaim_entry']),
    )
    out=[]
    for name,fn in rules:
        z=[r for r in rec if r['interval'][str(h)] and fn(r['interval'][str(h)])]
        out.append({'h':h,'rule':name,'n':len(z),
          'cats':{c:sum(r['cat']==c for r in z) for c in ('SHORT_SUCCESS','SHORT_FAILURE','DELAYED_BUY_WIN')},
          'short_success_precision':rnd(100*sum(r['cat']=='SHORT_SUCCESS' for r in z)/len(z),2) if z else None,
          'delayed_buy_precision':rnd(100*sum(r['cat']=='DELAYED_BUY_WIN' for r in z)/len(z),2) if z else None})
    return out

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; e7=a74.ema_series(rows,7); e20=a74.ema_series(rows,20); allrec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
        i=im[x[0]]; t=a60.trade(rows,i,2.,.7,360); p=a69.path_stats(rows,i,x[1])
        if t is None or p is None:continue
        r={'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']}; r['label']=a69.label(r)
        c60=a69.checkpoint(rows,r,e7,e20,60); c120=a69.checkpoint(rows,r,e7,e20,120)
        r['confirmed']=bool(c60 and c120 and a612.initial(c60) and a612.confirmed(c120))
        if not r['confirmed']:continue
        rr=dict(r); rr['confirmed']=True; r['flip']=a611.action(rows,rr,120,'FLIP',(1.0,.7)); r['cat']=category(r)
        r['checks']={str(h):a69.checkpoint(rows,r,e7,e20,h) for h in CHECKS}
        r['interval']={str(h):(interval_state(rows,r,e7,e20,h) if h>120 else None) for h in CHECKS}
        allrec.append(r)
    assert len(allrec)==27, len(allrec)
    disc=[r for r in allrec if sum(1 for x in rows if False)==0 and r['ts'] < 0]  # replaced below using chronological parent position
    # Parent split is first 82 of 138. Build exact membership from Friday timestamps.
    friday_ts=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==4 and d.hour==15 and d.minute==0: friday_ts.append(x[0])
    split_ts=set(friday_ts[:82]); disc=[r for r in allrec if r['ts'] in split_ts]; val=[r for r in allrec if r['ts'] not in split_ts]
    out={'status':'FRIDAY15_A617_FAILED_THESIS_ROUTER_ATLAS','confirmed_n':len(allrec),
      'counts':{'full':{c:sum(r['cat']==c for r in allrec) for c in ('SHORT_SUCCESS','SHORT_FAILURE','DELAYED_BUY_WIN')},
                'discovery':{c:sum(r['cat']==c for r in disc) for c in ('SHORT_SUCCESS','SHORT_FAILURE','DELAYED_BUY_WIN')},
                'validation':{c:sum(r['cat']==c for r in val) for c in ('SHORT_SUCCESS','SHORT_FAILURE','DELAYED_BUY_WIN')}},
      'atlas':{'full':pack(allrec),'discovery':pack(disc),'validation':pack(val)},
      'simple_rules':{'discovery':sum((simple_rules(disc,h) for h in (150,180,210)),[]),
                      'validation':sum((simple_rules(val,h) for h in (150,180,210)),[]),
                      'full':sum((simple_rules(allrec,h) for h in (150,180,210)),[])},
      'cases':[{'ts':r['ts'],'cat':r['cat'],'base':rnd(r['base'],3),'flip':rnd(r['flip'],3),
                'states':{str(h):r['interval'][str(h)] for h in (150,180,210)}} for r in allrec]}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
