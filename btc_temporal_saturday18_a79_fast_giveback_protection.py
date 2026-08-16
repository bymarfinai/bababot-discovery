"""Saturday18 A7.9 — causal fast-giveback PROFIT-LOCK study.

Frozen parent: BUY Saturday 18:00 WIB, TP2.6%, SL1.2%, max18h.
A7.7/A7.8 identified two mechanistic fast-giveback conditions after +0.5% MFE:
 C1: completed 5m close gives back to <=+0.4% within 5 minutes of the +0.5 hinge.
 C2: completed 5m close gives back to <=+0.3% within 30 minutes of the +0.5 hinge.
These conditions are fixed here; EMA is not required because A7.7 showed that below-EMA
failure logic would often cut eventual winners.

On a trigger, at the NEXT 5m open:
- if price is already at/below the proposed profit-lock, exit at that actual open;
- otherwise arm a protective stop at the lock while keeping original TP2.6 alive;
- if a future 5m bar touches both TP and lock, lock is assumed first (adverse precedence);
- no extra round-trip fee is invented: it is still one BUY position with one final exit;
- historical funding is charged only until the actual simulated exit.

Lock levels are ranked on first 83 Saturdays only; validation is then reported.
Note: classifier validation behavior was inspected in A7.8, so A7.9 is a robustness split,
not pristine untouched OOS for the classifier family itself.
"""
import json
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a76_hinge_statistics as a76
import btc_temporal_saturday18_a77_giveback_statistics as a77
from btc_temporal_a34_5m_events import load,ldt,rnd,TF,EVAL_START,EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade,FEE_PCT,NOTIONAL,max_dd,loss_streak
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.6; SL=1.2; HOLD=1080
CLASSIFIERS=(('C1_0.4_in_5m',0.4,5),('C2_0.3_in_30m',0.3,30))
LOCKS=(0.05,0.10,0.15,0.20,0.25,0.30,0.35)

def block_id(ts): return min(7,max(0,int((ts-EVAL_START)*8/(EVAL_END-EVAL_START))))

def funding_pnl(funding,tsmap,entry_ts,exit_ts,qty,entry_px):
    z=0.0
    for ft,rate in funding:
        if ft<=entry_ts: continue
        if ft>exit_ts: break
        px=(tsmap.get(ft) or [None,entry_px])[1]
        z += -qty*px*rate
    return z

def parent_record(rows,i,funding,tsmap,e7,e20):
    t=trade(rows,i,TP,SL,HOLD)
    if t is None:return None
    base=a74.funding_adjust(rows,t,funding,tsmap)[0]
    h=a76.first_hinge(rows,i,0.5,e7,e20)
    triggers={}
    if h:
        for name,lvl,speed in CLASSIFIERS:
            g=a77.first_giveback(rows,i,h,lvl,e7,e20)
            if g and g['since']<=speed:
                # A7.7 stores elapsed minutes from hinge, not an absolute bar index.
                triggers[name]={**g,'j':h['j']+int(g['since']//5)}
            else:
                triggers[name]=None
    else:
        triggers={name:None for name,_,_ in CLASSIFIERS}
    return {'ts':t['ts'],'i':i,'entry':t['entry'],'base':base,'reason':t['reason'],'bars':t['bars'],'triggers':triggers}

def managed_trade(rows,r,trigger,lock,funding,tsmap):
    if trigger is None:return r['base'],False,'NO_TRIGGER'
    j=trigger['j']+1
    end=min(len(rows),r['i']+HOLD//5)
    if j>=end:return r['base'],False,'TOO_LATE'
    e=r['entry']; tp_px=e*(1+TP/100.0); lock_px=e*(1+lock/100.0)
    decision_px=rows[j][1]
    exit_px=None;exit_i=None;reason=None
    if decision_px<=lock_px:
        exit_px=decision_px;exit_i=j;reason='MARKET_BELOW_LOCK'
    else:
        for k in range(j,end):
            x=rows[k]
            if x[0]!=rows[j][0]+(k-j)*TF:return r['base'],False,'DATA_GAP'
            hit_lock=x[3]<=lock_px; hit_tp=x[2]>=tp_px
            if hit_lock and hit_tp:
                exit_px=lock_px;exit_i=k;reason='LOCK_AMBIG';break
            if hit_lock:
                exit_px=lock_px;exit_i=k;reason='LOCK';break
            if hit_tp:
                exit_px=tp_px;exit_i=k;reason='TP';break
        if exit_px is None:
            exit_i=end-1;exit_px=rows[exit_i][4];reason='TIMEOUT'
    gross_pct=100*(exit_px-e)/e
    raw=NOTIONAL*(gross_pct-FEE_PCT)/100.0
    fp=funding_pnl(funding,tsmap,rows[r['i']][0],rows[exit_i][0],NOTIONAL/e,e)
    return raw+fp,True,reason

def summarize(vals,key):
    p=[x[key] for x in vals];n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    blocks=[rnd(sum(x[key] for x in vals if block_id(x['ts'])==b),3) for b in range(8)]
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),
      'pf':rnd(pos/neg,3) if neg>0 else None,'mdd':rnd(max_dd(p),3),'ls':loss_streak(p),'positive_blocks':sum(x>0 for x in blocks),'blocks':blocks}

def evaluate(rows,recs,name,lock,funding,tsmap):
    vals=[];actions=rescued=damaged=improved_losses=clipped_winners=0;reasons={}
    for r in recs:
        final,act,reason=managed_trade(rows,r,r['triggers'].get(name),lock,funding,tsmap)
        if act:
            actions+=1;reasons[reason]=reasons.get(reason,0)+1
            if r['base']<=0 and final>0:rescued+=1
            if r['base']>0 and final<=0:damaged+=1
            if r['base']<=0 and final>r['base']:improved_losses+=1
            if r['base']>0 and final>0 and final<r['base']:clipped_winners+=1
        vals.append({'ts':r['ts'],'base':r['base'],'final':final})
    b=summarize(vals,'base');z=summarize(vals,'final')
    z.update({'actions':actions,'rescued':rescued,'damaged':damaged,'improved_losses':improved_losses,
      'clipped_winners':clipped_winners,'delta':rnd(z['pnl']-b['pnl'],3),'reasons':reasons})
    return z

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};tsmap={x[0]:x for x in rows};funding,_,miss=load_funding();e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20)
    idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==5 and d.hour==18 and d.minute==0:idx.append(im[x[0]])
    recs=[parent_record(rows,i,funding,tsmap,e7,e20) for i in idx];recs=[r for r in recs if r]
    disc=recs[:83];val=recs[83:]
    base=summarize([{'ts':r['ts'],'base':r['base']} for r in recs],'base')
    allres=[]
    for name,_,_ in CLASSIFIERS:
        for lock in LOCKS:
            d=evaluate(rows,disc,name,lock,funding,tsmap)
            allres.append({'classifier':name,'lock':lock,'discovery':d})
    allres.sort(key=lambda x:(x['discovery']['delta'],x['discovery']['pf'] or 0,-x['discovery']['mdd'],-x['discovery']['damaged']),reverse=True)
    audit=[]
    for x in allres:
        y=dict(x);y['validation']=evaluate(rows,val,y['classifier'],y['lock'],funding,tsmap);y['full']=evaluate(rows,recs,y['classifier'],y['lock'],funding,tsmap);audit.append(y)
    selected=[]
    for name,_,_ in CLASSIFIERS:
        q=[x for x in audit if x['classifier']==name]
        q.sort(key=lambda x:(x['discovery']['delta'],x['discovery']['pf'] or 0,-x['discovery']['mdd']),reverse=True)
        selected.append(q[0])
    out={'status':'SATURDAY18_A79_FAST_GIVEBACK_PROTECTION','parent':base,'funding_missing':miss,
      'classifiers':CLASSIFIERS,'locks':LOCKS,'selected_by_discovery_only':selected,'all_configs':audit}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
