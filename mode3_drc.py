"""
Mode 3 — Directional Regime Classifier (DRC)
============================================

Konsep: Setiap 15m candle close, engine hitung P(BULL), P(BEAR), P(SIDEWAYS)
via 2 independent predictors yang harus agree:

    Predictor A: KNN Historical Analog Matching
        - Extract feature fingerprint dari current candle
        - Cari 50 candle historis terdekat di feature space (euclidean)
        - Cek apa yang terjadi 4-8 candle setelahnya di analog
        - Return probability empirical dari base rate

    Predictor B: Multi-Model Voting Ensemble
        - 7 sub-models independent, tiap kasih vote arah
        - Trend, mean-reversion, structure, volume flow,
          session bias, volatility regime, correlation (BTC leader)
        - Weighted majority vote

    Entry: A + B agree, both confidence >= 0.75, gap >= 0.5

Author: BabaBot Mode 3 R&D
Target: WR >= 75%, RR >= 1:1, TP 0.3-0.5% bruto per trade
"""

from __future__ import annotations
import numpy as np
import sqlite3
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone


# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

@dataclass
class DRCConfig:
    # Data
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    days: int = 1825  # 5 tahun

    # Predictor A — KNN
    knn_k: int = 50                       # neighbors count
    knn_lookforward: int = 8              # candles ahead to check outcome
    knn_move_threshold: float = 0.004     # 0.4% move to classify direction
    knn_warmup: int = 5000                # min historical candles before KNN active
    knn_min_confidence: float = 0.70      # min P(BULL) or P(BEAR) from KNN to signal

    # Predictor B — Multi-Model Voting
    ensemble_min_confidence: float = 0.60 # weighted vote confidence threshold
    ensemble_min_agree: int = 4           # min sub-models must agree on direction (out of 7)

    # Entry final
    require_both_predictors: bool = True  # A AND B must agree
    joint_confidence_min: float = 0.75    # min avg(A_conf, B_conf)
    joint_gap_min: float = 0.50           # min |P(BULL) - P(BEAR)|

    # Risk
    sl_atr_mult: float = 1.2              # SL = 1.2 × ATR(14)
    tp_pct_options: tuple = (0.003, 0.004, 0.005)  # TP sweep: 0.3%, 0.4%, 0.5%
    max_hold_candles: int = 32            # 32 × 15m = 8 hours max hold
    min_sl_pct: float = 0.001             # SL floor 0.1%
    max_sl_pct: float = 0.005             # SL ceiling 0.5% (RR guard)

    # Simulation
    position_usd: float = 1050.0          # 10.5% of $10k
    leverage: int = 50
    fee_pct: float = 0.001                # 0.10% roundtrip (Binance futures taker)


# ═══════════════════════════════════════════════════════════════
# INDICATOR HELPERS (self-contained, no external TA lib needed)
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
    if avg_loss == 0:
        out[period] = 100
    else:
        rs = avg_gain / avg_loss
        out[period] = 100 - (100 / (1 + rs))
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        if avg_loss == 0:
            out[i] = 100
        else:
            rs = avg_gain / avg_loss
            out[i] = 100 - (100 / (1 + rs))
    return out


def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    tr = np.zeros(n, dtype=np.float64)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    out = np.full(n, np.nan, dtype=np.float64)
    if n < period:
        return out
    out[period - 1] = np.mean(tr[:period])
    for i in range(period, n):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def macd(closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    ef, es = ema(closes, fast), ema(closes, slow)
    macd_line = ef - es
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def adx(highs, lows, closes, period: int = 14):
    """Simplified ADX — returns adx, +DI, -DI"""
    n = len(closes)
    tr = np.zeros(n); dm_p = np.zeros(n); dm_m = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        up = highs[i] - highs[i - 1]
        dn = lows[i - 1] - lows[i]
        dm_p[i] = up if (up > dn and up > 0) else 0
        dm_m[i] = dn if (dn > up and dn > 0) else 0

    def wilder(arr, p):
        out = np.zeros_like(arr, dtype=np.float64)
        if len(arr) < p: return out
        out[p - 1] = np.sum(arr[:p])
        for i in range(p, len(arr)):
            out[i] = out[i - 1] - out[i - 1] / p + arr[i]
        return out

    tr_s = wilder(tr, period)
    dmp_s = wilder(dm_p, period)
    dmm_s = wilder(dm_m, period)
    di_p = np.where(tr_s > 0, 100 * dmp_s / tr_s, 0)
    di_m = np.where(tr_s > 0, 100 * dmm_s / tr_s, 0)
    dx = np.where((di_p + di_m) > 0, 100 * np.abs(di_p - di_m) / (di_p + di_m), 0)

    adx_out = np.zeros(n)
    if n >= 2 * period:
        adx_out[2 * period - 1] = np.mean(dx[period:2 * period])
        for i in range(2 * period, n):
            adx_out[i] = (adx_out[i - 1] * (period - 1) + dx[i]) / period
    return adx_out, di_p, di_m


def bb(closes: np.ndarray, period: int = 20, mult: float = 2.0):
    n = len(closes)
    mid = np.full(n, np.nan); up = np.full(n, np.nan); lo = np.full(n, np.nan)
    for i in range(period - 1, n):
        window = closes[i - period + 1:i + 1]
        m = np.mean(window); s = np.std(window)
        mid[i] = m; up[i] = m + mult * s; lo[i] = m - mult * s
    return mid, up, lo


# ═══════════════════════════════════════════════════════════════
# FEATURE EXTRACTION — 15-dim fingerprint per candle
# ═══════════════════════════════════════════════════════════════

def build_features(data: dict) -> dict:
    """
    Pre-compute all features for the entire series.
    data = {'open','high','low','close','volume','open_time'} numpy arrays
    Returns dict of features (all np arrays same length).
    """
    o, h, l, c, v = data['open'], data['high'], data['low'], data['close'], data['volume']
    n = len(c)

    rsi14 = rsi(c, 14)
    macd_line, macd_sig, macd_hist = macd(c, 12, 26, 9)
    atr14 = atr(h, l, c, 14)
    ema20 = ema(c, 20)
    ema50 = ema(c, 50)
    ema200 = ema(c, 200)
    adx14, dip, dim = adx(h, l, c, 14)
    bb_mid, bb_up, bb_lo = bb(c, 20, 2.0)

    # Derived
    body = c - o
    hl_range = np.where((h - l) > 0, h - l, 1e-9)
    body_range_ratio = body / hl_range  # -1..1, negative = bear body
    atr_pct = atr14 / c * 100
    volume_sma20 = np.full(n, np.nan)
    for i in range(19, n):
        volume_sma20[i] = np.mean(v[i - 19:i + 1])
    volume_ratio = np.where(volume_sma20 > 0, v / volume_sma20, 1.0)

    # close_position within candle range
    close_position = np.where((h - l) > 0, (c - l) / (h - l), 0.5)

    # ema distance %
    ema_dist_20 = (c - ema20) / c * 100
    ema_dist_200 = np.where(~np.isnan(ema200), (c - ema200) / c * 100, 0.0)

    # ema20 slope (linear over 5 candles)
    ema20_slope = np.zeros(n)
    for i in range(4, n):
        if not np.isnan(ema20[i]) and not np.isnan(ema20[i - 4]):
            ema20_slope[i] = (ema20[i] - ema20[i - 4]) / ema20[i - 4] * 100

    # BB position (0=at lower, 0.5=mid, 1=at upper)
    bb_position = np.where(
        (bb_up - bb_lo) > 0,
        (c - bb_lo) / (bb_up - bb_lo),
        0.5
    )

    # DI gap (dip - dim), positive = bullish
    di_gap = dip - dim

    # Hour of day (UTC) — encode as sin/cos for cyclical
    hours = np.zeros(n)
    for i, ts in enumerate(data['open_time']):
        hours[i] = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).hour
    hour_sin = np.sin(2 * np.pi * hours / 24)
    hour_cos = np.cos(2 * np.pi * hours / 24)

    # Prev candle directions (as -1/0/1)
    prev_dir = np.zeros(n)
    for i in range(1, n):
        d = c[i - 1] - o[i - 1]
        if d > 0: prev_dir[i] = 1
        elif d < 0: prev_dir[i] = -1

    # Consecutive same direction count
    consec = np.zeros(n)
    for i in range(1, n):
        d_now = 1 if c[i] > o[i] else (-1 if c[i] < o[i] else 0)
        d_prev = 1 if c[i - 1] > o[i - 1] else (-1 if c[i - 1] < o[i - 1] else 0)
        if d_now == d_prev and d_now != 0:
            consec[i] = consec[i - 1] + 1

    return {
        'rsi14': rsi14,
        'macd_hist': macd_hist,
        'macd_line': macd_line,
        'atr14': atr14,
        'atr_pct': atr_pct,
        'ema20': ema20,
        'ema50': ema50,
        'ema200': ema200,
        'adx14': adx14,
        'di_plus': dip,
        'di_minus': dim,
        'di_gap': di_gap,
        'bb_mid': bb_mid,
        'bb_up': bb_up,
        'bb_lo': bb_lo,
        'bb_position': bb_position,
        'body_range_ratio': body_range_ratio,
        'close_position': close_position,
        'volume_ratio': volume_ratio,
        'ema_dist_20': ema_dist_20,
        'ema_dist_200': ema_dist_200,
        'ema20_slope': ema20_slope,
        'hour_sin': hour_sin,
        'hour_cos': hour_cos,
        'hours': hours,
        'prev_dir': prev_dir,
        'consec': consec,
    }


# Feature names for KNN fingerprint (15 dims chosen for signal density)
KNN_FEATURES = [
    'rsi14', 'macd_hist', 'atr_pct',
    'body_range_ratio', 'close_position', 'volume_ratio',
    'ema_dist_20', 'ema_dist_200', 'ema20_slope',
    'di_gap', 'bb_position',
    'hour_sin', 'hour_cos',
    'prev_dir', 'consec',
]


def normalize_features(feats: dict, feature_names: list) -> tuple:
    """Return (matrix [n, d], means, stds) — z-score normalization."""
    n = len(feats[feature_names[0]])
    d = len(feature_names)
    mat = np.zeros((n, d), dtype=np.float64)
    for j, name in enumerate(feature_names):
        arr = np.array(feats[name], dtype=np.float64)
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        mat[:, j] = arr
    # Compute stats using only warmup+ candles (skip NaN-dominated start)
    means = np.mean(mat, axis=0)
    stds = np.std(mat, axis=0)
    stds = np.where(stds < 1e-9, 1.0, stds)
    mat = (mat - means) / stds
    return mat, means, stds


# ═══════════════════════════════════════════════════════════════
# PREDICTOR A — KNN Historical Analog Matching
# ═══════════════════════════════════════════════════════════════

def compute_forward_labels(closes: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                            lookforward: int, threshold: float) -> np.ndarray:
    """
    For each candle i, look at candles i+1 to i+lookforward:
      - If price moves +threshold BEFORE -threshold → label +1 (BULL)
      - If price moves -threshold BEFORE +threshold → label -1 (BEAR)
      - Else → 0 (SIDEWAYS)
    Uses triple-barrier method (Marcos López de Prado style).
    """
    n = len(closes)
    labels = np.zeros(n, dtype=np.int8)
    for i in range(n - lookforward):
        entry = closes[i]
        up_target = entry * (1 + threshold)
        dn_target = entry * (1 - threshold)
        hit_up = -1; hit_dn = -1
        for k in range(1, lookforward + 1):
            if highs[i + k] >= up_target and hit_up == -1:
                hit_up = k
            if lows[i + k] <= dn_target and hit_dn == -1:
                hit_dn = k
            if hit_up != -1 or hit_dn != -1:
                break
        if hit_up != -1 and (hit_dn == -1 or hit_up < hit_dn):
            labels[i] = 1
        elif hit_dn != -1 and (hit_up == -1 or hit_dn < hit_up):
            labels[i] = -1
        else:
            labels[i] = 0
    return labels


def knn_predict(current_vec: np.ndarray, hist_mat: np.ndarray,
                hist_labels: np.ndarray, k: int) -> tuple:
    """
    Return (p_bull, p_bear, p_sideways) from k nearest historical analogs.
    hist_mat is normalized [m, d]; current_vec is normalized [d].
    """
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
# PREDICTOR B — Multi-Model Voting Ensemble
# ═══════════════════════════════════════════════════════════════

def ensemble_vote(i: int, feats: dict, closes: np.ndarray,
                  btc_returns: Optional[np.ndarray] = None) -> tuple:
    """
    7 sub-models. Each returns score in [-1, +1] (bear ... bull).
    Returns (p_bull, p_bear, p_sideways, votes_dict).
    """
    votes = {}

    # 1) TREND MODEL — EMA20 slope + EMA20 vs EMA50 + ADX direction
    tr = 0.0
    if not np.isnan(feats['ema20'][i]) and not np.isnan(feats['ema50'][i]):
        tr += 0.4 if feats['ema20'][i] > feats['ema50'][i] else -0.4
    tr += np.clip(feats['ema20_slope'][i] * 2, -0.3, 0.3)
    if feats['adx14'][i] > 20:
        tr += 0.3 if feats['di_gap'][i] > 0 else -0.3
    votes['trend'] = float(np.clip(tr, -1, 1))

    # 2) MEAN REVERSION — RSI extreme + BB position
    mr = 0.0
    r = feats['rsi14'][i]
    if not np.isnan(r):
        if r < 30: mr += 0.7        # oversold → bullish
        elif r < 40: mr += 0.3
        elif r > 70: mr -= 0.7      # overbought → bearish
        elif r > 60: mr -= 0.3
    bp = feats['bb_position'][i]
    if not np.isnan(bp):
        if bp < 0.1: mr += 0.3      # at lower band
        elif bp > 0.9: mr -= 0.3    # at upper band
    votes['mean_rev'] = float(np.clip(mr, -1, 1))

    # 3) STRUCTURE — recent liquidity sweep + FVG proxy
    #   Sweep: current low is lowest of last 20 AND close back above low → bull
    st = 0.0
    if i >= 20:
        recent_low = np.min(feats['ema20'][i - 20:i]) if not np.isnan(feats['ema20'][i-20:i]).all() else None
        # crude sweep detection using candle low vs 20-candle low
        candle_low = closes[i] - abs(feats['body_range_ratio'][i]) * feats['atr14'][i]
        # Bull sweep: prev candle made new low, current candle closes above prev high proxy
        prev_low_20 = np.min(closes[i - 20:i])
        prev_high_20 = np.max(closes[i - 20:i])
        if closes[i - 1] < prev_low_20 * 1.001 and closes[i] > closes[i - 1] * 1.002:
            st += 0.6  # bullish sweep
        if closes[i - 1] > prev_high_20 * 0.999 and closes[i] < closes[i - 1] * 0.998:
            st -= 0.6  # bearish sweep
    votes['structure'] = float(np.clip(st, -1, 1))

    # 4) VOLUME FLOW — body direction × volume ratio
    vf = 0.0
    if feats['volume_ratio'][i] > 1.2:
        vf += 0.6 * feats['body_range_ratio'][i]  # -1..1 sign follows body
    votes['volume'] = float(np.clip(vf, -1, 1))

    # 5) SESSION BIAS — London (8-16 UTC) + NY (13-21 UTC) skew
    sb = 0.0
    hour = feats['hours'][i]
    if 8 <= hour < 16 or 13 <= hour < 21:
        # In active sessions, follow trend
        sb = 0.3 * (1 if feats['ema20_slope'][i] > 0 else -1)
    votes['session'] = float(np.clip(sb, -1, 1))

    # 6) VOLATILITY REGIME — expanding ATR favors trend, contracting favors reversion
    vol = 0.0
    if i >= 20:
        atr_prev = feats['atr14'][i - 10] if not np.isnan(feats['atr14'][i - 10]) else feats['atr14'][i]
        atr_now = feats['atr14'][i]
        if atr_prev > 0:
            expansion = (atr_now - atr_prev) / atr_prev
            if expansion > 0.15:  # expanding → follow trend
                vol = 0.4 * np.sign(feats['ema20_slope'][i])
            elif expansion < -0.15:  # contracting → mild bull bias if RSI < 50
                vol = 0.2 if feats['rsi14'][i] < 50 else -0.2
    votes['volatility'] = float(np.clip(vol, -1, 1))

    # 7) CORRELATION / BTC LEADER — for alts, BTC direction leads
    corr = 0.0
    if btc_returns is not None and i < len(btc_returns) and i >= 3:
        recent_btc = np.mean(btc_returns[max(0, i - 3):i])
        if recent_btc > 0.002: corr = 0.4
        elif recent_btc < -0.002: corr = -0.4
    votes['correlation'] = float(np.clip(corr, -1, 1))

    # Aggregate — weighted sum
    weights = {
        'trend': 1.5,
        'mean_rev': 1.0,
        'structure': 1.5,
        'volume': 1.0,
        'session': 0.5,
        'volatility': 0.8,
        'correlation': 0.7,
    }
    total_w = sum(weights.values())
    score = sum(votes[k] * weights[k] for k in votes) / total_w  # -1..1

    # Convert to probabilities
    # score > 0 → more bull; use softmax-like squash
    if score > 0.1:
        p_bull = 0.5 + score * 0.5  # 0.55 .. 1.0
        p_bear = max(0.0, 0.3 - score * 0.3)
        p_side = 1 - p_bull - p_bear
    elif score < -0.1:
        p_bear = 0.5 + abs(score) * 0.5
        p_bull = max(0.0, 0.3 - abs(score) * 0.3)
        p_side = 1 - p_bull - p_bear
    else:
        p_bull = 0.33; p_bear = 0.33; p_side = 0.34

    # Count agreeing sub-models
    n_bull_votes = sum(1 for v in votes.values() if v > 0.15)
    n_bear_votes = sum(1 for v in votes.values() if v < -0.15)

    return p_bull, p_bear, p_side, votes, n_bull_votes, n_bear_votes


# ═══════════════════════════════════════════════════════════════
# DECISION — combine A + B
# ═══════════════════════════════════════════════════════════════

def make_decision(p_a: tuple, p_b: tuple, n_bull_votes: int, n_bear_votes: int,
                  cfg: DRCConfig) -> tuple:
    """
    p_a = (bull, bear, side) from KNN
    p_b = (bull, bear, side) from Ensemble
    Returns ('LONG'|'SHORT'|'NONE', conf, reason)
    """
    a_bull, a_bear, _ = p_a
    b_bull, b_bear, _ = p_b

    # Predictor A gate
    a_dir = 'LONG' if a_bull >= cfg.knn_min_confidence else ('SHORT' if a_bear >= cfg.knn_min_confidence else None)
    if a_dir is None:
        return 'NONE', 0.0, 'A_low_conf'

    # Predictor B gate — must agree direction AND meet threshold
    b_dir = None
    if b_bull >= cfg.ensemble_min_confidence and n_bull_votes >= cfg.ensemble_min_agree:
        b_dir = 'LONG'
    elif b_bear >= cfg.ensemble_min_confidence and n_bear_votes >= cfg.ensemble_min_agree:
        b_dir = 'SHORT'
    if b_dir is None:
        return 'NONE', 0.0, 'B_low_conf'

    if a_dir != b_dir:
        return 'NONE', 0.0, 'A_B_disagree'

    # Joint checks
    if a_dir == 'LONG':
        joint_conf = (a_bull + b_bull) / 2
        gap = min(a_bull - a_bear, b_bull - b_bear)
    else:
        joint_conf = (a_bear + b_bear) / 2
        gap = min(a_bear - a_bull, b_bear - b_bull)

    if joint_conf < cfg.joint_confidence_min:
        return 'NONE', joint_conf, 'joint_conf_low'
    if gap < cfg.joint_gap_min:
        return 'NONE', joint_conf, 'gap_low'

    return a_dir, joint_conf, 'OK'


# ═══════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════

@dataclass
class Trade:
    entry_idx: int
    exit_idx: int
    direction: str
    entry_price: float
    exit_price: float
    sl_price: float
    tp_price: float
    pnl_pct_gross: float
    pnl_usd_net: float
    outcome: str  # 'TP'|'SL'|'TIMEOUT'
    conf: float
    hold_candles: int


def backtest(data: dict, cfg: DRCConfig, tp_pct: float,
             btc_returns: Optional[np.ndarray] = None,
             verbose: bool = False) -> dict:
    """
    Main backtest. Returns metrics dict + trades list.
    Uses 1 position at a time (per user requirement).
    """
    feats = build_features(data)
    n = len(data['close'])

    # Forward labels for KNN training (only usable for i < n - lookforward)
    labels = compute_forward_labels(
        data['close'], data['high'], data['low'],
        cfg.knn_lookforward, cfg.knn_move_threshold
    )

    # Normalize feature matrix once
    feat_mat, _, _ = normalize_features(feats, KNN_FEATURES)

    trades = []
    position = None  # {'dir', 'entry_idx', 'entry_price', 'sl', 'tp', 'conf'}
    signal_counts = {'NONE': 0, 'A_low_conf': 0, 'B_low_conf': 0,
                     'A_B_disagree': 0, 'joint_conf_low': 0, 'gap_low': 0, 'OK': 0}

    for i in range(cfg.knn_warmup, n - cfg.knn_lookforward):
        # ── STEP 1: manage existing position ──
        if position is not None:
            hi, lo = data['high'][i], data['low'][i]
            hit_tp = (hi >= position['tp']) if position['dir'] == 'LONG' else (lo <= position['tp'])
            hit_sl = (lo <= position['sl']) if position['dir'] == 'LONG' else (hi >= position['sl'])
            exit_reason = None; exit_price = None
            if hit_tp and hit_sl:
                # Ambiguous — assume SL first (conservative)
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
                    pnl_pct_gross=pnl_gross * 100,
                    pnl_usd_net=pnl_usd_net,
                    outcome=exit_reason, conf=position['conf'],
                    hold_candles=i - position['entry_idx'],
                ))
                position = None

        # ── STEP 2: skip if position still open ──
        if position is not None:
            continue

        # ── STEP 3: extract signal at this candle close ──
        # Guard against feature NaNs
        if np.any(np.isnan(feat_mat[i])):
            continue
        if np.isnan(feats['atr14'][i]) or feats['atr14'][i] <= 0:
            continue

        # Predictor A — KNN over ALL historical data before i (no lookahead)
        # Use only labels that are already realized (i.e. index + lookforward <= i)
        max_hist = i - cfg.knn_lookforward
        if max_hist < cfg.knn_warmup:
            continue
        hist_slice = feat_mat[:max_hist]
        label_slice = labels[:max_hist]
        # Filter out zero-label (sideways) samples? No — keep, they contribute to p_side
        p_bull_a, p_bear_a, p_side_a = knn_predict(
            feat_mat[i], hist_slice, label_slice, cfg.knn_k
        )

        # Predictor B — Ensemble
        p_bull_b, p_bear_b, p_side_b, votes, nbv, nsv = ensemble_vote(
            i, feats, data['close'], btc_returns=btc_returns
        )

        # Decision
        direction, conf, reason = make_decision(
            (p_bull_a, p_bear_a, p_side_a),
            (p_bull_b, p_bear_b, p_side_b),
            nbv, nsv, cfg
        )
        signal_counts[reason] = signal_counts.get(reason, 0) + 1

        if direction == 'NONE':
            continue

        # ── STEP 4: open position with dynamic SL, fixed TP% ──
        entry_price = data['close'][i]
        sl_dist_pct = np.clip(
            cfg.sl_atr_mult * feats['atr14'][i] / entry_price,
            cfg.min_sl_pct, cfg.max_sl_pct
        )
        if direction == 'LONG':
            sl = entry_price * (1 - sl_dist_pct)
            tp = entry_price * (1 + tp_pct)
        else:
            sl = entry_price * (1 + sl_dist_pct)
            tp = entry_price * (1 - tp_pct)

        # RR guard: reject if TP < SL_dist (would violate RR ≥ 1:1)
        if tp_pct < sl_dist_pct:
            continue

        position = {
            'dir': direction, 'entry_idx': i, 'entry_price': entry_price,
            'sl': sl, 'tp': tp, 'conf': conf,
        }

    # ── Compute metrics ──
    return summarize(trades, data, cfg, tp_pct, signal_counts)


def summarize(trades: list, data: dict, cfg: DRCConfig, tp_pct: float,
              signal_counts: dict) -> dict:
    if len(trades) == 0:
        return {
            'trades': 0, 'wins': 0, 'losses': 0, 'timeouts': 0,
            'wr': 0.0, 'total_pnl_usd': 0.0,
            'profit_per_day': 0.0, 'avg_pnl_usd': 0.0,
            'avg_pnl_pct_gross': 0.0,
            'max_dd_usd': 0.0, 'avg_hold_candles': 0,
            'data_days': 0, 'tp_pct': tp_pct,
            'sl_atr_mult': cfg.sl_atr_mult,
            'symbol': cfg.symbol, 'timeframe': cfg.timeframe,
            'signal_counts': signal_counts, 'trades_list': [],
        }
    wins = [t for t in trades if t.outcome == 'TP']
    losses = [t for t in trades if t.outcome == 'SL']
    timeouts = [t for t in trades if t.outcome == 'TIMEOUT']
    wr = len(wins) / len(trades) * 100
    total_pnl = sum(t.pnl_usd_net for t in trades)
    # Data-days from time span
    dt_span_ms = data['open_time'][-1] - data['open_time'][0]
    data_days = dt_span_ms / (1000 * 60 * 60 * 24)
    ppd = total_pnl / data_days if data_days > 0 else 0.0

    # Equity + drawdown
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
        'tp_pct': tp_pct,
        'sl_atr_mult': cfg.sl_atr_mult,
        'symbol': cfg.symbol, 'timeframe': cfg.timeframe,
        'signal_counts': signal_counts,
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
# DATA LOADER — reads Railway SQLite `klines` table
# ═══════════════════════════════════════════════════════════════

def load_klines(db_path: str, symbol: str, timeframe: str,
                days: Optional[int] = None) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    query = """
        SELECT open_time, open, high, low, close, volume
        FROM klines
        WHERE symbol = ? AND timeframe = ?
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


def compute_btc_returns(db_path: str, timeframe: str = "15m") -> Optional[np.ndarray]:
    """Load BTCUSDT closes and compute pct returns for correlation model."""
    try:
        btc = load_klines(db_path, "BTCUSDT", timeframe)
        c = btc['close']
        r = np.zeros(len(c))
        r[1:] = np.diff(c) / c[:-1]
        return r
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# HIGH-LEVEL RUNNER
# ═══════════════════════════════════════════════════════════════

def run_mode3(db_path: str, symbol: str, timeframe: str = "15m",
              days: int = 1825, tp_options=None, cfg: DRCConfig = None) -> list:
    """
    Sweep TP options for a single pair. Returns list of results (one per TP).
    """
    cfg = cfg or DRCConfig(symbol=symbol, timeframe=timeframe, days=days)
    tp_options = tp_options or cfg.tp_pct_options

    data = load_klines(db_path, symbol, timeframe, days=days)
    btc_r = None
    if symbol != "BTCUSDT":
        btc_r = compute_btc_returns(db_path, timeframe)
        # Align by timestamp — simple length match assumption (both timeframes same)

    results = []
    for tp in tp_options:
        cfg2 = DRCConfig(
            symbol=symbol, timeframe=timeframe, days=days,
            sl_atr_mult=cfg.sl_atr_mult,
        )
        r = backtest(data, cfg2, tp_pct=tp, btc_returns=btc_r)
        results.append(r)
    return results


if __name__ == "__main__":
    # Quick self-test with synthetic random walk data
    print("Mode 3 DRC — self-test with synthetic data")
    np.random.seed(42)
    n = 20000
    ts_start = 1704067200000  # 2024-01-01
    ts = ts_start + np.arange(n) * 15 * 60 * 1000
    price = 50000 + np.cumsum(np.random.randn(n) * 20)
    high = price + np.abs(np.random.randn(n) * 15)
    low = price - np.abs(np.random.randn(n) * 15)
    open_ = np.roll(price, 1); open_[0] = price[0]
    vol = np.abs(np.random.randn(n) * 100 + 500)

    data = {
        'open_time': ts.astype(np.int64),
        'open': open_, 'high': high, 'low': low,
        'close': price, 'volume': vol,
    }
    cfg = DRCConfig(symbol="TEST", timeframe="15m", days=200,
                    knn_warmup=1000)
    for tp in [0.003, 0.004, 0.005]:
        r = backtest(data, cfg, tp_pct=tp)
        print(f"TP {tp*100:.1f}%: trades={r['trades']}, WR={r['wr']}%, "
              f"PPD=${r['profit_per_day']}, avg_pnl=${r['avg_pnl_usd']}")
