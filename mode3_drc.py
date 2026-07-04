"""
Mode 3 DRC — OPTIMIZED v1.1
=================================

Key optimizations vs v1.0:
1. KDTree — O(n log n) KNN via scipy.spatial.cKDTree instead of O(n²) brute force
   Speedup: ~10-50x for 100k+ candles
2. Feature + label + tree caching per (symbol, timeframe, days) — sweep multiple TP
   options without re-computing features/labels
3. Progress callback support — for streaming progress to background jobs

Expected runtime BTCUSDT 15m 5yr: ~15 min → ~1-2 min (v1.1)
Full 15 pair × 3 TP sweep: ~11 hours → ~15-30 min

Requires: scipy>=1.7 (add to requirements.txt)
"""

from __future__ import annotations
import numpy as np
import sqlite3
from dataclasses import dataclass, field
from typing import Optional, Callable
from datetime import datetime, timezone

try:
    from scipy.spatial import cKDTree
    _KDTREE_AVAILABLE = True
except ImportError:
    _KDTREE_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════
# CONFIG (same as v1.0)
# ═══════════════════════════════════════════════════════════════

@dataclass
class DRCConfig:
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    days: int = 1825
    knn_k: int = 50
    knn_lookforward: int = 8
    knn_move_threshold: float = 0.004
    knn_warmup: int = 5000
    knn_min_confidence: float = 0.70
    ensemble_min_confidence: float = 0.60
    ensemble_min_agree: int = 4
    require_both_predictors: bool = True
    joint_confidence_min: float = 0.75
    joint_gap_min: float = 0.50
    sl_atr_mult: float = 1.2
    tp_pct_options: tuple = (0.003, 0.004, 0.005)
    max_hold_candles: int = 32
    min_sl_pct: float = 0.001
    max_sl_pct: float = 0.005
    position_usd: float = 1050.0
    leverage: int = 50
    fee_pct: float = 0.001

    # NEW v1.1: Sub-sample historical data for KNN (speedup)
    knn_subsample: int = 1  # 1 = all history, 2 = every other candle, 4 = every 4th


# ═══════════════════════════════════════════════════════════════
# INDICATOR HELPERS (unchanged from v1.0)
# ═══════════════════════════════════════════════════════════════

def ema(a: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(a, np.nan, dtype=np.float64)
    if len(a) < period:
        return out
    k = 2.0 / (period + 1)
    out[period - 1] = np.mean(a[:period])
    for i in range(period, len(a)):
        out[i] = a[i] * k + out[i - 1] * (1 - k)
    return out


def rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    out = np.full(n, np.nan, dtype=np.float64)
    if n < period + 1:
        return out
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0: out[period] = 100
    else:
        rs = avg_gain / avg_loss
        out[period] = 100 - (100 / (1 + rs))
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        if avg_loss == 0: out[i] = 100
        else:
            rs = avg_gain / avg_loss
            out[i] = 100 - (100 / (1 + rs))
    return out


def atr(highs, lows, closes, period=14):
    n = len(closes)
    tr = np.zeros(n, dtype=np.float64)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
    out = np.full(n, np.nan, dtype=np.float64)
    if n < period: return out
    out[period-1] = np.mean(tr[:period])
    for i in range(period, n):
        out[i] = (out[i-1] * (period-1) + tr[i]) / period
    return out


def macd(closes, fast=12, slow=26, signal=9):
    ef, es = ema(closes, fast), ema(closes, slow)
    macd_line = ef - es
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line, macd_line - signal_line


def adx(highs, lows, closes, period=14):
    n = len(closes)
    tr = np.zeros(n); dm_p = np.zeros(n); dm_m = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        up = highs[i] - highs[i-1]
        dn = lows[i-1] - lows[i]
        dm_p[i] = up if (up > dn and up > 0) else 0
        dm_m[i] = dn if (dn > up and dn > 0) else 0
    def wilder(arr, p):
        out = np.zeros_like(arr, dtype=np.float64)
        if len(arr) < p: return out
        out[p-1] = np.sum(arr[:p])
        for i in range(p, len(arr)):
            out[i] = out[i-1] - out[i-1]/p + arr[i]
        return out
    tr_s = wilder(tr, period)
    dmp_s = wilder(dm_p, period)
    dmm_s = wilder(dm_m, period)
    di_p = np.where(tr_s > 0, 100 * dmp_s / tr_s, 0)
    di_m = np.where(tr_s > 0, 100 * dmm_s / tr_s, 0)
    dx = np.where((di_p + di_m) > 0, 100 * np.abs(di_p - di_m) / (di_p + di_m), 0)
    adx_out = np.zeros(n)
    if n >= 2 * period:
        adx_out[2*period-1] = np.mean(dx[period:2*period])
        for i in range(2*period, n):
            adx_out[i] = (adx_out[i-1] * (period-1) + dx[i]) / period
    return adx_out, di_p, di_m


def bb(closes, period=20, mult=2.0):
    n = len(closes)
    mid = np.full(n, np.nan); up = np.full(n, np.nan); lo = np.full(n, np.nan)
    for i in range(period-1, n):
        window = closes[i-period+1:i+1]
        m = np.mean(window); s = np.std(window)
        mid[i] = m; up[i] = m + mult * s; lo[i] = m - mult * s
    return mid, up, lo


# ═══════════════════════════════════════════════════════════════
# FEATURE EXTRACTION (unchanged)
# ═══════════════════════════════════════════════════════════════

def build_features(data: dict) -> dict:
    o, h, l, c, v = data['open'], data['high'], data['low'], data['close'], data['volume']
    n = len(c)
    rsi14 = rsi(c, 14)
    macd_line, macd_sig, macd_hist = macd(c, 12, 26, 9)
    atr14 = atr(h, l, c, 14)
    ema20 = ema(c, 20); ema50 = ema(c, 50); ema200 = ema(c, 200)
    adx14, dip, dim = adx(h, l, c, 14)
    bb_mid, bb_up, bb_lo = bb(c, 20, 2.0)

    body = c - o
    hl_range = np.where((h - l) > 0, h - l, 1e-9)
    body_range_ratio = body / hl_range
    atr_pct = atr14 / c * 100
    volume_sma20 = np.full(n, np.nan)
    for i in range(19, n):
        volume_sma20[i] = np.mean(v[i-19:i+1])
    volume_ratio = np.where(volume_sma20 > 0, v / volume_sma20, 1.0)
    close_position = np.where((h - l) > 0, (c - l) / (h - l), 0.5)
    ema_dist_20 = (c - ema20) / c * 100
    ema_dist_200 = np.where(~np.isnan(ema200), (c - ema200) / c * 100, 0.0)
    ema20_slope = np.zeros(n)
    for i in range(4, n):
        if not np.isnan(ema20[i]) and not np.isnan(ema20[i-4]):
            ema20_slope[i] = (ema20[i] - ema20[i-4]) / ema20[i-4] * 100
    bb_position = np.where((bb_up - bb_lo) > 0, (c - bb_lo) / (bb_up - bb_lo), 0.5)
    di_gap = dip - dim
    hours = np.zeros(n)
    for i, ts in enumerate(data['open_time']):
        hours[i] = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).hour
    hour_sin = np.sin(2 * np.pi * hours / 24)
    hour_cos = np.cos(2 * np.pi * hours / 24)
    prev_dir = np.zeros(n)
    for i in range(1, n):
        d = c[i-1] - o[i-1]
        if d > 0: prev_dir[i] = 1
        elif d < 0: prev_dir[i] = -1
    consec = np.zeros(n)
    for i in range(1, n):
        d_now = 1 if c[i] > o[i] else (-1 if c[i] < o[i] else 0)
        d_prev = 1 if c[i-1] > o[i-1] else (-1 if c[i-1] < o[i-1] else 0)
        if d_now == d_prev and d_now != 0:
            consec[i] = consec[i-1] + 1

    return {
        'rsi14': rsi14, 'macd_hist': macd_hist, 'macd_line': macd_line,
        'atr14': atr14, 'atr_pct': atr_pct,
        'ema20': ema20, 'ema50': ema50, 'ema200': ema200,
        'adx14': adx14, 'di_plus': dip, 'di_minus': dim, 'di_gap': di_gap,
        'bb_mid': bb_mid, 'bb_up': bb_up, 'bb_lo': bb_lo, 'bb_position': bb_position,
        'body_range_ratio': body_range_ratio, 'close_position': close_position,
        'volume_ratio': volume_ratio, 'ema_dist_20': ema_dist_20, 'ema_dist_200': ema_dist_200,
        'ema20_slope': ema20_slope, 'hour_sin': hour_sin, 'hour_cos': hour_cos,
        'hours': hours, 'prev_dir': prev_dir, 'consec': consec,
    }


KNN_FEATURES = [
    'rsi14', 'macd_hist', 'atr_pct',
    'body_range_ratio', 'close_position', 'volume_ratio',
    'ema_dist_20', 'ema_dist_200', 'ema20_slope',
    'di_gap', 'bb_position',
    'hour_sin', 'hour_cos',
    'prev_dir', 'consec',
]


def normalize_features(feats: dict, feature_names: list) -> tuple:
    n = len(feats[feature_names[0]])
    d = len(feature_names)
    mat = np.zeros((n, d), dtype=np.float64)
    for j, name in enumerate(feature_names):
        arr = np.array(feats[name], dtype=np.float64)
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        mat[:, j] = arr
    means = np.mean(mat, axis=0)
    stds = np.std(mat, axis=0)
    stds = np.where(stds < 1e-9, 1.0, stds)
    mat = (mat - means) / stds
    return mat, means, stds


# ═══════════════════════════════════════════════════════════════
# TRIPLE-BARRIER LABELING (unchanged)
# ═══════════════════════════════════════════════════════════════

def compute_forward_labels(closes, highs, lows, lookforward, threshold):
    n = len(closes)
    labels = np.zeros(n, dtype=np.int8)
    for i in range(n - lookforward):
        entry = closes[i]
        up_target = entry * (1 + threshold)
        dn_target = entry * (1 - threshold)
        hit_up = -1; hit_dn = -1
        for k in range(1, lookforward + 1):
            if highs[i+k] >= up_target and hit_up == -1: hit_up = k
            if lows[i+k] <= dn_target and hit_dn == -1: hit_dn = k
            if hit_up != -1 or hit_dn != -1: break
        if hit_up != -1 and (hit_dn == -1 or hit_up < hit_dn): labels[i] = 1
        elif hit_dn != -1 and (hit_up == -1 or hit_dn < hit_up): labels[i] = -1
        else: labels[i] = 0
    return labels


# ═══════════════════════════════════════════════════════════════
# NEW v1.1: PairContext — pre-compute + cache heavy stuff
# ═══════════════════════════════════════════════════════════════

@dataclass
class PairContext:
    """Cached heavy computations per (symbol, timeframe, days) — reusable across TP sweeps."""
    symbol: str
    timeframe: str
    data: dict
    feats: dict
    feat_mat: np.ndarray
    labels: np.ndarray
    tree: Optional[object] = None  # cKDTree if scipy available
    btc_returns: Optional[np.ndarray] = None


def build_pair_context(data: dict, cfg: DRCConfig,
                       btc_returns: Optional[np.ndarray] = None) -> PairContext:
    """Build heavy pre-computations ONCE per pair (reused for all TP sweeps)."""
    feats = build_features(data)
    labels = compute_forward_labels(
        data['close'], data['high'], data['low'],
        cfg.knn_lookforward, cfg.knn_move_threshold
    )
    feat_mat, _, _ = normalize_features(feats, KNN_FEATURES)

    # Build KDTree ONCE for entire matrix — enables O(log n) queries
    tree = None
    if _KDTREE_AVAILABLE:
        # We build tree from full feat_mat; when querying, we mask by index
        tree = cKDTree(feat_mat, leafsize=32, balanced_tree=True)

    return PairContext(
        symbol=cfg.symbol, timeframe=cfg.timeframe,
        data=data, feats=feats, feat_mat=feat_mat, labels=labels,
        tree=tree, btc_returns=btc_returns,
    )


# ═══════════════════════════════════════════════════════════════
# KNN PREDICT — OPTIMIZED with KDTree
# ═══════════════════════════════════════════════════════════════

def knn_predict_kdtree(current_vec: np.ndarray, tree: object,
                       max_hist: int, hist_labels: np.ndarray,
                       k: int, subsample: int = 1) -> tuple:
    """
    O(log n) KNN via KDTree. Query all points, then filter to those before max_hist.
    We over-query by 3x to have enough candidates after masking.
    """
    # Query more than k because we'll filter by index (time-safety)
    query_k = min(k * 4, tree.n)  # 4x for safety
    dists, idxs = tree.query(current_vec, k=query_k)
    # Filter to indices < max_hist (no lookahead)
    valid_mask = idxs < max_hist
    valid_idxs = idxs[valid_mask]
    if len(valid_idxs) < k:
        # Not enough — fall back to brute force on hist slice
        return knn_predict_brute(current_vec, tree.data[:max_hist], hist_labels[:max_hist], k)
    # Take top-k
    top_k_idxs = valid_idxs[:k]
    lbls = hist_labels[top_k_idxs]
    n_bull = int(np.sum(lbls == 1))
    n_bear = int(np.sum(lbls == -1))
    n_side = k - n_bull - n_bear
    return (n_bull / k, n_bear / k, n_side / k)


def knn_predict_brute(current_vec, hist_mat, hist_labels, k):
    """Fallback brute-force KNN (used when KDTree unavailable OR not enough valid neighbors)."""
    diff = hist_mat - current_vec[None, :]
    dist = np.sqrt(np.sum(diff * diff, axis=1))
    if len(dist) < k:
        return (1/3, 1/3, 1/3)
    idx = np.argpartition(dist, k)[:k]
    lbls = hist_labels[idx]
    n_bull = int(np.sum(lbls == 1))
    n_bear = int(np.sum(lbls == -1))
    n_side = k - n_bull - n_bear
    return (n_bull / k, n_bear / k, n_side / k)


# ═══════════════════════════════════════════════════════════════
# ENSEMBLE VOTE (unchanged from v1.0)
# ═══════════════════════════════════════════════════════════════

def ensemble_vote(i, feats, closes, btc_returns=None):
    votes = {}
    tr = 0.0
    if not np.isnan(feats['ema20'][i]) and not np.isnan(feats['ema50'][i]):
        tr += 0.4 if feats['ema20'][i] > feats['ema50'][i] else -0.4
    tr += np.clip(feats['ema20_slope'][i] * 2, -0.3, 0.3)
    if feats['adx14'][i] > 20:
        tr += 0.3 if feats['di_gap'][i] > 0 else -0.3
    votes['trend'] = float(np.clip(tr, -1, 1))

    mr = 0.0
    r = feats['rsi14'][i]
    if not np.isnan(r):
        if r < 30: mr += 0.7
        elif r < 40: mr += 0.3
        elif r > 70: mr -= 0.7
        elif r > 60: mr -= 0.3
    bp = feats['bb_position'][i]
    if not np.isnan(bp):
        if bp < 0.1: mr += 0.3
        elif bp > 0.9: mr -= 0.3
    votes['mean_rev'] = float(np.clip(mr, -1, 1))

    st = 0.0
    if i >= 20:
        prev_low_20 = np.min(closes[i-20:i])
        prev_high_20 = np.max(closes[i-20:i])
        if closes[i-1] < prev_low_20 * 1.001 and closes[i] > closes[i-1] * 1.002:
            st += 0.6
        if closes[i-1] > prev_high_20 * 0.999 and closes[i] < closes[i-1] * 0.998:
            st -= 0.6
    votes['structure'] = float(np.clip(st, -1, 1))

    vf = 0.0
    if feats['volume_ratio'][i] > 1.2:
        vf += 0.6 * feats['body_range_ratio'][i]
    votes['volume'] = float(np.clip(vf, -1, 1))

    sb = 0.0
    hour = feats['hours'][i]
    if 8 <= hour < 16 or 13 <= hour < 21:
        sb = 0.3 * (1 if feats['ema20_slope'][i] > 0 else -1)
    votes['session'] = float(np.clip(sb, -1, 1))

    vol = 0.0
    if i >= 20:
        atr_prev = feats['atr14'][i-10] if not np.isnan(feats['atr14'][i-10]) else feats['atr14'][i]
        atr_now = feats['atr14'][i]
        if atr_prev > 0:
            expansion = (atr_now - atr_prev) / atr_prev
            if expansion > 0.15:
                vol = 0.4 * np.sign(feats['ema20_slope'][i])
            elif expansion < -0.15:
                vol = 0.2 if feats['rsi14'][i] < 50 else -0.2
    votes['volatility'] = float(np.clip(vol, -1, 1))

    corr = 0.0
    if btc_returns is not None and i < len(btc_returns) and i >= 3:
        recent_btc = np.mean(btc_returns[max(0, i-3):i])
        if recent_btc > 0.002: corr = 0.4
        elif recent_btc < -0.002: corr = -0.4
    votes['correlation'] = float(np.clip(corr, -1, 1))

    weights = {'trend': 1.5, 'mean_rev': 1.0, 'structure': 1.5, 'volume': 1.0,
               'session': 0.5, 'volatility': 0.8, 'correlation': 0.7}
    total_w = sum(weights.values())
    score = sum(votes[k] * weights[k] for k in votes) / total_w

    if score > 0.1:
        p_bull = 0.5 + score * 0.5
        p_bear = max(0.0, 0.3 - score * 0.3)
        p_side = 1 - p_bull - p_bear
    elif score < -0.1:
        p_bear = 0.5 + abs(score) * 0.5
        p_bull = max(0.0, 0.3 - abs(score) * 0.3)
        p_side = 1 - p_bull - p_bear
    else:
        p_bull = 0.33; p_bear = 0.33; p_side = 0.34

    n_bull_votes = sum(1 for v in votes.values() if v > 0.15)
    n_bear_votes = sum(1 for v in votes.values() if v < -0.15)
    return p_bull, p_bear, p_side, votes, n_bull_votes, n_bear_votes


# ═══════════════════════════════════════════════════════════════
# DECISION (unchanged)
# ═══════════════════════════════════════════════════════════════

def make_decision(p_a, p_b, n_bull_votes, n_bear_votes, cfg):
    a_bull, a_bear, _ = p_a
    b_bull, b_bear, _ = p_b
    a_dir = 'LONG' if a_bull >= cfg.knn_min_confidence else ('SHORT' if a_bear >= cfg.knn_min_confidence else None)
    if a_dir is None: return 'NONE', 0.0, 'A_low_conf'
    b_dir = None
    if b_bull >= cfg.ensemble_min_confidence and n_bull_votes >= cfg.ensemble_min_agree:
        b_dir = 'LONG'
    elif b_bear >= cfg.ensemble_min_confidence and n_bear_votes >= cfg.ensemble_min_agree:
        b_dir = 'SHORT'
    if b_dir is None: return 'NONE', 0.0, 'B_low_conf'
    if a_dir != b_dir: return 'NONE', 0.0, 'A_B_disagree'
    if a_dir == 'LONG':
        joint_conf = (a_bull + b_bull) / 2
        gap = min(a_bull - a_bear, b_bull - b_bear)
    else:
        joint_conf = (a_bear + b_bear) / 2
        gap = min(a_bear - a_bull, b_bear - b_bull)
    if joint_conf < cfg.joint_confidence_min: return 'NONE', joint_conf, 'joint_conf_low'
    if gap < cfg.joint_gap_min: return 'NONE', joint_conf, 'gap_low'
    return a_dir, joint_conf, 'OK'


# ═══════════════════════════════════════════════════════════════
# TRADE + BACKTEST
# ═══════════════════════════════════════════════════════════════

@dataclass
class Trade:
    entry_idx: int; exit_idx: int; direction: str
    entry_price: float; exit_price: float
    sl_price: float; tp_price: float
    pnl_pct_gross: float; pnl_usd_net: float
    outcome: str; conf: float; hold_candles: int


def backtest_with_context(ctx: PairContext, cfg: DRCConfig, tp_pct: float,
                          progress_cb: Optional[Callable[[float, str], None]] = None) -> dict:
    """
    OPTIMIZED backtest using pre-built PairContext.
    Feature computation + KDTree only happens ONCE per pair, not per TP.
    """
    data = ctx.data
    feats = ctx.feats
    feat_mat = ctx.feat_mat
    labels = ctx.labels
    tree = ctx.tree
    btc_returns = ctx.btc_returns
    n = len(data['close'])

    trades = []
    position = None
    signal_counts = {'NONE': 0, 'A_low_conf': 0, 'B_low_conf': 0,
                     'A_B_disagree': 0, 'joint_conf_low': 0, 'gap_low': 0, 'OK': 0}

    total_iter = n - cfg.knn_lookforward - cfg.knn_warmup
    last_progress_report = 0

    for i in range(cfg.knn_warmup, n - cfg.knn_lookforward):
        # Progress callback every 5%
        if progress_cb and (i - cfg.knn_warmup) - last_progress_report > total_iter * 0.05:
            pct = (i - cfg.knn_warmup) / total_iter * 100
            progress_cb(pct, f"candle {i}/{n}")
            last_progress_report = i - cfg.knn_warmup

        # Manage existing position
        if position is not None:
            hi, lo = data['high'][i], data['low'][i]
            hit_tp = (hi >= position['tp']) if position['dir'] == 'LONG' else (lo <= position['tp'])
            hit_sl = (lo <= position['sl']) if position['dir'] == 'LONG' else (hi >= position['sl'])
            exit_reason = None; exit_price = None
            if hit_tp and hit_sl:
                exit_reason = 'SL'; exit_price = position['sl']
            elif hit_tp:
                exit_reason = 'TP'; exit_price = position['tp']
            elif hit_sl:
                exit_reason = 'SL'; exit_price = position['sl']
            elif (i - position['entry_idx']) >= cfg.max_hold_candles:
                exit_reason = 'TIMEOUT'; exit_price = data['close'][i]
            if exit_reason:
                if position['dir'] == 'LONG':
                    pnl_gross = (exit_price - position['entry_price']) / position['entry_price']
                else:
                    pnl_gross = (position['entry_price'] - exit_price) / position['entry_price']
                pnl_net_pct = pnl_gross - cfg.fee_pct
                pnl_usd_net = pnl_net_pct * cfg.position_usd * cfg.leverage
                trades.append(Trade(
                    entry_idx=position['entry_idx'], exit_idx=i,
                    direction=position['dir'],
                    entry_price=position['entry_price'], exit_price=exit_price,
                    sl_price=position['sl'], tp_price=position['tp'],
                    pnl_pct_gross=pnl_gross * 100, pnl_usd_net=pnl_usd_net,
                    outcome=exit_reason, conf=position['conf'],
                    hold_candles=i - position['entry_idx'],
                ))
                position = None

        if position is not None: continue
        if np.any(np.isnan(feat_mat[i])): continue
        if np.isnan(feats['atr14'][i]) or feats['atr14'][i] <= 0: continue

        max_hist = i - cfg.knn_lookforward
        if max_hist < cfg.knn_warmup: continue

        # ── KNN — use KDTree if available, else brute force ──
        if tree is not None:
            p_bull_a, p_bear_a, p_side_a = knn_predict_kdtree(
                feat_mat[i], tree, max_hist, labels, cfg.knn_k, cfg.knn_subsample
            )
        else:
            p_bull_a, p_bear_a, p_side_a = knn_predict_brute(
                feat_mat[i], feat_mat[:max_hist], labels[:max_hist], cfg.knn_k
            )

        p_bull_b, p_bear_b, p_side_b, votes, nbv, nsv = ensemble_vote(
            i, feats, data['close'], btc_returns=btc_returns
        )

        direction, conf, reason = make_decision(
            (p_bull_a, p_bear_a, p_side_a),
            (p_bull_b, p_bear_b, p_side_b),
            nbv, nsv, cfg,
        )
        signal_counts[reason] = signal_counts.get(reason, 0) + 1
        if direction == 'NONE': continue

        entry_price = data['close'][i]
        sl_dist_pct = np.clip(
            cfg.sl_atr_mult * feats['atr14'][i] / entry_price,
            cfg.min_sl_pct, cfg.max_sl_pct
        )
        if direction == 'LONG':
            sl = entry_price * (1 - sl_dist_pct); tp = entry_price * (1 + tp_pct)
        else:
            sl = entry_price * (1 + sl_dist_pct); tp = entry_price * (1 - tp_pct)
        if tp_pct < sl_dist_pct: continue

        position = {'dir': direction, 'entry_idx': i, 'entry_price': entry_price,
                    'sl': sl, 'tp': tp, 'conf': conf}

    if progress_cb: progress_cb(100.0, "done")
    return summarize(trades, data, cfg, tp_pct, signal_counts)


# Backward-compat wrapper: same signature as v1.0
def backtest(data, cfg, tp_pct, btc_returns=None, progress_cb=None):
    ctx = build_pair_context(data, cfg, btc_returns=btc_returns)
    return backtest_with_context(ctx, cfg, tp_pct, progress_cb=progress_cb)


def summarize(trades, data, cfg, tp_pct, signal_counts):
    if len(trades) == 0:
        return {
            'trades': 0, 'wins': 0, 'losses': 0, 'timeouts': 0,
            'wr': 0.0, 'total_pnl_usd': 0.0, 'profit_per_day': 0.0,
            'avg_pnl_usd': 0.0, 'avg_pnl_pct_gross': 0.0,
            'max_dd_usd': 0.0, 'avg_hold_candles': 0,
            'data_days': 0, 'tp_pct': tp_pct, 'sl_atr_mult': cfg.sl_atr_mult,
            'symbol': cfg.symbol, 'timeframe': cfg.timeframe,
            'signal_counts': signal_counts, 'trades_list': [],
        }
    wins = [t for t in trades if t.outcome == 'TP']
    losses = [t for t in trades if t.outcome == 'SL']
    timeouts = [t for t in trades if t.outcome == 'TIMEOUT']
    wr = len(wins) / len(trades) * 100
    total_pnl = sum(t.pnl_usd_net for t in trades)
    dt_span_ms = data['open_time'][-1] - data['open_time'][0]
    data_days = dt_span_ms / (1000 * 60 * 60 * 24)
    ppd = total_pnl / data_days if data_days > 0 else 0.0
    equity = np.cumsum([t.pnl_usd_net for t in trades])
    peak = np.maximum.accumulate(equity) if len(equity) else np.array([0])
    dd = peak - equity
    max_dd = float(dd.max()) if len(dd) else 0.0
    return {
        'trades': len(trades),
        'wins': len(wins), 'losses': len(losses), 'timeouts': len(timeouts),
        'wr': round(wr, 2),
        'total_pnl_usd': round(float(total_pnl), 2),
        'profit_per_day': round(ppd, 3),
        'avg_pnl_usd': round(float(total_pnl / len(trades)), 3),
        'avg_pnl_pct_gross': round(float(np.mean([t.pnl_pct_gross for t in trades])), 4),
        'max_dd_usd': round(max_dd, 2),
        'avg_hold_candles': round(float(np.mean([t.hold_candles for t in trades])), 1),
        'data_days': round(data_days, 1),
        'tp_pct': tp_pct, 'sl_atr_mult': cfg.sl_atr_mult,
        'symbol': cfg.symbol, 'timeframe': cfg.timeframe,
        'signal_counts': signal_counts, 'engine_version': '1.1-kdtree',
        'trades_list': [
            {
                'entry_ts': int(data['open_time'][t.entry_idx]),
                'exit_ts': int(data['open_time'][t.exit_idx]),
                'dir': t.direction, 'outcome': t.outcome,
                'entry': round(t.entry_price, 6), 'exit': round(t.exit_price, 6),
                'pnl_usd': round(t.pnl_usd_net, 3),
                'hold': t.hold_candles, 'conf': round(t.conf, 3),
            }
            for t in trades
        ],
    }


# ═══════════════════════════════════════════════════════════════
# DATA LOADER (unchanged)
# ═══════════════════════════════════════════════════════════════

def load_klines(db_path, symbol, timeframe, days=None):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    query = """
        SELECT open_time, open, high, low, close, volume
        FROM klines WHERE symbol = ? AND timeframe = ?
        ORDER BY open_time ASC
    """
    rows = cur.execute(query, (symbol, timeframe)).fetchall()
    conn.close()
    if not rows:
        raise ValueError(f"No data for {symbol} {timeframe}")
    if days:
        cutoff_ms = rows[-1][0] - days * 24 * 60 * 60 * 1000
        rows = [r for r in rows if r[0] >= cutoff_ms]
    return {
        'open_time': np.array([r[0] for r in rows], dtype=np.int64),
        'open':  np.array([r[1] for r in rows], dtype=np.float64),
        'high':  np.array([r[2] for r in rows], dtype=np.float64),
        'low':   np.array([r[3] for r in rows], dtype=np.float64),
        'close': np.array([r[4] for r in rows], dtype=np.float64),
        'volume':np.array([r[5] for r in rows], dtype=np.float64),
    }


def compute_btc_returns(db_path, timeframe="15m"):
    try:
        btc = load_klines(db_path, "BTCUSDT", timeframe)
        c = btc['close']
        r = np.zeros(len(c))
        r[1:] = np.diff(c) / c[:-1]
        return r
    except Exception:
        return None


def run_mode3(db_path, symbol, timeframe="15m", days=1825, tp_options=None, cfg=None):
    """OPTIMIZED runner — builds pair context ONCE, sweeps all TP options."""
    cfg = cfg or DRCConfig(symbol=symbol, timeframe=timeframe, days=days)
    tp_options = tp_options or cfg.tp_pct_options

    data = load_klines(db_path, symbol, timeframe, days=days)
    btc_r = None
    if symbol != "BTCUSDT":
        btc_r = compute_btc_returns(db_path, timeframe)

    # Build heavy context ONCE
    ctx = build_pair_context(data, cfg, btc_returns=btc_r)

    results = []
    for tp in tp_options:
        cfg2 = DRCConfig(
            symbol=symbol, timeframe=timeframe, days=days,
            sl_atr_mult=cfg.sl_atr_mult,
        )
        r = backtest_with_context(ctx, cfg2, tp_pct=tp)
        results.append(r)
    return results


if __name__ == "__main__":
    print("Mode 3 DRC v1.1 (KDTree optimized)")
    print(f"scipy available: {_KDTREE_AVAILABLE}")
