"""
BabaBot AI Strategy Discovery — Step 1B: Backtesting Core
Simulate trading strategy di atas historical data dari market_data.db

Usage:
    from backtesting_core import Backtester, StrategyConfig
    
    config = StrategyConfig(
        symbol="BTCUSDT",
        timeframe="5m",
        indicators={"ema_fast": 9, "ema_slow": 21, "rsi_period": 14},
        entry_logic="ema_cross_rsi",
        sl_pct=0.3,
        tp_pct=0.8,
        fee_pct=0.08,  # roundtrip (0.04% x2)
        slippage_pct=0.02,
        initial_capital=1000.0,
        days=90
    )
    
    bt = Backtester(db_path="market_data.db")
    result = bt.run(config)
    print(result)
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
    entry_logic: str = "ema_cross"          # lihat ENTRY_LOGICS di bawah
    exit_logic: str = "sl_tp"               # sl_tp only for now
    
    # Indicator Parameters
    indicators: dict = field(default_factory=lambda: {
        "ema_fast": 9,
        "ema_slow": 21,
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "bb_period": 20,
        "bb_std": 2.0,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_period": 14,
        "stoch_k": 14,
        "stoch_d": 3,
        "adx_period": 14,
    })
    
    # Risk Management
    sl_pct: float = 0.3           # Stop Loss % dari entry
    tp_pct: float = 0.8           # Take Profit % dari entry
    fee_pct: float = 0.08         # Total fee roundtrip (0.04% x2)
    slippage_pct: float = 0.02    # Slippage per side
    
    # Capital
    initial_capital: float = 1000.0
    position_size_pct: float = 100.0  # % of capital per trade
    
    # Data
    days: int = 90                # Berapa hari data yang dipakai
    train_pct: float = 75.0       # % untuk training, sisanya OOS validation
    
    # Filter
    direction: str = "both"       # "long", "short", "both"
    session_filter: Optional[str] = None  # "asia", "london", "ny", None


# ============================================================
# RESULT
# ============================================================

@dataclass
class BacktestResult:
    # Identity
    symbol: str = ""
    timeframe: str = ""
    entry_logic: str = ""
    
    # Core Metrics
    total_trades: int = 0
    win_rate: float = 0.0         # %
    profit_per_day: float = 0.0   # $ per day
    net_profit: float = 0.0       # $ total
    max_drawdown: float = 0.0     # % dari peak equity
    
    # Advanced Metrics
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0    # gross profit / gross loss
    avg_win: float = 0.0          # $ avg win per trade
    avg_loss: float = 0.0         # $ avg loss per trade
    avg_rr: float = 0.0           # avg reward/risk ratio
    
    # Trade Breakdown
    long_trades: int = 0
    short_trades: int = 0
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0
    
    # Validation
    oos_win_rate: float = 0.0     # Out-of-sample win rate
    oos_profit_per_day: float = 0.0
    oos_trades: int = 0
    
    # Status
    status: str = "ok"            # "ok", "insufficient_data", "no_trades", "error"
    error: str = ""
    data_days: int = 0
    
    # Meets criteria?
    meets_criteria: bool = False
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def summary(self) -> str:
        if self.status != "ok":
            return f"❌ {self.status}: {self.error}"
        
        criteria = "✅ MEETS CRITERIA" if self.meets_criteria else "❌ Below criteria"
        return (
            f"{criteria}\n"
            f"Symbol: {self.symbol} {self.timeframe} | Logic: {self.entry_logic}\n"
            f"Trades: {self.total_trades} | WR: {self.win_rate:.1f}% | "
            f"Profit/day: ${self.profit_per_day:.2f} | DD: {self.max_drawdown:.1f}%\n"
            f"Sharpe: {self.sharpe_ratio:.2f} | PF: {self.profit_factor:.2f} | "
            f"Avg W/L: ${self.avg_win:.2f}/${self.avg_loss:.2f}\n"
            f"OOS: {self.oos_trades} trades | WR: {self.oos_win_rate:.1f}% | "
            f"Profit/day: ${self.oos_profit_per_day:.2f}"
        )


# ============================================================
# INDICATOR CALCULATIONS
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

def calc_macd(closes: np.ndarray, fast: int, slow: int, signal: int):
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(np.where(np.isnan(macd_line), 0, macd_line), signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calc_bb(closes: np.ndarray, period: int, std_mult: float):
    upper = np.full_like(closes, np.nan)
    middle = np.full_like(closes, np.nan)
    lower = np.full_like(closes, np.nan)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        mid = np.mean(window)
        std = np.std(window, ddof=0)
        middle[i] = mid
        upper[i] = mid + std_mult * std
        lower[i] = mid - std_mult * std
    return upper, middle, lower

def calc_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int) -> np.ndarray:
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

def calc_adx(highs, lows, closes, period):
    adx = np.full_like(closes, np.nan)
    if len(closes) < period * 2:
        return adx
    dm_plus = np.maximum(highs[1:] - highs[:-1], 0)
    dm_minus = np.maximum(lows[:-1] - lows[1:], 0)
    mask = dm_plus <= dm_minus
    dm_plus[mask] = 0
    mask2 = dm_minus <= dm_plus[~mask] if len(dm_plus[~mask]) else np.ones(len(dm_minus), bool)
    tr = np.maximum(highs[1:] - lows[1:],
         np.maximum(np.abs(highs[1:] - closes[:-1]),
                    np.abs(lows[1:] - closes[:-1])))
    
    def smooth(arr, p):
        result = np.full(len(arr) + 1, np.nan)
        result[p] = np.sum(arr[:p])
        for i in range(p + 1, len(arr) + 1):
            result[i] = result[i-1] - result[i-1]/p + arr[i-1]
        return result[1:]
    
    tr_s = smooth(tr, period)
    dmp_s = smooth(dm_plus, period)
    dmm_s = smooth(dm_minus, period)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        di_plus = np.where(tr_s > 0, dmp_s / tr_s * 100, 0)
        di_minus = np.where(tr_s > 0, dmm_s / tr_s * 100, 0)
        dx = np.where((di_plus + di_minus) > 0,
                      np.abs(di_plus - di_minus) / (di_plus + di_minus) * 100, 0)
    
    adx_val = np.mean(dx[:period])
    adx[period * 2] = adx_val
    for i in range(period * 2 + 1, len(closes)):
        adx_val = (adx_val * (period - 1) + dx[i - period]) / period
        adx[i] = adx_val
    return adx


# ============================================================
# ENTRY LOGICS
# ============================================================

def get_signals(data: dict, config: StrategyConfig) -> np.ndarray:
    """
    Return array of signals: 1=LONG, -1=SHORT, 0=no signal
    """
    closes = data['close']
    highs = data['high']
    lows = data['low']
    n = len(closes)
    signals = np.zeros(n, dtype=int)
    ind = config.indicators
    
    logic = config.entry_logic
    direction = config.direction
    
    # Pre-compute indicators yang dibutuhkan
    if logic in ("ema_cross", "ema_cross_rsi", "ema_cross_volume"):
        ema_fast = calc_ema(closes, ind.get("ema_fast", 9))
        ema_slow = calc_ema(closes, ind.get("ema_slow", 21))
    
    if logic in ("ema_cross_rsi", "rsi_ob_os", "rsi_divergence"):
        rsi = calc_rsi(closes, ind.get("rsi_period", 14))
    
    if logic in ("macd_cross", "macd_zero"):
        macd_line, signal_line, histogram = calc_macd(
            closes, ind.get("macd_fast", 12),
            ind.get("macd_slow", 26), ind.get("macd_signal", 9))
    
    if logic in ("bb_bounce", "bb_squeeze"):
        bb_upper, bb_mid, bb_lower = calc_bb(
            closes, ind.get("bb_period", 20), ind.get("bb_std", 2.0))
    
    if logic in ("stoch_cross",):
        stoch_k, stoch_d = calc_stoch(
            highs, lows, closes,
            ind.get("stoch_k", 14), ind.get("stoch_d", 3))

    for i in range(2, n):
        sig = 0
        
        if logic == "ema_cross":
            # EMA crossover
            if (not np.isnan(ema_fast[i]) and not np.isnan(ema_slow[i]) and
                not np.isnan(ema_fast[i-1]) and not np.isnan(ema_slow[i-1])):
                if ema_fast[i-1] <= ema_slow[i-1] and ema_fast[i] > ema_slow[i]:
                    sig = 1   # LONG: fast cross above slow
                elif ema_fast[i-1] >= ema_slow[i-1] and ema_fast[i] < ema_slow[i]:
                    sig = -1  # SHORT: fast cross below slow
        
        elif logic == "ema_cross_rsi":
            # EMA cross + RSI filter
            oversold = ind.get("rsi_oversold", 30)
            overbought = ind.get("rsi_overbought", 70)
            if (not np.isnan(ema_fast[i]) and not np.isnan(rsi[i])):
                if (ema_fast[i-1] <= ema_slow[i-1] and ema_fast[i] > ema_slow[i]
                        and rsi[i] < overbought):
                    sig = 1
                elif (ema_fast[i-1] >= ema_slow[i-1] and ema_fast[i] < ema_slow[i]
                        and rsi[i] > oversold):
                    sig = -1
        
        elif logic == "rsi_ob_os":
            # RSI overbought/oversold
            oversold = ind.get("rsi_oversold", 30)
            overbought = ind.get("rsi_overbought", 70)
            if not np.isnan(rsi[i]) and not np.isnan(rsi[i-1]):
                if rsi[i-1] <= oversold and rsi[i] > oversold:
                    sig = 1   # LONG: RSI cross above oversold
                elif rsi[i-1] >= overbought and rsi[i] < overbought:
                    sig = -1  # SHORT: RSI cross below overbought
        
        elif logic == "macd_cross":
            # MACD line cross signal line
            if (not np.isnan(macd_line[i]) and not np.isnan(signal_line[i]) and
                not np.isnan(macd_line[i-1])):
                if macd_line[i-1] <= signal_line[i-1] and macd_line[i] > signal_line[i]:
                    sig = 1
                elif macd_line[i-1] >= signal_line[i-1] and macd_line[i] < signal_line[i]:
                    sig = -1
        
        elif logic == "macd_zero":
            # MACD cross zero line
            if not np.isnan(macd_line[i]) and not np.isnan(macd_line[i-1]):
                if macd_line[i-1] <= 0 and macd_line[i] > 0:
                    sig = 1
                elif macd_line[i-1] >= 0 and macd_line[i] < 0:
                    sig = -1
        
        elif logic == "bb_bounce":
            # Bollinger Band bounce
            if (not np.isnan(bb_lower[i]) and not np.isnan(bb_upper[i])):
                if closes[i-1] <= bb_lower[i-1] and closes[i] > bb_lower[i]:
                    sig = 1   # LONG: price bounce off lower band
                elif closes[i-1] >= bb_upper[i-1] and closes[i] < bb_upper[i]:
                    sig = -1  # SHORT: price bounce off upper band
        
        elif logic == "stoch_cross":
            # Stochastic crossover
            oversold = ind.get("rsi_oversold", 20)
            overbought = ind.get("rsi_overbought", 80)
            if (not np.isnan(stoch_k[i]) and not np.isnan(stoch_d[i]) and
                not np.isnan(stoch_k[i-1])):
                if (stoch_k[i-1] <= stoch_d[i-1] and stoch_k[i] > stoch_d[i]
                        and stoch_k[i] < oversold):
                    sig = 1
                elif (stoch_k[i-1] >= stoch_d[i-1] and stoch_k[i] < stoch_d[i]
                        and stoch_k[i] > overbought):
                    sig = -1
        
        elif logic == "ema_trend_pullback":
            # Trend following: only trade in EMA trend direction
            ema200 = calc_ema(closes, 200)
            if not np.isnan(ema_fast[i]) and not np.isnan(ema200[i]):
                in_uptrend = closes[i] > ema200[i]
                in_downtrend = closes[i] < ema200[i]
                if (ema_fast[i-1] <= ema_slow[i-1] and ema_fast[i] > ema_slow[i]
                        and in_uptrend):
                    sig = 1
                elif (ema_fast[i-1] >= ema_slow[i-1] and ema_fast[i] < ema_slow[i]
                        and in_downtrend):
                    sig = -1
        
        # Apply direction filter
        if direction == "long" and sig == -1:
            sig = 0
        elif direction == "short" and sig == 1:
            sig = 0
        
        signals[i] = sig
    
    return signals


# ============================================================
# SESSION FILTER
# ============================================================

def apply_session_filter(timestamps_ms: np.ndarray, signals: np.ndarray,
                         session: Optional[str]) -> np.ndarray:
    if not session:
        return signals
    
    filtered = signals.copy()
    session_hours = {
        "asia":   (0, 8),    # UTC 00:00-08:00
        "london": (7, 16),   # UTC 07:00-16:00
        "ny":     (13, 22),  # UTC 13:00-22:00
    }
    
    if session not in session_hours:
        return signals
    
    start_h, end_h = session_hours[session]
    for i, ts in enumerate(timestamps_ms):
        hour = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).hour
        if not (start_h <= hour < end_h):
            filtered[i] = 0
    return filtered


# ============================================================
# TRADE SIMULATOR
# ============================================================

def simulate_trades(data: dict, signals: np.ndarray, config: StrategyConfig,
                    start_idx: int = 0, end_idx: Optional[int] = None) -> list:
    """
    Simulate trades dan return list of trade dicts.
    """
    closes = data['close']
    n = end_idx or len(closes)
    
    trades = []
    in_position = False
    entry_price = 0.0
    entry_idx = 0
    trade_direction = 0
    
    total_cost_pct = config.fee_pct + config.slippage_pct * 2
    
    for i in range(start_idx, n):
        if not in_position:
            if signals[i] != 0:
                # Entry
                in_position = True
                trade_direction = signals[i]
                # Slippage: long entry slightly higher, short entry slightly lower
                slip = closes[i] * config.slippage_pct / 100
                entry_price = closes[i] + slip if trade_direction == 1 else closes[i] - slip
                entry_idx = i
                
                # Set SL/TP
                if trade_direction == 1:
                    sl_price = entry_price * (1 - config.sl_pct / 100)
                    tp_price = entry_price * (1 + config.tp_pct / 100)
                else:
                    sl_price = entry_price * (1 + config.sl_pct / 100)
                    tp_price = entry_price * (1 - config.tp_pct / 100)
        
        else:
            # Check SL/TP
            exit_price = None
            exit_reason = None
            
            if trade_direction == 1:
                if closes[i] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "sl"
                elif closes[i] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "tp"
            else:
                if closes[i] >= sl_price:
                    exit_price = sl_price
                    exit_reason = "sl"
                elif closes[i] <= tp_price:
                    exit_price = tp_price
                    exit_reason = "tp"
            
            if exit_price:
                # Calculate PnL
                if trade_direction == 1:
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100
                
                pnl_pct -= total_cost_pct  # Kurangi fee + slippage
                
                position_size = config.initial_capital * config.position_size_pct / 100
                pnl_dollar = position_size * pnl_pct / 100
                
                trades.append({
                    "entry_idx": entry_idx,
                    "exit_idx": i,
                    "direction": trade_direction,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "pnl_pct": pnl_pct,
                    "pnl_dollar": pnl_dollar,
                    "bars_held": i - entry_idx,
                    "timestamp_entry": data['open_time'][entry_idx],
                })
                
                in_position = False
    
    return trades


# ============================================================
# METRICS CALCULATOR
# ============================================================

def calc_metrics(trades: list, data_days: float, initial_capital: float) -> dict:
    if not trades:
        return {"total_trades": 0, "status": "no_trades"}
    
    pnls = np.array([t['pnl_dollar'] for t in trades])
    total_trades = len(trades)
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    
    win_rate = len(wins) / total_trades * 100
    net_profit = float(np.sum(pnls))
    profit_per_day = net_profit / data_days if data_days > 0 else 0
    avg_win = float(np.mean(wins)) if len(wins) > 0 else 0
    avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0
    
    # Profit Factor
    gross_profit = float(np.sum(wins)) if len(wins) > 0 else 0
    gross_loss = abs(float(np.sum(losses))) if len(losses) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    # Max Drawdown (dari equity curve)
    equity = initial_capital + np.cumsum(pnls)
    equity = np.insert(equity, 0, initial_capital)
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity) / peak * 100
    max_drawdown = float(np.max(drawdown))
    
    # Sharpe Ratio (annualized, assume daily returns)
    if len(pnls) > 1:
        daily_returns = pnls / initial_capital
        sharpe = float(np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)) if np.std(daily_returns) > 0 else 0
    else:
        sharpe = 0
    
    # Avg RR
    avg_rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    # Long/Short breakdown
    long_trades_list = [t for t in trades if t['direction'] == 1]
    short_trades_list = [t for t in trades if t['direction'] == -1]
    long_wins = [t for t in long_trades_list if t['pnl_dollar'] > 0]
    short_wins = [t for t in short_trades_list if t['pnl_dollar'] > 0]
    
    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 2),
        "profit_per_day": round(profit_per_day, 4),
        "net_profit": round(net_profit, 4),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 3),
        "profit_factor": round(profit_factor, 3),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "avg_rr": round(avg_rr, 3),
        "long_trades": len(long_trades_list),
        "short_trades": len(short_trades_list),
        "long_win_rate": round(len(long_wins)/len(long_trades_list)*100, 2) if long_trades_list else 0,
        "short_win_rate": round(len(short_wins)/len(short_trades_list)*100, 2) if short_trades_list else 0,
        "status": "ok"
    }


# ============================================================
# BACKTESTER
# ============================================================

class Backtester:
    def __init__(self, db_path: str = "market_data.db"):
        self.db_path = db_path
    
    def _load_data(self, symbol: str, timeframe: str, days: int) -> Optional[dict]:
        """Load OHLCV dari SQLite ke numpy arrays."""
        if not Path(self.db_path).exists():
            return None
        
        conn = sqlite3.connect(self.db_path)
        try:
            # Hitung cutoff timestamp
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            cutoff_ms = now_ms - days * 24 * 3600 * 1000
            
            rows = conn.execute("""
                SELECT open_time, open, high, low, close, volume
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
            }
        finally:
            conn.close()
    
    def run(self, config: StrategyConfig) -> BacktestResult:
        result = BacktestResult(
            symbol=config.symbol,
            timeframe=config.timeframe,
            entry_logic=config.entry_logic,
        )
        
        # Load data
        data = self._load_data(config.symbol, config.timeframe, config.days)
        if data is None or len(data['close']) < 100:
            result.status = "insufficient_data"
            result.error = f"Not enough data for {config.symbol} {config.timeframe}"
            return result
        
        n = len(data['close'])
        candles_per_day = {'1m': 1440, '3m': 480, '5m': 288, '15m': 96, '1h': 24}
        cpd = candles_per_day.get(config.timeframe, 288)
        data_days = n / cpd
        result.data_days = round(data_days, 1)
        
        # Split train/OOS
        train_end = int(n * config.train_pct / 100)
        
        # Generate signals
        signals = get_signals(data, config)
        
        # Apply session filter
        if config.session_filter:
            signals = apply_session_filter(data['open_time'], signals, config.session_filter)
        
        # Simulate — TRAIN
        train_trades = simulate_trades(data, signals, config, start_idx=0, end_idx=train_end)
        train_days = train_end / cpd
        train_metrics = calc_metrics(train_trades, train_days, config.initial_capital)
        
        if train_metrics.get("status") == "no_trades":
            result.status = "no_trades"
            result.error = "No trades generated on training set"
            return result
        
        # Simulate — OOS
        oos_trades = simulate_trades(data, signals, config, start_idx=train_end)
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
        
        # Check if meets criteria
        result.meets_criteria = (
            result.profit_per_day >= 10.0 and
            result.max_drawdown <= 5.0 and
            result.win_rate >= 55.0 and
            result.data_days >= 90 and
            result.oos_profit_per_day > 0 and
            result.oos_win_rate >= 50.0 and
            result.total_trades >= 30
        )
        
        return result
    
    def run_batch(self, configs: list) -> list:
        """Run multiple configs dan return list of results."""
        results = []
        for i, config in enumerate(configs):
            print(f"[{i+1}/{len(configs)}] {config.symbol} {config.timeframe} {config.entry_logic}...", 
                  end=" ", flush=True)
            r = self.run(config)
            results.append(r)
            status = "✅ MEETS" if r.meets_criteria else f"({r.win_rate:.0f}% WR, ${r.profit_per_day:.2f}/day)"
            print(status if r.status == "ok" else f"❌ {r.status}")
        return results


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    print("🧪 BabaBot Backtesting Core — Quick Test\n")
    
    bt = Backtester(db_path="market_data.db")
    
    # Test beberapa kombinasi
    test_configs = [
        StrategyConfig(symbol="BTCUSDT", timeframe="5m", entry_logic="ema_cross",
                      indicators={"ema_fast": 9, "ema_slow": 21},
                      sl_pct=0.3, tp_pct=0.8, days=90),
        
        StrategyConfig(symbol="ETHUSDT", timeframe="15m", entry_logic="ema_cross_rsi",
                      indicators={"ema_fast": 9, "ema_slow": 21, "rsi_period": 14,
                                  "rsi_oversold": 35, "rsi_overbought": 65},
                      sl_pct=0.25, tp_pct=0.7, days=90),
        
        StrategyConfig(symbol="BTCUSDT", timeframe="5m", entry_logic="rsi_ob_os",
                      indicators={"rsi_period": 14, "rsi_oversold": 25, "rsi_overbought": 75},
                      sl_pct=0.4, tp_pct=1.0, days=90),
        
        StrategyConfig(symbol="XRPUSDT", timeframe="15m", entry_logic="macd_cross",
                      sl_pct=0.5, tp_pct=1.2, days=90),
    ]
    
    results = bt.run_batch(test_configs)
    
    print("\n" + "="*60)
    print("📊 RESULTS")
    print("="*60)
    for r in results:
        print(f"\n{r.summary()}")
    
    meets = [r for r in results if r.meets_criteria]
    print(f"\n{'='*60}")
    print(f"✅ Strategies meeting criteria: {len(meets)}/{len(results)}")
