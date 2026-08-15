#!/usr/bin/env python3
"""V7-I — independent pre-window holdout for frozen FIB 24h consensus rule.

Primary rule is unchanged from V7-H. No side-specific filter is added despite
V7-H's SUPPLY/DEMAND asymmetry; side split is diagnostic only.

Holdout window: the 971 days immediately BEFORE the V7-F/G/H window.
This data was outside the frozen 2023-12-18..2026-08-15 discovery/validation
window used to select the candidate.
"""
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import numpy as np

from research import v7_f_fib_120d_archive_audit as archive
from research import v7_g_fib_regime_forensic as g

PAIRS=g.PAIRS
DAYS=971
BLOCK_DAYS=120
BAND=g.BAND
WINDOW_END=g.WINDOW_START
WINDOW_START=WINDOW_END-timedelta(days=DAYS)
WARMUP_DAYS=10
DATA_START=WINDOW_START-timedelta(days=WARMUP_DAYS)
DB='/tmp/v7_i_fib_holdout.db'


def stat(rows):
    n=len(rows); w=sum(int(r['win']) for r in rows)
    return {'n':n,'wins':w,'losses':n-w,'wr_pct':round(100.0*w/n,2) if n else None}


def build_db():
    if os.path.exists(DB): os.unlink(DB)
    conn=sqlite3.connect(DB)
    conn.execute('''CREATE TABLE klines(
        symbol TEXT,timeframe TEXT,open_time INTEGER,
        open REAL,high REAL,low REAL,close REAL,volume REAL,
        close_time INTEGER,quote_volume REAL,trades INTEGER,
        taker_buy_volume REAL,taker_buy_quote_volume REAL,
        PRIMARY KEY(symbol,timeframe,open_time))''')
    coverage={}
    for p in PAIRS:
        coverage[p]={}
        for tf in ('1h','5m'):
            rows=archive.load_series(p,tf,DATA_START,WINDOW_END)
            conn.executemany('INSERT OR REPLACE INTO klines VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',rows)
            conn.commit()
            coverage[p][tf]={
                'rows':len(rows),
                'first':datetime.fromtimestamp(rows[0][2]/1000,tz=timezone.utc).isoformat() if rows else None,
                'last':datetime.fromtimestamp(rows[-1][2]/1000,tz=timezone.utc).isoformat() if rows else None,
            }
    conn.close(); coverage['_state_warmup_days']=WARMUP_DAYS
    return coverage


def event_load(symbol,timeframe,days):
    conn=sqlite3.connect(DB)
    try:
        return conn.execute('''SELECT open_time,open,high,low,close,volume
            FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<?
            ORDER BY open_time ASC''',
            (symbol,timeframe,int(WINDOW_START.timestamp()*1000),int(WINDOW_END.timestamp()*1000))).fetchall()
    finally: conn.close()


def state_series(symbol,atr_func):
    conn=sqlite3.connect(DB)
    try:
        rows=conn.execute('''SELECT open_time,open,high,low,close,volume
            FROM klines WHERE symbol=? AND timeframe='1h' AND open_time>=? AND open_time<?
            ORDER BY open_time ASC''',
            (symbol,int(DATA_START.timestamp()*1000),int(WINDOW_END.timestamp()*1000))).fetchall()
    finally: conn.close()
    T=[int(r[0]) for r in rows]
    H=np.asarray([r[2] for r in rows],dtype=float); L=np.asarray([r[3] for r in rows],dtype=float); C=np.asarray([r[4] for r in rows],dtype=float)
    ATR=atr_func(H,L,C,14)
    atr_pct=np.asarray([(100.0*ATR[i]/C[i]) if C[i]>0 else 0.0 for i in range(len(C))],dtype=float)
    return {'T':T,'C':C,'ATR_PCT':atr_pct}


def grouped(rows,key,vals):
    return {v:stat([r for r in rows if r.get(key)==v]) for v in vals}


def main():
    coverage=build_db(); os.environ['DB_PATH']=DB
    import v4_context_fib_forensic_endpoint as fib
    import v4_market_state_forensic_endpoint as ms
    from v4_structural_zone_endpoint import _atr

    fib._load=event_load
    all_series={p:state_series(p,_atr) for p in PAIRS}
    events=[]; source={}; errors={}
    for p in PAIRS:
        d=fib.context_fib_forensic(symbols=p,days=DAYS,rr=1.0,confirm_bars=3,sample_limit=500)
        source[p]={'overall':d.get('overall'),'fib_bands':d.get('fib_bands'),'errors':d.get('errors')}
        if d.get('errors'): errors[p]=d.get('errors')
        sample=d.get('sample') or []
        if int((d.get('overall') or {}).get('n',0) or 0)>len(sample): raise RuntimeError(f'sample truncated {p}')
        for x in sample:
            if x.get('fib_band')!=BAND or x.get('outcome') not in ('BOUNCE','BREAK'): continue
            dt=datetime.fromisoformat(x['confirm_time'])
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            dt=dt.astimezone(timezone.utc)
            event_close_ms=int(dt.timestamp()*1000)+300_000
            oi=ms._latest_completed_index(all_series[p]['T'],event_close_ms)
            own=ms._pair_state(all_series[p],oi) if oi>=0 else None
            if not own: raise RuntimeError(f'missing state {p} {dt.isoformat()}')
            trade_dir=1 if x.get('side')=='DEMAND' else -1
            market=ms._market_state(all_series,event_close_ms,trade_dir)
            own24=100.0*own['ret24h']*trade_dir if own.get('ret24h') is not None else None
            align24=market.get('market_alignment24h')
            delta=(dt-WINDOW_START).total_seconds(); block=int(delta//(BLOCK_DAYS*86400))+1 if delta>=0 else 0
            events.append({'pair':p,'side':x.get('side'),'t':dt,'block':block,'win':1 if x.get('outcome')=='BOUNCE' else 0,
                           'candidate':bool(own24 is not None and own24>0 and align24 is not None and align24>=0.75),
                           'own_signed_ret24h_pct':own24,'market_alignment24h':align24})
    events.sort(key=lambda r:r['t'])
    full=[r for r in events if 1<=r['block']<=8]; rem=[r for r in events if r['block']==9]
    sel=[r for r in full if r['candidate']]; rej=[r for r in full if not r['candidate']]
    blocks=[]
    for b in range(1,9):
        base=[r for r in full if r['block']==b]; ss=[r for r in base if r['candidate']]
        blocks.append({'block':b,'baseline':stat(base),'selected':stat(ss),'rejected':stat([r for r in base if not r['candidate']])})
    first=[r for r in sel if r['block']<=4]; second=[r for r in sel if r['block']>=5]
    pairs=grouped(sel,'pair',PAIRS); sides=grouped(sel,'side',['DEMAND','SUPPLY'])
    eligible_pairs=[s for s in pairs.values() if s['n']>=5]; eligible_sides=[s for s in sides.values() if s['n']>=5]
    lift=(stat(sel)['wr_pct'] or 0)-(stat(rej)['wr_pct'] or 0)
    checks={
        'candidate_n_ge25_and_wr_ge60':stat(sel)['n']>=25 and (stat(sel)['wr_pct'] or 0)>=60.0,
        'candidate_beats_rejected_by_ge10pp':lift>=10.0,
        'both_halves_n_ge8_and_wr_gt50':len(first)>=8 and len(second)>=8 and (stat(first)['wr_pct'] or 0)>50.0 and (stat(second)['wr_pct'] or 0)>50.0,
        'at_least_3_pairs_n_ge5_and_wr_gt50':sum(1 for s in eligible_pairs if (s['wr_pct'] or 0)>50.0)>=3,
        'both_sides_n_ge5_and_wr_gt50':len(eligible_sides)==2 and all((s['wr_pct'] or 0)>50.0 for s in eligible_sides),
    }
    result={
        'phase':'V7-I','status':'INDEPENDENT_PREWINDOW_HOLDOUT',
        'definition':{
            'primary_rule':'identical V7-H all-direction rule; no supply-only post-hoc filter',
            'window_start':WINDOW_START.isoformat(),'window_end':WINDOW_END.isoformat(),'history_days':DAYS,
            'fib_band':BAND,'rr':1.0,'confirm_bars':3,'own_24h_rule':'signed return > 0','market_24h_rule':'alignment >=0.75',
            'threshold_sweep':False,'side_filter':False,'tp_sl_sweep':False,'live_changes':False,
        },
        'coverage':coverage,'errors':errors,'baseline':stat(full),'candidate':stat(sel),'rejected':stat(rej),'wr_lift_pp':round(lift,2),
        'remainder_11d':{'baseline':stat(rem),'candidate':stat([r for r in rem if r['candidate']])},
        'chronological_halves':{'blocks_1_4':stat(first),'blocks_5_8':stat(second)},'blocks_120d':blocks,
        'by_pair':pairs,'by_side':sides,
        'replication_gate':{'checks':checks,'passed':all(checks.values())},
        'verdict':'PASS_INDEPENDENT_PREWINDOW_REPLICATION' if all(checks.values()) else 'FAIL_INDEPENDENT_PREWINDOW_REPLICATION',
        'source_pair_diagnostics':source,
    }
    print('V7_I_RESULT',json.dumps(result,separators=(',',':'),default=str))

if __name__=='__main__': main()
