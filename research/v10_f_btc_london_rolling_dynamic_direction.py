#!/usr/bin/env python3
"""V10-F — Rolling adaptive BTC London direction engine.

Research only. Exact model family from V10-E, but retrained causally every day on the
previous 120 London sessions. This tests whether daily adaptation handles regime drift.

Frozen:
- BTCUSDT 5m
- London 08:00 local DST-aware; decision +15m
- same V10-E features
- DecisionTree max_depth=3, min_samples_leaf=15, random_state=42
- training leaf purity >=60% -> majority BUY/SELL, else NO TRADE
- rolling lookback exactly 120 prior sessions
- target next 60m direction
- no parameter sweep, no TP/SL, no fees/slippage, no live changes
"""
import json
from datetime import datetime,timedelta,timezone
from statistics import mean, median
from zoneinfo import ZoneInfo
from research.v7_f_fib_120d_archive_audit import load_series

PAIR='BTCUSDT'
END=datetime.fromisoformat('2026-08-04T15:11:15.831175+00:00')
START=END-timedelta(days=971)
DATA_START=(START-timedelta(days=130)).replace(hour=0,minute=0,second=0,microsecond=0)
DATA_END=(END+timedelta(days=2)).replace(hour=0,minute=0,second=0,microsecond=0)
LON=ZoneInfo('Europe/London')
LOOKBACK=120
FEATURES=['pre_ret_1h','pre_ret_4h','pre_ret_24h','day_pos','day_range_pct','dist_hod_pct','dist_lod_pct','dist_pdh_pct','dist_pdl_pct','rv_1h','rv_4h','open15_ret','open15_range_pct','open15_close_pos']

def dt(r): return datetime.fromtimestamp(int(r[2])/1000,tz=timezone.utc)
def O(r): return float(r[3])
def H(r): return float(r[4])
def L(r): return float(r[5])
def C(r): return float(r[6])
def pct(a,b): return 100*(b-a)/a if a else 0.0
def win(rows,a,b): return [r for r in rows if a<=dt(r)<b]
def rv(rs):
    if len(rs)<2:return 0.0
    vals=[]; p=C(rs[0])
    for r in rs[1:]:
        q=C(r); vals.append(abs(pct(p,q))); p=q
    return mean(vals) if vals else 0.0

def lon_open(d):
    z=datetime(d.year,d.month,d.day,tzinfo=timezone.utc); cc=[]
    for k in (-1,0,1):
        ld=(z+timedelta(days=k)).astimezone(LON).date()
        u=datetime(ld.year,ld.month,ld.day,8,0,tzinfo=LON).astimezone(timezone.utc)
        if u.date()==d:cc.append(u)
    return sorted(cc)[0] if cc else None

def sample(rows,d):
    op=lon_open(d)
    if not op:return None
    dec=op+timedelta(minutes=15)
    op15=win(rows,op,dec)
    fut=win(rows,dec,dec+timedelta(minutes=65))
    pre24=win(rows,dec-timedelta(hours=24),dec)
    if len(op15)<3 or len(fut)<12 or len(pre24)<250:return None
    entry=C(op15[-1]); exit60=C(fut[11])
    pre1=win(rows,dec-timedelta(hours=1),dec); pre4=win(rows,dec-timedelta(hours=4),dec)
    ds=datetime(op.year,op.month,op.day,tzinfo=timezone.utc); daypre=win(rows,ds,dec)
    if not daypre:return None
    prevd=d-timedelta(days=1); pr=[r for r in rows if dt(r).date()==prevd]
    if len(pr)<200:return None
    pdh=max(H(r) for r in pr); pdl=min(L(r) for r in pr)
    hod=max(H(r) for r in daypre); lod=min(L(r) for r in daypre); dr=hod-lod
    oph=max(H(r) for r in op15); opl=min(L(r) for r in op15); opr=oph-opl
    x={'pre_ret_1h':pct(C(pre1[0]),entry),'pre_ret_4h':pct(C(pre4[0]),entry),'pre_ret_24h':pct(C(pre24[0]),entry),
       'day_pos':(entry-lod)/dr if dr else .5,'day_range_pct':100*dr/entry,'dist_hod_pct':100*(hod-entry)/entry,'dist_lod_pct':100*(entry-lod)/entry,
       'dist_pdh_pct':100*(pdh-entry)/entry,'dist_pdl_pct':100*(entry-pdl)/entry,'rv_1h':rv(pre1),'rv_4h':rv(pre4),
       'open15_ret':pct(O(op15[0]),entry),'open15_range_pct':100*opr/entry,'open15_close_pos':(entry-opl)/opr if opr else .5}
    y=1 if exit60>entry else 0 if exit60<entry else None
    if y is None:return None
    return {'date':str(d),'time':dec,'x':x,'y':y,'ret60':pct(entry,exit60)}

def main():
    from sklearn.tree import DecisionTreeClassifier
    rows=load_series(PAIR,'5m',DATA_START,DATA_END)
    days=sorted(set(dt(r).date() for r in rows))
    ss=[]
    for d in days:
        s=sample(rows,d)
        if s and START<=s['time']<END:ss.append(s)
    preds=[]
    for i in range(LOOKBACK,len(ss)):
        tr=ss[i-LOOKBACK:i]; te=ss[i]
        X=[[z['x'][f] for f in FEATURES] for z in tr]; y=[z['y'] for z in tr]
        clf=DecisionTreeClassifier(max_depth=3,min_samples_leaf=15,random_state=42).fit(X,y)
        leafs=clf.apply(X); leaf=int(clf.apply([[te['x'][f] for f in FEATURES]])[0])
        idx=[j for j,z in enumerate(leafs) if int(z)==leaf]
        buys=sum(y[j]==1 for j in idx); sells=len(idx)-buys
        maj=1 if buys>=sells else 0; purity=max(buys,sells)/len(idx)
        action=maj if purity>=.60 else -1
        preds.append({'date':te['date'],'y':te['y'],'ret60':te['ret60'],'action':action,'purity':purity,'leaf_n':len(idx)})
    traded=[p for p in preds if p['action'] in (0,1)]
    wins=sum(p['action']==p['y'] for p in traded)
    # non-overlapping 120-session chunks of predictions, oldest anchored
    blocks=[]
    for k in range(0,len(preds),120):
        b=preds[k:k+120]; bt=[p for p in b if p['action'] in (0,1)]
        if not b:continue
        w=sum(p['action']==p['y'] for p in bt)
        blocks.append({'block':len(blocks)+1,'n_days':len(b),'trades':len(bt),'wins':w,'losses':len(bt)-w,'coverage_pct':round(100*len(bt)/len(b),2),'wr_pct':round(100*w/len(bt),2) if bt else None})
    out={'phase':'V10-F','status':'BTC_LONDON_ROLLING_DYNAMIC_DIRECTION','definition':{'lookback_sessions':LOOKBACK,'model':'same V10-E tree refit daily','decision':'London +15m','target':'next60m direction','leaf_gate':'purity>=60%','threshold_sweep':False,'tp_sl':None,'fees_slippage':'not applied','live_changes':False},
         'coverage':{'samples_in_window':len(ss),'walkforward_predictions':len(preds),'trades':len(traded)},
         'overall':{'trades':len(traded),'wins':wins,'losses':len(traded)-wins,'coverage_pct':round(100*len(traded)/len(preds),2) if preds else None,'wr_pct':round(100*wins/len(traded),2) if traded else None,'mean_signed_ret_pct':round(mean([(p['ret60'] if p['action']==1 else -p['ret60']) for p in traded]),5) if traded else None},
         'blocks_120_sessions':blocks}
    print('V10_F_RESULT',json.dumps(out,separators=(',',':')))
if __name__=='__main__':main()
