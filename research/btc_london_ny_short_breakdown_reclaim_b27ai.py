#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_london_ny_short_mirror_b27ad as ad

ROOT = Path(__file__).resolve().parent.parent
IN_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Trades.csv'
IN_SUMMARY = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Summary.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_BREAKDOWN_RECLAIM_B27AI_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_BREAKDOWN_RECLAIM_B27AI_Trades.csv'
OUT_SUMMARY = ROOT / 'BTC_LONDON_NY_SHORT_BREAKDOWN_RECLAIM_B27AI_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_BREAKDOWN_RECLAIM_B27AI_Status.txt'

PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
RULES = ('BLIND_F15','EARLY_REJECT','SAME_BAR_REJECTION')
NOTIONAL = 500.0
FEE = 0.40
BAR5 = pd.Timedelta(minutes=5)


def as_bool(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().eq('true')


def dt(df: pd.DataFrame, cols) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors='coerce')
    return df


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def fmt_num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def fmt_pct(x):
    if pd.isna(x): return '-'
    return f'{100*float(x):.1f}%'


def money(x):
    if pd.isna(x): return '-'
    return f'${float(x):+.2f}'


def load_frozen() -> tuple[pd.DataFrame,pd.DataFrame]:
    t = pd.read_csv(IN_TRADES)
    t = dt(t, ['signal_ts','entry_start','session_end','h2_bar_start'])
    t['entry_executed_b'] = as_bool(t.entry_executed)
    for c in ['fixed_net_pnl_usd','hybrid_net_pnl_usd','entry_px','L','H','range','F65','E20_DOWN']:
        t[c] = pd.to_numeric(t[c], errors='coerce')
    s = pd.read_csv(IN_SUMMARY)
    return t, s


def summarize_existing(g: pd.DataFrame) -> dict:
    e = g[g.entry_executed_b].copy()
    if not len(e):
        return {'trades':0,'fixed_wr':np.nan,'fixed_pf':np.nan,'fixed_exp':np.nan,'fixed_total':0.0,
                'hybrid_wr':np.nan,'hybrid_pf':np.nan,'hybrid_exp':np.nan,'hybrid_total':0.0}
    f = e.fixed_net_pnl_usd.astype(float)
    h = e.hybrid_net_pnl_usd.astype(float)
    return {'trades':len(e),'fixed_wr':float((f>0).mean()),'fixed_pf':pf(f),'fixed_exp':float(f.mean()),'fixed_total':float(f.sum()),
            'hybrid_wr':float((h>0).mean()),'hybrid_pf':pf(h),'hybrid_exp':float(h.mean()),'hybrid_total':float(h.sum())}


def assert_baseline_reproduction(t: pd.DataFrame, stored: pd.DataFrame) -> None:
    for rule in RULES:
        for part in (*PARTS,'POOLED_MAJOR'):
            g = t[(t.rule==rule) & (t.partition.isin(MAJOR) if part=='POOLED_MAJOR' else (t.partition==part))]
            calc = summarize_existing(g)
            z = stored[(stored.rule==rule) & (stored.partition==part)]
            if len(z)!=1:
                raise AssertionError(f'missing B27AD stored summary {rule} {part}')
            z=z.iloc[0]
            if int(calc['trades']) != int(z.trades):
                raise AssertionError(f'baseline trade count mismatch {rule} {part}')
            for k in ('fixed_total','hybrid_total','fixed_exp','hybrid_exp'):
                a=float(calc[k]); b=float(z[k])
                if not np.isclose(a,b,rtol=1e-10,atol=1e-8,equal_nan=True):
                    raise AssertionError(f'baseline {k} mismatch {rule} {part}: {a} vs {b}')


def time_exit(x5: pd.DataFrame, end: pd.Timestamp):
    p=int(x5.index.searchsorted(end,side='left'))
    if p>=len(x5) or x5.index[p] != end:
        raise AssertionError('missing session-end 5m open')
    return end,float(x5.iloc[p].open)


def simulate_reclaim(x5: pd.DataFrame, r: pd.Series) -> dict:
    if not bool(r.entry_executed_b):
        return {'b27ai_exit_reason':'NO_TRADE','b27ai_exit_px':np.nan,'b27ai_net_pnl_usd':np.nan,'b27ai_hold_minutes':np.nan,
                'breakdown_accepted':False,'acceptance_bar_start':pd.NaT,'e20_diag_reached':False,
                'preaccept_f65_invalid':False,'trough_px_in_trade':np.nan,'trough_extension_r':np.nan,
                'realized_exit_extension_r':np.nan,'capture_ratio':np.nan,'giveback_r':np.nan}

    entry_start=pd.Timestamp(r.entry_start); end=pd.Timestamp(r.session_end)
    entry=float(r.entry_px); L=float(r.L); R=float(r['range']); F65=float(r.F65); E20=float(r.E20_DOWN)
    if not (R>0 and entry>L):
        raise AssertionError('invalid frozen short geometry')
    q=ad.fast_slice(x5,entry_start,end)
    if q.empty or q.index[0] != entry_start:
        raise AssertionError('missing B27AI execution slice')

    accepted=False; acceptance_bar=pd.NaT; e20=False; preinvalid=False
    exit_ts=pd.NaT; exit_px=np.nan; reason=None
    trough=np.inf

    for ts,bar in q.iterrows():
        lo=float(bar.low); c=float(bar.close)
        if not accepted:
            # A deep wick/H2/E20 touch alone never activates the breakdown state.
            if lo <= E20:
                e20=True
            if c > F65:
                exit_ts=ts+BAR5; exit_px=c; reason='PRE_ACCEPT_CLOSE_INVALIDATION_F65'; preinvalid=True
                break
            if c < L:
                accepted=True; acceptance_bar=ts
                trough=min(trough,lo)
                continue
        else:
            trough=min(trough,lo)
            if lo <= E20:
                e20=True
            # Frozen structural failure: completed close has reclaimed London Low.
            if c >= L:
                exit_ts=ts+BAR5; exit_px=c; reason='BREAKDOWN_RECLAIM_L'
                break

    if reason is None:
        exit_ts,exit_px=time_exit(x5,end)
        reason='TIME_EXIT_SESSION_END'

    gross=1.0-float(exit_px)/entry
    net=gross*NOTIONAL-FEE
    hold=float((pd.Timestamp(exit_ts)-entry_start)/pd.Timedelta(minutes=1))

    trough_ext=np.nan; exit_ext=np.nan; cap=np.nan; give=np.nan
    if accepted and np.isfinite(trough):
        trough_ext=(L-float(trough))/R
        exit_ext=(L-float(exit_px))/R
        fav=max(0.0,L-float(trough))
        captured=max(0.0,L-float(exit_px))
        if fav>0:
            cap=captured/fav
        give=trough_ext-exit_ext

    return {'b27ai_exit_reason':reason,'b27ai_exit_px':float(exit_px),'b27ai_net_pnl_usd':net,'b27ai_hold_minutes':hold,
            'breakdown_accepted':bool(accepted),'acceptance_bar_start':acceptance_bar,'e20_diag_reached':bool(e20),
            'preaccept_f65_invalid':bool(preinvalid),'trough_px_in_trade':float(trough) if accepted and np.isfinite(trough) else np.nan,
            'trough_extension_r':trough_ext,'realized_exit_extension_r':exit_ext,'capture_ratio':cap,'giveback_r':give}


def synthetic_tests() -> None:
    idx=pd.date_range('2026-01-02 13:30',periods=8,freq='5min',tz='UTC')
    x=pd.DataFrame([
        {'open':91.0,'high':92.0,'low':90.5,'close':91.0},
        {'open':91.0,'high':91.2,'low':89.0,'close':89.5},  # accepted close<L
        {'open':89.5,'high':89.8,'low':87.5,'close':88.0},
        {'open':88.0,'high':90.4,'low':87.8,'close':90.1},  # reclaim exit
        {'open':90.1,'high':91.0,'low':89.9,'close':90.5},
        {'open':90.5,'high':91.0,'low':90.0,'close':90.6},
        {'open':90.6,'high':91.0,'low':90.2,'close':90.7},
        {'open':90.7,'high':91.0,'low':90.4,'close':90.8},
    ],index=idx)
    r=pd.Series({'entry_executed_b':True,'entry_start':idx[0],'session_end':idx[-1],
                 'entry_px':91.0,'L':90.0,'H':100.0,'range':10.0,'F65':96.5,'E20_DOWN':88.0})
    o=simulate_reclaim(x,r)
    assert o['breakdown_accepted'] and o['b27ai_exit_reason']=='BREAKDOWN_RECLAIM_L'
    assert abs(o['b27ai_exit_px']-90.1)<1e-12

    # E20 wick without close<L must NOT create acceptance; later F65 invalidates.
    y=x.copy(); y.loc[idx[1],['low','close']]=[87.5,90.5]; y.loc[idx[2],['high','close']]=[97.0,97.0]
    o=simulate_reclaim(y,r)
    assert not o['breakdown_accepted'] and o['e20_diag_reached'] and o['preaccept_f65_invalid']


def summarize_new(g: pd.DataFrame) -> dict:
    e=g[g.entry_executed_b].copy()
    if not len(e):
        return {'trades':0,'wr':np.nan,'pf':np.nan,'exp':np.nan,'total':0.0,'accept_rate':np.nan,'e20_rate':np.nan,
                'preinvalid':0,'reclaim_exits':0,'time_exits':0,'med_trough_ext':np.nan,'med_exit_ext':np.nan,'med_capture':np.nan,'med_giveback':np.nan}
    p=e.b27ai_net_pnl_usd.astype(float); acc=e[e.breakdown_accepted.astype(bool)]
    return {'trades':len(e),'wr':float((p>0).mean()),'pf':pf(p),'exp':float(p.mean()),'total':float(p.sum()),
            'accept_rate':float(e.breakdown_accepted.mean()),'e20_rate':float(e.e20_diag_reached.mean()),
            'preinvalid':int((e.b27ai_exit_reason=='PRE_ACCEPT_CLOSE_INVALIDATION_F65').sum()),
            'reclaim_exits':int((e.b27ai_exit_reason=='BREAKDOWN_RECLAIM_L').sum()),
            'time_exits':int((e.b27ai_exit_reason=='TIME_EXIT_SESSION_END').sum()),
            'med_trough_ext':float(acc.trough_extension_r.median()) if len(acc) else np.nan,
            'med_exit_ext':float(acc.realized_exit_extension_r.median()) if len(acc) else np.nan,
            'med_capture':float(acc.capture_ratio.median()) if len(acc) else np.nan,
            'med_giveback':float(acc.giveback_r.median()) if len(acc) else np.nan}


def main() -> None:
    synthetic_tests()
    t,stored=load_frozen()
    assert_baseline_reproduction(t,stored)
    x5,coverage=b21.load5()
    assert abs(float(coverage)-1.0)<1e-12

    outs=[simulate_reclaim(x5,r) for _,r in t.iterrows()]
    z=pd.concat([t.reset_index(drop=True),pd.DataFrame(outs)],axis=1)

    rows=[]
    for rule in RULES:
        for part in PARTS:
            g=z[(z.rule==rule)&(z.partition==part)]
            base=summarize_existing(g)
            rows.append({'rule':rule,'partition':part,**summarize_new(g),
                         'b27ad_fixed_total':base['fixed_total'],'b27ad_hybrid_total':base['hybrid_total']})
        g=z[(z.rule==rule)&z.partition.isin(MAJOR)]
        base=summarize_existing(g)
        rows.append({'rule':rule,'partition':'POOLED_MAJOR',**summarize_new(g),
                     'b27ad_fixed_total':base['fixed_total'],'b27ad_hybrid_total':base['hybrid_total']})
    sm=pd.DataFrame(rows)

    p=sm[(sm.rule=='EARLY_REJECT')&sm.partition.isin(MAJOR)].copy()
    pooled=sm[(sm.rule=='EARLY_REJECT')&(sm.partition=='POOLED_MAJOR')].iloc[0]
    supported=bool(len(p)==3 and (p['exp']>=0).all() and (p['pf']>=1.0).all() and
                   float(pooled['exp'])>0 and float(pooled['pf'])>=1.20 and
                   float(pooled['total'])>float(pooled['b27ad_fixed_total']) and
                   float(pooled['total'])>float(pooled['b27ad_hybrid_total']))
    status='B27AI_SUPPORTED' if supported else 'B27AI_NOT_SUPPORTED'

    z.to_csv(OUT_TRADES,index=False)
    sm.to_csv(OUT_SUMMARY,index=False)
    OUT_STATUS.write_text(status+'\n')

    lines=[]
    lines.append('# B27AI — BTC London -> New York SHORT Breakdown-Reclaim Exit — Result')
    lines.append('')
    lines.append(f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.')
    lines.append('')
    lines.append('**Audit status: PASS.** Frozen B27AD trade identities and fixed/hybrid economics reproduce before B27AI is interpreted. No 4H regime blocks a trade.')
    lines.append('')
    lines.append('## All-regime SHORT-specific exit')
    lines.append('')
    lines.append('| Rule | Partition | N | WR | PF | Exp | Total | Breakdown accepted | E20 diag | F65 invalid | L-reclaim exits | Time exits | B27AD fixed | B27AD hybrid |')
    lines.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for r in sm.itertuples(index=False):
        lines.append(f'| {r.rule} | {r.partition} | {int(r.trades)} | {fmt_pct(r.wr)} | {fmt_num(r.pf)} | {money(r.exp)} | {money(r.total)} | {fmt_pct(r.accept_rate)} | {fmt_pct(r.e20_rate)} | {int(r.preinvalid)} | {int(r.reclaim_exits)} | {int(r.time_exits)} | {money(r.b27ad_fixed_total)} | {money(r.b27ad_hybrid_total)} |')
    lines.append('')
    lines.append('## Accepted-breakdown path capture')
    lines.append('')
    lines.append('| Rule | Partition | Median trough below L | Median realized exit vs L | Median capture | Median giveback |')
    lines.append('|---|---|---:|---:|---:|---:|')
    for r in sm.itertuples(index=False):
        lines.append(f'| {r.rule} | {r.partition} | {fmt_num(r.med_trough_ext)}R | {fmt_num(r.med_exit_ext)}R | {fmt_pct(r.med_capture)} | {fmt_num(r.med_giveback)}R |')
    lines.append('')
    lines.append(f'**Overall: {status}.**')
    lines.append('')
    lines.append('B27AI does not tune F15/F65, add a regime gate, or use E20 as an exit. Reference-validation primary N remains only 22 trades and is a limitation.')
    lines.append('')
    lines.append('Research only; live BBC unchanged.')
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
