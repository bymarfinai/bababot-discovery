#!/usr/bin/env python3
"""V10-G — BTC London causal extreme acceptance/rejection state machine.

Frozen mechanistic dynamic policy, research only:
- At London 08:00 local (DST-aware), freeze current UTC-day HIGH-so-far and LOW-so-far.
- Observe first 2h after London open on completed 5m candles.
- HIGH rejection: wick > frozen HSF and close < HSF -> SELL at that close.
- LOW rejection: wick < frozen LSF and close > LSF -> BUY.
- HIGH acceptance: two consecutive 5m closes > frozen HSF -> BUY at second close.
- LOW acceptance: two consecutive 5m closes < frozen LSF -> SELL at second close.
- Earliest causal trigger wins; one trade max/session day.
- Target = signed close-to-close return 60m after trigger.
- Also report natural taker-flow confirmation: taker-buy quote share >.5 for BUY, <.5 for SELL.
No threshold sweep, no TP/SL, no fees/slippage, no live changes.
"""
import json
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from statistics import mean, median
from zoneinfo import ZoneInfo
from research.v7_f_fib_120d_archive_audit import load_series
PAIR='BTCUSDT'
PREV_START=datetime.fromisoformat('2025-12-07T15:11:15.831175+00:00')
LATEST_START=datetime.fromisoformat('2026-04-06T15:11:15.831175+00:00')
LATEST_END=datetime.fromisoformat('2026-08-04T15:11:15.831175+00:00')
DATA_START=(PREV_START-timedelta(days=2)).replace(hour=0,minute=0,second=0,microsecond=0)
DATA_END=(LATEST_END+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
LON=ZoneInfo('Europe/London')
def dt(r):return datetime.fromtimestamp(int(r[2])/1000,tz=timezone.utc)
def H(r):return float(r[4])
def L(r):return float(r[5])
def C(r):return float(r[6])
def block(t):
    if PREV_START<=t<LATEST_START:return 'previous_120d'
    if LATEST_START<=t<LATEST_END:return 'latest_120d'
    return None
def lon_open(d):
    z=datetime(d.year,d.month,d.day,tzinfo=timezone.utc); out=[]
    for k in (-1,0,1):
        ld=(z+timedelta(days=k)).astimezone(LON).date(); u=datetime(ld.year,ld.month,ld.day,8,0,tzinfo=LON).astimezone(timezone.utc)
        if u.date()==d:out.append(u)
    return min(out) if out else None
def signed(entry,exitpx,direction):
    r=100*(exitpx-entry)/entry
    return r if direction=='BUY' else -r
def flow_share(r):
    q=float(r[9]); tq=float(r[12])
    return tq/q if q>0 else .5
def summary(ev):
    n=len(ev); wins=sum(e['ret60']>0 for e in ev); losses=sum(e['ret60']<0 for e in ev); res=wins+losses
    return {'n':n,'resolved':res,'wins':wins,'losses':losses,'wr_pct':round(100*wins/res,2) if res else None,'mean_signed_ret_pct':round(mean(e['ret60'] for e in ev),5) if ev else None,'median_signed_ret_pct':round(median(e['ret60'] for e in ev),5) if ev else None}
def main():
    rows=load_series(PAIR,'5m',DATA_START,DATA_END); byday=defaultdict(list)
    for r in rows:byday[dt(r).date()].append(r)
    for d in byday:byday[d].sort(key=lambda r:int(r[2]))
    events=[]; session_days={'previous_120d':0,'latest_120d':0}
    for d,dr in sorted(byday.items()):
        op=lon_open(d); b=block(op) if op else None
        if not b:continue
        session_days[b]+=1
        pre=[r for r in dr if dt(r)<op]
        if not pre:continue
        hsf=max(H(r) for r in pre); lsf=min(L(r) for r in pre)
        w=[r for r in dr if op<=dt(r)<op+timedelta(hours=2)]
        candidates=[]
        prev=None
        for r in w:
            t=dt(r); close=C(r)
            # immediate rejection events
            if H(r)>hsf and close<hsf:candidates.append((t,'HIGH_REJECT','SELL',r))
            if L(r)<lsf and close>lsf:candidates.append((t,'LOW_REJECT','BUY',r))
            # two-close acceptance events, completed bars only
            if prev is not None:
                if C(prev)>hsf and close>hsf:candidates.append((t,'HIGH_ACCEPT','BUY',r))
                if C(prev)<lsf and close<lsf:candidates.append((t,'LOW_ACCEPT','SELL',r))
            prev=r
        if not candidates:continue
        t,typ,direction,trig=sorted(candidates,key=lambda z:z[0])[0]
        after=[r for r in dr if dt(r)>t]
        if len(after)<12:continue
        exitpx=C(after[11]); r60=signed(C(trig),exitpx,direction); fs=flow_share(trig)
        flowok=(fs>.5) if direction=='BUY' else (fs<.5)
        events.append({'date':str(d),'block':b,'type':typ,'direction':direction,'ret60':r60,'flow_share':fs,'flow_confirm':flowok})
    types=['HIGH_REJECT','LOW_REJECT','HIGH_ACCEPT','LOW_ACCEPT']
    out_types={}
    for typ in types:
        out_types[typ]={}
        for b in ('previous_120d','latest_120d'):
            x=[e for e in events if e['type']==typ and e['block']==b]; out_types[typ][b]=summary(x); out_types[typ][b]['flow_confirmed']=summary([e for e in x if e['flow_confirm']])
        x=[e for e in events if e['type']==typ]; out_types[typ]['combined']=summary(x); out_types[typ]['combined']['flow_confirmed']=summary([e for e in x if e['flow_confirm']])
    policy={}
    for b in ('previous_120d','latest_120d'):
        x=[e for e in events if e['block']==b]; policy[b]=summary(x); policy[b]['session_days']=session_days[b]; policy[b]['coverage_pct']=round(100*len(x)/session_days[b],2) if session_days[b] else None; policy[b]['flow_confirmed']=summary([e for e in x if e['flow_confirm']])
    policy['combined']=summary(events); policy['combined']['flow_confirmed']=summary([e for e in events if e['flow_confirm']])
    out={'phase':'V10-G','status':'BTC_LONDON_EXTREME_ACCEPT_REJECT_STATE','definition':{'levels':'UTC-day H/L frozen at London open','window':'first2h','rejection':'wick through + same 5m close back inside','acceptance':'two consecutive closes outside','direction':'reject=>reverse; accept=>continue','one_trade':'earliest trigger','target':'next60m close direction','flow_confirm':'taker buy quote share >50% BUY / <50% SELL','threshold_sweep':False,'tp_sl':None,'live_changes':False},'policy':policy,'by_event':out_types}
    print('V10_G_RESULT',json.dumps(out,separators=(',',':')))
if __name__=='__main__':main()
