"""BTC Friday15 A6.8 — frozen EMA7/EMA20 pullback robustness.

Frozen candidate from A6.7, no re-selection:
Friday 15:00 WIB BUY iff at the exact open, using EMAs through completed 5m bar i-1:
- open < EMA7
- open < EMA20
- EMA7 15m slope < 0
- EMA20 15m slope < 0

Fixed execution: TP2.0 / SL0.7 / 360m / 0.15% roundtrip / $500 notional.
Audit: years, 8 blocks, leave-one-trade-out, top-winner concentration, extra costs.
Research only, no live mutation.
"""
import json, datetime as dt
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a724_preentry_wrongway_atlas as a724
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

TP=2.0;SL=.7;HOLD=360
EXTRA=(0.00,0.02,0.05,0.10,0.15)

def rule(x):return x['d7']<0 and x['d20']<0 and x['s7_15']<0 and x['s20_15']<0

def bid(ts):return min(7,max(0,int((ts-EVAL_START)*8/(EVAL_END-EVAL_START))))

def stats(q,key='pnl'):
    p=[r[key] for r in q];n=len(p)
    if not p:return {'n':0}
    pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0);blocks=[rnd(sum(r[key] for r in q if bid(r['ts'])==b),3) for b in range(8)]
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),
      'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p),
      'positive_blocks':sum(x>0 for x in blocks),'blocks':blocks}

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);allr=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
        i=im[x[0]];px=a724.pre_features(rows,i,e7,e20);t=a60.trade(rows,i,TP,SL,HOLD)
        if px is not None and t is not None:allr.append({'i':i,'ts':x[0],'prex':px,'pnl':t['net_usd'],'reason':t['reason']})
    split=int(len(allr)*.60);sel=[r for r in allr if rule(r['prex'])];sd=[r for r in allr[:split] if rule(r['prex'])];sv=[r for r in allr[split:] if rule(r['prex'])]
    years={}
    for y in (2023,2024,2025,2026):
        q=[r for r in sel if dt.datetime.fromtimestamp(r['ts']/1000,dt.timezone.utc).year==y]
        if q:years[str(y)]=stats(q)
    # Leave-one-selected-trade-out: audit dependence on every selected occurrence.
    loo=[]
    for k,r in enumerate(sel):
        q=sel[:k]+sel[k+1:];s=stats(q)
        loo.append({'ts':r['ts'],'removed_pnl':rnd(r['pnl'],3),'n':s['n'],'wr':s['wr'],'pnl':s['pnl'],'pf':s['pf'],'mdd':s['mdd']})
    # Concentration: remove largest positive selected trades, not re-optimize anything.
    winners=sorted([r for r in sel if r['pnl']>0],key=lambda r:r['pnl'],reverse=True)
    concentration=[]
    for n in (1,3,5,10):
        gone={r['ts'] for r in winners[:n]};q=[r for r in sel if r['ts'] not in gone]
        concentration.append({'remove_top_winners':n,'removed_usd':rnd(sum(r['pnl'] for r in winners[:n]),3),'remaining':stats(q)})
    cost=[]
    for ex in EXTRA:
        usd=a60.NOTIONAL*ex/100.0;q=[dict(r,stressed=r['pnl']-usd) for r in sel]
        cost.append({'extra_cost_pct_notional':ex,'extra_usd_per_trade':rnd(usd,3),'stats':stats(q,'stressed')})
    out={'status':'FRIDAY15_A68_FROZEN_PULLBACK_ROBUSTNESS',
      'frozen_rule':'Friday15 BUY: open<EMA7 & open<EMA20 & EMA7_15m_slope<0 & EMA20_15m_slope<0; EMAs completed i-1',
      'execution':'TP2.0 / SL0.7 / hold360 / fee0.15 / notional500',
      'all_fridays':len(allr),'selected':len(sel),'coverage_pct':rnd(100*len(sel)/len(allr),2),
      'full':stats(sel),'discovery':stats(sd),'validation':stats(sv),'years':years,
      'exit_reasons':{'TP':sum(r['reason']=='TP' for r in sel),'SL':sum(r['reason'] in ('SL','AMB_SL') for r in sel),'TIMEOUT':sum(r['reason']=='TIMEOUT' for r in sel)},
      'leave_one_out':loo,'winner_concentration':concentration,'extra_cost':cost}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
