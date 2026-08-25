#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_f85_long_b27do_live_executable_exit_b27dq as dq
import btc_generic_f15_short_clock_scan_b27dr as dr

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_F85_LONG_F15_SHORT_COLLISION_B27DT_Result.md'
OUT_SUM = ROOT / 'BTC_F85_LONG_F15_SHORT_COLLISION_B27DT_Summary.csv'
OUT_DETAIL = ROOT / 'BTC_F85_LONG_F15_SHORT_COLLISION_B27DT_Detail.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_F15_SHORT_COLLISION_B27DT_Status.txt'

PARTS = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')
CLOCKS = {
    'SHORT_2000': 1200,
    'SHORT_0430': 270,
    'SHORT_0330': 210,
    'SHORT_0300': 180,
    'SHORT_2100': 1260,
    'SHORT_0000': 0,
}
SETS = {**{k: (v,) for k, v in CLOCKS.items()}, 'SHORT6_BASKET': tuple(CLOCKS.values())}


def pf(vals):
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def metrics(d):
    if d is None or len(d) == 0:
        return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0}
    v = pd.to_numeric(d.pnl, errors='coerce').dropna()
    return {'n':int(len(v)), 'wins':int((v>0).sum()),
            'wr':float((v>0).mean()) if len(v) else np.nan,
            'pf':pf(v), 'expectancy':float(v.mean()) if len(v) else np.nan,
            'net':float(v.sum())}


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'
def usd(x): return '-' if pd.isna(x) else f'${float(x):+.2f}'


def utc_ts(x):
    t = pd.Timestamp(x)
    return t.tz_localize('UTC') if t.tzinfo is None else t.tz_convert('UTC')


def build_hybrid_safe(stream, live):
    """B27DQ-equivalent hybrid construction with Pandas-3-safe tz assignment."""
    q = stream.copy().reset_index(drop=True)
    l = live.copy().reset_index(drop=True)
    if len(q) != len(l): raise AssertionError('B27DQ live attachment length mismatch')
    mask = q.zone.isin(dq.RUNNER_ZONES)
    # Preserve exact B27DQ values; only avoid numpy .values timezone stripping.
    q['exit_ts'] = q['exit_ts'].astype('object')
    q.loc[mask, 'exit_ts'] = [utc_ts(x) for x in l.loc[mask, 'live_exit_ts'].tolist()]
    q.loc[mask, 'exit_px'] = pd.to_numeric(l.loc[mask, 'live_exit_px'], errors='raise').to_numpy()
    q.loc[mask, 'net_pnl_usd'] = pd.to_numeric(l.loc[mask, 'live_net_pnl_usd'], errors='raise').to_numpy()
    q['exit_ts'] = pd.to_datetime(q['exit_ts'], utc=True)
    return q


def normalize_long(d, accepted_source=False):
    q = d.copy()
    q['entry_ts'] = pd.to_datetime(q.entry_bar_start, utc=True)
    q['exit_ts_norm'] = pd.to_datetime(q.exit_ts, utc=True)
    q['pnl'] = pd.to_numeric(q.net_pnl_usd, errors='coerce')
    q['side'] = 'LONG'; q['source'] = 'LONG_' + q.zone.astype(str); q['clock_min_norm'] = -1
    q['candidate_id'] = q.partition.astype(str)+'|LONG|'+q.zone.astype(str)+'|'+q.entry_ts.astype(str)
    if accepted_source and 'accepted' in q.columns: q = q[q.accepted.astype(bool)]
    return q[['partition','entry_ts','exit_ts_norm','pnl','side','source','clock_min_norm','candidate_id']].dropna().reset_index(drop=True)


def normalize_short(cases):
    q = cases[cases.entry_executed.astype(bool) & cases.fixed_net_pnl_usd.notna()].copy()
    q['entry_ts'] = pd.to_datetime(q.entry_start, utc=True)
    q['exit_ts_norm'] = q.entry_ts + pd.to_timedelta(pd.to_numeric(q.fixed_hold_minutes), unit='m')
    q['pnl'] = pd.to_numeric(q.fixed_net_pnl_usd, errors='coerce')
    q['side'] = 'SHORT'; rev = {v:k for k,v in CLOCKS.items()}; q['source'] = q.clock_min.map(rev)
    q['clock_min_norm'] = pd.to_numeric(q.clock_min).astype(int)
    q['candidate_id'] = q.partition.astype(str)+'|SHORT|'+q.clock_min.astype(str)+'|'+q.entry_ts.astype(str)
    return q[['partition','entry_ts','exit_ts_norm','pnl','side','source','clock_min_norm','candidate_id']].reset_index(drop=True)


def build_long(x5):
    stream = dq.dn.dl.load_stream(x5)
    live = dq.attach_live_runner(stream, x5)
    hybrid = build_hybrid_safe(stream, live)
    locked_parts = [dq.dn.dl.dg.lock(hybrid[hybrid.partition == p].copy(), f'B27DT_LONG_BASE_{p}') for p in PARTS]
    locked = pd.concat(locked_parts, ignore_index=True)
    pooled = locked[locked.partition.isin(MAJOR)].copy(); s = dq.summarize(pooled)
    if not (int(s['accepted']) == 227 and abs(float(s['wr'])-.722) <= .003 and
            abs(float(s['pf'])-2.25) <= .03 and abs(float(s['total_net'])-289.76) <= .20 and
            int(s['max_loss_streak']) == 3):
        raise AssertionError('B27DQ baseline parity failed: '+str(s))
    return hybrid, locked, s


def build_shorts(x5):
    anchors = pd.date_range(x5.index.min().normalize(), x5.index.max().normalize(), freq='D', tz='UTC')
    rows = []
    for a in anchors:
        for cm in sorted(set(CLOCKS.values())):
            r = dr.build_case(x5, a, cm)
            if r is not None: rows.append(r)
    if not rows: raise RuntimeError('no B27DT short cases')
    return pd.DataFrame(rows)


def overlap(a0,a1,b0,b1): return a0 < b1 and b0 < a1


def lock_rows(d, label):
    out=[]
    for part in PARTS:
        q=d[d.partition==part].copy()
        if q.empty: continue
        q['side_order']=q.side.map({'LONG':0,'SHORT':1}).fillna(9)
        q=q.sort_values(['entry_ts','side_order','clock_min_norm','candidate_id']).reset_index(drop=True)
        active_exit=pd.NaT; active_side=None; active_id=None
        for r in q.itertuples(index=False):
            accept = pd.isna(active_exit) or pd.Timestamp(r.entry_ts) >= pd.Timestamp(active_exit)
            z=r._asdict(); z['portfolio']=label; z['accepted_portfolio']=bool(accept)
            z['blocked_by_side']=None if accept else active_side; z['blocked_by_id']=None if accept else active_id
            out.append(z)
            if accept: active_exit=pd.Timestamp(r.exit_ts_norm); active_side=r.side; active_id=r.candidate_id
    return pd.DataFrame(out)


def long_protected(shorts, base_long, name):
    s=shorts.copy(); flags=[]
    for r in s.itertuples(index=False):
        hit=False
        for l in base_long[base_long.partition==r.partition].itertuples(index=False):
            if overlap(pd.Timestamp(r.entry_ts),pd.Timestamp(r.exit_ts_norm),pd.Timestamp(l.entry_ts),pd.Timestamp(l.exit_ts_norm)):
                hit=True; break
        flags.append(hit)
    s['blocked_by_long']=flags
    lock=lock_rows(s[~s.blocked_by_long].copy(), name+'_LONG_PROTECTED')
    acc=lock[lock.accepted_portfolio.astype(bool)].copy() if len(lock) else lock
    return acc, int(s.blocked_by_long.sum()), int((~lock.accepted_portfolio.astype(bool)).sum()) if len(lock) else 0, lock


def pooled(d): return d[d.partition.isin(MAJOR)].copy()


def summarize_set(name, clocks, short_all, raw_long, base_long, base_net):
    shorts=short_all[short_all.clock_min_norm.isin(clocks)].copy(); sm=metrics(pooled(shorts))
    lp_acc,b_long,b_short,lp_lock=long_protected(shorts,base_long,name); lpm=metrics(pooled(lp_acc))
    fs=lock_rows(pd.concat([raw_long,shorts],ignore_index=True),name+'_FIRST_SIGNAL')
    fs_acc=fs[fs.accepted_portfolio.astype(bool)].copy(); fm=metrics(pooled(fs_acc))
    fl=pooled(fs_acc[fs_acc.side=='LONG']); fsht=pooled(fs_acc[fs_acc.side=='SHORT']); flm=metrics(fl); fsm=metrics(fsht)
    base_ids=set(pooled(base_long).candidate_id); fs_ids=set(fl.candidate_id); displaced=pooled(base_long); displaced=displaced[displaced.candidate_id.isin(base_ids-fs_ids)]
    fsa=pooled(fs)
    sbL=int(((~fsa.accepted_portfolio.astype(bool))&(fsa.side=='SHORT')&(fsa.blocked_by_side=='LONG')).sum())
    lbS=int(((~fsa.accepted_portfolio.astype(bool))&(fsa.side=='LONG')&(fsa.blocked_by_side=='SHORT')).sum())
    if fm['net'] <= base_net + 1e-12: cls='PORTFOLIO_DEGRADES'
    elif len(displaced)==0 and flm['net'] >= base_net-1e-9: cls='FIRST_SIGNAL_ADDS_WITHOUT_LONG_DAMAGE'
    else: cls='FIRST_SIGNAL_ADDS_WITH_LONG_DISPLACEMENT'
    row={'set':name,'standalone_n':sm['n'],'standalone_wr':sm['wr'],'standalone_pf':sm['pf'],'standalone_net':sm['net'],
         'lp_blocked_by_long':b_long,'lp_blocked_by_short':b_short,'lp_short_n':lpm['n'],'lp_short_wr':lpm['wr'],'lp_short_pf':lpm['pf'],'lp_short_net':lpm['net'],
         'lp_combined_net':base_net+lpm['net'],'lp_delta_vs_long':lpm['net'],
         'fs_total_n':fm['n'],'fs_total_wr':fm['wr'],'fs_total_pf':fm['pf'],'fs_total_net':fm['net'],'fs_delta_vs_long':fm['net']-base_net,
         'fs_long_n':flm['n'],'fs_long_wr':flm['wr'],'fs_long_net':flm['net'],'fs_short_n':fsm['n'],'fs_short_wr':fsm['wr'],'fs_short_net':fsm['net'],
         'fs_displaced_baseline_long_n':len(displaced),'fs_displaced_baseline_long_net':float(displaced.pnl.sum()) if len(displaced) else 0.0,
         'fs_short_blocked_by_long':sbL,'fs_long_blocked_by_short':lbS,'classification':cls}
    details=[]
    if len(lp_lock): x=lp_lock.copy(); x['set']=name; x['scenario']='LONG_PROTECTED'; details.append(x)
    if len(fs): x=fs.copy(); x['set']=name; x['scenario']='FIRST_SIGNAL_WINS'; details.append(x)
    return row,details


def main():
    x5,coverage=dq.dn.dl.dj.b21.load5(); raw,locked,base=build_long(x5)
    rawL=normalize_long(raw); baseL=normalize_long(locked,accepted_source=True); base_net=float(base['total_net'])
    shorts=normalize_short(build_shorts(x5)); rows=[]; details=[]
    for name,clocks in SETS.items():
        r,d=summarize_set(name,clocks,shorts,rawL,baseL,base_net); rows.append(r); details.extend(d)
    s=pd.DataFrame(rows); det=pd.concat(details,ignore_index=True) if details else pd.DataFrame(); s.to_csv(OUT_SUM,index=False); det.to_csv(OUT_DETAIL,index=False)
    lines=['# B27DT — F85 LONG + F15 SHORT Collision / Portfolio Interference Audit — Result','',
           f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
           f'**B27DQ LONG parity: PASS.** Pooled-major N={int(base["accepted"])}, WR={pct(base["wr"])}, PF={num(base["pf"])}, net={usd(base["total_net"])}, max loss streak={int(base["max_loss_streak"])}.','',
           '## LONG_PROTECTED — incremental SHORT without displacing any B27DQ LONG','',
           '| Set | Standalone N | Standalone WR | PF | Standalone Net | Blocked by LONG | Blocked by SHORT | Added N | Added WR | Added PF | Added Net | Combined Net |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in s.itertuples(index=False): lines.append(f'| {r.set} | {r.standalone_n} | {pct(r.standalone_wr)} | {num(r.standalone_pf)} | {usd(r.standalone_net)} | {r.lp_blocked_by_long} | {r.lp_blocked_by_short} | {r.lp_short_n} | {pct(r.lp_short_wr)} | {num(r.lp_short_pf)} | {usd(r.lp_short_net)} | {usd(r.lp_combined_net)} |')
    lines += ['','## FIRST_SIGNAL_WINS — LONG and SHORT compete for one BTC slot','',
              '| Set | Total N | Total WR | PF | Combined Net | Delta | LONG N | LONG WR | LONG Net | SHORT N | SHORT WR | SHORT Net | Displaced LONG | SHORT blocked by LONG | LONG blocked by SHORT | Class |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in s.itertuples(index=False): lines.append(f'| {r.set} | {r.fs_total_n} | {pct(r.fs_total_wr)} | {num(r.fs_total_pf)} | {usd(r.fs_total_net)} | {usd(r.fs_delta_vs_long)} | {r.fs_long_n} | {pct(r.fs_long_wr)} | {usd(r.fs_long_net)} | {r.fs_short_n} | {pct(r.fs_short_wr)} | {usd(r.fs_short_net)} | {r.fs_displaced_baseline_long_n} | {r.fs_short_blocked_by_long} | {r.fs_long_blocked_by_short} | {r.classification} |')
    bl=s.sort_values(['lp_delta_vs_long','lp_short_pf'],ascending=[False,False]).iloc[0]; bf=s.sort_values(['fs_delta_vs_long','fs_total_pf'],ascending=[False,False]).iloc[0]
    lines += ['','## Mechanical readout','',f'Best LONG-protected incremental set: **{bl["set"]}**, adds {usd(bl["lp_short_net"])}; combined {usd(bl["lp_combined_net"])}.',f'Best FIRST_SIGNAL set: **{bf["set"]}**, delta {usd(bf["fs_delta_vs_long"])}; displaced baseline LONG={int(bf["fs_displaced_baseline_long_n"])}.','',
              'Guardrail: six SHORT clocks were selected after B27DR inspection; B27DT is exploratory historical portfolio-interference evidence, not pristine OOS validation.','','Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text('B27DT_COLLISION_AUDIT_COMPLETED\n'); print('\n'.join(lines))

if __name__=='__main__': main()
