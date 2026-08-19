#!/usr/bin/env python3
"""BBC V4-A: causal post-close 15m EMA20 confirmation.

Research only. No exchange endpoints.

Frozen concept:
- Signal: completed 1H EMA7 reclaim/reject.
- BULL body ratio >= 0.5; BEAR body ratio >= 0.6.
- SIDEWAYS ignored.
- Baseline: enter at next 1H open.
- V4-A: after 1H signal completes, inspect ONLY the next hour's completed
  15m bars #1-#3 for legacy-style EMA20 confirmation; enter at the NEXT
  15m bar open. Confirmation on bar #4 is deliberately too late and expires.
- TP/SL 1.3%/1.3%; 0.15% modeled round-trip cost; one position per pair.
- Exits are managed on completed 15m OHLC; same-bar dual touch is conservative
  (SL first).
"""
from __future__ import annotations

import csv, io, json, sys, time, zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mode3 import compute_ema_series

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
WINDOWS = [90, 120, 971]
END = datetime(2026, 8, 19, 0, 0, tzinfo=timezone.utc)
WARMUP_DAYS = 60
COST = 0.0015
NOTIONAL = 500.0
TP = 0.013
SL = 0.013
BASE_MONTHLY = "https://data.binance.vision/data/futures/um/monthly/klines"
BASE_DAILY = "https://data.binance.vision/data/futures/um/daily/klines"
OUT_JSON = ROOT / "BTC_BBC_V4A_Causal_MTF_Confirmation.json"
OUT_MD = ROOT / "BTC_BBC_V4A_Causal_MTF_Confirmation.md"
S = requests.Session(); S.headers.update({"User-Agent":"bababot-v4a/1.0"})


def nts(x):
    v=int(x)
    while v>10**14: v//=1000
    return v


def parse(raw):
    z=zipfile.ZipFile(io.BytesIO(raw)); name=z.namelist()[0]; out=[]
    with z.open(name) as f:
        for r in csv.reader(io.TextIOWrapper(f,encoding='utf-8')):
            if len(r)<6: continue
            try: out.append((nts(r[0]),float(r[1]),float(r[2]),float(r[3]),float(r[4]),float(r[5])))
            except: continue
    return out


def get(url):
    err=None
    for n in range(4):
        try:
            r=S.get(url,timeout=45)
            if r.status_code==404: return None
            r.raise_for_status(); return r.content
        except Exception as e:
            err=e; time.sleep(1+n)
    raise RuntimeError(f"download failed {url}: {err}")


def nm(d): return date(d.year+(d.month==12),1 if d.month==12 else d.month+1,1)

def months(a,b):
    d=date(a.year,a.month,1)
    while d<b:
        yield d; d=nm(d)


def fetch(symbol,tf,start,end,minutes):
    rows=[]; sd=start.date(); ed=end.date()
    for m in months(sd,ed):
        ym=m.strftime('%Y-%m'); u=f"{BASE_MONTHLY}/{symbol}/{tf}/{symbol}-{tf}-{ym}.zip"; raw=get(u)
        if raw is not None:
            rows+=parse(raw); print(symbol,tf,ym,'monthly')
        else:
            d=max(m,sd); hi=min(nm(m),ed)
            while d<hi:
                ds=d.isoformat(); raw=get(f"{BASE_DAILY}/{symbol}/{tf}/{symbol}-{tf}-{ds}.zip")
                if raw is not None: rows+=parse(raw)
                d+=timedelta(days=1)
            print(symbol,tf,ym,'daily')
    lo=int(start.timestamp()*1000); hi=int(end.timestamp()*1000)
    dd={r[0]:r for r in rows if lo<=r[0]<hi}; out=[dd[k] for k in sorted(dd)]
    expected=max(1,int((end-start).total_seconds()//(minutes*60)))
    cov=len(out)/expected
    if cov<0.985: raise RuntimeError(f"{symbol} {tf} coverage {len(out)}/{expected}={cov:.3%}")
    return out


def br(r):
    span=r[2]-r[3]
    return abs(r[4]-r[1])/span if span>0 else 0


def signal(r,e):
    o,h,l,c=r[1],r[2],r[3],r[4]
    if l<=e and c>e and c>o and br(r)>=0.5: return 'LONG'
    if h>=e and c<e and c<o and br(r)>=0.6: return 'SHORT'
    return None


def confirm(r,e,side):
    o,h,l,c=r[1],r[2],r[3],r[4]
    if side=='LONG': return l<=e and c>e and c>o
    return h>=e and c<e and c<o


def close_trade(pos,price,ts,typ):
    raw=(price-pos['entry'])/pos['entry'] if pos['side']=='LONG' else (pos['entry']-price)/pos['entry']
    net=raw-COST
    return {**pos,'exit_time':ts,'exit_price':price,'exit_type':typ,'pnl_usd':net*NOTIONAL,'pnl_pct':net}


def manage(pos,r):
    h,l=r[2],r[3]
    if pos['side']=='LONG':
        if l<pos['sl']: return close_trade(pos,pos['sl'],r[0],'SL')
        if h>=pos['tp']: return close_trade(pos,pos['tp'],r[0],'TP')
    else:
        if h>pos['sl']: return close_trade(pos,pos['sl'],r[0],'SL')
        if l<=pos['tp']: return close_trade(pos,pos['tp'],r[0],'TP')
    return None


def open_pos(side,price,ts,signal_ts):
    if side=='LONG': sl=price*(1-SL); tp=price*(1+TP)
    else: sl=price*(1+SL); tp=price*(1-TP)
    return {'side':side,'entry':price,'sl':sl,'tp':tp,'entry_time':ts,'signal_time':signal_ts}


def prepare(rows1,rows15):
    ema1=compute_ema_series(np.array([r[4] for r in rows1],float),7)
    ema15=compute_ema_series(np.array([r[4] for r in rows15],float),20)
    i15={r[0]:i for i,r in enumerate(rows15)}
    byh={}
    for r in rows15: byh.setdefault(r[0]//3600000,[]).append(r)
    for k in byh: byh[k].sort(key=lambda x:x[0])
    return ema1,ema15,i15,byh


def run(rows1,rows15,mode):
    ema1,ema15,i15,byh=prepare(rows1,rows15)
    pos=None; trades=[]; armed=None; scheduled=None
    for i,r1 in enumerate(rows1):
        bars=byh.get(r1[0]//3600000,[])[:4]
        # This hour is the execution/confirmation hour for the signal armed at
        # the PREVIOUS 1H close.
        for j,b in enumerate(bars):
            if scheduled is not None and scheduled['ts']==b[0] and pos is None:
                pos=open_pos(scheduled['side'],b[1],b[0],scheduled['signal_time']); scheduled=None
            if pos is not None:
                done=manage(pos,b)
                if done is not None: trades.append(done); pos=None
            if mode=='mtf_confirm' and pos is None and scheduled is None and armed is not None and j<=2:
                ei=i15[b[0]]
                if confirm(b,ema15[ei],armed['side']):
                    # Entry must be at the following 15m open, never this close.
                    if j+1<len(bars): nxt=bars[j+1]
                    else: nxt=None
                    if nxt is not None:
                        scheduled={'ts':nxt[0],'side':armed['side'],'signal_time':armed['signal_time']}
                        armed=None
        # Any unconfirmed prior-hour setup expires at this completed 1H close.
        if mode=='mtf_confirm': armed=None

        # Generate a fresh signal only now, after the 1H candle is complete.
        sg=signal(r1,ema1[i])
        if pos is None and sg is not None:
            if mode=='next_1h_open':
                if i+1<len(rows1):
                    scheduled={'ts':rows1[i+1][0],'side':sg,'signal_time':r1[0]}
            else:
                armed={'side':sg,'signal_time':r1[0]}
    if pos is not None:
        last=rows15[-1]; trades.append(close_trade(pos,last[4],last[0],'END'))
    return trades


def stat(xs):
    xs=sorted(xs,key=lambda x:(x['exit_time'],x['entry_time']))
    n=len(xs); wins=[x['pnl_usd'] for x in xs if x['pnl_usd']>0]; losses=[x['pnl_usd'] for x in xs if x['pnl_usd']<=0]
    gp=sum(wins); gl=-sum(losses); pnl=gp-gl; eq=peak=dd=0; streak=ms=0
    for x in xs:
        eq+=x['pnl_usd']; peak=max(peak,eq); dd=max(dd,peak-eq)
        if x['pnl_usd']<=0: streak+=1; ms=max(ms,streak)
        else: streak=0
    return {'trades':n,'wins':len(wins),'losses':len(losses),'wr_pct':round(100*len(wins)/n,2) if n else None,'pnl_usd':round(pnl,2),'expectancy_usd':round(pnl/n,4) if n else None,'profit_factor':round(gp/gl,3) if gl else None,'max_drawdown_usd':round(dd,2),'max_loss_streak':ms}


def md(p):
    L=['# BBC V4-A — Causal Post-Close 15m Confirmation','', '**Research-only. No live files or orders are touched.**','',f"End-exclusive: `{p['end_exclusive_utc']}`",'', 'Signal: completed 1H EMA7 reclaim/reject. V4-A waits for EMA20 confirmation during the next hour and enters at the following 15m open. Confirmation on 15m #4 is not tradable and expires.','']
    for d in WINDOWS:
        w=p['windows'][str(d)]; L += [f'## {d} days','', '| Mode | Trades | WR | PnL | Exp/trade | PF | DD |','|---|---:|---:|---:|---:|---:|---:|']
        for m in ('next_1h_open','mtf_confirm'):
            s=w[m]['overall']; L.append(f"| {m} | {s['trades']} | {s['wr_pct'] if s['wr_pct'] is not None else '-'}% | ${s['pnl_usd']:+.2f} | ${s['expectancy_usd'] if s['expectancy_usd'] is not None else 0:+.4f} | {s['profit_factor'] if s['profit_factor'] is not None else '-'} | ${s['max_drawdown_usd']:.2f} |")
        z=w['mtf_delta']; L += ['',f"MTF delta: PnL **${z['pnl_usd']:+.2f}**, WR **{z['wr_pct']:+.2f} pp**, expectancy **${z['expectancy_usd']:+.4f}/trade**, trade count **{z['trades']:+d}**.",'','### MTF confirmation by pair','', '| Pair | Trades | WR | PnL | PF | DD |','|---|---:|---:|---:|---:|---:|']
        for q in PAIRS:
            s=w['mtf_confirm']['by_pair'][q]; L.append(f"| {q} | {s['trades']} | {s['wr_pct'] if s['wr_pct'] is not None else '-'}% | ${s['pnl_usd']:+.2f} | {s['profit_factor'] if s['profit_factor'] is not None else '-'} | ${s['max_drawdown_usd']:.2f} |")
        L.append('')
    L += ['## Decision rule','','No threshold sweep follows automatically. KEEP as a live-candidate research branch only if causal MTF materially improves economics and is not dependent on one pair or one recent window; otherwise REJECT this concept.','']
    return '\n'.join(L)


def main():
    data_start=END-timedelta(days=max(WINDOWS)+WARMUP_DAYS)
    D={}; meta={}
    for p in PAIRS:
        r1=fetch(p,'1h',data_start,END,60); r15=fetch(p,'15m',data_start,END,15); D[p]=(r1,r15)
        meta[p]={'bars_1h':len(r1),'bars_15m':len(r15),'first_utc':datetime.fromtimestamp(r1[0][0]/1000,timezone.utc).isoformat(),'last_1h_open_utc':datetime.fromtimestamp(r1[-1][0]/1000,timezone.utc).isoformat()}
    out={'phase':'BBC_V4A_CAUSAL_MTF','status':'RESEARCH_ONLY','generated_at_utc':datetime.now(timezone.utc).isoformat(),'end_exclusive_utc':END.isoformat(),'definition':{'signal':'completed_1h_ema7_reclaim_reject','baseline_entry':'next_1h_open','candidate':'next_hour_completed_15m_ema20_confirmation_bars_1_to_3_then_next_15m_open','tp_pct':TP,'sl_pct':SL,'cost_pct':COST,'sideways':False,'threshold_sweep':False},'data':meta,'windows':{}}
    for d in WINDOWS:
        start=END-timedelta(days=d); sm=int(start.timestamp()*1000); modes={m:[] for m in ('next_1h_open','mtf_confirm')}
        for p in PAIRS:
            r1,r15=D[p]; sim=start-timedelta(days=WARMUP_DAYS); simms=int(sim.timestamp()*1000)
            a=[x for x in r1 if simms<=x[0]<int(END.timestamp()*1000)]; b=[x for x in r15 if simms<=x[0]<int(END.timestamp()*1000)]
            for m in modes:
                tr=run(a,b,m)
                for x in tr:
                    if sm<=x['entry_time']<int(END.timestamp()*1000): modes[m].append({**x,'symbol':p})
        w={}
        for m,xs in modes.items():
            w[m]={'overall':stat(xs),'by_pair':{p:stat([x for x in xs if x['symbol']==p]) for p in PAIRS}}
            span=(END-start)/4; w[m]['by_block']={f'Q{j+1}':stat([x for x in xs if int((start+span*j).timestamp()*1000)<=x['entry_time']<int((start+span*(j+1)).timestamp()*1000)]) for j in range(4)}
        a=w['next_1h_open']['overall']; b=w['mtf_confirm']['overall']; w['mtf_delta']={'trades':b['trades']-a['trades'],'pnl_usd':round(b['pnl_usd']-a['pnl_usd'],2),'wr_pct':round((b['wr_pct'] or 0)-(a['wr_pct'] or 0),2),'expectancy_usd':round((b['expectancy_usd'] or 0)-(a['expectancy_usd'] or 0),4)}
        out['windows'][str(d)]=w
    OUT_JSON.write_text(json.dumps(out,indent=2)+'\n'); OUT_MD.write_text(md(out)); print(md(out))

if __name__=='__main__': main()
