"""Friday T-Method F5.8 — pre-pivot causal signature atlas.

Builds on F5.7 oracle labels but does NOT use the oracle pivot as a live rule.
At each 5m decision open from +15m to +180m while the parent is alive, compute
features available at that instant. Future diagnostic label:
GOOD_REVERSE = fixed SHORT 0.7/0.7/180m is profitable AND combined BUY-close +
SHORT improves frozen parent by >= $2.

Goals:
1) find causal features whose rank direction is stable discovery->validation,
2) measure what changes in the 15m immediately before each strong oracle pivot,
3) locate earliest future-good reversal windows for F5.9 sequential routing.

No live rule is selected here.
"""
import json, statistics, math
from collections import Counter
import btc_temporal_friday15_f57_reversal_pivot_atlas as F57
from btc_temporal_a34_5m_events import load, ldt, rnd, TF
from btc_temporal_friday15_a60_money_geometry import trade

FEATURES=('progress','mfe','mae','giveback','ret5','ret15','ret30','taker5','taker15','taker30',
          'range_ratio','volume_ratio','body_ratio','close_pos','red_frac15','red_frac30','lh3','ll3')


def mean(xs):return statistics.mean(xs) if xs else 0.0

def feat(rows,i,j):
    e=rows[i][1]; prev=rows[j-1]; q=rows[i:j]
    if not q:return None
    pre=rows[max(i-12,i):i]  # pre-entry local baseline; may be empty due slicing logic below
    pre=rows[max(0,i-12):i]
    pre_rng=statistics.median([x[2]-x[3] for x in pre]) if pre else max(prev[2]-prev[3],1e-9)
    pre_vol=statistics.median([x[6] for x in pre]) if pre else max(prev[6],1e-9)
    mfe=max(100*(x[2]-e)/e for x in q);mae=max(100*(e-x[3])/e for x in q)
    progress=100*(rows[j][1]-e)/e; peak=max(x[2] for x in q);giveback=100*(peak-rows[j][1])/e
    def ret(n):
        k=max(i,j-n//5);return 100*(rows[j][1]-rows[k][1])/rows[k][1]
    def taker(n):
        k=max(i,j-n//5);qq=rows[k:j];return mean([x[9]/x[6]-0.5 if x[6] else 0.0 for x in qq])
    def redfrac(n):
        k=max(i,j-n//5);qq=rows[k:j];return sum(x[4]<x[1] for x in qq)/len(qq) if qq else 0
    rng=(prev[2]-prev[3])/max(pre_rng,1e-9);vol=prev[6]/max(pre_vol,1e-9)
    body=abs(prev[4]-prev[1])/max(prev[2]-prev[3],1e-9);closepos=(prev[4]-prev[3])/max(prev[2]-prev[3],1e-9)
    last3=rows[max(i,j-3):j]
    lh3=1 if len(last3)>=3 and last3[-1][2]<last3[-2][2]<last3[-3][2] else 0
    ll3=1 if len(last3)>=3 and last3[-1][3]<last3[-2][3]<last3[-3][3] else 0
    return {'progress':progress,'mfe':mfe,'mae':mae,'giveback':giveback,
            'ret5':ret(5),'ret15':ret(15),'ret30':ret(30),'taker5':taker(5),'taker15':taker(15),'taker30':taker(30),
            'range_ratio':rng,'volume_ratio':vol,'body_ratio':body,'close_pos':closepos,
            'red_frac15':redfrac(15),'red_frac30':redfrac(30),'lh3':lh3,'ll3':ll3}


def auc(rows,key):
    pos=[r[key] for r in rows if r['good']];neg=[r[key] for r in rows if not r['good']]
    if not pos or not neg:return None
    wins=ties=0
    for a in pos:
        for b in neg:
            if a>b:wins+=1
            elif a==b:ties+=1
    return (wins+.5*ties)/(len(pos)*len(neg))


def stability(rows,split_ts):
    d=[r for r in rows if r['ts']<split_ts];v=[r for r in rows if r['ts']>=split_ts];out=[]
    for k in FEATURES:
        a=auc(d,k);b=auc(v,k)
        if a is None or b is None:continue
        same=(a-.5)*(b-.5)>=0
        out.append({'feature':k,'disc_auc':rnd(a,4),'val_auc':rnd(b,4),'same_direction':same,
                    'disc_strength':rnd(abs(a-.5),4),'val_strength':rnd(abs(b-.5),4),'min_strength':rnd(min(abs(a-.5),abs(b-.5)),4)})
    out.sort(key=lambda z:(z['same_direction'],z['min_strength']),reverse=True)
    return out


def main():
    rows=load(); idx=F57.indices(rows); entries=[]; events=[]
    for i in idx:
        p=trade(rows,i,F57.BUY_TP,F57.BUY_SL,F57.BUY_HOLD)
        if p is None:continue
        ev=[]
        for m in range(F57.START_MIN,F57.END_MIN+1,F57.STEP_MIN):
            j=i+m//5
            if j>=len(rows) or rows[j][0]!=rows[i][0]+(j-i)*TF:continue
            if not F57.parent_alive_before(rows,i,j):continue
            s=F57.short_trade(rows,j)
            if s is None:continue
            buy=F57.buy_close_pnl(rows[i][1],rows[j][1]);combined=buy+s['net_usd'];delta=combined-p['net_usd']
            z=feat(rows,i,j);z.update({'ts':rows[i][0],'m':m,'short':s['net_usd'],'combined':combined,'delta':delta,
                                       'good':bool(s['net_usd']>=1.0 and delta>=2.0)})
            ev.append(z);events.append(z)
        good=[z for z in ev if z['good']]
        best=max(ev,key=lambda z:z['combined']) if ev else None
        strong=bool(best and best['short']>=1.0 and best['delta']>=2.0)
        entries.append({'ts':rows[i][0],'ev':ev,'first_good':min([z['m'] for z in good],default=None),'best':best,'strong':strong})
    split=int(len(entries)*.60);split_ts=entries[split]['ts']
    stab=stability(events,split_ts)
    # First-good distribution is less oracle-extreme than best-pivot selection: earliest point at which fixed reverse would work.
    fg=[r['first_good'] for r in entries if r['first_good'] is not None]
    fgd=[r['first_good'] for r in entries[:split] if r['first_good'] is not None];fgv=[r['first_good'] for r in entries[split:] if r['first_good'] is not None]
    # Paired 15m-before -> best strong pivot changes.
    pairs=[]
    for r in entries:
        if not r['strong'] or not r['best'] or r['best']['m']<30:continue
        target=r['best'];prev=min(r['ev'],key=lambda z:abs(z['m']-(target['m']-15)))
        if abs(prev['m']-(target['m']-15))>5:continue
        pairs.append({k:target[k]-prev[k] for k in FEATURES})
    paired=[]
    for k in FEATURES:
        xs=[p[k] for p in pairs]
        if xs:
            paired.append({'feature':k,'median_change_15m':rnd(statistics.median(xs),4),'mean_change_15m':rnd(statistics.mean(xs),4),
                           'positive_share':rnd(sum(x>0 for x in xs)/len(xs),3)})
    paired.sort(key=lambda z:abs(z['median_change_15m']),reverse=True)
    # Conditional GOOD rates for natural sign states, descriptive only.
    signs={}
    for k in ('ret5','ret15','ret30','taker5','taker15','taker30','giveback','progress','lh3','ll3'):
        if k in ('giveback','progress','lh3','ll3'):
            cond=lambda r,kk=k:r[kk]>0
        else:cond=lambda r,kk=k:r[kk]<0
        q=[r for r in events if cond(r)]; signs[k]={'n':len(q),'good_rate':rnd(sum(r['good'] for r in q)/len(q),3) if q else None}
    out={'status':'FRIDAY_TMETHOD_F58_PREPIVOT_CAUSAL_SIGNATURE','data':{'entries':len(entries),'events':len(events),'discovery_entries':split,'validation_entries':len(entries)-split},
         'label':'GOOD_REVERSE = short_net>=1.0 and combined_delta>=2.0 using fixed F5.7 short geometry',
         'event_good_rate':rnd(sum(r['good'] for r in events)/len(events),3),
         'feature_stability':stab,
         'first_good':{'n':len(fg),'median':rnd(statistics.median(fg),2) if fg else None,'discovery_n':len(fgd),'discovery_median':rnd(statistics.median(fgd),2) if fgd else None,
                       'validation_n':len(fgv),'validation_median':rnd(statistics.median(fgv),2) if fgv else None,
                       'bins15':dict(sorted(Counter(F57.bucket_time(x) for x in fg).items()))},
         'paired_15m_before_to_strong_oracle':{'n':len(pairs),'changes':paired},'natural_sign_good_rates':signs,
         'notes':'Future labels only for forensics. F5.9 must select causal sequential rules on discovery and freeze into validation.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
