"""
BabaBot AI Strategy Discovery — Step 1B: Backtesting Core v2
Full search space support: 18 indicators, 7 entry logics, 5 filters, dynamic SL/TP
"""

import sqlite3
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# CONFIG
# ============================================================

@dataclass
class StrategyConfig:
    symbol: str = "BTCUSDT"
    timeframe: str = "5m"
    
    # Entry/Exit Logic
    entry_logic: str = "ema_cross"
    entry_logic_2: Optional[str] = None  # Level 2: second entry for AND confirmation
    exit_logic: str = "sl_tp"           # "sl_tp" or "indicator"
    
    # Indicator Parameters
    indicators: dict = field(default_factory=lambda: {
        # Trend
        "ema_fast": 9, "ema_slow": 21,
        "sma_fast": 10, "sma_slow": 50,
        "supertrend_period": 10, "supertrend_factor": 3.0,
        "sar_acceleration": 0.02, "sar_max": 0.2,
        "ichimoku_tenkan": 9, "ichimoku_kijun": 26, "ichimoku_senkou": 52,
        # Momentum
        "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70,
        "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
        "stoch_k": 14, "stoch_d": 3, "stoch_oversold": 20, "stoch_overbought": 80,
        "adx_period": 14, "adx_threshold": 25,
        "cci_period": 14, "cci_oversold": -100, "cci_overbought": 100,
        # Volume
        "volume_sma_period": 20, "volume_spike_mult": 2.0,
        "taker_buy_ratio_threshold": 0.55,
        "obv_ema_period": 20,
        # Volatility
        "bb_period": 20, "bb_std": 2.0,
        "atr_period": 14,
        "keltner_period": 20, "keltner_mult": 1.5,
        "donchian_period": 20,
    })
    
    # Risk Management
    sl_pct: float = 0.3
    tp_pct: float = 0.8
    sl_atr_mult: float = 1.5        # Kalau pakai dynamic SL
    tp_atr_mult: float = 3.0        # Kalau pakai dynamic TP
    use_atr_sl_tp: bool = False      # True = dynamic, False = fixed %
    sl_check_mode: str = "wick"      # "wick" = check high/low, "close" = check close only
    
    # Costs
    fee_pct: float = 0.10         # Binance Futures taker 0.05% x2
    slippage_pct: float = 0.01
    
    # Capital
    initial_capital: float = 10000.0  # $10K modal
    position_size_pct: float = 10.5   # ~$1,050 per trade
    
    # Data
    days: int = 90
    train_pct: float = 75.0
    start_date: Optional[str] = None  # "2024-01-01" — if set, overrides days
    end_date: Optional[str] = None    # "2024-12-31"
    
    # Filters
    direction: str = "both"
    session_filter: Optional[str] = None      # "asia", "london", "ny", "london_ny"
    trend_filter: Optional[str] = None        # "ema200_long", "ema200_short", "adx_direction"
    volatility_filter: Optional[str] = None   # "atr_min", "atr_max", "bb_squeeze"
    volume_filter: Optional[str] = None       # "volume_spike", "taker_buy"
    regime_filter: Optional[str] = None       # "trending", "ranging"
    
    # Filter thresholds
    atr_min_threshold: float = 0.0
    atr_max_threshold: float = 999.0
    bb_squeeze_threshold: float = 0.02
    volume_min_mult: float = 1.5


# ============================================================
# RESULT
# ============================================================

@dataclass
class BacktestResult:
    symbol: str = ""
    timeframe: str = ""
    entry_logic: str = ""
    entry_logic_2: str = ""  # Level 2: second entry logic (if used)
    sl_type: str = "fixed"
    sl_check_mode: str = "wick"
    
    total_trades: int = 0
    win_rate: float = 0.0
    profit_per_day: float = 0.0
    net_profit: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_rr: float = 0.0
    max_consecutive_losses: int = 0
    
    long_trades: int = 0
    short_trades: int = 0
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0
    
    oos_win_rate: float = 0.0
    oos_profit_per_day: float = 0.0
    oos_trades: int = 0
    
    # Stage 6: Trade duration metrics
    avg_trade_duration_hours: float = 0.0
    min_trade_duration_hours: float = 0.0
    max_trade_duration_hours: float = 0.0
    avg_bars_held: float = 0.0
    
    # Stage 6: Drawdown sequence metrics
    avg_drawdown_duration_bars: float = 0.0
    max_drawdown_duration_bars: int = 0
    avg_drawdown_recovery_bars: float = 0.0
    max_drawdown_recovery_bars: int = 0
    drawdown_periods: int = 0
    
    status: str = "ok"
    error: str = ""
    data_days: float = 0.0
    meets_criteria: bool = False
    regime_stats: dict = None  # per-regime WR and P&L
    avg_max_wick_against: float = 0.0  # avg worst wick against per trade
    avg_max_wick_favor: float = 0.0   # avg best wick in favor per trade
    pct_trades_wick_hit_sl: float = 0.0  # % trades where wick would've hit SL
    pct_trades_wick_hit_tp: float = 0.0  # % trades where wick reached TP zone
    suggested_tp: float = 0.0  # optimal TP based on wick data (75th percentile)
    equity_curve: list = field(default_factory=list)  # Stage 10: equity points for charting
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def summary(self) -> str:
        if self.status != "ok":
            return f"❌ {self.status}: {self.error}"
        criteria = "✅ MEETS CRITERIA" if self.meets_criteria else "❌ Below criteria"
        duration_str = ""
        if self.avg_trade_duration_hours > 0:
            if self.avg_trade_duration_hours >= 24:
                duration_str = f"\nDuration: avg {self.avg_trade_duration_hours/24:.1f}d | min {self.min_trade_duration_hours/24:.1f}d | max {self.max_trade_duration_hours/24:.1f}d"
            else:
                duration_str = f"\nDuration: avg {self.avg_trade_duration_hours:.1f}h | min {self.min_trade_duration_hours:.1f}h | max {self.max_trade_duration_hours:.1f}h"
        dd_str = ""
        if self.drawdown_periods > 0:
            dd_str = f"\nDD Periods: {self.drawdown_periods} | Avg Duration: {self.avg_drawdown_duration_bars:.0f} trades | Max Recovery: {self.max_drawdown_recovery_bars} trades"
        return (
            f"{criteria}\n"
            f"{self.symbol} {self.timeframe} | {self.entry_logic}"
            f"{' AND ' + self.entry_logic_2 if self.entry_logic_2 else ''}\n"
            f"Trades: {self.total_trades} | WR: {self.win_rate:.1f}% | "
            f"P/day: ${self.profit_per_day:.2f} | DD: {self.max_drawdown:.1f}%\n"
            f"Sharpe: {self.sharpe_ratio:.2f} | PF: {self.profit_factor:.2f} | "
            f"MaxConsecLoss: {self.max_consecutive_losses}"
            f"{duration_str}{dd_str}\n"
            f"OOS: {self.oos_trades} trades | WR: {self.oos_win_rate:.1f}% | "
            f"P/day: ${self.oos_profit_per_day:.2f}"
        )


# ============================================================
# INDICATORS
# ============================================================

def calc_ema(prices: np.ndarray, period: int) -> np.ndarray:
    ema = np.full_like(prices, np.nan)
    if len(prices) < period:
        return ema
    k = 2.0 / (period + 1)
    ema[period - 1] = np.mean(prices[:period])
    for i in range(period, len(prices)):
        ema[i] = prices[i] * k + ema[i-1] * (1 - k)
    return ema

def calc_sma(prices: np.ndarray, period: int) -> np.ndarray:
    sma = np.full_like(prices, np.nan)
    for i in range(period - 1, len(prices)):
        sma[i] = np.mean(prices[i - period + 1:i + 1])
    return sma

def calc_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    rsi = np.full_like(closes, np.nan)
    if len(closes) < period + 1:
        return rsi
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(closes) - 1):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
        rsi[i + 1] = 100 - (100 / (1 + rs))
    return rsi

def calc_macd(closes, fast, slow, signal):
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(np.where(np.isnan(macd_line), 0, macd_line), signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calc_bb(closes, period, std_mult):
    upper = np.full_like(closes, np.nan)
    middle = np.full_like(closes, np.nan)
    lower = np.full_like(closes, np.nan)
    width = np.full_like(closes, np.nan)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        mid = np.mean(window)
        std = np.std(window, ddof=0)
        middle[i] = mid
        upper[i] = mid + std_mult * std
        lower[i] = mid - std_mult * std
        width[i] = (upper[i] - lower[i]) / mid if mid != 0 else 0
    return upper, middle, lower, width

def calc_atr(highs, lows, closes, period) -> np.ndarray:
    atr = np.full_like(closes, np.nan)
    if len(closes) < period + 1:
        return atr
    tr = np.maximum(highs[1:] - lows[1:],
         np.maximum(np.abs(highs[1:] - closes[:-1]),
                    np.abs(lows[1:] - closes[:-1])))
    atr_val = np.mean(tr[:period])
    atr[period] = atr_val
    for i in range(period + 1, len(closes)):
        atr_val = (atr_val * (period - 1) + tr[i - 1]) / period
        atr[i] = atr_val
    return atr

def calc_stoch(highs, lows, closes, k_period, d_period):
    stoch_k = np.full_like(closes, np.nan)
    for i in range(k_period - 1, len(closes)):
        h = np.max(highs[i - k_period + 1:i + 1])
        l = np.min(lows[i - k_period + 1:i + 1])
        stoch_k[i] = (closes[i] - l) / (h - l) * 100 if h != l else 50.0
    stoch_d = calc_ema(np.where(np.isnan(stoch_k), 0, stoch_k), d_period)
    return stoch_k, stoch_d

def calc_cci(highs, lows, closes, period):
    cci = np.full_like(closes, np.nan)
    for i in range(period - 1, len(closes)):
        tp = (highs[i-period+1:i+1] + lows[i-period+1:i+1] + closes[i-period+1:i+1]) / 3
        mean_tp = np.mean(tp)
        mean_dev = np.mean(np.abs(tp - mean_tp))
        cci[i] = (tp[-1] - mean_tp) / (0.015 * mean_dev) if mean_dev != 0 else 0
    return cci

def calc_obv(closes, volumes):
    obv = np.zeros_like(closes)
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv[i] = obv[i-1] + volumes[i]
        elif closes[i] < closes[i-1]:
            obv[i] = obv[i-1] - volumes[i]
        else:
            obv[i] = obv[i-1]
    return obv

def calc_supertrend(highs, lows, closes, period, factor):
    atr = calc_atr(highs, lows, closes, period)
    upper_band = np.full_like(closes, np.nan)
    lower_band = np.full_like(closes, np.nan)
    supertrend = np.full_like(closes, np.nan)
    direction = np.zeros_like(closes, dtype=int)  # 1=up, -1=down
    
    for i in range(period, len(closes)):
        if np.isnan(atr[i]):
            continue
        hl2 = (highs[i] + lows[i]) / 2
        basic_upper = hl2 + factor * atr[i]
        basic_lower = hl2 - factor * atr[i]
        
        # Upper band
        if i == period:
            upper_band[i] = basic_upper
            lower_band[i] = basic_lower
        else:
            upper_band[i] = basic_upper if (basic_upper < upper_band[i-1] or closes[i-1] > upper_band[i-1]) else upper_band[i-1]
            lower_band[i] = basic_lower if (basic_lower > lower_band[i-1] or closes[i-1] < lower_band[i-1]) else lower_band[i-1]
        
        # Direction
        if i == period:
            direction[i] = 1 if closes[i] > upper_band[i] else -1
        else:
            if direction[i-1] == -1 and closes[i] > upper_band[i]:
                direction[i] = 1
            elif direction[i-1] == 1 and closes[i] < lower_band[i]:
                direction[i] = -1
            else:
                direction[i] = direction[i-1]
        
        supertrend[i] = lower_band[i] if direction[i] == 1 else upper_band[i]
    
    return supertrend, direction

def calc_donchian(highs, lows, period):
    dc_upper = np.full_like(highs, np.nan)
    dc_lower = np.full_like(lows, np.nan)
    dc_mid = np.full_like(highs, np.nan)
    for i in range(period - 1, len(highs)):
        dc_upper[i] = np.max(highs[i - period + 1:i + 1])
        dc_lower[i] = np.min(lows[i - period + 1:i + 1])
        dc_mid[i] = (dc_upper[i] + dc_lower[i]) / 2
    return dc_upper, dc_lower, dc_mid

def calc_keltner(highs, lows, closes, period, mult):
    mid = calc_ema(closes, period)
    atr = calc_atr(highs, lows, closes, period)
    upper = mid + mult * atr
    lower = mid - mult * atr
    return upper, mid, lower

def calc_adx(highs, lows, closes, period):
    adx = np.full_like(closes, np.nan)
    di_plus = np.full_like(closes, np.nan)
    di_minus = np.full_like(closes, np.nan)
    if len(closes) < period * 2:
        return adx, di_plus, di_minus
    
    dm_plus = np.maximum(highs[1:] - highs[:-1], 0.0)
    dm_minus = np.maximum(lows[:-1] - lows[1:], 0.0)
    mask = dm_plus <= dm_minus
    dm_plus_f = dm_plus.copy()
    dm_minus_f = dm_minus.copy()
    dm_plus_f[mask] = 0
    dm_minus_f[~mask] = 0
    
    tr = np.maximum(highs[1:] - lows[1:],
         np.maximum(np.abs(highs[1:] - closes[:-1]),
                    np.abs(lows[1:] - closes[:-1])))
    
    def wilder_smooth(arr, p):
        result = np.full(len(arr) + 1, np.nan)
        result[p] = np.sum(arr[:p])
        for i in range(p + 1, len(arr) + 1):
            result[i] = result[i-1] - result[i-1]/p + arr[i-1]
        return result[1:]
    
    tr_s = wilder_smooth(tr, period)
    dmp_s = wilder_smooth(dm_plus_f, period)
    dmm_s = wilder_smooth(dm_minus_f, period)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        dip = np.where(tr_s > 0, dmp_s / tr_s * 100, 0)
        dim = np.where(tr_s > 0, dmm_s / tr_s * 100, 0)
        dx = np.where((dip + dim) > 0, np.abs(dip - dim) / (dip + dim) * 100, 0)
    
    adx_val = np.mean(dx[:period])
    adx_out = np.full(len(closes), np.nan)
    adx_out[period * 2] = adx_val
    for i in range(period * 2 + 1, len(closes)):
        adx_val = (adx_val * (period - 1) + dx[i - period]) / period
        adx_out[i] = adx_val
    
    # Fix array size mismatch — dip/dim derived from diff (n-1 elements)
    dip_len = len(dip)
    dim_len = len(dim)
    di_plus[1:dip_len+1] = dip
    di_minus[1:dim_len+1] = dim
    
    return adx_out, di_plus, di_minus

def calc_parabolic_sar(highs, lows, acceleration=0.02, max_af=0.2):
    sar = np.full_like(highs, np.nan)
    trend = np.zeros_like(highs, dtype=int)
    if len(highs) < 2:
        return sar, trend
    
    af = acceleration
    ep = lows[0]
    sar[0] = highs[0]
    trend[0] = -1  # start bearish
    
    for i in range(1, len(highs)):
        prev_sar = sar[i-1]
        if trend[i-1] == 1:  # Uptrend
            sar[i] = prev_sar + af * (ep - prev_sar)
            sar[i] = min(sar[i], lows[i-1], lows[i-2] if i > 1 else lows[i-1])
            if lows[i] < sar[i]:
                trend[i] = -1
                sar[i] = ep
                ep = lows[i]
                af = acceleration
            else:
                trend[i] = 1
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + acceleration, max_af)
        else:  # Downtrend
            sar[i] = prev_sar + af * (ep - prev_sar)
            sar[i] = max(sar[i], highs[i-1], highs[i-2] if i > 1 else highs[i-1])
            if highs[i] > sar[i]:
                trend[i] = 1
                sar[i] = ep
                ep = highs[i]
                af = acceleration
            else:
                trend[i] = -1
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + acceleration, max_af)
    
    return sar, trend

def calc_ichimoku(highs, lows, closes, tenkan=9, kijun=26, senkou=52):
    def mid(h, l, p):
        result = np.full_like(closes, np.nan)
        for i in range(p-1, len(closes)):
            result[i] = (np.max(h[i-p+1:i+1]) + np.min(l[i-p+1:i+1])) / 2
        return result
    
    tenkan_sen = mid(highs, lows, tenkan)
    kijun_sen = mid(highs, lows, kijun)
    chikou = np.roll(closes, -kijun)
    senkou_a = np.roll((tenkan_sen + kijun_sen) / 2, kijun)
    senkou_b_base = mid(highs, lows, senkou)
    senkou_b = np.roll(senkou_b_base, kijun)
    
    return tenkan_sen, kijun_sen, senkou_a, senkou_b, chikou

def calc_vwap(highs, lows, closes, volumes, open_times=None):
    typical_price = (highs + lows + closes) / 3
    n = len(closes)
    vwap = np.full(n, np.nan)
    
    if open_times is not None and len(open_times) == n:
        # Daily reset VWAP
        cum_tp_vol = 0.0
        cum_vol = 0.0
        prev_day = -1
        for i in range(n):
            # Determine day from timestamp (ms)
            cur_day = int(open_times[i] // 86_400_000)
            if cur_day != prev_day:
                cum_tp_vol = 0.0
                cum_vol = 0.0
                prev_day = cur_day
            cum_tp_vol += typical_price[i] * volumes[i]
            cum_vol += volumes[i]
            vwap[i] = cum_tp_vol / cum_vol if cum_vol > 0 else np.nan
    else:
        # Fallback: cumulative (no reset)
        cum_tp_vol = np.cumsum(typical_price * volumes)
        cum_vol = np.cumsum(volumes)
        vwap = np.where(cum_vol > 0, cum_tp_vol / cum_vol, np.nan)
    
    return vwap


# ============================================================
# PRECOMPUTE ALL INDICATORS
# ============================================================

def precompute_indicators(data: dict, config: StrategyConfig) -> dict:
    """Pre-compute semua indikator yang mungkin dibutuhkan."""
    closes = data['close']
    highs = data['high']
    lows = data['low']
    volumes = data['volume']
    taker_buy = data.get('taker_buy_volume', volumes * 0.5)
    ind = config.indicators
    
    result = {}
    
    # Trend
    result['ema_fast'] = calc_ema(closes, ind.get('ema_fast', 9))
    result['ema_slow'] = calc_ema(closes, ind.get('ema_slow', 21))
    result['ema_200'] = calc_ema(closes, 200)
    result['sma_fast'] = calc_sma(closes, ind.get('sma_fast', 10))
    result['sma_slow'] = calc_sma(closes, ind.get('sma_slow', 50))
    result['supertrend'], result['supertrend_dir'] = calc_supertrend(
        highs, lows, closes,
        ind.get('supertrend_period', 10), ind.get('supertrend_factor', 3.0))
    result['sar'], result['sar_trend'] = calc_parabolic_sar(
        highs, lows,
        ind.get('sar_acceleration', 0.02), ind.get('sar_max', 0.2))
    result['tenkan'], result['kijun'], result['senkou_a'], result['senkou_b'], result['chikou'] = calc_ichimoku(
        highs, lows, closes,
        ind.get('ichimoku_tenkan', 9), ind.get('ichimoku_kijun', 26), ind.get('ichimoku_senkou', 52))
    result['vwap'] = calc_vwap(highs, lows, closes, volumes, data.get('open_time'))
    
    # Momentum
    result['rsi'] = calc_rsi(closes, ind.get('rsi_period', 14))
    result['macd'], result['macd_signal'], result['macd_hist'] = calc_macd(
        closes, ind.get('macd_fast', 12), ind.get('macd_slow', 26), ind.get('macd_signal', 9))
    result['stoch_k'], result['stoch_d'] = calc_stoch(
        highs, lows, closes, ind.get('stoch_k', 14), ind.get('stoch_d', 3))
    result['adx'], result['di_plus'], result['di_minus'] = calc_adx(
        highs, lows, closes, ind.get('adx_period', 14))
    result['cci'] = calc_cci(highs, lows, closes, ind.get('cci_period', 14))
    
    # Volume
    result['obv'] = calc_obv(closes, volumes)
    result['obv_ema'] = calc_ema(result['obv'], ind.get('obv_ema_period', 20))
    result['volume_sma'] = calc_sma(volumes, ind.get('volume_sma_period', 20))
    result['taker_buy_ratio'] = np.where(volumes > 0, taker_buy / volumes, 0.5)
    
    # Volatility
    result['bb_upper'], result['bb_mid'], result['bb_lower'], result['bb_width'] = calc_bb(
        closes, ind.get('bb_period', 20), ind.get('bb_std', 2.0))
    result['atr'] = calc_atr(highs, lows, closes, ind.get('atr_period', 14))
    result['kc_upper'], result['kc_mid'], result['kc_lower'] = calc_keltner(
        highs, lows, closes, ind.get('keltner_period', 20), ind.get('keltner_mult', 1.5))
    result['dc_upper'], result['dc_lower'], result['dc_mid'] = calc_donchian(
        highs, lows, ind.get('donchian_period', 20))
    
    return result


# ============================================================
# ENTRY LOGICS
# ============================================================

ENTRY_LOGICS = [
    # Crossover
    "ema_cross", "ema_cross_rsi", "ema_cross_volume", "ema_trend_pullback",
    "sma_cross", "macd_cross", "macd_zero", "stoch_cross",
    "supertrend_flip", "sar_flip", "ichimoku_cross", "vwap_cross",
    # Breakout
    "donchian_breakout", "bb_breakout", "keltner_breakout",
    # Mean Reversion
    "rsi_ob_os", "bb_bounce", "cci_ob_os", "stoch_ob_os",
    # Momentum
    "adx_momentum", "macd_histogram_momentum",
    # Divergence
    "rsi_divergence", "obv_divergence",
    # Volume
    "volume_spike_momentum",
]

# ============================================================
# REGIME CLASSIFIER — tag each candle with market regime
# ============================================================
def classify_regime(data: dict, ind: dict) -> np.ndarray:
    """Classify each candle: 0=sideways, 1=bull, -1=bear, 2=shock"""
    closes = data['close']
    n = len(closes)
    regimes = np.zeros(n, dtype=int)
    
    ema200 = ind.get('ema_200', calc_ema(closes, 200))
    atr = ind.get('atr', np.zeros(n))
    adx = ind.get('adx', np.zeros(n))
    
    # ATR rolling average for shock detection
    atr_sma = np.full(n, np.nan)
    for i in range(20, n):
        atr_sma[i] = np.mean(atr[i-20:i])
    
    # EMA200 slope (over 10 bars)
    ema_slope = np.zeros(n)
    for i in range(10, n):
        if not np.isnan(ema200[i]) and not np.isnan(ema200[i-10]) and ema200[i-10] != 0:
            ema_slope[i] = (ema200[i] - ema200[i-10]) / ema200[i-10] * 100
    
    for i in range(n):
        if np.isnan(ema200[i]):
            regimes[i] = 0  # not enough data, default sideways
            continue
        
        # Shock: ATR spike > 2x average
        if not np.isnan(atr_sma[i]) and atr_sma[i] > 0 and atr[i] > atr_sma[i] * 2:
            regimes[i] = 2
        # Sideways: ADX < 20
        elif not np.isnan(adx[i]) and adx[i] < 20:
            regimes[i] = 0
        # Bull: price above EMA200 + slope positive
        elif closes[i] > ema200[i] and ema_slope[i] > 0:
            regimes[i] = 1
        # Bear: price below EMA200 + slope negative
        elif closes[i] < ema200[i] and ema_slope[i] < 0:
            regimes[i] = -1
        else:
            regimes[i] = 0  # mixed signals = sideways
    
    return regimes

REGIME_NAMES = {0: "sideways", 1: "bull", -1: "bear", 2: "shock"}

def calc_regime_stats(trades: list, regimes: np.ndarray) -> dict:
    """Compute WR and P&L per regime from trades"""
    stats = {}
    for code, name in REGIME_NAMES.items():
        regime_trades = [t for t in trades if t.get('regime') == code]
        total = len(regime_trades)
        if total == 0:
            stats[name] = {"trades": 0, "win_rate": 0, "avg_pnl": 0}
            continue
        wins = sum(1 for t in regime_trades if t.get('pnl', 0) > 0)
        avg_pnl = np.mean([t.get('pnl', 0) for t in regime_trades])
        stats[name] = {"trades": total, "win_rate": round(wins / total * 100, 1), "avg_pnl": round(float(avg_pnl), 4)}
    return stats

def get_signals(data: dict, ind: dict, config: StrategyConfig) -> np.ndarray:
    closes = data['close']
    highs = data['high']
    lows = data['low']
    volumes = data['volume']
    n = len(closes)
    signals = np.zeros(n, dtype=int)
    logic = config.entry_logic
    cfg = config.indicators
    direction = config.direction
    
    for i in range(3, n):
        sig = 0
        
        # ── CROSSOVER ──────────────────────────────
        if logic == "ema_cross":
            ef, es = ind['ema_fast'], ind['ema_slow']
            if not (np.isnan(ef[i]) or np.isnan(es[i])):
                if ef[i-1] <= es[i-1] and ef[i] > es[i]: sig = 1
                elif ef[i-1] >= es[i-1] and ef[i] < es[i]: sig = -1
        
        elif logic == "ema_cross_rsi":
            ef, es, rsi = ind['ema_fast'], ind['ema_slow'], ind['rsi']
            ob = cfg.get('rsi_overbought', 70)
            os_ = cfg.get('rsi_oversold', 30)
            if not (np.isnan(ef[i]) or np.isnan(rsi[i])):
                if ef[i-1] <= es[i-1] and ef[i] > es[i] and rsi[i] < ob: sig = 1
                elif ef[i-1] >= es[i-1] and ef[i] < es[i] and rsi[i] > os_: sig = -1
        
        elif logic == "ema_cross_volume":
            ef, es = ind['ema_fast'], ind['ema_slow']
            vsma = ind['volume_sma']
            mult = cfg.get('volume_spike_mult', 1.5)
            if not (np.isnan(ef[i]) or np.isnan(vsma[i])):
                if ef[i-1] <= es[i-1] and ef[i] > es[i] and volumes[i] > vsma[i] * mult: sig = 1
                elif ef[i-1] >= es[i-1] and ef[i] < es[i] and volumes[i] > vsma[i] * mult: sig = -1
        
        elif logic == "ema_trend_pullback":
            ef, es, e200 = ind['ema_fast'], ind['ema_slow'], ind['ema_200']
            if not (np.isnan(ef[i]) or np.isnan(e200[i])):
                if ef[i-1] <= es[i-1] and ef[i] > es[i] and closes[i] > e200[i]: sig = 1
                elif ef[i-1] >= es[i-1] and ef[i] < es[i] and closes[i] < e200[i]: sig = -1
        
        elif logic == "sma_cross":
            sf, ss = ind['sma_fast'], ind['sma_slow']
            if not (np.isnan(sf[i]) or np.isnan(ss[i])):
                if sf[i-1] <= ss[i-1] and sf[i] > ss[i]: sig = 1
                elif sf[i-1] >= ss[i-1] and sf[i] < ss[i]: sig = -1
        
        elif logic == "macd_cross":
            ml, sl_ = ind['macd'], ind['macd_signal']
            if not (np.isnan(ml[i]) or np.isnan(sl_[i])):
                if ml[i-1] <= sl_[i-1] and ml[i] > sl_[i]: sig = 1
                elif ml[i-1] >= sl_[i-1] and ml[i] < sl_[i]: sig = -1
        
        elif logic == "macd_zero":
            ml = ind['macd']
            if not np.isnan(ml[i]):
                if ml[i-1] <= 0 and ml[i] > 0: sig = 1
                elif ml[i-1] >= 0 and ml[i] < 0: sig = -1
        
        elif logic == "macd_histogram_momentum":
            mh = ind['macd_hist']
            if not (np.isnan(mh[i]) or np.isnan(mh[i-1]) or np.isnan(mh[i-2])):
                if mh[i] > mh[i-1] > mh[i-2] and mh[i] > 0: sig = 1
                elif mh[i] < mh[i-1] < mh[i-2] and mh[i] < 0: sig = -1
        
        elif logic == "stoch_cross":
            sk, sd = ind['stoch_k'], ind['stoch_d']
            os_ = cfg.get('stoch_oversold', 20)
            ob = cfg.get('stoch_overbought', 80)
            if not (np.isnan(sk[i]) or np.isnan(sd[i])):
                if sk[i-1] <= sd[i-1] and sk[i] > sd[i] and sk[i] < ob: sig = 1
                elif sk[i-1] >= sd[i-1] and sk[i] < sd[i] and sk[i] > os_: sig = -1
        
        elif logic == "stoch_ob_os":
            sk = ind['stoch_k']
            os_ = cfg.get('stoch_oversold', 20)
            ob = cfg.get('stoch_overbought', 80)
            if not np.isnan(sk[i]):
                if sk[i-1] <= os_ and sk[i] > os_: sig = 1
                elif sk[i-1] >= ob and sk[i] < ob: sig = -1
        
        elif logic == "supertrend_flip":
            st_dir = ind['supertrend_dir']
            if st_dir[i-1] == -1 and st_dir[i] == 1: sig = 1
            elif st_dir[i-1] == 1 and st_dir[i] == -1: sig = -1
        
        elif logic == "sar_flip":
            sar_tr = ind['sar_trend']
            if sar_tr[i-1] == -1 and sar_tr[i] == 1: sig = 1
            elif sar_tr[i-1] == 1 and sar_tr[i] == -1: sig = -1
        
        elif logic == "ichimoku_cross":
            tenkan, kijun = ind['tenkan'], ind['kijun']
            if not (np.isnan(tenkan[i]) or np.isnan(kijun[i])):
                if tenkan[i-1] <= kijun[i-1] and tenkan[i] > kijun[i]: sig = 1
                elif tenkan[i-1] >= kijun[i-1] and tenkan[i] < kijun[i]: sig = -1
        
        elif logic == "vwap_cross":
            vwap = ind['vwap']
            if not np.isnan(vwap[i]):
                if closes[i-1] <= vwap[i-1] and closes[i] > vwap[i]: sig = 1
                elif closes[i-1] >= vwap[i-1] and closes[i] < vwap[i]: sig = -1
        
        # ── BREAKOUT ───────────────────────────────
        elif logic == "donchian_breakout":
            dc_u, dc_l = ind['dc_upper'], ind['dc_lower']
            if not np.isnan(dc_u[i-1]):
                if closes[i] > dc_u[i-1]: sig = 1
                elif closes[i] < dc_l[i-1]: sig = -1
        
        elif logic == "bb_breakout":
            bbu, bbl = ind['bb_upper'], ind['bb_lower']
            if not np.isnan(bbu[i]):
                if closes[i-1] <= bbu[i-1] and closes[i] > bbu[i]: sig = 1
                elif closes[i-1] >= bbl[i-1] and closes[i] < bbl[i]: sig = -1
        
        elif logic == "keltner_breakout":
            kcu, kcl = ind['kc_upper'], ind['kc_lower']
            if not np.isnan(kcu[i]):
                if closes[i-1] <= kcu[i-1] and closes[i] > kcu[i]: sig = 1
                elif closes[i-1] >= kcl[i-1] and closes[i] < kcl[i]: sig = -1
        
        # ── MEAN REVERSION ─────────────────────────
        elif logic == "rsi_ob_os":
            rsi = ind['rsi']
            os_ = cfg.get('rsi_oversold', 30)
            ob = cfg.get('rsi_overbought', 70)
            if not np.isnan(rsi[i]):
                if rsi[i-1] <= os_ and rsi[i] > os_: sig = 1
                elif rsi[i-1] >= ob and rsi[i] < ob: sig = -1
        
        elif logic == "bb_bounce":
            bbu, bbl = ind['bb_upper'], ind['bb_lower']
            if not np.isnan(bbl[i]):
                if closes[i-1] <= bbl[i-1] and closes[i] > bbl[i]: sig = 1
                elif closes[i-1] >= bbu[i-1] and closes[i] < bbu[i]: sig = -1
        
        elif logic == "cci_ob_os":
            cci = ind['cci']
            os_ = cfg.get('cci_oversold', -100)
            ob = cfg.get('cci_overbought', 100)
            if not np.isnan(cci[i]):
                if cci[i-1] <= os_ and cci[i] > os_: sig = 1
                elif cci[i-1] >= ob and cci[i] < ob: sig = -1
        
        # ── MOMENTUM ───────────────────────────────
        elif logic == "adx_momentum":
            adx = ind['adx']
            dip, dim = ind['di_plus'], ind['di_minus']
            threshold = cfg.get('adx_threshold', 25)
            if not (np.isnan(adx[i]) or np.isnan(dip[i])):
                if adx[i] > threshold and dip[i] > dim[i] and dip[i-1] <= dim[i-1]: sig = 1
                elif adx[i] > threshold and dim[i] > dip[i] and dim[i-1] <= dip[i-1]: sig = -1
        
        # ── DIVERGENCE ─────────────────────────────
        elif logic == "rsi_divergence":
            rsi = ind['rsi']
            # Bullish: price lower low, RSI higher low (lookback 15 bars)
            lb = 15
            if i >= lb and not np.isnan(rsi[i]):
                price_ll = closes[i] < np.min(closes[i-lb:i])
                rsi_hl = rsi[i] > np.min(rsi[i-lb:i])
                price_hh = closes[i] > np.max(closes[i-lb:i])
                rsi_lh = rsi[i] < np.max(rsi[i-lb:i])
                if price_ll and rsi_hl: sig = 1   # Bullish divergence
                elif price_hh and rsi_lh: sig = -1  # Bearish divergence
        
        elif logic == "obv_divergence":
            obv = ind['obv']
            obv_ema = ind['obv_ema']
            lb = 15
            if i >= lb and not np.isnan(obv_ema[i]):
                price_ll = closes[i] < np.min(closes[i-lb:i])
                obv_hl = obv[i] > np.min(obv[i-lb:i])
                price_hh = closes[i] > np.max(closes[i-lb:i])
                obv_lh = obv[i] < np.max(obv[i-lb:i])
                if price_ll and obv_hl: sig = 1
                elif price_hh and obv_lh: sig = -1
        
        # ── VOLUME ─────────────────────────────────
        elif logic == "volume_spike_momentum":
            vsma = ind['volume_sma']
            mult = cfg.get('volume_spike_mult', 2.0)
            if not np.isnan(vsma[i]) and vsma[i] > 0:
                is_spike = volumes[i] > vsma[i] * mult
                if is_spike and closes[i] > closes[i-1]: sig = 1
                elif is_spike and closes[i] < closes[i-1]: sig = -1
        
        # Direction filter
        if direction == "long" and sig == -1: sig = 0
        elif direction == "short" and sig == 1: sig = 0
        
        signals[i] = sig
    
    return signals


# ============================================================
# FILTERS
# ============================================================

def apply_filters(data: dict, ind: dict, signals: np.ndarray, config: StrategyConfig) -> np.ndarray:
    filtered = signals.copy()
    closes = data['close']
    volumes = data['volume']
    
    # Session filter
    if config.session_filter:
        session_hours = {
            "asia":       (0, 8),
            "london":     (8, 16),
            "ny":         (13, 21),
            "london_ny":  (13, 16),
        }
        if config.session_filter in session_hours:
            start_h, end_h = session_hours[config.session_filter]
            for i, ts in enumerate(data['open_time']):
                hour = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).hour
                if not (start_h <= hour < end_h):
                    filtered[i] = 0
    
    # Trend filter
    if config.trend_filter:
        e200 = ind['ema_200']
        adx = ind['adx']
        dip, dim = ind['di_plus'], ind['di_minus']
        for i in range(len(filtered)):
            if filtered[i] == 0:
                continue
            if config.trend_filter == "ema200_long":
                if np.isnan(e200[i]) or closes[i] < e200[i]:
                    filtered[i] = 0
            elif config.trend_filter == "ema200_short":
                if np.isnan(e200[i]) or closes[i] > e200[i]:
                    filtered[i] = 0
            elif config.trend_filter == "adx_direction":
                if np.isnan(adx[i]) or np.isnan(dip[i]):
                    filtered[i] = 0
                elif filtered[i] == 1 and dip[i] < dim[i]:
                    filtered[i] = 0
                elif filtered[i] == -1 and dim[i] < dip[i]:
                    filtered[i] = 0
    
    # Volatility filter
    if config.volatility_filter:
        atr = ind['atr']
        bb_width = ind['bb_width']
        for i in range(len(filtered)):
            if filtered[i] == 0:
                continue
            if config.volatility_filter == "atr_min":
                if np.isnan(atr[i]) or atr[i] < config.atr_min_threshold:
                    filtered[i] = 0
            elif config.volatility_filter == "atr_max":
                if np.isnan(atr[i]) or atr[i] > config.atr_max_threshold:
                    filtered[i] = 0
            elif config.volatility_filter == "bb_squeeze":
                if np.isnan(bb_width[i]) or bb_width[i] < config.bb_squeeze_threshold:
                    filtered[i] = 0
    
    # Volume filter
    if config.volume_filter:
        vsma = ind['volume_sma']
        tbr = ind['taker_buy_ratio']
        for i in range(len(filtered)):
            if filtered[i] == 0:
                continue
            if config.volume_filter == "volume_spike":
                if np.isnan(vsma[i]) or volumes[i] < vsma[i] * config.volume_min_mult:
                    filtered[i] = 0
            elif config.volume_filter == "taker_buy":
                thr = config.indicators.get('taker_buy_ratio_threshold', 0.55)
                if filtered[i] == 1 and tbr[i] < thr:
                    filtered[i] = 0
                elif filtered[i] == -1 and tbr[i] > (1 - thr):
                    filtered[i] = 0
    
    # Regime filter
    if config.regime_filter:
        adx = ind['adx']
        threshold = config.indicators.get('adx_threshold', 25)
        for i in range(len(filtered)):
            if filtered[i] == 0:
                continue
            if np.isnan(adx[i]):
                filtered[i] = 0
                continue
            if config.regime_filter == "trending" and adx[i] < threshold:
                filtered[i] = 0
            elif config.regime_filter == "ranging" and adx[i] > threshold:
                filtered[i] = 0
    
    return filtered


# ============================================================
# TRADE SIMULATOR
# ============================================================

def simulate_trades(data: dict, ind: dict, signals: np.ndarray,
                    config: StrategyConfig, start_idx: int = 0,
                    end_idx: Optional[int] = None, regimes: np.ndarray = None) -> list:
    closes = data['close']
    highs = data['high']
    lows = data['low']
    n = end_idx or len(closes)
    atr = ind.get('atr', np.zeros(len(closes)))
    total_cost_pct = config.fee_pct + config.slippage_pct * 2
    
    trades = []
    in_position = False
    entry_price = 0.0
    entry_idx = 0
    trade_dir = 0
    sl_price = 0.0
    tp_price = 0.0
    max_wick_against = 0.0  # worst wick against position (%)
    max_wick_favor = 0.0    # best wick in favor (%)
    
    for i in range(start_idx, n):
        if not in_position:
            if signals[i] != 0:
                in_position = True
                trade_dir = signals[i]
                slip = closes[i] * config.slippage_pct / 100
                entry_price = closes[i] + slip if trade_dir == 1 else closes[i] - slip
                entry_idx = i
                max_wick_against = 0.0
                max_wick_favor = 0.0
                
                # SL/TP: dynamic (ATR) or fixed (%)
                if config.use_atr_sl_tp and not np.isnan(atr[i]) and atr[i] > 0:
                    sl_dist = atr[i] * config.sl_atr_mult
                    tp_dist = atr[i] * config.tp_atr_mult
                else:
                    sl_dist = entry_price * config.sl_pct / 100
                    tp_dist = entry_price * config.tp_pct / 100
                
                if trade_dir == 1:
                    sl_price = entry_price - sl_dist
                    tp_price = entry_price + tp_dist
                else:
                    sl_price = entry_price + sl_dist
                    tp_price = entry_price - tp_dist
        else:
            exit_price = None
            exit_reason = None
            
            # Track max wick against/favor while in position
            if trade_dir == 1:  # LONG
                wick_against_pct = (entry_price - lows[i]) / entry_price * 100
                wick_favor_pct = (highs[i] - entry_price) / entry_price * 100
            else:  # SHORT
                wick_against_pct = (highs[i] - entry_price) / entry_price * 100
                wick_favor_pct = (entry_price - lows[i]) / entry_price * 100
            max_wick_against = max(max_wick_against, wick_against_pct)
            max_wick_favor = max(max_wick_favor, wick_favor_pct)
            
            # SL/TP check — mode: "wick" (high/low) or "close"
            if config.sl_check_mode == "wick":
                # Wick mode: more realistic for hard stop orders
                # If both SL and TP hit in same candle, assume worst case (SL first)
                if trade_dir == 1:  # LONG
                    sl_hit = lows[i] <= sl_price
                    tp_hit = highs[i] >= tp_price
                    if sl_hit and tp_hit:
                        exit_price = sl_price
                        exit_reason = "sl"
                    elif sl_hit:
                        exit_price = sl_price
                        exit_reason = "sl"
                    elif tp_hit:
                        exit_price = tp_price
                        exit_reason = "tp"
                else:  # SHORT
                    sl_hit = highs[i] >= sl_price
                    tp_hit = lows[i] <= tp_price
                    if sl_hit and tp_hit:
                        exit_price = sl_price
                        exit_reason = "sl"
                    elif sl_hit:
                        exit_price = sl_price
                        exit_reason = "sl"
                    elif tp_hit:
                        exit_price = tp_price
                        exit_reason = "tp"
            else:
                # Close mode: check candle close only
                if trade_dir == 1:  # LONG
                    if closes[i] <= sl_price:
                        exit_price = sl_price
                        exit_reason = "sl"
                    elif closes[i] >= tp_price:
                        exit_price = tp_price
                        exit_reason = "tp"
                else:  # SHORT
                    if closes[i] >= sl_price:
                        exit_price = sl_price
                        exit_reason = "sl"
                    elif closes[i] <= tp_price:
                        exit_price = tp_price
                        exit_reason = "tp"
            
            if exit_price:
                pnl_pct = ((exit_price - entry_price) / entry_price * 100
                           if trade_dir == 1
                           else (entry_price - exit_price) / entry_price * 100)
                pnl_pct -= total_cost_pct
                
                position_size = config.initial_capital * config.position_size_pct / 100
                pnl_dollar = position_size * pnl_pct / 100
                
                trades.append({
                    "entry_idx": entry_idx,
                    "exit_idx": i,
                    "direction": trade_dir,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "pnl_pct": pnl_pct,
                    "pnl_dollar": pnl_dollar,
                    "pnl": pnl_dollar,
                    "bars_held": i - entry_idx,
                    "timestamp_entry": data['open_time'][entry_idx],
                    "timestamp_exit": data['open_time'][i],
                    "regime": int(regimes[entry_idx]) if regimes is not None else 0,
                    "max_wick_against": round(max_wick_against, 4),
                    "max_wick_favor": round(max_wick_favor, 4),
                })
                in_position = False
    
    return trades


# ============================================================
# METRICS
# ============================================================

def calc_metrics(trades: list, data_days: float, initial_capital: float) -> dict:
    if not trades:
        return {"total_trades": 0, "status": "no_trades"}
    
    pnls = np.array([t['pnl_dollar'] for t in trades])
    total = len(trades)
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    
    win_rate = len(wins) / total * 100
    net_profit = float(np.sum(pnls))
    profit_per_day = net_profit / data_days if data_days > 0 else 0
    avg_win = float(np.mean(wins)) if len(wins) > 0 else 0
    avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0
    
    gross_profit = float(np.sum(wins)) if len(wins) > 0 else 0
    gross_loss = abs(float(np.sum(losses))) if len(losses) > 0 else 1e-9
    profit_factor = gross_profit / gross_loss
    
    equity = initial_capital + np.cumsum(pnls)
    equity = np.insert(equity, 0, initial_capital)
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity) / peak * 100
    max_drawdown = float(np.max(drawdown))
    
    daily_returns = pnls / initial_capital
    sharpe = float(np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)) if np.std(daily_returns) > 0 else 0
    avg_rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    # Max consecutive losses
    consec = 0
    max_consec = 0
    for p in pnls:
        if p <= 0:
            consec += 1
            max_consec = max(max_consec, consec)
        else:
            consec = 0
    
    long_tr = [t for t in trades if t['direction'] == 1]
    short_tr = [t for t in trades if t['direction'] == -1]
    long_w = [t for t in long_tr if t['pnl_dollar'] > 0]
    short_w = [t for t in short_tr if t['pnl_dollar'] > 0]
    
    # ── Stage 6: Trade duration ──
    bars_held_arr = np.array([t['bars_held'] for t in trades])
    
    # Calculate duration in hours from timestamps if available
    avg_duration_hours = 0.0
    min_duration_hours = 0.0
    max_duration_hours = 0.0
    
    durations_ms = []
    for t in trades:
        ts_entry = t.get('timestamp_entry', 0)
        ts_exit = t.get('timestamp_exit', 0)
        if ts_entry and ts_exit and ts_exit > ts_entry:
            durations_ms.append(ts_exit - ts_entry)
    
    if durations_ms:
        durations_hours = [d / 3_600_000 for d in durations_ms]  # ms → hours
        avg_duration_hours = sum(durations_hours) / len(durations_hours)
        min_duration_hours = min(durations_hours)
        max_duration_hours = max(durations_hours)
    
    # ── Stage 6: Drawdown sequence analysis ──
    # Track each drawdown period: when equity drops below peak until recovery
    dd_durations = []      # how long each drawdown lasted (in trades)
    dd_recoveries = []     # how long from bottom to recovery (in trades)
    
    in_drawdown = False
    dd_start_idx = 0
    dd_bottom_idx = 0
    dd_bottom_val = 0
    
    for i in range(len(equity)):
        if equity[i] < peak[i]:
            # In drawdown
            if not in_drawdown:
                in_drawdown = True
                dd_start_idx = i
                dd_bottom_idx = i
                dd_bottom_val = equity[i]
            elif equity[i] < dd_bottom_val:
                dd_bottom_idx = i
                dd_bottom_val = equity[i]
        else:
            # Recovered or at peak
            if in_drawdown:
                dd_duration = i - dd_start_idx  # total drawdown period
                dd_recovery = i - dd_bottom_idx  # recovery from bottom
                dd_durations.append(dd_duration)
                dd_recoveries.append(dd_recovery)
                in_drawdown = False
    
    # If still in drawdown at end
    if in_drawdown:
        dd_durations.append(len(equity) - 1 - dd_start_idx)
        dd_recoveries.append(len(equity) - 1 - dd_bottom_idx)
    
    num_dd_periods = len(dd_durations)
    avg_dd_duration = sum(dd_durations) / len(dd_durations) if dd_durations else 0
    max_dd_duration = max(dd_durations) if dd_durations else 0
    avg_dd_recovery = sum(dd_recoveries) / len(dd_recoveries) if dd_recoveries else 0
    max_dd_recovery = max(dd_recoveries) if dd_recoveries else 0
    
    return {
        "total_trades": total,
        "win_rate": round(win_rate, 2),
        "profit_per_day": round(profit_per_day, 4),
        "net_profit": round(net_profit, 4),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 3),
        "profit_factor": round(profit_factor, 3),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "avg_rr": round(avg_rr, 3),
        "max_consecutive_losses": max_consec,
        "long_trades": len(long_tr),
        "short_trades": len(short_tr),
        "long_win_rate": round(len(long_w)/len(long_tr)*100, 2) if long_tr else 0,
        "short_win_rate": round(len(short_w)/len(short_tr)*100, 2) if short_tr else 0,
        # Stage 6: Trade duration metrics
        "avg_bars_held": round(float(np.mean(bars_held_arr)), 2) if len(bars_held_arr) > 0 else 0,
        "avg_trade_duration_hours": round(avg_duration_hours, 2),
        "min_trade_duration_hours": round(min_duration_hours, 2),
        "max_trade_duration_hours": round(max_duration_hours, 2),
        # Stage 6: Drawdown sequence metrics
        "avg_drawdown_duration_bars": round(avg_dd_duration, 2),
        "max_drawdown_duration_bars": max_dd_duration,
        "avg_drawdown_recovery_bars": round(avg_dd_recovery, 2),
        "max_drawdown_recovery_bars": max_dd_recovery,
        "drawdown_periods": num_dd_periods,
        "status": "ok",
        # Stage 10: Equity curve (downsampled to max 100 points)
        "equity_curve": _downsample(equity.tolist(), 100),
    }

def _downsample(arr: list, max_points: int) -> list:
    """Downsample array to max_points, keeping first and last."""
    if len(arr) <= max_points:
        return [round(v, 2) for v in arr]
    step = len(arr) / max_points
    result = [round(arr[int(i * step)], 2) for i in range(max_points - 1)]
    result.append(round(arr[-1], 2))
    return result


# ============================================================
# CORRELATION TRACKER (Stage 6)
# ============================================================

def calc_correlation(trade_lists: list[list[dict]], labels: list[str] = None) -> dict:
    """
    Analyze correlation between multiple strategy trade lists.
    
    Args:
        trade_lists: list of trade lists from different strategies
        labels: optional names for each strategy
    
    Returns:
        dict with correlation matrix and overlap analysis
    """
    if len(trade_lists) < 2:
        return {"error": "Need at least 2 trade lists for correlation", "matrix": []}
    
    n = len(trade_lists)
    if not labels:
        labels = [f"Strategy_{i+1}" for i in range(n)]
    
    # Build time ranges for each strategy's trades
    trade_ranges = []
    for trades in trade_lists:
        ranges = []
        for t in trades:
            entry_ts = t.get('timestamp_entry', 0)
            exit_ts = t.get('timestamp_exit', 0)
            if entry_ts and exit_ts:
                ranges.append((entry_ts, exit_ts, t['pnl_dollar']))
        trade_ranges.append(ranges)
    
    # Calculate pairwise overlap and PnL correlation
    matrix = []
    overlap_details = []
    
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(1.0)
                continue
            
            # Count overlapping trades (both open at the same time)
            overlaps = 0
            same_direction_pnl = 0  # both win or both lose simultaneously
            total_compared = 0
            
            for t1 in trade_ranges[i]:
                for t2 in trade_ranges[j]:
                    # Check time overlap
                    if t1[0] < t2[1] and t2[0] < t1[1]:
                        overlaps += 1
                        total_compared += 1
                        # Check if PnL direction matches (both + or both -)
                        if (t1[2] > 0 and t2[2] > 0) or (t1[2] <= 0 and t2[2] <= 0):
                            same_direction_pnl += 1
            
            # Correlation = same_direction / total overlapping trades
            correlation = same_direction_pnl / total_compared if total_compared > 0 else 0
            row.append(round(correlation, 3))
            
            if i < j:  # Only store once per pair
                overlap_details.append({
                    "pair": f"{labels[i]} vs {labels[j]}",
                    "overlapping_trades": overlaps,
                    "same_direction_pnl": same_direction_pnl,
                    "correlation": round(correlation, 3),
                    "verdict": "HIGH_CORR" if correlation > 0.7 else "MODERATE" if correlation > 0.4 else "LOW_CORR"
                })
        
        matrix.append(row)
    
    return {
        "labels": labels,
        "matrix": matrix,
        "overlap_details": overlap_details,
        "portfolio_diversified": all(d['correlation'] < 0.7 for d in overlap_details)
    }


# ============================================================
# BACKTESTER
# ============================================================

class Backtester:
    def __init__(self, db_path: str = "market_data.db"):
        self.db_path = db_path
    
    def _load_data(self, symbol: str, timeframe: str, days: int, start_date: str = None, end_date: str = None) -> Optional[dict]:
        if not Path(self.db_path).exists():
            return None
        conn = sqlite3.connect(self.db_path)
        try:
            if start_date and end_date:
                # Date range mode: use explicit start/end dates
                start_ms = int(datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
                end_ms = int(datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000) + 86400000  # end of day
                rows = conn.execute("""
                    SELECT open_time, open, high, low, close, volume, taker_buy_volume
                    FROM klines
                    WHERE symbol=? AND timeframe=? AND open_time >= ? AND open_time < ?
                    ORDER BY open_time ASC
                """, (symbol, timeframe, start_ms, end_ms)).fetchall()
            else:
                # Legacy mode: last N days
                now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
                cutoff_ms = now_ms - days * 24 * 3600 * 1000
                rows = conn.execute("""
                    SELECT open_time, open, high, low, close, volume, taker_buy_volume
                    FROM klines
                    WHERE symbol=? AND timeframe=? AND open_time >= ?
                    ORDER BY open_time ASC
                """, (symbol, timeframe, cutoff_ms)).fetchall()
            if not rows:
                return None
            arr = np.array(rows, dtype=float)
            return {
                'open_time': arr[:, 0],
                'open':  arr[:, 1],
                'high':  arr[:, 2],
                'low':   arr[:, 3],
                'close': arr[:, 4],
                'volume':arr[:, 5],
                'taker_buy_volume': arr[:, 6],
            }
        except Exception as e:
            return None
        finally:
            conn.close()
    
    def run(self, config: StrategyConfig) -> BacktestResult:
        result = BacktestResult(
            symbol=config.symbol,
            timeframe=config.timeframe,
            entry_logic=config.entry_logic,
            entry_logic_2=config.entry_logic_2 or "",
            sl_type="atr" if config.use_atr_sl_tp else "fixed",
            sl_check_mode=config.sl_check_mode,
        )
        
        data = self._load_data(config.symbol, config.timeframe, config.days, config.start_date, config.end_date)
        if data is None or len(data['close']) < 100:
            result.status = "insufficient_data"
            result.error = f"Not enough data for {config.symbol} {config.timeframe}"
            return result
        
        n = len(data['close'])
        candles_per_day = {'1m': 1440, '3m': 480, '5m': 288, '15m': 96, '1h': 24, '4h': 6}
        cpd = candles_per_day.get(config.timeframe, 288)
        data_days = n / cpd
        result.data_days = round(data_days, 1)
        
        train_end = int(n * config.train_pct / 100)
        
        # Precompute indicators
        ind = precompute_indicators(data, config)
        
        # Generate signals from primary entry logic
        signals = get_signals(data, ind, config)
        
        # Level 2: Multi-entry confirmation (AND within window)
        if config.entry_logic_2 and config.entry_logic_2 in ENTRY_LOGICS:
            from dataclasses import replace as dc_replace
            config2 = dc_replace(config, entry_logic=config.entry_logic_2)
            signals2 = get_signals(data, ind, config2)
            
            # AND: entry only when both signals agree within lookback window
            window = 3  # candle lookback window
            combined = np.zeros(len(signals), dtype=int)
            for i in range(window, len(signals)):
                if signals[i] != 0:
                    # Primary fired → check if secondary also fired in window
                    for j in range(max(0, i - window), i + 1):
                        if signals2[j] == signals[i]:
                            combined[i] = signals[i]
                            break
                elif signals2[i] != 0:
                    # Secondary fired → check if primary also fired in window
                    for j in range(max(0, i - window), i + 1):
                        if signals[j] == signals2[i]:
                            combined[i] = signals2[i]
                            break
            signals = combined
        
        # Apply filters
        signals = apply_filters(data, ind, signals, config)
        
        # Classify regimes
        regimes = classify_regime(data, ind)
        
        # Train
        train_trades = simulate_trades(data, ind, signals, config, 0, train_end, regimes)
        train_days = train_end / cpd
        train_metrics = calc_metrics(train_trades, train_days, config.initial_capital)
        
        if train_metrics.get("status") == "no_trades":
            result.status = "no_trades"
            result.error = "No trades on training set"
            return result
        
        # OOS
        oos_trades = simulate_trades(data, ind, signals, config, train_end, None, regimes)
        oos_days = (n - train_end) / cpd
        oos_metrics = calc_metrics(oos_trades, oos_days, config.initial_capital)
        
        # Fill result
        for k, v in train_metrics.items():
            if hasattr(result, k):
                setattr(result, k, v)
        
        result.oos_win_rate = oos_metrics.get("win_rate", 0)
        result.oos_profit_per_day = oos_metrics.get("profit_per_day", 0)
        result.oos_trades = oos_metrics.get("total_trades", 0)
        result.status = "ok"
        
        # Regime stats (all trades combined)
        all_trades = train_trades + oos_trades
        result.regime_stats = calc_regime_stats(all_trades, regimes)
        
        # Wick stats
        if all_trades:
            wicks_against = [t.get('max_wick_against', 0) for t in all_trades]
            wicks_favor = [t.get('max_wick_favor', 0) for t in all_trades]
            result.avg_max_wick_against = round(float(np.mean(wicks_against)), 4)
            result.avg_max_wick_favor = round(float(np.mean(wicks_favor)), 4)
            sl_pct_val = config.sl_pct
            tp_pct_val = config.tp_pct
            wick_hit_sl = sum(1 for w in wicks_against if w >= sl_pct_val)
            wick_hit_tp = sum(1 for w in wicks_favor if w >= tp_pct_val)
            result.pct_trades_wick_hit_sl = round(wick_hit_sl / len(all_trades) * 100, 1)
            result.pct_trades_wick_hit_tp = round(wick_hit_tp / len(all_trades) * 100, 1)
            # Suggested TP: 75th percentile of max wick favor (achievable by 75% of trades)
            result.suggested_tp = round(float(np.percentile(wicks_favor, 75)), 2) if len(wicks_favor) >= 5 else 0
        
        result.meets_criteria = (
            result.profit_per_day >= 3.0 and
            result.max_drawdown <= 5.0 and
            result.win_rate >= 55.0 and
            result.data_days >= 90 and
            result.oos_profit_per_day > 0 and
            result.oos_win_rate >= 50.0 and
            result.total_trades >= 30
        )
        
        return result
    
    def run_batch(self, configs: list) -> list:
        results = []
        for i, config in enumerate(configs):
            print(f"[{i+1}/{len(configs)}] {config.symbol} {config.timeframe} {config.entry_logic}...", end=" ", flush=True)
            r = self.run(config)
            results.append(r)
            if r.status == "ok":
                status = "✅ MEETS" if r.meets_criteria else f"WR:{r.win_rate:.0f}% P/d:${r.profit_per_day:.2f}"
            else:
                status = f"❌ {r.status}"
            print(status)
        return results


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    print("🧪 BabaBot Backtesting Core v2 — Full Search Space\n")
    bt = Backtester(db_path="market_data.db")
    
    test_configs = [
        StrategyConfig(symbol="BTCUSDT", timeframe="5m", entry_logic="ema_cross",
                      sl_pct=0.3, tp_pct=0.8, days=90),
        StrategyConfig(symbol="ETHUSDT", timeframe="15m", entry_logic="supertrend_flip",
                      sl_pct=0.4, tp_pct=1.2, days=90),
        StrategyConfig(symbol="BTCUSDT", timeframe="5m", entry_logic="rsi_ob_os",
                      trend_filter="ema200_long", direction="long",
                      sl_pct=0.3, tp_pct=0.9, days=90),
        StrategyConfig(symbol="XRPUSDT", timeframe="15m", entry_logic="donchian_breakout",
                      volume_filter="volume_spike", sl_pct=0.5, tp_pct=1.5, days=90),
        StrategyConfig(symbol="BTCUSDT", timeframe="5m", entry_logic="ema_cross",
                      use_atr_sl_tp=True, sl_atr_mult=1.5, tp_atr_mult=3.0, days=90),
    ]
    
    results = bt.run_batch(test_configs)
    print("\n" + "="*60)
    for r in results:
        print(f"\n{r.summary()}")
    meets = [r for r in results if r.meets_criteria]
    print(f"\n✅ Meets criteria: {len(meets)}/{len(results)}")
