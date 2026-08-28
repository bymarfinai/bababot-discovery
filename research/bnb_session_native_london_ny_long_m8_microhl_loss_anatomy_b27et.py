from __future__ import annotations

from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'research'
for p in (str(ROOT), str(RESEARCH)):
    if p not in sys.path:
        sys.path.insert(0, p)

import bnb_session_native_london_ny_long_m1_structure_b27em as b27em
import bnb_session_native_london_ny_long_m7_entry_economics_b27es as b27es

TARGET = 'BNBUSDT'
BAR5 = pd.Timedelta(minutes=5)
CAND = 'E5_MICRO_HL_BULL'
EXT_R = 0.30
STOP_R = 0.30
PFX = 'BNB_SESSION_NATIVE_LONDON_NY_LONG_M8_MICROHL_LOSS_ANATOMY_B27ET'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_FEATURES = ROOT / f'{PFX}_Feature_Comparison.csv'
OUT_PATHS = ROOT / f'{PFX}_Loss_Paths.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

FEATURES = [
    'entry_depth_R','minutes_leave_to_entry','pre_entry_bar_count',
    'minutes_ny_open_to_entry','minutes_entry_to_ny_close','reference_range_pct',
    'signal_range_R','signal_body_R','signal_body_ratio','signal_close_position',
    'signal_low_depth_R','prev_low_depth_R','micro_hl_lift_R','micro_close_lift_R',
    'pre_entry_max_depth_R','pre_entry_max_close_depth_R',
]


def qstats(x: pd.Series):
    z = pd.to_numeric(x, errors='coerce').dropna()
    if z.empty:
        return (np.nan, np.nan, np.nan)
    return (float(z.quantile(.25)), float(z.median()), float(z.quantile(.75)))


def cles_loss_gt_win(win: pd.Series, loss: pd.Series):
    a = pd.to_numeric(win, errors='coerce').dropna().to_numpy(dtype=float)
    b = pd.to_numeric(loss, errors='coerce').dropna().to_numpy(dtype=float)
    if len(a) == 0 or len(b) == 0:
        return np.nan
    gt = 0.0
    n = 0
    for lv in b:
        gt += float((lv > a).sum()) + 0.5 * float((lv == a).sum())
        n += len(a)
    return gt / n if n else np.nan


def bar_features(exe, leave_ts, entry_ts, H, R):
    signal_start = entry_ts - BAR5
    prev_start = signal_start - BAR5
    if signal_start not in exe.index or prev_start not in exe.index:
        raise AssertionError(f'missing signal/prev bar at {entry_ts}')
    s = exe.loc[signal_start]
    p = exe.loc[prev_start]
    o,h,l,c = map(float, [s.open,s.high,s.low,s.close])
    po,ph,pl,pc = map(float, [p.open,p.high,p.low,p.close])
    rg = h-l
    pre = exe[(exe.index >= leave_ts) & (exe.index <= signal_start)]
    if pre.empty:
        raise AssertionError('empty pre-entry window')
    return {
        'signal_start': signal_start,
        'signal_range_R': rg/R,
        'signal_body_R': (c-o)/R,
        'signal_body_ratio': abs(c-o)/rg if rg > 0 else 0.0,
        'signal_close_position': (c-l)/rg if rg > 0 else 0.5,
        'signal_low_depth_R': (H-l)/R,
        'prev_low_depth_R': (H-pl)/R,
        'micro_hl_lift_R': (l-pl)/R,
        'micro_close_lift_R': (c-pc)/R,
        'pre_entry_max_depth_R': (H-float(pre.low.min()))/R,
        'pre_entry_max_close_depth_R': float(((H-pre.close.astype(float))/R).max()),
        'pre_entry_bar_count': int(len(pre)),
    }


def strict_progress(q, exit_ts, H, R, exit_type):
    if exit_type in ('SL','SL_BOTH'):
        pre = q[q.index < exit_ts]
    else:
        pre = q[q.index <= exit_ts]
    if pre.empty:
        max_high = np.nan
        min_low = np.nan
    else:
        max_high = float(pre.high.max())
        min_low = float(pre.low.min())
    hit_h = bool(not np.isnan(max_high) and max_high >= H)
    hit_h10 = bool(not np.isnan(max_high) and max_high >= H + .10*R)
    hit_h20 = bool(not np.isnan(max_high) and max_high >= H + .20*R)
    mfe_r = max(0.0, (max_high - float(q.iloc[0].open))/R) if not np.isnan(max_high) else 0.0
    mae_r = max(0.0, (float(q.iloc[0].open) - min_low)/R) if not np.isnan(min_low) else 0.0
    max_ext = max(0.0, (max_high-H)/R) if not np.isnan(max_high) else 0.0
    return hit_h, hit_h10, hit_h20, mfe_r, mae_r, max_ext


def loss_class(exit_type, gross_return, net_return, hit_h, hit_h10, hit_h20):
    if net_return > 0:
        return 'NET_WIN'
    if exit_type in ('SL','SL_BOTH'):
        if hit_h20:
            return 'SL_AFTER_H20_BEFORE_TP'
        if hit_h10:
            return 'SL_AFTER_H10_BEFORE_H20'
        if hit_h:
            return 'SL_AFTER_H_BEFORE_H10'
        return 'SL_BEFORE_H'
    if exit_type == 'SESSION_CLOSE':
        if gross_return > 0 and net_return <= 0:
            return 'COST_FLIP_CLOSE'
        if hit_h:
            return 'CLOSE_LOSS_AFTER_H'
        return 'CLOSE_LOSS_BEFORE_H'
    return 'OTHER_NET_LOSS'


def build(x5):
    entries, exec_map = b27es.build_entries(x5)
    e = entries[entries.candidate == CAND].copy().sort_values('entry_ts')
    if len(e) != 50:
        raise AssertionError(f'expected 50 E5 entries, got {len(e)}')

    sessions = b27em.session_rows(x5)
    dev = sessions[(sessions.partition=='development') & sessions.leave.fillna(False).astype(bool)].copy()
    smap = {str(r.local_date): r for _,r in dev.iterrows()}

    rows=[]
    for _,r in e.iterrows():
        local_date = str(r.local_date)
        s = smap[local_date]
        ny_open = pd.Timestamp(s.ny_open_utc)
        ny_close = pd.Timestamp(s.ny_close_utc)
        exe_full = b27em.fs(x5, ny_open, ny_close)
        entry_ts = pd.Timestamp(r.entry_ts)
        q = exec_map[(local_date, CAND)]
        z = b27es.simulate_one(q, float(r.entry_px), float(r.H), float(r.R), EXT_R, STOP_R)
        bf = bar_features(exe_full, pd.Timestamp(r.leave_ts), entry_ts, float(r.H), float(r.R))
        exit_ts = pd.Timestamp(z['exit_ts'])
        hit_h,hit_h10,hit_h20,pre_mfe,pre_mae,max_ext = strict_progress(q, exit_ts, float(r.H), float(r.R), z['exit_type'])
        cls = loss_class(z['exit_type'], float(z['gross_return']), float(z['net_return']), hit_h,hit_h10,hit_h20)
        rec = {
            'local_date':local_date,'entry_ts':entry_ts,'exit_ts':exit_ts,
            'exit_type':z['exit_type'],'gross_return':float(z['gross_return']),'net_return':float(z['net_return']),
            'pnl_usd_500':float(z['pnl_usd_500']),'net_win':bool(z['net_win']),'loss_class':cls,
            'entry_px':float(r.entry_px),'H':float(r.H),'L':float(r.L),'R':float(r.R),
            'entry_depth_R':float(r.entry_depth_R),'minutes_leave_to_entry':float(r.minutes_leave_to_entry),
            'minutes_ny_open_to_entry':float((entry_ts-ny_open)/pd.Timedelta(minutes=1)),
            'minutes_entry_to_ny_close':float((ny_close-entry_ts)/pd.Timedelta(minutes=1)),
            'reference_range_pct':float(r.R/r.H),
            'minutes_entry_to_exit_complete':float(((exit_ts+BAR5)-entry_ts)/pd.Timedelta(minutes=1)),
            'hit_H_strict_before_exit':hit_h,'hit_H10_strict_before_exit':hit_h10,'hit_H20_strict_before_exit':hit_h20,
            'pre_exit_mfe_R':pre_mfe,'pre_exit_mae_R':pre_mae,'pre_exit_max_extension_above_H_R':max_ext,
            'target_progress_R':max_ext,
        }
        rec.update(bf)
        rows.append(rec)
    d=pd.DataFrame(rows).sort_values('entry_ts').reset_index(drop=True)
    if len(d)!=50:
        raise AssertionError('trade count mismatch')
    if int((d.exit_type=='TP').sum())!=19 or int(d.exit_type.isin(['SL','SL_BOTH']).sum())!=20 or int((d.exit_type=='SESSION_CLOSE').sum())!=11:
        raise AssertionError('exit-count integrity mismatch')
    if int(d.net_win.sum())!=25 or int((~d.net_win).sum())!=25:
        raise AssertionError(f'net win/loss mismatch {int(d.net_win.sum())}/{int((~d.net_win).sum())}')
    if int((d.exit_type=='SL_BOTH').sum())!=0:
        raise AssertionError('unexpected same-bar collision')
    return d


def feature_compare(d):
    w=d[d.net_win]
    l=d[~d.net_win]
    rows=[]
    for k in FEATURES:
        wp25,wmed,wp75=qstats(w[k]); lp25,lmed,lp75=qstats(l[k])
        cl=cles_loss_gt_win(w[k],l[k])
        rows.append({'feature':k,'winner_p25':wp25,'winner_median':wmed,'winner_p75':wp75,
                     'loser_p25':lp25,'loser_median':lmed,'loser_p75':lp75,
                     'cles_loss_gt_win':cl,'separation_from_0_5':abs(cl-.5) if not pd.isna(cl) else np.nan})
    return pd.DataFrame(rows).sort_values('separation_from_0_5',ascending=False).reset_index(drop=True)


def main():
    prereg=ROOT/f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27ET preregistration missing')
    x5,cov=b27em.data_base.load5(TARGET)
    if cov<.995:
        raise AssertionError(f'coverage gate failed {cov}')
    d=build(x5)
    d.to_csv(OUT_DETAIL,index=False)
    fc=feature_compare(d)
    fc.to_csv(OUT_FEATURES,index=False)
    losses=d[~d.net_win].copy()
    ps=(losses.groupby('loss_class',dropna=False)
        .agg(losses=('local_date','size'),median_time_to_exit_min=('minutes_entry_to_exit_complete','median'),
             median_pre_exit_mfe_R=('pre_exit_mfe_R','median'),median_pnl_usd_500=('pnl_usd_500','median'))
        .reset_index().sort_values(['losses','loss_class'],ascending=[False,True]))
    ps['share_of_losses']=ps.losses/len(losses)
    ps.to_csv(OUT_PATHS,index=False)

    h_reach=int(losses.hit_H_strict_before_exit.sum())
    h10=int(losses.hit_H10_strict_before_exit.sum())
    h20=int(losses.hit_H20_strict_before_exit.sum())
    cost_flip=int((losses.loss_class=='COST_FLIP_CLOSE').sum())
    sl=int(losses.exit_type.isin(['SL','SL_BOTH']).sum())
    close=int((losses.exit_type=='SESSION_CLOSE').sum())
    immediate15=int((losses.minutes_entry_to_exit_complete<=15).sum())

    lines=[
        '# BNB Session-Native LONG M8 MICRO_HL_BULL Loss Anatomy — B27ET Result','',
        f'Raw BNB 5m coverage: **{cov:.4%}**.','',
        'Frozen setup: **E5_MICRO_HL_BULL**, TP **H+0.30R**, SL **0.30R**, total cost **0.15%**. Development only.','',
        'Integrity: **50 trades = 25 net winners + 25 net losers**; exits = **19 TP + 20 SL + 11 session close**; same-bar TP/SL collisions = **0**.','',
        '## Loss path breakdown','',
        '| Loss path | Count | Share losses | Median exit time | Median pre-exit MFE | Median PnL @ $500 |','|---|---:|---:|---:|---:|---:|']
    for _,r in ps.iterrows():
        lines.append(f"| {r.loss_class} | {int(r.losses)} | {100*r.share_of_losses:.1f}% | {r.median_time_to_exit_min:.1f}m | {r.median_pre_exit_mfe_R:.3f}R | ${r.median_pnl_usd_500:.2f} |")
    lines += ['', '## What losers did before failing','',
              f'- Hard-stop exits among net losers: **{sl}/{len(losses)} ({100*sl/len(losses):.1f}%)**.',
              f'- Session-close exits among net losers: **{close}/{len(losses)} ({100*close/len(losses):.1f}%)**.',
              f'- Reached H on a completed bar strictly before exit: **{h_reach}/{len(losses)} ({100*h_reach/len(losses):.1f}%)**.',
              f'- Reached H+0.10R strictly before exit: **{h10}/{len(losses)} ({100*h10/len(losses):.1f}%)**.',
              f'- Reached H+0.20R strictly before exit: **{h20}/{len(losses)} ({100*h20/len(losses):.1f}%)**.',
              f'- Net losses resolved within <=15 minutes: **{immediate15}/{len(losses)} ({100*immediate15/len(losses):.1f}%)**.',
              f'- Gross-positive close trades flipped negative only by costs: **{cost_flip}**.','',
              '## Strongest causal pre-entry descriptive differences','',
              '| Rank | Feature | Winner median | Loser median | P(loss > win) |','|---:|---|---:|---:|---:|']
    for i,r in fc.head(8).iterrows():
        lines.append(f"| {i+1} | {r.feature} | {r.winner_median:.4f} | {r.loser_median:.4f} | {100*r.cles_loss_gt_win:.1f}% |")
    lines += ['',
              'Common-language effect size is descriptive only: 50% means no directional separation; values far above 50% mean losses tend to have larger feature values, far below 50% mean losses tend to have smaller values.','',
              'No threshold/filter is selected or promoted from this milestone.','',
              '**Status: B27ET_BNB_MICROHL_LOSS_ANATOMY_COMPLETE**','',
              'STOP: no filter selection, no TP/SL retuning, no holdout reveal, no August, no SHORT/live integration.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text('B27ET_BNB_MICROHL_LOSS_ANATOMY_COMPLETE\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
