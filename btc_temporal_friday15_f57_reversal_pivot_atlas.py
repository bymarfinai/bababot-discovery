"""Friday T-Method F5.7 — oracle reversal-pivot atlas.

Purpose: diagnose whether Friday15 BUY occurrences contain an economically useful
BUY->SHORT state transition and where it tends to occur. This is ORACLE
forensics only. No pivot time from this script is deployable.

Frozen parent:
- Friday 15:00 WIB BUY
- TP2.0 / SL0.7 / hold6h
- $500 notional
- 0.15% round-trip fee

Diagnostic sequential SHORT geometry is intentionally fixed, not optimized:
- SHORT TP0.70 / SL0.70 / hold180m
- own 0.15% round-trip fee

At every causal 5m decision open from +15m through +180m, provided the parent BUY
is still alive immediately before the decision, compute:
1) close BUY at actual decision open,
2) optionally open the fixed SHORT,
3) combined PnL vs leaving the frozen parent alone.

The oracle selects the best historical pivot per occurrence only to create labels
for subsequent causal-signature research. It must never be used directly live.
"""
import json, statistics
from collections import Counter, defaultdict
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_friday15_a60_money_geometry import trade, FEE_PCT, NOTIONAL, max_dd, loss_streak

BUY_TP=2.0; BUY_SL=0.7; BUY_HOLD=360
SHORT_TP=0.7; SHORT_SL=0.7; SHORT_HOLD=180
START_MIN=15; END_MIN=180; STEP_MIN=5


def short_trade(rows,j,tp=SHORT_TP,sl=SHORT_SL,hold=SHORT_HOLD):
    e=rows[j][1]; tp_px=e*(1-tp/100); sl_px=e*(1+sl/100)
    end=min(len(rows),j+hold//5); ex=None; reason='TIMEOUT'
    for k in range(j,end):
        if rows[k][0] != rows[j][0]+(k-j)*TF: return None
        x=rows[k]; hit_tp=x[3]<=tp_px; hit_sl=x[2]>=sl_px
        if hit_tp and hit_sl: ex=sl_px; reason='SL_AMBIG'; break
        if hit_sl: ex=sl_px; reason='SL'; break
        if hit_tp: ex=tp_px; reason='TP'; break
    if ex is None:
        if end<=j:return None
        ex=rows[end-1][4]
    gross=100*(e-ex)/e
    return {'net_usd':NOTIONAL*(gross-FEE_PCT)/100,'gross_pct':gross,'reason':reason,'exit':ex}


def parent_alive_before(rows,i,decision_i):
    e=rows[i][1]; tp=e*(1+BUY_TP/100); sl=e*(1-BUY_SL/100)
    # Bars i..decision_i-1 are completed before decision open.
    for k in range(i,decision_i):
        if rows[k][0] != rows[i][0]+(k-i)*TF:return False
        x=rows[k]; hit_tp=x[2]>=tp; hit_sl=x[3]<=sl
        if hit_tp or hit_sl:return False
    return True


def buy_close_pnl(entry,exit_px):
    gross=100*(exit_px-entry)/entry
    return NOTIONAL*(gross-FEE_PCT)/100


def path_state(rows,i,j):
    e=rows[i][1]; q=rows[i:j]
    if not q:return None
    mfe=max(100*(x[2]-e)/e for x in q); mae=max(100*(e-x[3])/e for x in q)
    closes=[x[4] for x in q]
    progress=100*(rows[j][1]-e)/e
    peak=max(x[2] for x in q); giveback=100*(peak-rows[j][1])/e
    return {'mfe':mfe,'mae':mae,'progress':progress,'giveback':giveback}


def indices(rows):
    out=[]
    for i,x in enumerate(rows):
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==4 and dt.hour==15 and dt.minute==0:out.append(i)
    return out


def summarize(ps):
    if not ps:return {'n':0}
    pos=sum(x for x in ps if x>0); neg=-sum(x for x in ps if x<=0); w=sum(x>0 for x in ps)
    return {'n':len(ps),'wr':rnd(100*w/len(ps),2),'pnl':rnd(sum(ps),3),'exp':rnd(statistics.mean(ps),4),
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(max_dd(ps),3),'ls':loss_streak(ps)}


def bucket_time(m):
    return int(15*round(m/15))


def main():
    rows=load(); recs=[]
    for i in indices(rows):
        p=trade(rows,i,BUY_TP,BUY_SL,BUY_HOLD)
        if p is None:continue
        e=rows[i][1]; candidates=[]
        for m in range(START_MIN,END_MIN+1,STEP_MIN):
            j=i+m//5
            if j>=len(rows) or rows[j][0]!=rows[i][0]+(j-i)*TF:continue
            if not parent_alive_before(rows,i,j):continue
            st=path_state(rows,i,j)
            s=short_trade(rows,j)
            if s is None:continue
            buy=buy_close_pnl(e,rows[j][1]); combined=buy+s['net_usd']
            candidates.append({'m':m,'buy_close':buy,'short':s['net_usd'],'combined':combined,
                               'delta':combined-p['net_usd'],'short_reason':s['reason'],**st})
        if candidates:
            best=max(candidates,key=lambda z:z['combined'])
            best_exit=max(candidates,key=lambda z:z['buy_close'])
        else:
            best=best_exit=None
        qualifies=bool(best and best['delta']>0 and best['short']>0)
        strong=bool(best and best['delta']>=2.0 and best['short']>=1.0)
        recs.append({'ts':rows[i][0],'date':ldt(rows[i][0]).strftime('%Y-%m-%d'),'parent':p['net_usd'],
                     'parent_reason':p['reason'],'best':best,'best_exit':best_exit,'qualifies':qualifies,'strong':strong,
                     'candidates':candidates})

    parent=[r['parent'] for r in recs]
    qual=[r for r in recs if r['qualifies']]; strong=[r for r in recs if r['strong']]
    # Oracle portfolio diagnostic: replace parent only when oracle says profitable reversal.
    oracle=[r['best']['combined'] if r['qualifies'] else r['parent'] for r in recs]
    strong_oracle=[r['best']['combined'] if r['strong'] else r['parent'] for r in recs]
    bins=Counter(bucket_time(r['best']['m']) for r in qual)
    strong_bins=Counter(bucket_time(r['best']['m']) for r in strong)
    by_reason=defaultdict(lambda:{'n':0,'qual':0,'gain':0.0})
    for r in recs:
        z=by_reason[r['parent_reason']];z['n']+=1
        if r['qualifies']:z['qual']+=1;z['gain']+=r['best']['delta']
    # Pivot-state medians for subsequent causal signature design.
    fields=('m','mfe','mae','progress','giveback','short','delta')
    meds={k:rnd(statistics.median([r['best'][k] for r in qual]),4) if qual else None for k in fields}
    strong_meds={k:rnd(statistics.median([r['best'][k] for r in strong]),4) if strong else None for k in fields}
    # Top examples by oracle gain, capped to keep logs manageable.
    examples=[]
    for r in sorted(qual,key=lambda x:x['best']['delta'],reverse=True)[:25]:
        examples.append({'date':r['date'],'parent':rnd(r['parent'],3),'reason':r['parent_reason'],
                         **{k:rnd(r['best'][k],3) if isinstance(r['best'][k],float) else r['best'][k] for k in fields},
                         'short_reason':r['best']['short_reason']})
    split=int(len(recs)*.60)
    def subset(q):
        qq=[r for r in q if r['qualifies']]
        return {'entries':len(q),'qual_n':len(qq),'qual_share':rnd(len(qq)/len(q),3) if q else None,
                'oracle_gain':rnd(sum(r['best']['delta'] for r in qq),3),
                'pivot_med':rnd(statistics.median([r['best']['m'] for r in qq]),2) if qq else None}
    out={'status':'FRIDAY_TMETHOD_F57_REVERSAL_PIVOT_ATLAS','design':{
            'parent':'BUY TP2.0 SL0.7 hold360','short_diag':'SHORT TP0.7 SL0.7 hold180','pivot_scan_min':[START_MIN,END_MIN,STEP_MIN],
            'oracle_only':True},
         'data':{'entries':len(recs),'discovery':split,'validation':len(recs)-split},
         'parent':summarize(parent),'oracle_reversal_portfolio':summarize(oracle),'strong_oracle_portfolio':summarize(strong_oracle),
         'capacity':{'qualifying_reversals':len(qual),'share':rnd(len(qual)/len(recs),3),'strong_reversals':len(strong),
                     'total_oracle_gain':rnd(sum(r['best']['delta'] for r in qual),3),'median':meds,'strong_median':strong_meds,
                     'pivot_bins_15m':dict(sorted(bins.items())),'strong_pivot_bins_15m':dict(sorted(strong_bins.items()))},
         'chronology':{'discovery':subset(recs[:split]),'validation':subset(recs[split:])},
         'parent_reason_attribution':{k:{'n':v['n'],'qual':v['qual'],'qual_share':rnd(v['qual']/v['n'],3),'oracle_gain':rnd(v['gain'],3)} for k,v in by_reason.items()},
         'examples':examples,
         'notes':'Oracle atlas only. Pivot times and labels use future information and are not deployable.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
