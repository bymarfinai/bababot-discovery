"""
sweep.py — Phase E: Parameter Sweep + Walk-Forward Validation
==============================================================

Grid sweep untuk auto-find optimal parameters. Support:
- Multi-parameter grid (kombinasi cartesian)
- Walk-forward validation (train 70% / test 30%) untuk hindari overfitting
- Ranking by composite score (WR × frequency × PnL)
- Top-N config selector

Author: BabaBot team
Version: 0.1.0 (Phase E)
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable, Any
from itertools import product
import time

from .regime import RegimeConfig
from .state_machine import StateMachineConfig
from .classifier import ClassifierConfig
from .backtest import BacktestConfig, BacktestResult, run_regime_backtest


# ═════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════

@dataclass
class SweepGrid:
    """
    Parameter grid. Setiap field adalah list of values untuk sweep.
    Empty list = pakai default.
    """
    # Range detection
    range_max_width_pct: list[float] = field(default_factory=list)
    range_confirmation_candles: list[int] = field(default_factory=list)
    va_percentage: list[float] = field(default_factory=list)

    # State machine
    confirmation_candles: list[int] = field(default_factory=list)
    reclaim_buffer_pct: list[float] = field(default_factory=list)
    reclaim_volume_multiplier: list[float] = field(default_factory=list)
    watching_max_candles: list[int] = field(default_factory=list)
    fake_break_max_candles: list[int] = field(default_factory=list)

    # Backtest
    sl_atr_multiplier: list[float] = field(default_factory=list)
    tp1_ratio: list[float] = field(default_factory=list)  # sisanya auto-balance
    max_hold_candles: list[int] = field(default_factory=list)
    trailing_atr_multiplier: list[float] = field(default_factory=list)

    def get_default() -> "SweepGrid":
        """Sensible default grid untuk exploratory sweep."""
        return SweepGrid(
            range_max_width_pct=[0.03, 0.04, 0.05],
            va_percentage=[0.68, 0.70, 0.72],
            reclaim_buffer_pct=[0.0005, 0.001, 0.002],
            reclaim_volume_multiplier=[1.1, 1.2, 1.5],
            sl_atr_multiplier=[1.2, 1.5, 2.0],
            tp1_ratio=[0.4, 0.5, 0.6],
            max_hold_candles=[6, 8, 12],
        )


@dataclass
class SweepConfig:
    """Config untuk sweep runner."""
    train_split: float = 0.7           # 70% data untuk train, 30% test
    warmup: int = 100                  # Candles skipped di awal
    top_n: int = 10                    # Return top N configs
    min_trades_train: int = 20         # Skip config kalau train trades < 20
    parallel: bool = False             # Parallel execution (require multiprocessing)

    # Scoring weights (composite score)
    weight_wr: float = 0.4             # WR importance
    weight_pnl: float = 0.4            # Total PnL importance
    weight_frequency: float = 0.2      # Trades/day importance (nearer to target = better)
    target_trades_per_day: float = 2.5 # Target frequency


# ═════════════════════════════════════════════════════════════
# RESULT OBJECTS
# ═════════════════════════════════════════════════════════════

@dataclass
class SweepRunResult:
    """Result dari 1 config run (train + test)."""
    config_id: int
    params: dict                       # Parameters dari grid ini

    # Train stats
    train_trades: int
    train_wr: float
    train_pnl: float
    train_max_dd: float
    train_trades_per_day: float

    # Test stats
    test_trades: int
    test_wr: float
    test_pnl: float
    test_max_dd: float
    test_trades_per_day: float

    # Composite scores
    train_score: float
    test_score: float
    overfitting_ratio: float           # test_score / train_score (0-1, lebih 1 = overfit)

    skipped: bool = False
    skip_reason: str = ""


@dataclass
class SweepSummary:
    """Aggregate result dari full sweep."""
    total_configs: int
    completed_configs: int
    skipped_configs: int
    runtime_sec: float
    top_configs: list[SweepRunResult]  # Sorted by test_score desc
    all_results: list[SweepRunResult]


# ═════════════════════════════════════════════════════════════
# GRID EXPANSION
# ═════════════════════════════════════════════════════════════

def expand_grid(grid: SweepGrid) -> list[dict]:
    """
    Cartesian product dari semua param dengan values non-empty.

    Returns:
        List of dict, tiap dict = param combination.
    """
    # Collect non-empty fields
    params = {}
    for key, val in asdict(grid).items():
        if isinstance(val, list) and len(val) > 0:
            params[key] = val

    if not params:
        return [{}]  # Empty grid → single default run

    keys = list(params.keys())
    values = [params[k] for k in keys]

    combos = []
    for combo in product(*values):
        combos.append(dict(zip(keys, combo)))

    return combos


# ═════════════════════════════════════════════════════════════
# APPLY PARAMS TO CONFIG
# ═════════════════════════════════════════════════════════════

def apply_params(
    params: dict,
    regime_cfg: RegimeConfig,
    sm_cfg: StateMachineConfig,
    cls_cfg: ClassifierConfig,
    bt_cfg: BacktestConfig,
) -> tuple[RegimeConfig, StateMachineConfig, ClassifierConfig, BacktestConfig]:
    """Apply params dari sweep grid ke configs (return updated copies)."""
    import copy
    rc = copy.copy(regime_cfg)
    sc = copy.copy(sm_cfg)
    cc = copy.copy(cls_cfg)
    bc = copy.copy(bt_cfg)

    for key, val in params.items():
        # Route param to correct config
        if key in ("range_max_width_pct", "range_confirmation_candles", "va_percentage"):
            setattr(rc, key, val)
        elif key in ("confirmation_candles", "reclaim_buffer_pct",
                     "reclaim_volume_multiplier", "watching_max_candles",
                     "fake_break_max_candles"):
            setattr(sc, key, val)
        elif key in ("sl_atr_multiplier", "max_hold_candles",
                     "trailing_atr_multiplier"):
            setattr(bc, key, val)
        elif key == "tp1_ratio":
            # tp1_ratio → auto balance tp2+tp3 to sum 1.0
            bc.tp1_ratio = val
            remaining = 1.0 - val
            bc.tp2_ratio = remaining * 0.6  # 60% of remaining
            bc.tp3_ratio = remaining * 0.4

    return rc, sc, cc, bc


# ═════════════════════════════════════════════════════════════
# COMPOSITE SCORE
# ═════════════════════════════════════════════════════════════

def compute_score(
    wr: float,
    pnl: float,
    trades_per_day: float,
    starting_equity: float,
    sweep_cfg: SweepConfig,
) -> float:
    """
    Composite score untuk ranking configs.

    Score = w_wr × WR_normalized + w_pnl × PnL_normalized + w_freq × freq_score

    - WR_normalized: (WR - 0.5) × 2 → -1 to +1, clip at 0 for losing configs
    - PnL_normalized: pnl / starting_equity, clipped at [-1, 3]
    - freq_score: 1 - |trades_per_day - target| / target, clipped at 0
    """
    wr_norm = max(0.0, (wr - 0.5) * 2)          # 0.5 WR → 0 score, 1.0 WR → 1.0

    pnl_norm = pnl / starting_equity if starting_equity > 0 else 0.0
    pnl_norm = max(-1.0, min(3.0, pnl_norm)) / 3.0  # Scale to [-0.33, 1.0]
    pnl_norm = max(0.0, pnl_norm)

    freq_diff = abs(trades_per_day - sweep_cfg.target_trades_per_day)
    freq_score = max(0.0, 1.0 - freq_diff / sweep_cfg.target_trades_per_day)

    score = (
        sweep_cfg.weight_wr * wr_norm +
        sweep_cfg.weight_pnl * pnl_norm +
        sweep_cfg.weight_frequency * freq_score
    )
    return score


# ═════════════════════════════════════════════════════════════
# SINGLE CONFIG EVALUATOR (with walk-forward split)
# ═════════════════════════════════════════════════════════════

def evaluate_config(
    config_id: int,
    params: dict,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    sweep_cfg: SweepConfig,
    starting_equity: float,
    regime_cfg: Optional[RegimeConfig] = None,
    sm_cfg: Optional[StateMachineConfig] = None,
    cls_cfg: Optional[ClassifierConfig] = None,
    bt_cfg: Optional[BacktestConfig] = None,
) -> SweepRunResult:
    """
    Evaluate 1 config on train + test split.
    """
    regime_cfg = regime_cfg or RegimeConfig()
    sm_cfg = sm_cfg or StateMachineConfig()
    cls_cfg = cls_cfg or ClassifierConfig()
    bt_cfg = bt_cfg or BacktestConfig()

    rc, sc, cc, bc = apply_params(params, regime_cfg, sm_cfg, cls_cfg, bt_cfg)

    n = len(closes)
    split_idx = int(n * sweep_cfg.train_split)

    # Train slice
    train_result = run_regime_backtest(
        highs[:split_idx], lows[:split_idx],
        closes[:split_idx], volumes[:split_idx],
        cfg=bc, regime_cfg=rc, sm_cfg=sc, cls_cfg=cc,
        warmup=sweep_cfg.warmup,
    )

    if train_result.error or train_result.stats.total_trades < sweep_cfg.min_trades_train:
        return SweepRunResult(
            config_id=config_id, params=params,
            train_trades=train_result.stats.total_trades,
            train_wr=0.0, train_pnl=0.0, train_max_dd=0.0, train_trades_per_day=0.0,
            test_trades=0, test_wr=0.0, test_pnl=0.0, test_max_dd=0.0, test_trades_per_day=0.0,
            train_score=0.0, test_score=0.0, overfitting_ratio=0.0,
            skipped=True,
            skip_reason=train_result.error or f"insufficient_train_trades ({train_result.stats.total_trades})",
        )

    # Test slice
    test_result = run_regime_backtest(
        highs[split_idx:], lows[split_idx:],
        closes[split_idx:], volumes[split_idx:],
        cfg=bc, regime_cfg=rc, sm_cfg=sc, cls_cfg=cc,
        warmup=sweep_cfg.warmup,
    )

    if test_result.error:
        return SweepRunResult(
            config_id=config_id, params=params,
            train_trades=train_result.stats.total_trades,
            train_wr=train_result.stats.win_rate,
            train_pnl=train_result.stats.total_pnl_net,
            train_max_dd=train_result.stats.max_drawdown_pct,
            train_trades_per_day=train_result.stats.trades_per_day,
            test_trades=0, test_wr=0.0, test_pnl=0.0, test_max_dd=0.0, test_trades_per_day=0.0,
            train_score=0.0, test_score=0.0, overfitting_ratio=0.0,
            skipped=True, skip_reason=f"test_error: {test_result.error}",
        )

    # Compute scores
    train_score = compute_score(
        train_result.stats.win_rate,
        train_result.stats.total_pnl_net,
        train_result.stats.trades_per_day,
        starting_equity, sweep_cfg,
    )
    test_score = compute_score(
        test_result.stats.win_rate,
        test_result.stats.total_pnl_net,
        test_result.stats.trades_per_day,
        starting_equity, sweep_cfg,
    )

    overfitting_ratio = test_score / train_score if train_score > 1e-6 else 0.0

    return SweepRunResult(
        config_id=config_id, params=params,
        train_trades=train_result.stats.total_trades,
        train_wr=train_result.stats.win_rate,
        train_pnl=train_result.stats.total_pnl_net,
        train_max_dd=train_result.stats.max_drawdown_pct,
        train_trades_per_day=train_result.stats.trades_per_day,
        test_trades=test_result.stats.total_trades,
        test_wr=test_result.stats.win_rate,
        test_pnl=test_result.stats.total_pnl_net,
        test_max_dd=test_result.stats.max_drawdown_pct,
        test_trades_per_day=test_result.stats.trades_per_day,
        train_score=train_score,
        test_score=test_score,
        overfitting_ratio=overfitting_ratio,
    )


# ═════════════════════════════════════════════════════════════
# MAIN SWEEP RUNNER
# ═════════════════════════════════════════════════════════════

def run_sweep(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    grid: Optional[SweepGrid] = None,
    sweep_cfg: Optional[SweepConfig] = None,
    starting_equity: float = 100.0,
    progress_callback: Optional[Callable[[int, int, SweepRunResult], None]] = None,
) -> SweepSummary:
    """
    Full sweep runner.

    Args:
        highs, lows, closes, volumes: full history
        grid: SweepGrid dengan parameters. Default: SweepGrid.get_default()
        sweep_cfg: SweepConfig
        starting_equity: bankroll awal untuk PnL normalization
        progress_callback: optional callback(current, total, result) untuk progress log

    Returns:
        SweepSummary dengan top-N configs sorted by test_score.
    """
    grid = grid or SweepGrid.get_default()
    sweep_cfg = sweep_cfg or SweepConfig()

    t_start = time.time()

    param_combos = expand_grid(grid)
    total = len(param_combos)

    all_results: list[SweepRunResult] = []
    completed = 0
    skipped = 0

    for i, params in enumerate(param_combos):
        result = evaluate_config(
            config_id=i,
            params=params,
            highs=highs, lows=lows, closes=closes, volumes=volumes,
            sweep_cfg=sweep_cfg,
            starting_equity=starting_equity,
        )

        all_results.append(result)

        if result.skipped:
            skipped += 1
        else:
            completed += 1

        if progress_callback is not None:
            progress_callback(i + 1, total, result)

    # Sort by test_score (unless test skipped, in which case last)
    valid = [r for r in all_results if not r.skipped]
    invalid = [r for r in all_results if r.skipped]
    valid.sort(key=lambda r: r.test_score, reverse=True)

    top_n = valid[:sweep_cfg.top_n]

    runtime = time.time() - t_start

    return SweepSummary(
        total_configs=total,
        completed_configs=completed,
        skipped_configs=skipped,
        runtime_sec=runtime,
        top_configs=top_n,
        all_results=valid + invalid,
    )


# ═════════════════════════════════════════════════════════════
# EXPORT
# ═════════════════════════════════════════════════════════════

__all__ = [
    "SweepGrid",
    "SweepConfig",
    "SweepRunResult",
    "SweepSummary",
    "expand_grid",
    "apply_params",
    "compute_score",
    "evaluate_config",
    "run_sweep",
]
