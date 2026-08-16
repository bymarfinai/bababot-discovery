"""BTC Temporal A4 — post-entry rescue engine for Tuesday 06:00 SELL.

Intent
------
Keep the original high-coverage Tuesday trade: SELL every Tuesday at 06:00 WIB
with TP/SL 0.5%/0.5% and 4h max hold. Instead of trying to predict BUY/SELL
before entry, learn whether the *live post-entry path* still resembles a healthy
SELL winner. If not, test two causal rescue actions:

1) CUT: close the SELL early at the checkpoint.
2) FLIP: close SELL and immediately open BUY 0.5%/0.5% for the remaining horizon.
3) HYBRID: flip only when bullish price+flow confirmation is present; otherwise cut.

All decisions use only completed 5m bars before the checkpoint. The classifier
is walk-forward: every Tuesday is predicted from PRIOR calendar-day analogues
only. No future leakage. Full-sample rankings are descriptive; a 60/40
chronological discovery/validation split is also reported for configuration
selection. Research only; no live mutation.
"""
import json, math, statistics
from btc_temporal_a34_5m_events import load, ldt, context, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_a37_money_optimizer import trade as base_trade, FEE_PCT, NOTIONAL, max_drawdown, loss_streak

TP = 0.5
SL = 0.5
HOLD = 240
CHECKPOINTS = (5, 10, 15, 20, 30, 45, 60)
KS = (15, 25, 40)
THRESHOLDS = (0.55, 0.60, 0.65, 0.70)
POLICIES = ('CUT', 'FLIP', 'HYBRID')


def mean(xs):
    return statistics.mean(xs) if xs else 0.0


def median(xs):
    return statistics.median(xs) if xs else 0.0


def first_touch_state(rows, i, end_i=None):
    """Original SELL 0.5/0.5 state. Conservative SL-first if same 5m bar."""
    e = rows[i][1]
    tp_px = e * (1 - TP / 100.0)
    sl_px = e * (1 + SL / 100.0)
    end = min(len(rows), i + HOLD // 5) if end_i is None else min(end_i, len(rows))
    for j in range(i, end):
        if rows[j][0] != rows[i][0] + (j - i) * TF:
            return None
        hit_tp = rows[j][3] <= tp_px
        hit_sl = rows[j][2] >= sl_px
        if hit_tp and hit_sl:
            return ('SL', j)
        if hit_sl:
            return ('SL', j)
        if hit_tp:
            return ('TP', j)
    return ('TIMEOUT', end - 1)


def survived_to_checkpoint(rows, i, cp):
    """True only if original 0.5/0.5 SELL has not closed before decision time."""
    nb = cp // 5
    if nb <= 0 or i + nb >= len(rows):
        return False
    e = rows[i][1]
    tp_px = e * (1 - TP / 100.0)
    sl_px = e * (1 + SL / 100.0)
    for j in range(i, i + nb):  # completed bars only; decision is open at i+nb
        x = rows[j]
        if x[0] != rows[i][0] + (j - i) * TF:
            return False
        if x[2] >= sl_px or x[3] <= tp_px:
            return False
    return rows[i + nb][0] == rows[i][0] + nb * TF


def feature_vector(rows, i, cp):
    nb = cp // 5
    obs = rows[i:i + nb]
    if len(obs) != nb or not survived_to_checkpoint(rows, i, cp):
        return None
    c = context(rows, i)
    if c is None:
        return None
    e = rows[i][1]
    dec = rows[i + nb][1]
    hi = max(x[2] for x in obs)
    lo = min(x[3] for x in obs)
    rng = max(hi - lo, 1e-9)
    closes = [x[4] for x in obs]
    rets = [100.0 * (x[4] - x[1]) / x[1] for x in obs]
    path_abs = sum(abs(x) for x in rets)
    net = 100.0 * (dec - e) / e
    # From short perspective: positive mfe is favorable decline, mae is adverse rise.
    mfe = 100.0 * (e - lo) / e
    mae = 100.0 * (hi - e) / e
    close_pos = (dec - lo) / rng
    up_frac = sum(x > 0 for x in rets) / max(1, len(rets))
    last_ret = rets[-1] if rets else 0.0
    efficiency = abs(net) / max(path_abs, 1e-9)
    tbr = [(x[9] / x[6] if x[6] else 0.5) for x in obs]
    avg_t = mean(tbr)
    h = max(1, len(tbr) // 2)
    t_trend = mean(tbr[h:]) - mean(tbr[:h]) if len(tbr) > 1 else 0.0
    pre = rows[max(0, i - 12):i]
    pre_ranges = [x[2] - x[3] for x in pre]
    pre_q = [x[6] for x in pre]
    rbase = max(median(pre_ranges), 1e-9)
    qbase = max(median(pre_q), 1e-9)
    range_ratio = mean([x[2] - x[3] for x in obs]) / rbase
    vol_ratio = mean([x[6] for x in obs]) / qbase
    # A few stable pre-entry contextual anchors; no post-checkpoint data.
    return [
        net, mfe, mae, close_pos, up_frac, last_ret, efficiency,
        avg_t - 0.5, t_trend, range_ratio, vol_ratio,
        c['day_pos'], c['pre1'], c['pre4'], c['pre24'],
        100.0 * (e - c['daily_open']) / e,
        100.0 * (c['hod'] - e) / e,
        100.0 * (e - c['lod']) / e,
    ]


def build_examples(rows, indices, cp):
    out = []
    for i in indices:
        fv = feature_vector(rows, i, cp)
        if fv is None:
            continue
        ft = first_touch_state(rows, i)
        if ft is None or ft[0] not in ('TP', 'SL'):
            continue
        out.append({'i': i, 'ts': rows[i][0], 'x': fv, 'label': 1 if ft[0] == 'SL' else 0})
    return out


def knn_loss_probability(history, curx, k):
    if len(history) < max(12, k // 2):
        return None
    d = len(curx)
    mus = [mean([h['x'][z] for h in history]) for z in range(d)]
    sds = []
    for z in range(d):
        vals = [h['x'][z] for h in history]
        sd = statistics.pstdev(vals) if len(vals) > 1 else 1.0
        sds.append(max(sd, 1e-6))
    ds = []
    for h in history:
        dist = 0.0
        for z in range(d):
            a = (curx[z] - mus[z]) / sds[z]
            b = (h['x'][z] - mus[z]) / sds[z]
            dist += (a - b) ** 2
        ds.append((dist, h['label']))
    ds.sort(key=lambda q: q[0])
    q = ds[:min(k, len(ds))]
    # Distance-weighted vote with light smoothing.
    sw = 0.0; sl = 0.0
    for dist, lab in q:
        w = 1.0 / (0.25 + math.sqrt(max(dist, 0.0)))
        sw += w; sl += w * lab
    p = (sl + 1.0) / (sw + 2.0)
    return p


def exit_short_at(rows, i, cp):
    nb = cp // 5
    e = rows[i][1]
    px = rows[i + nb][1]
    gross_pct = 100.0 * (e - px) / e
    net_pct = gross_pct - FEE_PCT
    return NOTIONAL * net_pct / 100.0


def long_after_flip(rows, i, cp):
    """Close short at checkpoint then long 0.5/0.5 for remaining original 4h horizon."""
    nb = cp // 5
    j0 = i + nb
    if j0 >= len(rows):
        return None
    short_net = exit_short_at(rows, i, cp)
    e = rows[j0][1]
    tp_px = e * (1 + TP / 100.0)
    sl_px = e * (1 - SL / 100.0)
    end = min(len(rows), i + HOLD // 5)
    exit_px = None
    for j in range(j0, end):
        x = rows[j]
        if x[0] != rows[j0][0] + (j - j0) * TF:
            return None
        hit_tp = x[2] >= tp_px
        hit_sl = x[3] <= sl_px
        if hit_tp and hit_sl:
            exit_px = sl_px; break  # conservative adverse first
        if hit_sl:
            exit_px = sl_px; break
        if hit_tp:
            exit_px = tp_px; break
    if exit_px is None:
        if end <= j0:
            return None
        exit_px = rows[end - 1][4]
    gross_long_pct = 100.0 * (exit_px - e) / e
    long_net_pct = gross_long_pct - FEE_PCT
    return short_net + NOTIONAL * long_net_pct / 100.0


def bullish_confirmation(x):
    # Feature indices: net, mfe, mae, close_pos, up_frac, last_ret, efficiency,
    # avg_t-0.5, t_trend, ...
    net, mfe, mae, close_pos, up_frac, last_ret, _, taker, ttrend = x[:9]
    return (net > 0.08 and mae > mfe and close_pos > 0.60 and
            (up_frac >= 0.5 or last_ret > 0) and (taker > 0.01 or ttrend > 0.01))


def simulate_candidate(rows, tue_indices, all_examples_by_cp, cp, k, threshold, policy):
    base = []
    final = []
    records = []
    for i in tue_indices:
        b = base_trade(rows, i, TP, SL, HOLD)
        if b is None:
            continue
        bpnl = b['net_usd']
        base.append(bpnl)
        ft = first_touch_state(rows, i)
        original_class = ft[0] if ft else 'NA'
        action = 'HOLD'; p = None; fpnl = bpnl
        fv = feature_vector(rows, i, cp)
        if fv is not None:
            hist = [h for h in all_examples_by_cp[cp] if h['ts'] < rows[i][0]]
            p = knn_loss_probability(hist, fv, k)
            if p is not None and p >= threshold:
                if policy == 'CUT':
                    action = 'CUT'
                    fpnl = exit_short_at(rows, i, cp)
                elif policy == 'FLIP':
                    q = long_after_flip(rows, i, cp)
                    if q is not None:
                        action = 'FLIP'; fpnl = q
                elif policy == 'HYBRID':
                    if bullish_confirmation(fv):
                        q = long_after_flip(rows, i, cp)
                        if q is not None:
                            action = 'FLIP'; fpnl = q
                    else:
                        action = 'CUT'; fpnl = exit_short_at(rows, i, cp)
        final.append(fpnl)
        records.append({'ts': rows[i][0], 'base': bpnl, 'final': fpnl,
                        'original_class': original_class, 'action': action, 'p_loss': p})
    return summarize_policy(records, cp, k, threshold, policy)


def summarize_policy(records, cp, k, threshold, policy):
    base = [r['base'] for r in records]
    final = [r['final'] for r in records]
    n = len(records)
    triggered = [r for r in records if r['action'] != 'HOLD']
    base_sl = [r for r in records if r['original_class'] == 'SL']
    base_tp = [r for r in records if r['original_class'] == 'TP']
    rescued_positive = sum(r['base'] <= 0 and r['final'] > 0 for r in records)
    sl_to_positive = sum(r['original_class'] == 'SL' and r['final'] > 0 for r in records)
    damaged_positive = sum(r['base'] > 0 and r['final'] <= 0 for r in records)
    tp_damaged = sum(r['original_class'] == 'TP' and r['final'] <= 0 for r in records)
    improved_losses = sum(r['base'] < 0 and r['final'] > r['base'] for r in records)
    pos = sum(x for x in final if x > 0); neg = -sum(x for x in final if x < 0)
    blocks = []
    for b in range(8):
        q = [r['final'] for r in records if min(7, max(0, int((r['ts'] - EVAL_START) * 8 / (EVAL_END - EVAL_START)))) == b]
        blocks.append(rnd(sum(q), 3))
    return {
        'cp_min': cp, 'k': k, 'threshold': threshold, 'policy': policy,
        'trades': n, 'actions': len(triggered),
        'cuts': sum(r['action'] == 'CUT' for r in records),
        'flips': sum(r['action'] == 'FLIP' for r in records),
        'base_net_usd': rnd(sum(base), 3), 'net_pnl_usd': rnd(sum(final), 3),
        'delta_vs_base_usd': rnd(sum(final) - sum(base), 3),
        'net_wins': sum(x > 0 for x in final), 'net_losses': sum(x <= 0 for x in final),
        'net_wr': rnd(100 * sum(x > 0 for x in final) / n, 2) if n else None,
        'rescued_negative_to_positive': rescued_positive,
        'baseline_sl_count': len(base_sl), 'baseline_tp_count': len(base_tp),
        'sl_to_positive': sl_to_positive, 'improved_negative_trades': improved_losses,
        'damaged_positive_to_negative': damaged_positive, 'tp_damaged': tp_damaged,
        'profit_factor': rnd(pos / neg, 3) if neg > 0 else None,
        'max_dd_usd': rnd(max_drawdown(final), 3), 'max_loss_streak': loss_streak(final),
        'positive_blocks': sum(x > 0 for x in blocks), 'block_net_usd': blocks,
    }


def oracle(rows, tue_indices):
    out = []
    for cp in CHECKPOINTS:
        sl_total = sl_reachable = flip_positive = cut_improves = 0
        for i in tue_indices:
            ft = first_touch_state(rows, i)
            if ft is None or ft[0] != 'SL':
                continue
            sl_total += 1
            if not survived_to_checkpoint(rows, i, cp):
                continue
            sl_reachable += 1
            b = base_trade(rows, i, TP, SL, HOLD)
            cut = exit_short_at(rows, i, cp)
            flip = long_after_flip(rows, i, cp)
            if b and cut > b['net_usd']:
                cut_improves += 1
            if flip is not None and flip > 0:
                flip_positive += 1
        out.append({'cp_min': cp, 'baseline_sl': sl_total, 'sl_still_open': sl_reachable,
                    'oracle_cut_improves': cut_improves, 'oracle_flip_total_positive': flip_positive})
    return out


def main():
    rows = load(); im = {x[0]: i for i, x in enumerate(rows)}
    expected = (EVAL_END - EVAL_START) // TF
    exact = sum(EVAL_START <= x[0] < EVAL_END for x in rows)
    # All 06:00 local days create generic post-entry analogues.
    all_idx = []
    tue_idx = []
    for x in rows:
        dt = ldt(x[0])
        if dt.hour == 6 and dt.minute == 0:
            i = im[x[0]]; all_idx.append(i)
            if EVAL_START <= x[0] < EVAL_END and dt.weekday() == 1:
                tue_idx.append(i)
    ex = {cp: build_examples(rows, all_idx, cp) for cp in CHECKPOINTS}
    results = []
    for cp in CHECKPOINTS:
        for k in KS:
            for th in THRESHOLDS:
                for pol in POLICIES:
                    results.append(simulate_candidate(rows, tue_idx, ex, cp, k, th, pol))
    # Chronological 60/40 config selection. Select on discovery only, then inspect frozen validation.
    split = max(1, int(len(tue_idx) * 0.60))
    disc_idx, val_idx = tue_idx[:split], tue_idx[split:]
    disc_rows = []
    for cp in CHECKPOINTS:
        for k in KS:
            for th in THRESHOLDS:
                for pol in POLICIES:
                    r = simulate_candidate(rows, disc_idx, ex, cp, k, th, pol)
                    # Prefer actual money improvement, but heavily penalize damaging original winners.
                    score = r['delta_vs_base_usd'] - 2.0 * r['damaged_positive_to_negative']
                    disc_rows.append((score, r))
    disc_rows.sort(key=lambda z: (z[0], z[1]['positive_blocks'], z[1]['net_wr']), reverse=True)
    frozen = []
    seen = set()
    for score, r in disc_rows:
        key = (r['cp_min'], r['k'], r['threshold'], r['policy'])
        if key in seen:
            continue
        seen.add(key)
        vr = simulate_candidate(rows, val_idx, ex, *key)
        frozen.append({'discovery_score': rnd(score, 3), 'discovery': r, 'validation': vr})
        if len(frozen) >= 10:
            break
    by_net = sorted(results, key=lambda r: (r['net_pnl_usd'], r['positive_blocks'], -r['damaged_positive_to_negative']), reverse=True)
    by_rescue = sorted(results, key=lambda r: (r['sl_to_positive'] - r['tp_damaged'], r['net_pnl_usd']), reverse=True)
    base_ts = [base_trade(rows, i, TP, SL, HOLD) for i in tue_idx]
    base_ts = [x for x in base_ts if x is not None]
    base_pnls = [x['net_usd'] for x in base_ts]
    ft = [first_touch_state(rows, i) for i in tue_idx]
    out = {
        'status': 'A4_POST_ENTRY_RESCUE',
        'data': {
            'coverage': rnd(100 * exact / expected, 2), 'rows_5m': exact, 'tuesdays': len(tue_idx),
            'entry': 'Tuesday 06:00 WIB SELL', 'tp_pct': TP, 'sl_pct': SL, 'hold_min': HOLD,
            'fee_per_position_roundtrip_pct': FEE_PCT, 'notional_usd': NOTIONAL,
            'baseline_first_touch': {
                'tp': sum(x and x[0] == 'TP' for x in ft), 'sl': sum(x and x[0] == 'SL' for x in ft),
                'timeout': sum(x and x[0] == 'TIMEOUT' for x in ft),
            },
            'baseline_money': {'net_pnl_usd': rnd(sum(base_pnls), 3),
                'net_wins': sum(x > 0 for x in base_pnls), 'net_losses': sum(x <= 0 for x in base_pnls),
                'net_wr': rnd(100 * sum(x > 0 for x in base_pnls) / len(base_pnls), 2)},
            'config_count': len(results), 'split': {'discovery_tuesdays': len(disc_idx), 'validation_tuesdays': len(val_idx)},
        },
        'oracle_rescue_capacity': oracle(rows, tue_idx),
        'best_fullsample_net': by_net[:20],
        'best_fullsample_rescue_balance': by_rescue[:20],
        'discovery_selected_validation': frozen,
    }
    print('COVERAGE', exact, expected, rnd(100 * exact / expected, 2), 'TUESDAYS', len(tue_idx), flush=True)
    print('RESULT_JSON', json.dumps(out, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()
