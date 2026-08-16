#!/usr/bin/env python3
"""V10-H2 exact-parity validation of V10-G HIGH_ACCEPT inverse candidate.
At London open freeze UTC-day H/L-so-far. Detect four event types exactly as V10-G;
earliest causal event wins. Trade ONLY when earliest event is HIGH_ACCEPT, but direction
is frozen SELL (inverse of failed continuation discovered in V10-G). 8x120d.
"""
import json
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from statistics import mean,median
from zoneinfo import ZoneInfo
from research.v7_f_fib_120d_archive_audit import load_series
PAIR='BTCUSDT'; START=datetime.fromisoformat('2023-12-18T15:11:15.831175+00:00'); END=START+timedelta(days=960)
DATA_START=(START-timedelta(days=2)).replace(hour=0,minute=0,second=0,microsecond=0); DATA_END=(END+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0); LON=ZoneInfo('Europe/London')
def dt(r):return datetime.fromtimestamp(int(r[2])/1000,tz=timezone.utc)
def H(r):return float(r[4])
def L(r):return float(r[5])
def C(r):return float(r[6])
def flow(r):
    q=float(r[9]); tq=float(r[12]); return tq/q if q>0 else .5
def lon_open(d):
    z=datetime(d.year,d.month,d.day,tzinfo=timezone.utc); a=[]
    for k in (-1,0,1):
        ld=(z+timedelta(days=k)).astimezone(LON).date(); u=datetime(ld.year,ld.month,ld.day,8,0,tzinfo=LON).astimezone(timezone.utc)
        if u.date()==d:a.append(u)
    return min(a) if a else None
def blk(t):return int((t-START).total_seconds()//(120*86400))+1 if START<=t<END else None
def stat(es):
    n=len(es); w=sum(e['win'] for e in es); return {'n':n,'wins':w,'losses':n-w,'wr_pct':round(100*w/n,2) if n else None,'mean_signed_ret_pct':round(mean(e['ret'] for e in es),5) if es else None,'median_signed_ret_pct':round(median(e['ret'] for e in es),5) if es else None}
def main():
    rows=load_series(PAIR,'5m',DATA_START,DATA_END); bd=defaultdict(list)
    for r in rows:bd[dt(r).date()].append(r)
    for d in bd:bd[d].sort(key=lambda r:int(r[2]))
    ev=[]
    for d,dr in sorted(bd.items()):
        op=lon_open(d); b=blk(op) if op else None
        if b is None:continue
        pre=[r for r in dr if dt(r)<op]
        if not pre:continue
        hsf=max(H(r) for r in pre); lsf=min(L(r) for r in pre); w=[r for r in dr if op<=dt(r)<op+timedelta(hours=2)]
        cand=[]; prev=None
        for r in w:
            t=dt(r); cc=C(r)
            if H(r)>hsf and cc<hsf:cand.append((t,'HIGH_REJECT',r))
            if L(r)<lsf and cc>lsf:cand.append((t,'LOW_REJECT',r))
            if prev is not None:
                if C(prev)>hsf and cc>hsf:cand.append((t,'HIGH_ACCEPT',r))
                if C(prev)<lsf and cc<lsf:cand.append((t,'LOW_ACCEPT',r))
            prev=r
        if not cand:continue
        t,typ,trig=sorted(cand,key=lambda z:z[0])[0]
        if typ!='HIGH_ACCEPT':continue
        after=[r for r in dr if dt(r)>t]
        if len(after)<12:continue
        entry=C(trig); exitpx=C(after[11]); sr=-100*(exitpx-entry)/entry
        ev.append({'block':b,'ret':sr,'win':sr>0,'aggressive':flow(trig)>.5})
    blocks=[]
    for b in range(1,9):
        x=[e for e in ev if e['block']==b]; blocks.append({'block':b,'all':stat(x),'aggressive_buyers':stat([e for e in x if e['aggressive']])})
    old=[e for e in ev if e['block']<=6]; rec=[e for e in ev if e['block']>=7]
    out={'phase':'V10-H2','status':'EXACT_FIRST_EVENT_HIGH_ACCEPT_TRAP','definition':{'parity':'exact V10-G earliest-event state selection','trade_only':'earliest event HIGH_ACCEPT','direction':'SELL','horizon':'60m','aggressive':'taker-buy quote share >50%','threshold_sweep':False},'blocks':blocks,'older6':{'all':stat(old),'aggressive_buyers':stat([e for e in old if e['aggressive']])},'recent2':{'all':stat(rec),'aggressive_buyers':stat([e for e in rec if e['aggressive']])},'overall8':{'all':stat(ev),'aggressive_buyers':stat([e for e in ev if e['aggressive']])}}
    print('V10_H2_RESULT',json.dumps(out,separators=(',',':')))
if __name__=='__main__':main()
