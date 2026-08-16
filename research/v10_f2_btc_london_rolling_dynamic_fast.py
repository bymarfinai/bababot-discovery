#!/usr/bin/env python3
"""V10-F2 — compute-optimized exact V10-F rolling BTC London dynamic direction audit.
Same frozen model/features/policy; indexed 5m access only changes runtime, not strategy.
"""
import json,bisect
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from statistics import mean
from zoneinfo import ZoneInfo
from research.v7_f_fib_120d_archive_audit import load_series

PAIR='BTCUSDT'; END=datetime.fromisoformat('2026-08-04T15:11:15.831175+00:00'); START=END-timedelta(days=971)
DATA_START=(START-timedelta(days=130)).replace(hour=0,minute=0,second=0,microsecond=0); DATA_END=(END+timedelta(days=2)).replace(hour=0,minute=0,second=0,microsecond=0)
LON=ZoneInfo('Europe/London'); LOOKBACK=120
FEATURES=['pre_ret_1h','pre_ret_4h','pre_ret_24h','day_pos','day_range_pct','dist_hod_pct','dist_lod_pct','dist_pdh_pct','dist_pdl_pct','rv_1h','rv_4h','open15_ret','open15_range_pct','open15_close_pos']
def dt(r):return datetime.fromtimestamp(int(r[2])/1000,tz=timezone.utc)
def O(r):return float(r[3])
def H(r):return float(r[4])
def L(r):return float(r[5])
def C(r):return float(r[6])
def pct(a,b):return 100*(b-a)/a if a else 0.0
def rv(rs):
    if len(rs)<2:return 0.0
    return mean(abs(pct(C(a),C(b))) for a,b in zip(rs[:-1],rs[1:]))
def lon_open(d):
    z=datetime(d.year,d.month,d.day,tzinfo=timezone.utc); out=[]
    for k in (-1,0,1):
        ld=(z+timedelta(days=k)).astimezone(LON).date(); u=datetime(ld.year,ld.month,ld.day,8,0,tzinfo=LON).astimezone(timezone.utc)
        if u.date()==d:out.append(u)
    return min(out) if out else None

def main():
    from sklearn.tree import DecisionTreeClassifier
    rows=load_series(PAIR,'5m',DATA_START,DATA_END); rows.sort(key=lambda r:int(r[2]))
    ts=[int(r[2]) for r in rows]; by_day=defaultdict(list)
    for r in rows:by_day[dt(r).date()].append(r)
    samples=[]
    for d in sorted(by_day):
        op=lon_open(d)
        if not op or not (START<=op<END):continue
        opms=int(op.timestamp()*1000); i=bisect.bisect_left(ts,opms)
        # exact open bar plus enough history/future
        if i<288 or i+15>=len(rows) or ts[i]!=opms:continue
        op15=rows[i:i+3]; decision_i=i+3; entry=C(op15[-1]); future=rows[decision_i:decision_i+12]
        if len(future)<12:continue
        # guard contiguous 5m slices
        if int(future[-1][2])-int(future[0][2])!=11*300000:continue
        exit60=C(future[-1]); pre1=rows[decision_i-12:decision_i]; pre4=rows[decision_i-48:decision_i]; pre24=rows[decision_i-288:decision_i]
        if any((int(b[2])-int(a[2])!=300000) for a,b in zip(pre24[:-1],pre24[1:])):continue
        daypre=[r for r in by_day[d] if int(r[2])<int((op+timedelta(minutes=15)).timestamp()*1000)]
        prev=by_day.get(d-timedelta(days=1),[])
        if not daypre or len(prev)<200:continue
        hod=max(H(r) for r in daypre); lod=min(L(r) for r in daypre); dr=hod-lod; pdh=max(H(r) for r in prev); pdl=min(L(r) for r in prev)
        oph=max(H(r) for r in op15); opl=min(L(r) for r in op15); opr=oph-opl
        x={'pre_ret_1h':pct(C(pre1[0]),entry),'pre_ret_4h':pct(C(pre4[0]),entry),'pre_ret_24h':pct(C(pre24[0]),entry),
           'day_pos':(entry-lod)/dr if dr else .5,'day_range_pct':100*dr/entry,'dist_hod_pct':100*(hod-entry)/entry,'dist_lod_pct':100*(entry-lod)/entry,
           'dist_pdh_pct':100*(pdh-entry)/entry,'dist_pdl_pct':100*(entry-pdl)/entry,'rv_1h':rv(pre1),'rv_4h':rv(pre4),
           'open15_ret':pct(O(op15[0]),entry),'open15_range_pct':100*opr/entry,'open15_close_pos':(entry-opl)/opr if opr else .5}
        y=1 if exit60>entry else 0 if exit60<entry else None
        if y is not None:samples.append({'date':str(d),'x':x,'y':y,'ret60':pct(entry,exit60)})
    preds=[]
    for i in range(LOOKBACK,len(samples)):
        tr=samples[i-LOOKBACK:i]; te=samples[i]; X=[[s['x'][f] for f in FEATURES] for s in tr]; y=[s['y'] for s in tr]
        clf=DecisionTreeClassifier(max_depth=3,min_samples_leaf=15,random_state=42).fit(X,y); leafs=clf.apply(X); leaf=int(clf.apply([[te['x'][f] for f in FEATURES]])[0])
        ids=[j for j,z in enumerate(leafs) if int(z)==leaf]; buys=sum(y[j]==1 for j in ids); sells=len(ids)-buys; maj=1 if buys>=sells else 0; purity=max(buys,sells)/len(ids); action=maj if purity>=.60 else -1
        preds.append({'action':action,'y':te['y'],'ret60':te['ret60']})
    traded=[p for p in preds if p['action']>=0]; wins=sum(p['action']==p['y'] for p in traded)
    blocks=[]
    for q in range(0,len(preds),120):
        b=preds[q:q+120]; bt=[p for p in b if p['action']>=0]; w=sum(p['action']==p['y'] for p in bt)
        blocks.append({'block':len(blocks)+1,'days':len(b),'trades':len(bt),'wins':w,'losses':len(bt)-w,'coverage_pct':round(100*len(bt)/len(b),2) if b else None,'wr_pct':round(100*w/len(bt),2) if bt else None})
    out={'phase':'V10-F2','status':'BTC_LONDON_ROLLING_DYNAMIC_FAST','definition':{'strategy_equivalent_to':'V10-F','lookback':120,'model':'DecisionTree depth3 leaf15 daily refit','leaf_gate':'purity>=60%','decision':'London +15m','target':'next60m','no_strategy_change':True},'coverage':{'samples':len(samples),'predictions':len(preds),'trades':len(traded)},'overall':{'wins':wins,'losses':len(traded)-wins,'wr_pct':round(100*wins/len(traded),2) if traded else None,'coverage_pct':round(100*len(traded)/len(preds),2) if preds else None,'mean_signed_ret_pct':round(mean(p['ret60'] if p['action']==1 else -p['ret60'] for p in traded),5) if traded else None},'blocks_120':blocks}
    print('V10_F2_RESULT',json.dumps(out,separators=(',',':')))
if __name__=='__main__':main()
