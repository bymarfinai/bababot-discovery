#!/usr/bin/env python3
"""V7-M — frozen regime-switch forensic for BNB SUPPLY FIB <38.2.

Research only. No live changes, no threshold/TP-SL sweep.

Candidate identity is frozen from V7-J/K/L:
  BNBUSDT + SUPPLY + FIB <38.2 + RR1 + confirm_bars=3.

Selection era for a regime gate: blocks 6-8 only (the observed ON era).
Historical holdout: blocks 1-5 only. Block 5 is the immediate OFF era.

To avoid threshold fishing, candidate regime gates are restricted to the exact
binary bucket definitions that already existed in V7-G *before* this BNB-specific
forensic. No new continuous thresholds are searched here.

Gate selection rule is frozen before run:
1) evaluate each predeclared V7-G binary bucket on blocks 6-8;
2) require selected n>=8, selected WR>=65%, selected-vs-rejected lift>=15pp;
3) require the bucket to be TRUE in at least 2 of blocks 6,7,8 with per-block n>=2;
4) among qualifying gates choose highest minimum eligible block WR, then highest n;
5) freeze that one gate and report its untouched blocks 1-5 holdout performance.

A gate is considered replicated only if historical holdout has n>=8, WR>=60%,
beats holdout rejected by >=10pp, and at least 3 holdout blocks with n>=1 have
WR>=50%. These replication thresholds are diagnostic and frozen pre-run.
"""
import json, os, sqlite3
from datetime import datetime, timedelta, timezone

import numpy as np

from research import v7_f_fib_120d_archive_audit as archive
from research import v7_g_fib_regime_forensic as g

PAIR="BNBUSDT"
SIDE="SUPPLY"
BAND="<38.2"
DAYS=971
BLOCK_DAYS=120
WINDOW_END=g.WINDOW_END
WINDOW_START=g.WINDOW_START
WARMUP_DAYS=10
DATA_START=WINDOW_START-timedelta(days=WARMUP_DAYS)
DB="/tmp/v7_m_bnb_regime.db"


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
    for p in g.PAIRS:
        coverage[p]={}
        for tf in ('1h','5m'):
            rows=archive.load_series(p,tf,DATA_START,WINDOW_END)
            conn.executemany('INSERT OR REPLACE INTO klines VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',rows)
            conn.commit()
            coverage[p][tf]={'rows':len(rows),
                'first':datetime.fromtimestamp(rows[0][2]/1000,tz=timezone.utc).isoformat() if rows else None,
                'last':datetime.fromtimestamp(rows[-1][2]/1000,tz=timezone.utc).isoformat() if rows else None}
    conn.close(); return coverage


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
    H=np.asarray([r[2] for r in rows],float); L=np.asarray([r[3] for r in rows],float); C=np.asarray([r[4] for r in rows],float)
    ATR=atr_func(H,L,C,14)
    atr_pct=np.asarray([(100.0*ATR[i]/C[i]) if C[i]>0 else 0.0 for i in range(len(C))],float)
    return {'T':T,'C':C,'ATR_PCT':atr_pct}


def attach_state(x, all_series, ms):
    dt=datetime.fromisoformat(x['confirm_time'])
    if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
    dt=dt.astimezone(timezone.utc)
    event_close_ms=int(dt.timestamp()*1000)+300_000
    oi=ms._latest_completed_index(all_series[PAIR]['T'],event_close_ms)
    own=ms._pair_state(all_series[PAIR],oi) if oi>=0 else None
    if not own: raise RuntimeError('missing BNB state '+dt.isoformat())
    trade_dir=-1  # SUPPLY / short direction
    row={
        't':dt,'win':1 if x['outcome']=='BOUNCE' else 0,
        'own_signed_ret4h_pct':100.0*own['ret4h']*trade_dir if own.get('ret4h') is not None else None,
        'own_signed_ret24h_pct':100.0*own['ret24h']*trade_dir if own.get('ret24h') is not None else None,
        'own_signed_ret7d_pct':100.0*own['ret7d']*trade_dir if own.get('ret7d') is not None else None,
        'own_atr1h_pct':own.get('atr1h_pct'),'own_atr_ratio_7d':own.get('atr_ratio_7d'),
        'own_rv24_vs_prior7d':own.get('rv24_vs_prior7d'),'own_trend_eff24h':own.get('trend_eff24h'),
        'own_trend_eff7d':own.get('trend_eff7d'),
    }
    row.update(ms._market_state(all_series,event_close_ms,trade_dir))
    delta=(dt-WINDOW_START).total_seconds()
    row['block']=int(delta//(BLOCK_DAYS*86400))+1 if delta>=0 else 0
    return row


def bucket_eval(rows,name):
    yes=[r for r in rows if g.state_bucket_flags(r)[name]]
    no=[r for r in rows if not g.state_bucket_flags(r)[name]]
    sy,sn=stat(yes),stat(no)
    lift=(sy['wr_pct'] or 0)-(sn['wr_pct'] or 0) if sy['n'] and sn['n'] else None
    by_block={}
    for b in sorted(set(r['block'] for r in rows)):
        xb=[r for r in rows if r['block']==b and g.state_bucket_flags(r)[name]]
        by_block[str(b)]=stat(xb)
    eligible=[v for v in by_block.values() if v['n']>=2]
    min_block_wr=min((v['wr_pct'] for v in eligible),default=None)
    qualifying_blocks=sum(1 for v in eligible if (v['wr_pct'] or 0)>=50.0)
    return {'selected':sy,'rejected':sn,'lift_pp':round(lift,2) if lift is not None else None,
            'by_block':by_block,'eligible_blocks_n_ge2':len(eligible),'eligible_blocks_wr_ge50':qualifying_blocks,
            'min_eligible_block_wr':min_block_wr}


def main():
    coverage=build_db(); os.environ['DB_PATH']=DB
    import v4_context_fib_forensic_endpoint as fib
    import v4_market_state_forensic_endpoint as ms
    from v4_structural_zone_endpoint import _atr
    fib._load=event_load
    all_series={p:state_series(p,_atr) for p in g.PAIRS}

    d=fib.context_fib_forensic(symbols=PAIR,days=DAYS,rr=1.0,confirm_bars=3,sample_limit=500)
    if d.get('errors'): raise RuntimeError(str(d['errors']))
    sample=d.get('sample') or []
    rows=[]
    for x in sample:
        if x.get('outcome') not in ('BOUNCE','BREAK') or x.get('fib_band')!=BAND or x.get('side')!=SIDE: continue
        rows.append(attach_state(x,all_series,ms))
    rows.sort(key=lambda r:r['t'])
    rows=[r for r in rows if 1<=r['block']<=8]

    selection=[r for r in rows if 6<=r['block']<=8]
    holdout=[r for r in rows if 1<=r['block']<=5]
    bucket_names=list(g.state_bucket_flags(selection[0]).keys()) if selection else []
    reports={name:bucket_eval(selection,name) for name in bucket_names}

    qualifiers=[]
    for name,rep in reports.items():
        s=rep['selected']; lift=rep['lift_pp']
        eligible_good=sum(1 for v in rep['by_block'].values() if v['n']>=2 and (v['wr_pct'] or 0)>=50.0)
        if s['n']>=8 and (s['wr_pct'] or 0)>=65.0 and lift is not None and lift>=15.0 and eligible_good>=2:
            qualifiers.append((name,rep))
    qualifiers.sort(key=lambda z:((z[1]['min_eligible_block_wr'] if z[1]['min_eligible_block_wr'] is not None else -1),z[1]['selected']['n']),reverse=True)
    chosen=qualifiers[0][0] if qualifiers else None

    holdout_report=None; replication=None
    if chosen:
        holdout_report=bucket_eval(holdout,chosen)
        hs=holdout_report['selected']; hr=holdout_report['rejected']; lift=holdout_report['lift_pp']
        block_good=sum(1 for v in holdout_report['by_block'].values() if v['n']>=1 and (v['wr_pct'] or 0)>=50.0)
        checks={
            'holdout_n_ge8':hs['n']>=8,
            'holdout_wr_ge60':(hs['wr_pct'] or 0)>=60.0,
            'holdout_beats_rejected_by_ge10pp':lift is not None and lift>=10.0,
            'at_least_3_holdout_blocks_wr_ge50':block_good>=3,
        }
        replication={'checks':checks,'passed':all(checks.values())}

    # Descriptive B5 vs B6-8 medians for the already-frozen V7-G feature list only.
    b5=[r for r in rows if r['block']==5]; on=[r for r in rows if 6<=r['block']<=8]
    continuous={}
    for f in g.FEATURES:
        def med(xs):
            vals=[]
            for r in xs:
                try:
                    v=float(r.get(f))
                    if np.isfinite(v): vals.append(v)
                except Exception: pass
            return float(np.median(vals)) if vals else None
        continuous[f]={'block5_off_median':med(b5),'blocks6_8_on_median':med(on)}

    result={
        'phase':'V7-M','status':'BNB_SUPPLY_FIB_REGIME_SWITCH_FORENSIC',
        'definition':{'pair':PAIR,'side':SIDE,'fib_band':BAND,'rr':1.0,'confirm_bars':3,
                      'selection_blocks':[6,7,8],'historical_holdout_blocks':[1,2,3,4,5],
                      'bucket_inventory':'exact pre-existing V7-G binary buckets','continuous_threshold_search':False,
                      'tp_sl_sweep':False,'live_changes':False,'warmup_days':WARMUP_DAYS},
        'coverage':coverage,'source_overall':d.get('overall'),'source_fib_bands':d.get('fib_bands'),
        'candidate_all8':stat(rows),'selection_era':stat(selection),'holdout_era':stat(holdout),
        'block5_off':stat(b5),'blocks6_8_on':stat(on),
        'selection_bucket_reports':reports,
        'qualifying_gates_ranked':[name for name,_ in qualifiers],
        'chosen_gate':chosen,'chosen_gate_holdout':holdout_report,'replication_gate':replication,
        'continuous_feature_medians_descriptive_only':continuous,
        'verdict':('PASS_REGIME_SWITCH_REPLICATION' if replication and replication['passed'] else
                   'FAIL_REGIME_SWITCH_REPLICATION' if chosen else 'NO_PREDECLARED_GATE_QUALIFIED'),
        'interpretation_lock':'No post-run replacement of the chosen gate is permitted. If chosen gate fails blocks 1-5, this regime-switch hypothesis is rejected in this form.'
    }
    print('V7_M_RESULT',json.dumps(result,separators=(',',':'),default=str))

if __name__=='__main__': main()
