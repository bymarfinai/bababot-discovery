"""BTC Friday15 A6.40 — pre-entry regime attribution.

Diagnostics only. No strategy changes, no threshold selection.
Compare pre-entry market state across:
- PRE_DD: before 2025-05-09
- DD: 2025-05-09 through 2026-01-30 inclusive
- POST: after 2026-01-30

All features use information available strictly before Friday 15:00 WIB entry:
6h/24h/7d returns, prior 24h realized vol/range, completed-1H EMA20/EMA50
structure and slopes, and pre-entry 09:00-15:00 move.
"""
import json, math, statistics
import btc_temporal_friday15_a636_maxdd_forensics as a636
from btc_temporal_a34_5m_events import ldt, rnd

DD_START='2025-05-09'; DD_END='2026-01-30'


def mean(x): return statistics.mean(x) if x else None

def med(x): return statistics.median(x) if x else None

def sd(x): return statistics.stdev(x) if len(x)>1 else 0.0

def pct(a,b): return 100.0*(a/b-1.0) if b else 0.0

def ema(vals, n):
    if not vals: return []
    alpha=2.0/(n+1.0); out=[vals[0]]
    for v in vals[1:]: out.append(alpha*v+(1-alpha)*out[-1])
    return out

def hourly_closes(rows,i,hours=240):
    # Entry is exactly at :00; completed 1H closes are i-1, i-13, ...
    out=[]
    for k in range(hours-1,-1,-1):
        j=i-1-12*k
        if j<0: continue
        out.append(rows[j][4])
    return out

def feature_row(rows,r):
    i=r['i']; e=r['entry']; prev=rows[i-1][4]
    def ret_bars(n):
        j=i-1-n
        return pct(prev, rows[j][4]) if j>=0 else None
    q24=rows[max(0,i-288):i]
    closes=[x[4] for x in q24]
    lr=[math.log(closes[k]/closes[k-1]) for k in range(1,len(closes)) if closes[k-1]>0 and closes[k]>0]
    rv24=100*statistics.stdev(lr)*math.sqrt(len(lr)) if len(lr)>1 else 0.0
    range24=100*(max(x[2] for x in q24)/min(x[3] for x in q24)-1) if q24 else 0.0
    # Friday 09:00 WIB open to 14:55 close = six hours fully known at 15:00.
    j9=i-72
    morning=pct(prev,rows[j9][1]) if j9>=0 else None
    hc=hourly_closes(rows,i,240)
    e20=ema(hc,20); e50=ema(hc,50)
    c=hc[-1]
    f={
      'ret6h':ret_bars(72),
      'ret24h':ret_bars(288),
      'ret7d':ret_bars(2016),
      'morning_09_15':morning,
      'rv24':rv24,
      'range24':range24,
      'h1_dist_ema20':pct(c,e20[-1]),
      'h1_dist_ema50':pct(c,e50[-1]),
      'h1_ema20_vs_50':pct(e20[-1],e50[-1]),
      'h1_ema20_slope4':pct(e20[-1],e20[-5]) if len(e20)>=5 else None,
      'h1_ema50_slope12':pct(e50[-1],e50[-13]) if len(e50)>=13 else None,
      'h1_bull_stack':1 if c>e20[-1]>e50[-1] else 0,
      'h1_bear_stack':1 if c<e20[-1]<e50[-1] else 0,
    }
    return f

def group(date):
    s=str(date)
    if s<DD_START:return 'PRE_DD'
    if s<=DD_END:return 'DD'
    return 'POST'

def stats(vals):
    vals=[x for x in vals if x is not None]
    return {'n':len(vals),'mean':rnd(mean(vals),4),'median':rnd(med(vals),4),'sd':rnd(sd(vals),4)}

def smd(a,b):
    a=[x for x in a if x is not None]; b=[x for x in b if x is not None]
    if len(a)<2 or len(b)<2:return None
    den=math.sqrt((statistics.variance(a)+statistics.variance(b))/2)
    return rnd((mean(a)-mean(b))/den,3) if den>0 else 0.0

def corr(x,y):
    q=[(a,b) for a,b in zip(x,y) if a is not None and b is not None]
    if len(q)<3:return None
    xa=[a for a,b in q]; ya=[b for a,b in q]; mx=mean(xa); my=mean(ya)
    num=sum((a-mx)*(b-my) for a,b in q)
    den=math.sqrt(sum((a-mx)**2 for a in xa)*sum((b-my)**2 for b in ya))
    return rnd(num/den,3) if den else 0.0

def main():
    rows,rec=a636.build()
    for r in rec:
        r['date']=str(ldt(r['ts']).date()); r['grp']=group(r['date']); r['feat']=feature_row(rows,r)
    names=list(rec[0]['feat'].keys())
    groups={g:[r for r in rec if r['grp']==g] for g in ('PRE_DD','DD','POST')}
    by_feature={}
    for n in names:
        pre=[r['feat'][n] for r in groups['PRE_DD']]; dd=[r['feat'][n] for r in groups['DD']]; post=[r['feat'][n] for r in groups['POST']]
        allv=[r['feat'][n] for r in rec]; pnl=[r['chosen'] for r in rec]
        by_feature[n]={
          'pre':stats(pre),'dd':stats(dd),'post':stats(post),
          'smd_dd_vs_pre':smd(dd,pre),'smd_dd_vs_post':smd(dd,post),
          'corr_feature_vs_managed_pnl':corr(allv,pnl)
        }
    # Outcome summary and simple signs, no thresholds selected.
    group_summary={}
    for g,q in groups.items():
        p=[r['chosen'] for r in q]
        group_summary[g]={
          'n':len(q),'wr':rnd(100*sum(x>0 for x in p)/len(p),2),'pnl':rnd(sum(p),3),'avg_pnl':rnd(mean(p),4),
          'bull_stack_rate':rnd(100*mean([r['feat']['h1_bull_stack'] for r in q]),2),
          'bear_stack_rate':rnd(100*mean([r['feat']['h1_bear_stack'] for r in q]),2)
        }
    # Rank numeric features by absolute DD-vs-PRE effect size, excluding binary stacks.
    numeric=[n for n in names if n not in ('h1_bull_stack','h1_bear_stack')]
    ranked=sorted([{'feature':n,**by_feature[n]} for n in numeric],key=lambda z:abs(z['smd_dd_vs_pre'] or 0),reverse=True)
    out={'status':'FRIDAY15_A640_PREENTRY_REGIME_ATTRIBUTION','group_summary':group_summary,
         'features':by_feature,'ranked_dd_vs_pre':ranked,
         'notes':'Diagnostics only. Effect sizes describe pre-entry state differences; no thresholds or trading rules selected.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
