#!/usr/bin/env python3
"""V10-H — frozen BTC London High-of-Day breakout trap, 8x120d.

Candidate discovered in V10-G latest 2x120d; this script does NOT reselect direction.
Frozen setup:
- London 08:00 local DST-aware.
- Freeze UTC-day HOD-so-far immediately before London open.
- Within first 2h, require two consecutive completed 5m closes ABOVE frozen HOD.
- Enter SELL at second close (breakout-fade / buyer-trap hypothesis).
- Directional outcome = close 60m later versus entry.
- Report all events and natural aggressive-buyer subset where trigger-bar taker-buy quote share >50%.
- 8 non-overlapping 120d blocks over same 960d core window.
No TP/SL, no threshold sweep, no fees/slippage, no live changes.
"""
import json
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from statistics import mean,median
from zoneinfo import ZoneInfo
from research.v7_f_fib_120d_archive_audit import load_series
PAIR='BTCUSDT'
START=datetime.fromisoformat('2023-12-18T15:11:15.831175+00:00')
END=START+timedelta(days=960)
DATA_START=(START-timedelta(days=2)).replace(hour=0,minute=0,second=0,microsecond=0)
DATA_END=(END+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
LON=ZoneInfo('Europe/London')
def dt(r):return datetime.fromtimestamp(int(r[2])/1000,tz=timezone.utc)
def H(r):return float(r[4])
def C(r):return float(r[6])
def flow(r):
    q=float(r[9]); tq=float(r[12]); return tq/q if q>0 else .5
def lon_open(d):
    z=datetime(d.year,d.month,d.day,tzinfo=timezone.utc); out=[]
    for k in (-1,0,1):
        ld=(z+timedelta(days=k)).astimezone(LON).date(); u=datetime(ld.year,ld.month,ld.day,8,0,tzinfo=LON).astimezone(timezone.utc)
        if u.date()==d:out.append(u)
    return min(out) if out else None
def block(t):
    if not (START<=t<END):return None
    return int((t-START).total_seconds()//(120*86400))+1
def stat(es):
    w=sum(e['win'] for e in es); n=len(es)
    return {'n':n,'wins':w,'losses':n-w,'wr_pct':round(100*w/n,2) if n else None,'mean_signed_ret_pct':round(mean(e['ret'] for e in es),5) if es else None,'median_signed_ret_pct':round(median(e['ret'] for e in es),5) if es else None}
def main():
    rows=load_series(PAIR,'5m',DATA_START,DATA_END); byday=defaultdict(list)
    for r in rows:byday[dt(r).date()].append(r)
    for d in byday:byday[d].sort(key=lambda r:int(r[2]))
    events=[]
    for d,dr in sorted(byday.items()):
        op=lon_open(d); b=block(op) if op else None
        if b is None:continue
        pre=[r for r in dr if dt(r)<op]
        if not pre:continue
        hod=max(H(r) for r in pre); w=[r for r in dr if op<=dt(r)<op+timedelta(hours=2)]
        trig=None
        for a,z in zip(w[:-1],w[1:]):
            if C(a)>hod and C(z)>hod:
                trig=z;break
        if trig is None:continue
        after=[r for r in dr if dt(r)>dt(trig)]
        if len(after)<12:continue
        entry=C(trig); exitpx=C(after[11]); raw=100*(exitpx-entry)/entry; sr=-raw
        events.append({'block':b,'ret':sr,'win':sr>0,'flow_buy_gt50':flow(trig)>.5})
    blocks=[]
    for b in range(1,9):
        x=[e for e in events if e['block']==b]; xf=[e for e in x if e['flow_buy_gt50']]
        blocks.append({'block':b,'start':(START+timedelta(days=120*(b-1))).isoformat(),'end':(START+timedelta(days=120*b)).isoformat(),'all':stat(x),'aggressive_buyers':stat(xf)})
    older=[e for e in events if e['block']<=6]; recent=[e for e in events if e['block']>=7]
    out={'phase':'V10-H','status':'BTC_LONDON_HOD_BREAKOUT_TRAP_8X120D','definition':{'setup':'two consecutive 5m closes above HOD frozen at London open','direction':'SELL at second close','horizon':'60m','aggressive_buyer_subset':'trigger taker-buy quote share >50%','candidate_selection':'frozen from V10-G blocks7-8; no reselection','threshold_sweep':False,'tp_sl':None,'live_changes':False},'blocks':blocks,'older6':{'all':stat(older),'aggressive_buyers':stat([e for e in older if e['flow_buy_gt50']])},'recent2':{'all':stat(recent),'aggressive_buyers':stat([e for e in recent if e['flow_buy_gt50']])},'overall8':{'all':stat(events),'aggressive_buyers':stat([e for e in events if e['flow_buy_gt50']])}}
    print('V10_H_RESULT',json.dumps(out,separators=(',',':')))
if __name__=='__main__':main()
