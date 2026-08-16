"""Saturday18 A7.19 — frozen shallow-runner protection test.

Motivation is NOT a new threshold sweep. A7.12 already defined the natural loss taxonomy
boundary between C (MFE +0.5..<+0.8) and D (MFE >=+0.8). A7.18 showed the large validation
false-positive winner had already reached +1.02 MFE, while all five A7.17 eventual-loss
signals remained below +0.8.

Frozen strict-causal detector at 240 completed minutes:
- 0.50% <= MFE < 0.80%
- current progress +0.20%..+0.40%
- completed-window taker edge < 0
Decision at next 5m open.

Compare DIRECT actual-open exit and +0.20% real-style profit lock. All 139 entries remain.
Historical funding and 0.15% one-position roundtrip fee are preserved. No phantom fill.
"""
import json
import btc_temporal_saturday18_a717_lockable_profit_protection as a717

CP=240

def shallow_detector(s):
    return bool(s and 0.5<=s['mfe']<0.8 and 0.20<=s['progress']<=0.40 and s['taker']<0)

def managed(rows,r,mode,funding,tsmap,lock=None):
    s=r['state']
    if not shallow_detector(s):return r['base'],False,'NO_SIGNAL'
    j=s['decision_i'];e=r['entry'];dec=rows[j][1];entry_ts=rows[r['i']][0]
    if mode=='DIRECT':
        return a717.pnl_at_exit(e,dec,entry_ts,rows[j][0],funding,tsmap),True,'DIRECT'
    lock_px=e*(1+lock/100.0);tp_px=e*(1+a717.TP/100.0)
    if dec<=lock_px:
        return a717.pnl_at_exit(e,dec,entry_ts,rows[j][0],funding,tsmap),True,'MARKET_THROUGH_LOCK'
    end=min(len(rows),r['i']+a717.HOLD//5);exit_px=None;exit_i=None;reason='TIMEOUT'
    for k in range(j,end):
        if rows[k][0]!=rows[j][0]+(k-j)*a717.TF:return r['base'],False,'DATA_GAP'
        x=rows[k];hl=x[3]<=lock_px;ht=x[2]>=tp_px
        if hl and ht:exit_px=lock_px;exit_i=k;reason='LOCK_AMBIG';break
        if hl:exit_px=lock_px;exit_i=k;reason='LOCK';break
        if ht:exit_px=tp_px;exit_i=k;reason='TP';break
    if exit_px is None:exit_i=end-1;exit_px=rows[exit_i][4]
    return a717.pnl_at_exit(e,exit_px,entry_ts,rows[exit_i][0],funding,tsmap),True,reason

def evaluate(rows,recs,mode,funding,tsmap,lock=None):
    vals=[];actions=rescued=damaged=clipped=improved=0;reasons={}
    for r in recs:
        final,act,reason=managed(rows,r,mode,funding,tsmap,lock)
        if act:
            actions+=1;reasons[reason]=reasons.get(reason,0)+1
            if r['base']<=0 and final>0:rescued+=1
            if r['base']>0 and final<=0:damaged+=1
            if r['base']>0 and final>0 and final<r['base']:clipped+=1
            if r['base']<=0 and final>r['base']:improved+=1
        vals.append({'ts':r['ts'],'base':r['base'],'final':final})
    b=a717.summarize(vals,'base');z=a717.summarize(vals,'final')
    z.update({'delta':a717.rnd(z['pnl']-b['pnl'],3),'actions':actions,'rescued':rescued,'damaged':damaged,
              'clipped_winners':clipped,'improved_losses':improved,'reasons':reasons})
    return z

def main():
    rows,tsmap,funding,miss,recs=a717.build();disc=recs[:83];val=recs[83:]
    base=a717.summarize([{'ts':r['ts'],'base':r['base']} for r in recs],'base')
    configs=[]
    for mode,lock in [('DIRECT',None),('LOCK',0.20)]:
        configs.append({'mode':mode,'lock':lock,'discovery':evaluate(rows,disc,mode,funding,tsmap,lock),
                        'validation':evaluate(rows,val,mode,funding,tsmap,lock),
                        'full':evaluate(rows,recs,mode,funding,tsmap,lock)})
    print('RESULT_JSON',json.dumps({'status':'SATURDAY18_A719_SHALLOW_RUNNER_PROTECTION','parent':base,
      'detector':'240m: MFE 0.50..<0.80 & progress 0.20..0.40 & taker<0','funding_missing':miss,'configs':configs},separators=(',',':')),flush=True)
if __name__=='__main__':main()
