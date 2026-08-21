#!/usr/bin/env python3
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
import btc_orb_b0_baseline as b0

ROOT = Path(__file__).resolve().parent.parent
OUTJ = ROOT / 'BTC_WEEKLY_STRUCTURAL_B8_Result.json'
OUTM = ROOT / 'BTC_WEEKLY_STRUCTURAL_B8_Result.md'
OUTC = ROOT / 'BTC_WEEKLY_STRUCTURAL_B8_Selected.csv'
FEE = b0.FEE
VARIANTS = {'CONF2_FORCED': 2, 'CONF3_FORCED': 3}


def prep(k, tf):
    x = k[['open', 'high', 'low', 'close']].copy()
    if tf != '1h':
        x = x.resample(tf, origin='start_day', label='left', closed='left').agg(
            {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
        ).dropna()
    pc = x.close.shift(1)
    tr = pd.concat([
        x.high - x.low,
        (x.high - pc).abs(),
        (x.low - pc).abs(),
    ], axis=1).max(axis=1)
    x['atr'] = tr.rolling(14, min_periods=14).mean()
    x['hi20'] = x.high.shift(1).rolling(20, min_periods=20).max()
    x['lo20'] = x.low.shift(1).rolling(20, min_periods=20).min()
    x['mid20'] = (x.hi20 + x.lo20) / 2.0

    # Daily UTC opening range 00:00-04:00, available only after 04:00.
    d = pd.Series(x.index.floor('D'), index=x.index)
    if tf == '1h':
        orm = (x.index.hour >= 0) & (x.index.hour < 4)
    else:
        orm = x.index.hour == 0
    or_hi = x.high.where(orm).groupby(d).transform('max')
    or_lo = x.low.where(orm).groupby(d).transform('min')
    x['or_hi'] = or_hi
    x['or_lo'] = or_lo
    return x.dropna(subset=['atr', 'hi20', 'lo20', 'mid20'])


def orb_vote(x, i, tf):
    if i < 1:
        return None
    t = x.index[i]
    p = x.iloc[i - 1]
    b = x.iloc[i]
    # OR must be complete and previous/current bars must belong to same UTC day.
    if t.floor('D') != x.index[i - 1].floor('D'):
        return None
    if tf == '1h' and t.hour < 5:
        return None
    if tf == '4h' and t.hour < 8:
        return None
    oh, ol = float(b.or_hi), float(b.or_lo)
    if not np.isfinite(oh) or not np.isfinite(ol):
        return None
    if float(p.close) > oh and float(b.low) <= oh and float(b.close) > oh:
        return 'LONG'
    if float(p.close) < ol and float(b.high) >= ol and float(b.close) < ol:
        return 'SHORT'
    return None


def sr_vote(x, i):
    b = x.iloc[i]
    atr = float(b.atr)
    sup, res = float(b.lo20), float(b.hi20)
    if not np.isfinite(atr) or atr <= 0:
        return None
    tol = 0.15 * atr
    o, h, l, c = map(float, (b.open, b.high, b.low, b.close))
    body = max(abs(c - o), 1e-12)
    lower = max(0.0, min(o, c) - l)
    upper = max(0.0, h - max(o, c))
    long_ok = l <= sup + tol and c >= sup and c > o and lower >= 0.5 * body
    short_ok = h >= res - tol and c <= res and c < o and upper >= 0.5 * body
    if long_ok and not short_ok:
        return 'LONG'
    if short_ok and not long_ok:
        return 'SHORT'
    return None


def latest_fvg(x, i):
    # Gap must have completed strictly before signal bar i.
    lo = max(2, i - 12)
    for j in range(i - 1, lo - 1, -1):
        a = x.iloc[j - 2]
        c = x.iloc[j]
        # bullish FVG zone [a.high, c.low]
        if float(c.low) > float(a.high):
            zlo, zhi = float(a.high), float(c.low)
            prior = x.iloc[j + 1:i]
            if len(prior) and float(prior.low.min()) <= zlo:
                continue
            return ('LONG', zlo, zhi, j)
        # bearish FVG zone [c.high, a.low]
        if float(c.high) < float(a.low):
            zlo, zhi = float(c.high), float(a.low)
            prior = x.iloc[j + 1:i]
            if len(prior) and float(prior.high.max()) >= zhi:
                continue
            return ('SHORT', zlo, zhi, j)
    return None


def fvg_vote(x, i):
    g = latest_fvg(x, i)
    if g is None:
        return None
    side, zlo, zhi, _ = g
    b = x.iloc[i]
    h, l, c, o = map(float, (b.high, b.low, b.close, b.open))
    mid = (zlo + zhi) / 2.0
    touched = l <= zhi and h >= zlo
    if side == 'LONG' and touched and c > mid and c > o:
        return 'LONG'
    if side == 'SHORT' and touched and c < mid and c < o:
        return 'SHORT'
    return None


def fib_vote(x, i):
    if i < 12:
        return None
    w = x.iloc[i - 12:i]
    b = x.iloc[i]
    atr = float(b.atr)
    if not np.isfinite(atr) or atr <= 0:
        return None
    hi_pos = int(np.argmax(w.high.to_numpy(dtype=float)))
    lo_pos = int(np.argmin(w.low.to_numpy(dtype=float)))
    hi = float(w.high.iloc[hi_pos])
    lo = float(w.low.iloc[lo_pos])
    rng = hi - lo
    if rng < 2.0 * atr:
        return None
    o, h, l, c = map(float, (b.open, b.high, b.low, b.close))
    if lo_pos < hi_pos:  # bullish impulse, retrace downward
        zlo = hi - 0.618 * rng
        zhi = hi - 0.500 * rng
        touched = l <= zhi and h >= zlo
        if touched and c > o and c >= zhi:
            return 'LONG'
    elif hi_pos < lo_pos:  # bearish impulse, retrace upward
        zlo = lo + 0.500 * rng
        zhi = lo + 0.618 * rng
        touched = l <= zhi and h >= zlo
        if touched and c < o and c <= zlo:
            return 'SHORT'
    return None


def votes_at(x, i, tf):
    votes = {
        'ORB': orb_vote(x, i, tf),
        'SR': sr_vote(x, i),
        'FVG': fvg_vote(x, i),
        'FIB': fib_vote(x, i),
    }
    lv = [k for k, v in votes.items() if v == 'LONG']
    sv = [k for k, v in votes.items() if v == 'SHORT']
    if len(lv) > len(sv):
        side, count = 'LONG', len(lv)
    elif len(sv) > len(lv):
        side, count = 'SHORT', len(sv)
    else:
        side, count = None, len(lv)
    return votes, side, count, lv, sv


def monday(ts):
    t = pd.Timestamp(ts)
    return (t.floor('D') - pd.Timedelta(days=t.weekday())).tz_convert('UTC') if t.tzinfo else (t.floor('D') - pd.Timedelta(days=t.weekday())).tz_localize('UTC')


def complete_weeks(start, end_exclusive):
    start = pd.Timestamp(start, tz='UTC')
    end = pd.Timestamp(end_exclusive, tz='UTC')
    first = start.floor('D') - pd.Timedelta(days=start.weekday())
    if first < start:
        first += pd.Timedelta(days=7)
    out = []
    w = first
    while w + pd.Timedelta(days=7) <= end:
        out.append(w)
        w += pd.Timedelta(days=7)
    return out


def week_key(w):
    iso = w.isocalendar()
    return f'{int(iso.year):04d}-W{int(iso.week):02d}'


def checkpoint_index(x, w, tf):
    target = w + pd.Timedelta(days=4, hours=12)  # Friday 12:00 UTC signal bar
    loc = x.index.get_indexer([target])
    return int(loc[0]) if len(loc) and loc[0] >= 0 else None


def route_week(x, tf, w, conf):
    ck = checkpoint_index(x, w, tf)
    if ck is None or ck + 1 >= len(x):
        return None
    # Search Monday through fixed Friday checkpoint, causal chronological order.
    start_loc = int(x.index.searchsorted(w, side='left'))
    for i in range(start_loc, ck + 1):
        if i + 1 >= len(x):
            break
        votes, side, count, lv, sv = votes_at(x, i, tf)
        if side is not None and count >= conf:
            return {
                'signal_idx': i,
                'side': side,
                'route': 'CONFLUENCE',
                'vote_count': count,
                'votes': votes,
                'long_votes': ','.join(lv),
                'short_votes': ','.join(sv),
            }

    # Frozen forced fallback at checkpoint.
    votes, side, count, lv, sv = votes_at(x, ck, tf)
    if side is None:
        b = x.iloc[ck]
        side = 'SHORT' if float(b.close) > float(b.mid20) else 'LONG'
    return {
        'signal_idx': ck,
        'side': side,
        'route': 'FALLBACK',
        'vote_count': count,
        'votes': votes,
        'long_votes': ','.join(lv),
        'short_votes': ','.join(sv),
    }


def execute(x, signal_idx, side, hold):
    entry_idx = signal_idx + 1
    if entry_idx >= len(x):
        return None
    sig = x.iloc[signal_idx]
    entry = float(x.iloc[entry_idx].open)
    atr = float(sig.atr)
    if not np.isfinite(entry) or not np.isfinite(atr) or entry <= 0 or atr <= 0:
        return None
    risk_frac = atr / entry
    reward_frac = risk_frac + 2.0 * FEE
    if side == 'LONG':
        sl = entry - atr
        tp = entry * (1.0 + reward_frac)
    else:
        sl = entry + atr
        tp = entry * (1.0 - reward_frac)
    fut = x.iloc[entry_idx:entry_idx + hold]
    if fut.empty:
        return None
    px = float(fut.iloc[-1].close)
    exit_ts = fut.index[-1]
    reason = 'TIME'
    for t, b in fut.iterrows():
        if side == 'LONG':
            hit_sl = float(b.low) <= sl
            hit_tp = float(b.high) >= tp
        else:
            hit_sl = float(b.high) >= sl
            hit_tp = float(b.low) <= tp
        if hit_sl:
            px, exit_ts, reason = sl, t, 'SL'
            break
        if hit_tp:
            px, exit_ts, reason = tp, t, 'TP'
            break
    gross = (px / entry - 1.0) * (1.0 if side == 'LONG' else -1.0)
    net = gross - FEE
    return {
        'entry_ts': x.index[entry_idx],
        'exit_ts': exit_ts,
        'entry': entry,
        'sl': sl,
        'tp': tp,
        'risk_frac': risk_frac,
        'net_ret': net,
        'reason': reason,
    }


def stat(df, weeks_total):
    if df.empty:
        return {
            'weeks_total': weeks_total, 'n': 0, 'coverage': 0.0, 'wins': 0, 'losses': 0,
            'wr': None, 'decisive_wr': None, 'tp': 0, 'sl': 0, 'time': 0,
            'exp': None, 'pf': None, 'max_losing_streak': 0,
            'confluence': 0, 'fallback': 0,
        }
    a = df.net_ret.to_numpy(dtype=float)
    pos = a > 0
    gp = float(a[pos].sum())
    gl = float(-a[~pos].sum())
    tp_n = int((df.reason == 'TP').sum())
    sl_n = int((df.reason == 'SL').sum())
    time_n = int((df.reason == 'TIME').sum())
    dec_n = tp_n + sl_n
    streak = mx = 0
    for v in a:
        if v <= 0:
            streak += 1
            mx = max(mx, streak)
        else:
            streak = 0
    return {
        'weeks_total': weeks_total,
        'n': int(len(df)),
        'coverage': float(df.week.nunique() / weeks_total) if weeks_total else 0.0,
        'wins': int(pos.sum()),
        'losses': int((~pos).sum()),
        'wr': float(pos.mean()),
        'decisive_wr': float(tp_n / dec_n) if dec_n else None,
        'tp': tp_n, 'sl': sl_n, 'time': time_n,
        'exp': float(a.mean()),
        'pf': float(gp / gl) if gl > 0 else 999.0,
        'max_losing_streak': int(mx),
        'confluence': int((df.route == 'CONFLUENCE').sum()),
        'fallback': int((df.route == 'FALLBACK').sum()),
    }


def blocks(df):
    if df.empty:
        return []
    z = df.sort_values('entry_ts').reset_index(drop=True)
    edges = np.linspace(0, len(z), 5, dtype=int)
    out = []
    for i in range(4):
        q = z.iloc[edges[i]:edges[i + 1]]
        out.append(stat(q, max(1, q.week.nunique())))
    return out


def run_partition(x, tf, variant, conf, part, weeks):
    hold = 12 if tf == '1h' else 6
    rows = []
    for w in weeks:
        r = route_week(x, tf, w, conf)
        if r is None:
            continue
        tr = execute(x, r['signal_idx'], r['side'], hold)
        if tr is None:
            continue
        sig_t = x.index[r['signal_idx']]
        row = {
            'partition': part,
            'tf': tf,
            'variant': variant,
            'week': week_key(w),
            'week_start': w,
            'signal_ts': sig_t,
            'side': r['side'],
            'route': r['route'],
            'vote_count': r['vote_count'],
            'long_votes': r['long_votes'],
            'short_votes': r['short_votes'],
            'votes_json': json.dumps(r['votes'], sort_keys=True),
        }
        row.update(tr)
        rows.append(row)
    return pd.DataFrame(rows)


def fmt_pct(v):
    return '-' if v is None else f'{100*v:.2f}%'


def main():
    k = b0.load()
    data_end = k.index.max() + pd.Timedelta(hours=1)
    xmap = {'1h': prep(k, '1h'), '4h': prep(k, '4h')}
    parts = {
        'external': ('2020-01-01', '2022-01-01'),
        'development': ('2022-01-01', '2025-01-01'),
        'reference_validation': ('2025-01-01', '2026-07-30'),
        'august': ('2026-08-01', data_end),
    }

    all_rows = []
    results = []
    for tf, x in xmap.items():
        for variant, conf in VARIANTS.items():
            for part, (start, end) in parts.items():
                weeks = complete_weeks(start, end)
                df = run_partition(x, tf, variant, conf, part, weeks)
                if not df.empty:
                    all_rows.append(df)
                s = stat(df, len(weeks))
                losing_weeks = [] if df.empty else df.loc[df.net_ret <= 0, 'week'].tolist()
                results.append({
                    'tf': tf, 'variant': variant, 'partition': part,
                    'stats': s, 'blocks': blocks(df), 'losing_weeks': losing_weeks,
                })

    selected = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    if not selected.empty:
        selected = selected.sort_values(['tf', 'variant', 'entry_ts']).reset_index(drop=True)
        selected.to_csv(OUTC, index=False)

    def get(tf, variant, part):
        for r in results:
            if r['tf'] == tf and r['variant'] == variant and r['partition'] == part:
                return r['stats']
        return None

    robust = []
    high = []
    for tf in ['1h', '4h']:
        for variant in VARIANTS:
            e = get(tf, variant, 'external')
            v = get(tf, variant, 'reference_validation')
            if not e or not v:
                continue
            common_cov = e['coverage'] == 1.0 and v['coverage'] == 1.0
            common_n = e['n'] >= 20 and v['n'] >= 20
            if common_cov and common_n and e['wr'] == 1.0 and v['wr'] == 1.0 and e['exp'] > 0 and v['exp'] > 0 and e['pf'] > 1 and v['pf'] > 1:
                robust.append({'tf': tf, 'variant': variant})
            if common_cov and common_n and e['wr'] >= 0.80 and v['wr'] >= 0.80 and e['exp'] > 0 and v['exp'] > 0 and e['pf'] > 1 and v['pf'] > 1 and e['max_losing_streak'] <= 2 and v['max_losing_streak'] <= 2:
                high.append({'tf': tf, 'variant': variant})

    out = {
        'protocol': 'BTC_WEEKLY_STRUCTURAL_B8',
        'coverage_end': str(data_end),
        'fee': FEE,
        'robust_weekly_100': robust,
        'high_precision_weekly': high,
        'verdict': 'B8_ROBUST_WEEKLY_100_PASS' if robust else ('B8_HIGH_PRECISION_WEEKLY_PASS' if high else 'B8_NO_ROBUST_WEEKLY_100'),
        'results': results,
        'guardrail': 'Frozen B8 only; live BBC untouched; no post-result rescue.',
    }
    OUTJ.write_text(json.dumps(out, indent=2, default=str) + '\n')

    md = [
        '# BTC Weekly Structural Confluence B8 — Result', '',
        f"**Verdict: {out['verdict']}**", '',
        f"Coverage through **{data_end}**. Fee **{100*FEE:.2f}%** round trip. Net RR **1:1**. One trade maximum per complete ISO week; forced Friday fallback ensures weekly coverage when data are complete.", '',
        '| TF | Variant | Partition | Weeks/N/Coverage | Confluence/Fallback | TP/SL/TIME | WR | Decisive WR | Exp | PF | Max LS |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    order = ['development', 'reference_validation', 'external', 'august']
    for tf in ['1h', '4h']:
        for variant in VARIANTS:
            for part in order:
                s = get(tf, variant, part)
                if s is None:
                    continue
                md.append(
                    f"| {tf.upper()} | {variant} | {part} | {s['weeks_total']} / {s['n']} / {100*s['coverage']:.1f}% | "
                    f"{s['confluence']} / {s['fallback']} | {s['tp']}/{s['sl']}/{s['time']} | {fmt_pct(s['wr'])} | "
                    f"{fmt_pct(s['decisive_wr'])} | {'-' if s['exp'] is None else f'{100*s['exp']:.3f}%'} | "
                    f"{'-' if s['pf'] is None else f'{s['pf']:.3f}'} | {s['max_losing_streak']} |"
                )

    md += ['', '## Losing weeks']
    for r in results:
        if r['partition'] not in ('external', 'reference_validation'):
            continue
        lw = r['losing_weeks']
        md.append(f"- {r['tf'].upper()} / {r['variant']} / {r['partition']}: {len(lw)} losing weeks" + (f" — {', '.join(lw[:30])}" if lw else ''))

    md += ['', '## Gates', '']
    md.append(f"- `B8_ROBUST_WEEKLY_100`: **{'PASS' if robust else 'FAIL'}**")
    md.append(f"- `B8_HIGH_PRECISION_WEEKLY`: **{'PASS' if high else 'FAIL'}**")
    if robust:
        md.append(f"- Robust 100% cells: `{robust}`")
    if high:
        md.append(f"- High-precision cells: `{high}`")
    md += ['', 'Frozen preregistration honored. No post-result threshold/session/Fib/FVG/ORB/RR/hold rescue. Live BBC untouched.', '']
    OUTM.write_text('\n'.join(md))
    print(json.dumps(out, indent=2, default=str))


if __name__ == '__main__':
    main()
