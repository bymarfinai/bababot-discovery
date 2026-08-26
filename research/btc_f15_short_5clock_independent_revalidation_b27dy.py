#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bbc_f85_f15_signals as sig
import btc_f85_long_f15_short_collision_b27dt as dt
import btc_f15_short_2000_walkforward_portfolio_b27du as du
import btc_generic_f15_short_clock_scan_b27dr as dr

PFX = 'BTC_F15_SHORT_5CLOCK_INDEPENDENT_REVALIDATION_B27DY'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_WIN = ROOT / f'{PFX}_WindowSummary.csv'
OUT_YEAR = ROOT / f'{PFX}_YearSummary.csv'
OUT_SLIP = ROOT / f'{PFX}_Slippage.csv'
OUT_RAW = ROOT / f'{PFX}_RawParity.csv'
OUT_MIS = ROOT / f'{PFX}_RawMismatches.csv'
OUT_BASKET = ROOT / f'{PFX}_SurvivorBasket.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

CANDIDATES = {
    'SHORT_0000': 0,
    'SHORT_0300': 180,
    'SHORT_0330': 210,
    'SHORT_0430': 270,
    'SHORT_2100': 1260,
}
SHORT20 = 1200
WINDOWS = du.WINDOWS
MAJOR = dt.MAJOR
SLIPPAGE_BPS = (0, 2, 5, 10)


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def usd(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def close_num(a, b, tol=1e-10):
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    return abs(float(a)-float(b)) <= tol * max(1.0, abs(float(b)))


def fslice(x, start, end):
    a = int(x.index.searchsorted(start, side='left'))
    b = int(x.index.searchsorted(end, side='left'))
    return x.iloc[a:b]


def raw_replay_all(x5):
    rows = []
    sessions = 0
    anchors = pd.date_range(x5.index.min().normalize(), x5.index.max().normalize(), freq='D', tz='UTC')
    for anchor in anchors:
        for name, cm in CANDIDATES.items():
            rs = anchor + pd.Timedelta(minutes=cm)
            re = rs + sig.REF_DUR
            es = re
            ee = es + sig.EXEC_DUR
            part = dr.part_for_window(rs, es, ee)
            if part is None or es.weekday() >= 5:
                continue
            ref = fslice(x5, rs, re)
            exe = fslice(x5, es, ee)
            if len(ref) != sig.REF_BARS or len(exe) != sig.EXEC_BARS:
                continue
            adapter = sig.ShortF15Session(anchor, ref)
            adapter.source = name
            sessions += 1
            for s in sig.replay_session(adapter, exe):
                rows.append({
                    'clock': name,
                    'clock_min': cm,
                    'partition': part,
                    'entry_ts': pd.Timestamp(s.entry_ts),
                    'entry_px': float(s.entry_px),
                    'confirmation_bar_start': pd.Timestamp(s.confirmation_bar_start),
                    'H': float(s.H), 'L': float(s.L), 'range': float(s.R),
                    'F15': float(s.entry_level), 'F65': float(s.stop_level),
                    'E20_DOWN': float(s.target_level),
                    'touch_elapsed_min': float(s.touch_elapsed_min),
                })
    out = pd.DataFrame(rows)
    if len(out):
        out['entry_ts'] = pd.to_datetime(out.entry_ts, utc=True)
        out['confirmation_bar_start'] = pd.to_datetime(out.confirmation_bar_start, utc=True)
        out['candidate_id'] = (out.partition.astype(str)+'|SHORT|'+out.clock_min.astype(str)+'|'+out.entry_ts.astype(str))
    return out, sessions


def canonical_raw_rows(short_cases, name, cm):
    q = short_cases[(pd.to_numeric(short_cases.clock_min) == cm) &
                    short_cases.entry_executed.astype(bool) &
                    short_cases.fixed_net_pnl_usd.notna()].copy()
    if q.empty:
        return pd.DataFrame(columns=['clock','clock_min','partition','entry_ts','entry_px','confirmation_bar_start','H','L','range','F15','F65','E20_DOWN','touch_elapsed_min','candidate_id'])
    out = pd.DataFrame({
        'clock': name,
        'clock_min': cm,
        'partition': q.partition.astype(str),
        'entry_ts': pd.to_datetime(q.entry_start, utc=True),
        'entry_px': pd.to_numeric(q.entry_px, errors='raise'),
        'confirmation_bar_start': pd.to_datetime(q.confirmation_bar_start, utc=True),
        'H': pd.to_numeric(q.H, errors='raise'),
        'L': pd.to_numeric(q.L, errors='raise'),
        'range': pd.to_numeric(q['range'], errors='raise'),
        'F15': pd.to_numeric(q.F15, errors='raise'),
        'F65': pd.to_numeric(q.F65, errors='raise'),
        'E20_DOWN': pd.to_numeric(q.E20_DOWN, errors='raise'),
        'touch_elapsed_min': (pd.to_datetime(q.blind_touch_bar_start, utc=True)-pd.to_datetime(q.execution_start, utc=True))/pd.Timedelta(minutes=1),
    })
    out['candidate_id'] = out.partition.astype(str)+'|SHORT|'+str(cm)+'|'+out.entry_ts.astype(str)
    return out


def compare_raw(name, cm, generated_all, canonical, mismatch_rows):
    g = generated_all[generated_all.clock_min == cm].copy().sort_values(['entry_ts','candidate_id']).reset_index(drop=True)
    e = canonical.copy().sort_values(['entry_ts','candidate_id']).reset_index(drop=True)
    gid = g.candidate_id.astype(str).tolist()
    eid = e.candidate_id.astype(str).tolist()
    gm = g.set_index('candidate_id') if len(g) else pd.DataFrame()
    em = e.set_index('candidate_id') if len(e) else pd.DataFrame()
    common = sorted(set(gid) & set(eid))
    missing = sorted(set(eid) - set(gid))
    extra = sorted(set(gid) - set(eid))
    geometry = 0
    fields = ('entry_px','H','L','range','F15','F65','E20_DOWN','touch_elapsed_min')
    for cid in common:
        for field in fields:
            if not close_num(gm.at[cid, field], em.at[cid, field]):
                geometry += 1
                mismatch_rows.append({'clock':name,'candidate_id':cid,'field':field,'generated':gm.at[cid,field],'expected':em.at[cid,field]})
        if pd.Timestamp(gm.at[cid,'confirmation_bar_start']) != pd.Timestamp(em.at[cid,'confirmation_bar_start']):
            geometry += 1
            mismatch_rows.append({'clock':name,'candidate_id':cid,'field':'confirmation_bar_start','generated':gm.at[cid,'confirmation_bar_start'],'expected':em.at[cid,'confirmation_bar_start']})
    for cid in missing:
        mismatch_rows.append({'clock':name,'candidate_id':cid,'field':'MISSING_GENERATED','generated':'','expected':'present'})
    for cid in extra:
        mismatch_rows.append({'clock':name,'candidate_id':cid,'field':'EXTRA_GENERATED','generated':'present','expected':''})
    exact = (len(g)==len(e) and gid==eid and not missing and not extra and geometry==0)
    return {
        'clock':name,'clock_min':cm,
        'generated_n':len(g),'canonical_n':len(e),
        'identity_matches':sum(a==b for a,b in zip(gid,eid)),
        'missing_n':len(missing),'extra_n':len(extra),'geometry_mismatch_n':geometry,
        'raw_parity_supported':bool(exact),
    }


def standalone_window_rows(short_clock, base_long, portfolio_acc, name):
    rows = []
    for wname, start, end, completed in WINDOWS:
        s = du.between(dt.pooled(short_clock), start, end)
        b = du.between(dt.pooled(base_long), start, end)
        p = du.between(dt.pooled(portfolio_acc), start, end)
        ps = p[p.side == 'SHORT'].copy()
        pl = p[p.side == 'LONG'].copy()
        sm = du.metrics_df(s); bm = du.metrics_df(b); pm = du.metrics_df(p); psm = du.metrics_df(ps)
        displaced = set(b.candidate_id) - set(pl.candidate_id)
        window_pass = bool(sm['n'] >= 8 and pd.notna(sm['wr']) and sm['wr'] >= .60 and
                           pd.notna(sm['pf']) and sm['pf'] >= 1.20 and sm['net'] > 0)
        rows.append({
            'clock':name,'window':wname,'start':start,'end':end,'completed_gate_window':completed,
            'short_n':sm['n'],'short_wins':sm['wins'],'short_wr':sm['wr'],'short_pf':sm['pf'],'short_expectancy':sm['expectancy'],'short_net':sm['net'],'window_pass':window_pass,
            'long_only_n':bm['n'],'long_only_wr':bm['wr'],'long_only_pf':bm['pf'],'long_only_net':bm['net'],
            'portfolio_n':pm['n'],'portfolio_wr':pm['wr'],'portfolio_pf':pm['pf'],'portfolio_net':pm['net'],
            'accepted_short_n':psm['n'],'accepted_short_wr':psm['wr'],'accepted_short_net':psm['net'],
            'delta_vs_long':pm['net']-bm['net'],'displaced_long_n':len(displaced),
        })
    return rows


def year_rows(short_clock, name):
    q = dt.pooled(short_clock).copy()
    q['year'] = q.entry_ts.dt.year
    rows = []
    for year in sorted(q.year.dropna().unique()):
        m = du.metrics_df(q[q.year == year])
        rows.append({'clock':name,'year':int(year),**m})
    return rows


def slip_rows(short_cases, name, cm):
    q = short_cases[(pd.to_numeric(short_cases.clock_min)==cm) &
                    short_cases.partition.isin(MAJOR) &
                    short_cases.entry_executed.astype(bool) &
                    short_cases.fixed_net_pnl_usd.notna()].copy()
    rows=[]
    notional=float(dr.b27ad.NOTIONAL); fee=float(dr.b27ad.FEE)
    for bps in SLIPPAGE_BPS:
        f=float(bps)/10000.0
        entry=pd.to_numeric(q.entry_px,errors='raise')*(1.0-f)
        exitp=pd.to_numeric(q.fixed_exit_px,errors='raise')*(1.0+f)
        pnl=(1.0-exitp/entry)*notional-fee
        m=du.metrics_df(pd.DataFrame({'pnl':pnl}))
        rows.append({'clock':name,'clock_min':cm,'slippage_bps_per_fill':bps,**m})
    return rows


def main():
    x5, coverage = dt.dq.dn.dl.dj.b21.load5()
    raw_long_all, locked_long_all, base = dt.build_long(x5)
    raw_long = dt.normalize_long(raw_long_all, accepted_source=False)
    base_long = dt.normalize_long(locked_long_all, accepted_source=True)

    short_cases = dt.build_shorts(x5)
    short_all = dt.normalize_short(short_cases)
    generated_raw, raw_sessions = raw_replay_all(x5)

    mismatch_rows=[]; raw_rows=[]; win_rows=[]; year_out=[]; slip_out=[]; summary_rows=[]

    pooled_base = du.metrics_df(dt.pooled(base_long))
    if not (pooled_base['n']==227 and abs(pooled_base['net']-289.75971313529084)<=.25):
        raise AssertionError('B27DY pre-B27DX B27DQ control parity failed')

    # Existing current control: LONG + already validated SHORT20.
    short20 = short_all[short_all.clock_min_norm == SHORT20].copy()
    control_lock = dt.lock_rows(pd.concat([raw_long, short20], ignore_index=True), 'B27DY_CURRENT_LONG_SHORT20')
    control_acc = control_lock[control_lock.accepted_portfolio.astype(bool)].copy()
    control_metrics = du.metrics_df(dt.pooled(control_acc))
    if not (control_metrics['n']==283 and abs(control_metrics['net']-367.48603546601095)<=.25):
        raise AssertionError('B27DY current LONG+SHORT20 control parity failed')

    for name, cm in CANDIDATES.items():
        sclock = short_all[short_all.clock_min_norm == cm].copy()
        standalone = du.metrics_df(dt.pooled(sclock))

        plock = dt.lock_rows(pd.concat([raw_long, sclock], ignore_index=True), f'B27DY_{name}_INDEPENDENT')
        pacc = plock[plock.accepted_portfolio.astype(bool)].copy()
        win = standalone_window_rows(sclock, base_long, pacc, name)
        win_rows.extend(win)
        wdf = pd.DataFrame(win)
        completed = wdf[wdf.completed_gate_window.astype(bool)].copy()
        pass_windows = int(completed.window_pass.astype(bool).sum())
        chronological_supported = bool(pass_windows >= 3 and not ((completed.short_pf.notna()) & (completed.short_pf < .80)).any())

        pooled_pacc = dt.pooled(pacc)
        long_ids = set(dt.pooled(base_long).candidate_id)
        accepted_long_ids = set(pooled_pacc[pooled_pacc.side=='LONG'].candidate_id)
        displaced_long = len(long_ids - accepted_long_ids)
        positive_delta_windows = int((completed.delta_vs_long > 0).sum())
        pmetrics = du.metrics_df(pooled_pacc)
        portfolio_supported = bool(positive_delta_windows >= 3 and displaced_long == 0 and pmetrics['net'] > pooled_base['net'])

        slips = slip_rows(short_cases, name, cm)
        slip_out.extend(slips)
        s5 = pd.DataFrame(slips).query('slippage_bps_per_fill == 5').iloc[0]
        execution_supported = bool(pd.notna(s5.wr) and float(s5.wr)>=.65 and
                                   pd.notna(s5.pf) and float(s5.pf)>=1.50 and float(s5.net)>0)

        canon = canonical_raw_rows(short_cases, name, cm)
        raw_result = compare_raw(name, cm, generated_raw, canon, mismatch_rows)
        raw_rows.append(raw_result)
        raw_supported = bool(raw_result['raw_parity_supported'])

        year_out.extend(year_rows(sclock, name))

        survivor = bool(chronological_supported and portfolio_supported and execution_supported and raw_supported)

        # Incremental effect on the CURRENT LONG+SHORT20 control, diagnostic after independent gates.
        current_plus = dt.lock_rows(pd.concat([raw_long, short20, sclock], ignore_index=True), f'B27DY_CURRENT_PLUS_{name}')
        current_plus_acc = current_plus[current_plus.accepted_portfolio.astype(bool)].copy()
        current_plus_m = du.metrics_df(dt.pooled(current_plus_acc))

        summary_rows.append({
            'clock':name,'clock_min':cm,
            'standalone_n':standalone['n'],'standalone_wins':standalone['wins'],'standalone_wr':standalone['wr'],'standalone_pf':standalone['pf'],'standalone_net':standalone['net'],
            'completed_windows_pass':pass_windows,'chronological_supported':chronological_supported,
            'positive_portfolio_delta_windows':positive_delta_windows,'displaced_long_n':displaced_long,'portfolio_supported':portfolio_supported,
            'slip5_n':int(s5.n),'slip5_wr':float(s5.wr),'slip5_pf':float(s5.pf),'slip5_net':float(s5.net),'execution_supported':execution_supported,
            'raw_generated_n':raw_result['generated_n'],'raw_canonical_n':raw_result['canonical_n'],'raw_missing_n':raw_result['missing_n'],'raw_extra_n':raw_result['extra_n'],'raw_geometry_mismatch_n':raw_result['geometry_mismatch_n'],'raw_parity_supported':raw_supported,
            'survivor':survivor,
            'current_plus_clock_n':current_plus_m['n'],'current_plus_clock_wr':current_plus_m['wr'],'current_plus_clock_pf':current_plus_m['pf'],'current_plus_clock_net':current_plus_m['net'],
            'incremental_n_vs_current':current_plus_m['n']-control_metrics['n'],'incremental_net_vs_current':current_plus_m['net']-control_metrics['net'],
        })

    summary = pd.DataFrame(summary_rows)
    survivors = summary[summary.survivor.astype(bool)].copy()
    survivor_clocks = survivors.clock_min.astype(int).tolist()

    basket_short = short_all[short_all.clock_min_norm.isin([SHORT20, *survivor_clocks])].copy()
    basket_lock = dt.lock_rows(pd.concat([raw_long, basket_short], ignore_index=True), 'B27DY_SURVIVOR_BASKET')
    basket_acc = basket_lock[basket_lock.accepted_portfolio.astype(bool)].copy()
    basket_major = dt.pooled(basket_acc)
    basket_m = du.metrics_df(basket_major)
    basket_long = du.metrics_df(basket_major[basket_major.side=='LONG'])
    basket_short_m = du.metrics_df(basket_major[basket_major.side=='SHORT'])
    base_long_ids = set(dt.pooled(base_long).candidate_id)
    basket_long_ids = set(basket_major[basket_major.side=='LONG'].candidate_id)
    basket_displaced = len(base_long_ids - basket_long_ids)

    basket = pd.DataFrame([{
        'survivor_count':len(survivors),
        'survivor_clocks':','.join(survivors.clock.astype(str).tolist()),
        'includes_short20':True,
        'total_n':basket_m['n'],'wins':basket_m['wins'],'wr':basket_m['wr'],'pf':basket_m['pf'],'net':basket_m['net'],
        'long_n':basket_long['n'],'long_wr':basket_long['wr'],'long_net':basket_long['net'],
        'short_n':basket_short_m['n'],'short_wr':basket_short_m['wr'],'short_net':basket_short_m['net'],
        'displaced_baseline_long_n':basket_displaced,
        'incremental_n_vs_current_283':basket_m['n']-control_metrics['n'],
        'incremental_net_vs_current':basket_m['net']-control_metrics['net'],
        'current_control_n':control_metrics['n'],'current_control_wr':control_metrics['wr'],'current_control_pf':control_metrics['pf'],'current_control_net':control_metrics['net'],
    }])

    summary.to_csv(OUT_SUM,index=False)
    pd.DataFrame(win_rows).to_csv(OUT_WIN,index=False)
    pd.DataFrame(year_out).to_csv(OUT_YEAR,index=False)
    pd.DataFrame(slip_out).to_csv(OUT_SLIP,index=False)
    pd.DataFrame(raw_rows).to_csv(OUT_RAW,index=False)
    pd.DataFrame(mismatch_rows, columns=['clock','candidate_id','field','generated','expected']).to_csv(OUT_MIS,index=False)
    basket.to_csv(OUT_BASKET,index=False)

    survivor_n = len(survivors)
    status = f'B27DY_{survivor_n}_OF_5_ADDITIONAL_SHORT_CLOCKS_SURVIVE'
    OUT_STATUS.write_text(status+'\n')

    lines = [
        '# B27DY — Five Additional F15 SHORT Clocks Independent Revalidation — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**; raw causal sessions replayed: **{raw_sessions:,}**.','',
        f'Pre-B27DX current control reproduced: **N={control_metrics["n"]}, WR={pct(control_metrics["wr"])}, PF={num(control_metrics["pf"])}, net={usd(control_metrics["net"])}** (B27DQ LONG + validated SHORT20).','',
        '## Independent gates','',
        '| Clock | N | WR | PF | Net | WF pass | Portfolio | 5bps WR/PF/Net | Raw parity | Survivor | +N vs current | +Net vs current |',
        '|---|---:|---:|---:|---:|---:|---|---|---|---|---:|---:|'
    ]
    for r in summary.itertuples(index=False):
        lines.append(f'| {r.clock} | {r.standalone_n} | {pct(r.standalone_wr)} | {num(r.standalone_pf)} | {usd(r.standalone_net)} | {r.completed_windows_pass}/4 | {"PASS" if r.portfolio_supported else "FAIL"} | {pct(r.slip5_wr)} / {num(r.slip5_pf)} / {usd(r.slip5_net)} | {"PASS" if r.raw_parity_supported else f"FAIL ({r.raw_missing_n}M/{r.raw_extra_n}E/{r.raw_geometry_mismatch_n}G)"} | **{"YES" if r.survivor else "NO"}** | {int(r.incremental_n_vs_current):+d} | {usd(r.incremental_net_vs_current)} |')

    lines += ['', '## Survivor basket — added to existing LONG + SHORT20','']
    br = basket.iloc[0]
    lines += [
        f'Independent survivors: **{survivor_n}/5** — {br.survivor_clocks if br.survivor_clocks else "none"}.', '',
        '| Portfolio | N | WR | PF | Net | LONG N | SHORT N | Displaced LONG | Delta N vs 283 | Delta Net |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
        f'| Current LONG+SHORT20 | {int(br.current_control_n)} | {pct(br.current_control_wr)} | {num(br.current_control_pf)} | {usd(br.current_control_net)} | 227 | 56 | 0 | - | - |',
        f'| + B27DY survivors | {int(br.total_n)} | {pct(br.wr)} | {num(br.pf)} | {usd(br.net)} | {int(br.long_n)} | {int(br.short_n)} | {int(br.displaced_baseline_long_n)} | {int(br.incremental_n_vs_current_283):+d} | {usd(br.incremental_net_vs_current)} |',
        '',
        f'**Status: {status}**','',
        'Guardrail: B27DY uses the pre-B27DX LONG benchmark for portfolio compatibility. Surviving additional SHORT clocks are research candidates only until B27DX causal LONG correction and the final combined raw/control-plane parity are completed. No live exchange writes were changed.'
    ]
    text='\n'.join(lines)+'\n'
    OUT_MD.write_text(text)
    print(text)


if __name__ == '__main__':
    main()
