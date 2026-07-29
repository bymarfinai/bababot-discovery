"""Backtest endpoints: /backtest, /backtest/batch, feature-study, marthias-study, 
test-rules, bootstrap-validate, sltp-optimize, paper-run, equity-curve, 
walk-forward, fee-compare, combined-equity, deret-statistik, dca."""
import traceback
from fastapi import APIRouter, Security
from pydantic import BaseModel
from typing import Optional
import numpy as np

from shared import bt, verify_token, BacktestRequest, BatchBacktestRequest, CorrelationRequest, DB_PATH
from backtesting_core import (StrategyConfig, ENTRY_LOGICS, calc_correlation, 
    run_feature_study, run_marthias_study, test_ai_rules, bootstrap_validate_rules,
    run_sltp_optimization, run_paper_test, DCAConfig, backtest_dca, 
    backtest_deret_statistik, analyze_deviation_clusters)

router = APIRouter()

DEFAULT_IND = {"ema_fast": 9, "ema_slow": 21, "rsi_period": 14, "rsi_oversold": 30,
    "rsi_overbought": 70, "bb_period": 20, "bb_std": 2.0, "macd_fast": 12,
    "macd_slow": 26, "macd_signal": 9, "atr_period": 14, "stoch_k": 14, "stoch_d": 3, "adx_period": 14}

def _make_config(r, start_date=None, end_date=None):
    return StrategyConfig(symbol=r.symbol.upper(), timeframe=r.timeframe,
        entry_logic=r.entry_logic, entry_logic_2=r.entry_logic_2,
        indicators={**DEFAULT_IND, **r.indicators}, sl_pct=r.sl_pct, tp_pct=r.tp_pct,
        fee_pct=r.fee_pct, slippage_pct=r.slippage_pct, initial_capital=r.initial_capital,
        position_size_pct=r.position_size_pct, days=r.days, train_pct=r.train_pct,
        start_date=start_date or r.start_date, end_date=end_date or r.end_date,
        direction=r.direction, session_filter=r.session_filter, trend_filter=r.trend_filter,
        volatility_filter=r.volatility_filter, volume_filter=r.volume_filter,
        regime_filter=r.regime_filter, use_atr_sl_tp=r.use_atr_sl_tp,
        sl_atr_mult=r.sl_atr_mult, tp_atr_mult=r.tp_atr_mult)


@router.post("/backtest")
def run_backtest(req: BacktestRequest, _=Security(verify_token)):
    config = _make_config(req)
    result = bt.run(config)
    d = result.to_dict()
    if not req.include_equity: d.pop("equity_curve", None)
    return d


@router.post("/backtest/batch")
def run_batch(req: BatchBacktestRequest, _=Security(verify_token)):
    if len(req.configs) > 50: return {"error": "Max 50"}
    results = []
    for r in req.configs:
        if r.entry_logic: r.entry_logic = r.entry_logic.lower()
        if r.entry_logic_2: r.entry_logic_2 = r.entry_logic_2.lower()
        if r.entry_logic and r.entry_logic not in ENTRY_LOGICS:
            results.append({"symbol": r.symbol, "entry_logic": r.entry_logic, "win_rate": 0, "total_trades": 0, "status": "no_trades", "error": f"unknown: {r.entry_logic}", "meets_criteria": False})
            continue
        res = run_backtest(r)
        res["sl_pct"] = r.sl_pct; res["tp_pct"] = r.tp_pct; res.pop("equity_curve", None)
        results.append(res)
    return {"total": len(results), "meets_criteria": sum(1 for r in results if r.get("meets_criteria")), "results": results}


class FeatureStudyRequest(BaseModel):
    symbol: str = "SOLUSDT"; timeframe: str = "4h"; entry_logic: str = "stoch_ob_os"
    entry_logic_2: Optional[str] = None; sl_pct: float = 0.6; tp_pct: float = 1.5
    days: int = 365; start_date: Optional[str] = None; end_date: Optional[str] = None
    include_instances: bool = True; extra_features: Optional[list] = None

@router.post("/backtest/feature-study")
def feature_study(req: FeatureStudyRequest, _=Security(verify_token)):
    result = run_feature_study(backtester=bt, symbol=req.symbol.upper(), timeframe=req.timeframe,
        entry_logic=req.entry_logic, entry_logic_2=req.entry_logic_2, sl_pct=req.sl_pct,
        tp_pct=req.tp_pct, days=req.days, start_date=req.start_date, end_date=req.end_date,
        extra_features=req.extra_features)
    if not req.include_instances and result.get("status") == "ok": result.pop("instances", None)
    return result


class MarthiasStudyRequest(BaseModel):
    symbol: str = "SOLUSDT"; timeframe: str = "4h"; entry_logic: str = "stoch_ob_os"
    entry_logic_2: Optional[str] = None; sl_pct: float = 0.6; tp_pct: float = 1.5
    days: int = 365; start_date: Optional[str] = None; end_date: Optional[str] = None; min_per_group: int = 10

@router.post("/backtest/marthias-study")
def marthias_study(req: MarthiasStudyRequest, _=Security(verify_token)):
    return run_marthias_study(backtester=bt, symbol=req.symbol.upper(), timeframe=req.timeframe,
        entry_logic=req.entry_logic, entry_logic_2=req.entry_logic_2, sl_pct=req.sl_pct,
        tp_pct=req.tp_pct, days=req.days, start_date=req.start_date, end_date=req.end_date,
        min_per_group=req.min_per_group)


class TestRulesRequest(BaseModel):
    symbol: str = "SOLUSDT"; timeframe: str = "4h"; entry_logic: str = "stoch_ob_os"
    entry_logic_2: Optional[str] = None; sl_pct: float = 0.6; tp_pct: float = 1.5; days: int = 365; rules: list = []

@router.post("/backtest/test-rules")
def backtest_test_rules(req: TestRulesRequest, _=Security(verify_token)):
    return test_ai_rules(backtester=bt, symbol=req.symbol.upper(), timeframe=req.timeframe,
        entry_logic=req.entry_logic, entry_logic_2=req.entry_logic_2, sl_pct=req.sl_pct,
        tp_pct=req.tp_pct, days=req.days, rules=req.rules)


class BootstrapRequest(BaseModel):
    symbol: str = "SOLUSDT"; timeframe: str = "4h"; entry_logic: str = "stoch_ob_os"
    entry_logic_2: Optional[str] = None; sl_pct: float = 0.6; tp_pct: float = 1.5
    days: int = 365; rules: list = []; n_iterations: int = 100

@router.post("/backtest/bootstrap-validate")
def bootstrap_validate_endpoint(req: BootstrapRequest, _=Security(verify_token)):
    return bootstrap_validate_rules(backtester=bt, symbol=req.symbol.upper(), timeframe=req.timeframe,
        entry_logic=req.entry_logic, entry_logic_2=req.entry_logic_2, sl_pct=req.sl_pct,
        tp_pct=req.tp_pct, days=req.days, rules=req.rules, n_iterations=req.n_iterations)


class SLTPOptRequest(BaseModel):
    symbol: str = "SOLUSDT"; timeframe: str = "4h"; entry_logic: str = "stoch_ob_os"
    entry_logic_2: Optional[str] = None; days: int = 365; rule_filter: Optional[str] = None
    sl_presets: list = [0.4, 0.6, 0.8]; tp_base: float = 1.0

@router.post("/backtest/sltp-optimize")
def sltp_optimize(req: SLTPOptRequest, _=Security(verify_token)):
    return run_sltp_optimization(backtester=bt, symbol=req.symbol.upper(), timeframe=req.timeframe,
        entry_logic=req.entry_logic, entry_logic_2=req.entry_logic_2, days=req.days,
        rule_filter=req.rule_filter, sl_presets=req.sl_presets, tp_base=req.tp_base)


class PaperRunRequest(BaseModel):
    symbol: str; timeframe: str; entry_logic: str; entry_logic_2: Optional[str] = None
    rule: Optional[str] = None; sl_pct: float = 0.6; tp_pct: float = 1.5; discovery_days: int = 365

@router.post("/backtest/paper-run")
def paper_run_endpoint(req: PaperRunRequest):
    try:
        from backtesting_core import Backtester
        _bt = Backtester(db_path=DB_PATH)
        return run_paper_test(_bt, symbol=req.symbol.upper(), timeframe=req.timeframe,
            entry_logic=req.entry_logic, entry_logic_2=req.entry_logic_2, sl_pct=req.sl_pct,
            tp_pct=req.tp_pct, rule_filter=req.rule, discovery_days=req.discovery_days)
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}


# ── Walk-forward helper ──
def _backtest_with_rule(symbol, timeframe, entry_logic, entry_logic_2, sl_pct, tp_pct,
                        fee_pct, days=1825, start_date=None, end_date=None, rule_filter=None):
    from backtesting_core import parse_rule
    study = run_feature_study(backtester=bt, symbol=symbol.upper(), timeframe=timeframe,
        entry_logic=entry_logic, entry_logic_2=entry_logic_2, sl_pct=sl_pct, tp_pct=tp_pct,
        days=days, start_date=start_date, end_date=end_date)
    instances = study.get("instances", [])
    if not instances:
        return {"win_rate": 0, "total_trades": 0, "net_profit": 0, "max_drawdown": 0, "profit_per_day": 0}
    filtered = instances
    if rule_filter:
        conditions = parse_rule(rule_filter)
        if conditions:
            filtered = []
            for inst in instances:
                features = inst.get("features", {})
                ok = True
                for feat, op, val in conditions:
                    fv = features.get(feat)
                    if fv is None or not isinstance(fv, (int, float)): ok = False; break
                    if op == ">=" and not (fv >= val): ok = False; break
                    elif op == "<=" and not (fv <= val): ok = False; break
                    elif op == ">" and not (fv > val): ok = False; break
                    elif op == "<" and not (fv < val): ok = False; break
                if ok: filtered.append(inst)
    if not filtered:
        return {"win_rate": 0, "total_trades": 0, "net_profit": 0, "max_drawdown": 0, "profit_per_day": 0}
    total = len(filtered)
    wins = sum(1 for i in filtered if i.get("outcome", "") != "loss")
    pnls = [i.get("pnl_dollar", 0) for i in filtered]
    net_profit = round(sum(pnls), 2)
    equity = np.array([10000 + sum(pnls[:i+1]) for i in range(len(pnls))])
    equity = np.insert(equity, 0, 10000)
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / peak * 100
    max_dd = round(float(np.max(dd)), 2) if len(dd) > 0 else 0
    return {"win_rate": round(wins / total * 100, 2), "total_trades": total,
        "net_profit": net_profit, "max_drawdown": max_dd, "profit_per_day": round(net_profit / max(days, 1), 2)}


class EquityCurveRequest(BaseModel):
    symbol: str = "BTCUSDT"; timeframe: str = "1h"; entry_logic: str = "ema_cross"
    entry_logic_2: Optional[str] = None; sl_pct: float = 0.6; tp_pct: float = 1.5
    fee_pct: float = 0.10; initial_capital: float = 10000.0; position_size_pct: float = 10.5
    days: int = 1825; direction: str = "both"; rule_filter: Optional[str] = None

@router.post("/backtest/equity-curve")
def get_equity_curve(req: EquityCurveRequest, _=Security(verify_token)):
    try:
        from backtesting_core import parse_rule, _downsample
        study = run_feature_study(backtester=bt, symbol=req.symbol.upper(), timeframe=req.timeframe,
            entry_logic=req.entry_logic, entry_logic_2=req.entry_logic_2,
            sl_pct=req.sl_pct, tp_pct=req.tp_pct, days=req.days)
        if study.get("status") == "error": return {"ok": False, "error": study.get("error")}
        instances = study.get("instances", [])
        if not instances: return {"ok": False, "error": "No instances"}
        filtered = instances
        if req.rule_filter:
            conditions = parse_rule(req.rule_filter)
            if conditions:
                filtered = [inst for inst in instances if all(
                    (fv := inst.get("features", {}).get(f)) is not None and isinstance(fv, (int, float)) and
                    (fv >= v if o == ">=" else fv <= v if o == "<=" else fv > v if o == ">" else fv < v if o == "<" else True)
                    for f, o, v in conditions)]
        if not filtered: return {"ok": False, "error": "No trades after filter"}
        filtered.sort(key=lambda x: x.get("entry_ts", 0))
        pnls = np.array([i["pnl_dollar"] for i in filtered])
        equity = req.initial_capital + np.cumsum(pnls)
        equity = np.insert(equity, 0, req.initial_capital)
        total = len(filtered); wins = sum(1 for i in filtered if i.get("outcome", "") != "loss")
        peak = np.maximum.accumulate(equity); dd = (peak - equity) / peak * 100
        timestamps = [filtered[0]["entry_ts"] - 86400000] + [i["entry_ts"] for i in filtered]
        return {"ok": True, "total_trades": total, "win_rate": round(wins/total*100, 2),
            "net_profit": round(float(np.sum(pnls)), 2), "max_drawdown": round(float(np.max(dd)), 2),
            "equity_curve": _downsample(equity.tolist(), 100), "timestamps": _downsample(timestamps, 100)}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


class WalkForwardRequest(BaseModel):
    symbol: str = "BTCUSDT"; timeframe: str = "1h"; entry_logic: str = "ema_cross"
    entry_logic_2: Optional[str] = None; sl_pct: float = 0.6; tp_pct: float = 1.5
    fee_pct: float = 0.10; initial_capital: float = 10000.0; position_size_pct: float = 10.5
    direction: str = "both"; train_months: int = 24; test_months: int = 6; step_months: int = 6
    rule_filter: Optional[str] = None

@router.post("/backtest/walk-forward")
def run_walk_forward(req: WalkForwardRequest, _=Security(verify_token)):
    try:
        from datetime import datetime, timedelta
        start = datetime(2021, 1, 1); end = datetime.now(); windows = []; cursor = start
        while True:
            te = cursor + timedelta(days=req.train_months * 30)
            tse = te + timedelta(days=req.test_months * 30)
            if tse > end: break
            windows.append({"ts": cursor.strftime("%Y-%m-%d"), "te": te.strftime("%Y-%m-%d"),
                "tss": te.strftime("%Y-%m-%d"), "tse": tse.strftime("%Y-%m-%d"),
                "label": f"{cursor.strftime('%y/%m')}→{tse.strftime('%y/%m')}"})
            cursor += timedelta(days=req.step_months * 30)
        if not windows: return {"ok": False, "error": "Not enough data"}
        results = []
        for w in windows:
            tr = _backtest_with_rule(req.symbol, req.timeframe, req.entry_logic, req.entry_logic_2,
                req.sl_pct, req.tp_pct, req.fee_pct, start_date=w["ts"], end_date=w["te"], rule_filter=req.rule_filter)
            te = _backtest_with_rule(req.symbol, req.timeframe, req.entry_logic, req.entry_logic_2,
                req.sl_pct, req.tp_pct, req.fee_pct, start_date=w["tss"], end_date=w["tse"], rule_filter=req.rule_filter)
            results.append({"label": w["label"], "train_wr": tr.get("win_rate", 0), "train_trades": tr.get("total_trades", 0),
                "test_wr": te.get("win_rate", 0), "test_trades": te.get("total_trades", 0),
                "test_profit": te.get("net_profit", 0), "wr_gap": round(abs((tr.get("win_rate",0) or 0)-(te.get("win_rate",0) or 0)), 1)})
        valid = [r for r in results if r["test_trades"] >= 3]
        if not valid: verdict = "INSUFFICIENT_DATA"
        else:
            avg_gap = sum(r["wr_gap"] for r in valid) / len(valid)
            prof = sum(1 for r in valid if r["test_profit"] > 0)
            verdict = "ROBUST" if avg_gap <= 10 and prof >= len(valid)*0.6 else "ACCEPTABLE" if avg_gap <= 15 and prof >= len(valid)*0.4 else "OVERFITTING_RISK"
        return {"ok": True, "windows": results, "total_windows": len(results), "verdict": verdict}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


class FeeCompareRequest(BaseModel):
    symbol: str = "BTCUSDT"; timeframe: str = "1h"; entry_logic: str = "ema_cross"
    entry_logic_2: Optional[str] = None; sl_pct: float = 0.6; tp_pct: float = 1.5
    days: int = 1825; rule_filter: Optional[str] = None

@router.post("/backtest/fee-compare")
def run_fee_compare(req: FeeCompareRequest, _=Security(verify_token)):
    tiers = [{"label": "Default", "fee": 0.10}, {"label": "Taker VIP0", "fee": 0.04},
        {"label": "Maker VIP0", "fee": 0.02}, {"label": "Zero", "fee": 0.00}]
    return {"ok": True, "tiers": [{**_backtest_with_rule(req.symbol, req.timeframe, req.entry_logic,
        req.entry_logic_2, req.sl_pct, req.tp_pct, t["fee"], req.days, rule_filter=req.rule_filter),
        "label": t["label"], "fee_pct": t["fee"]} for t in tiers]}


@router.post("/backtest/correlation")
def run_correlation(req: CorrelationRequest, _=Security(verify_token)):
    if len(req.configs) < 2 or len(req.configs) > 10: return {"error": "Need 2-10 configs"}
    from backtesting_core import precompute_indicators, get_signals, apply_filters, simulate_trades
    all_trades = []; results = []; labels = req.labels or []
    for i, r in enumerate(req.configs):
        config = _make_config(r)
        data = bt._load_data(config.symbol, config.timeframe, config.days, config.start_date, config.end_date)
        result = bt.run(config); results.append(result.to_dict())
        if data and len(data['close']) >= 100:
            ind = precompute_indicators(data, config); signals = get_signals(data, ind, config)
            signals = apply_filters(data, ind, signals, config); trades = simulate_trades(data, ind, signals, config, 0)
            all_trades.append(trades)
        else: all_trades.append([])
        if i >= len(labels): labels.append(f"{config.symbol}_{config.timeframe}_{config.entry_logic}")
    return {"results": results, "correlation": calc_correlation(all_trades, labels)}


class MultiPeriodRequest(BaseModel):
    config: BacktestRequest; periods: list[dict] = []

@router.post("/backtest/multiperiod")
def run_multiperiod(req: MultiPeriodRequest, _=Security(verify_token)):
    periods = req.periods or [{"label": "2024", "start": "2024-01-01", "end": "2024-12-31"},
        {"label": "2025", "start": "2025-01-01", "end": "2025-12-31"},
        {"label": "2026", "start": "2026-01-01", "end": "2026-06-05"}]
    results = []
    for p in periods:
        config = _make_config(req.config, start_date=p["start"], end_date=p["end"])
        r = bt.run(config).to_dict()
        r.update({"period_label": p["label"], "period_start": p["start"], "period_end": p["end"]})
        results.append(r)
    prof = sum(1 for r in results if r.get("profit_per_day", 0) > 0 and r.get("status") == "ok")
    return {"strategy": f"{req.config.entry_logic} {req.config.symbol}", "periods": results,
        "total_periods": len(periods), "profitable_periods": prof, "consistent": prof == len(periods)}


class CombinedEquityRequest(BaseModel):
    strategies: list[dict]; days: int = 1825

@router.post("/backtest/combined-equity")
def run_combined_equity(req: CombinedEquityRequest, _=Security(verify_token)):
    try:
        from backtesting_core import _downsample
        all_trades = []; per_strategy = []
        for s in req.strategies[:10]:
            config = StrategyConfig(symbol=s.get("symbol","BTCUSDT").upper(), timeframe=s.get("timeframe","1h"),
                entry_logic=s.get("entry_logic","ema_cross"), entry_logic_2=s.get("entry_logic_2"),
                sl_pct=s.get("sl_pct",0.6), tp_pct=s.get("tp_pct",1.5), fee_pct=0.04, initial_capital=10000,
                position_size_pct=10.5/len(req.strategies), days=req.days, direction="both")
            r = bt.run(config).to_dict()
            label = f"{s.get('symbol','?')}_{s.get('timeframe','?')}_{s.get('entry_logic','?')}"
            for t in r.get("trades", []): all_trades.append({"ts": t.get("entry_ts",0), "pnl": t.get("pnl",0)})
            per_strategy.append({"label": label, "win_rate": r.get("win_rate",0), "total_trades": r.get("total_trades",0),
                "net_profit": r.get("net_profit",0), "max_drawdown": r.get("max_drawdown",0)})
        if not all_trades: return {"ok": False, "error": "No trades"}
        all_trades.sort(key=lambda x: x["ts"])
        pnls = np.array([t["pnl"] for t in all_trades])
        equity = 10000 + np.cumsum(pnls); equity = np.insert(equity, 0, 10000)
        timestamps = [all_trades[0]["ts"]-86400000] + [t["ts"] for t in all_trades]
        peak = np.maximum.accumulate(equity); dd = (peak-equity)/peak*100
        return {"ok": True, "equity_curve": _downsample(equity.tolist(),100), "timestamps": _downsample(timestamps,100),
            "total_trades": len(all_trades), "win_rate": round(sum(1 for t in all_trades if t["pnl"]>0)/len(all_trades)*100,2),
            "net_profit": round(float(np.sum(pnls)),2), "max_drawdown": round(float(np.max(dd)),2), "per_strategy": per_strategy}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Deret Statistik ──
@router.post("/backtest/deret-statistik")
def run_deret_backtest(req: dict, _=Security(verify_token)):
    try:
        result = backtest_deret_statistik(db_path=DB_PATH, symbol=req.get("symbol","ETHUSDT").upper(),
            timeframe=req.get("timeframe","4h"), window=req.get("window",5), buffer_pct=req.get("buffer_pct",0.5),
            tp_pct=req.get("tp_pct",1.0), sl_pct=req.get("sl_pct",1.0), days=req.get("days",1825),
            mode=req.get("mode","baret"), buffer2_pct=req.get("buffer2_pct",1.0),
            close_filter_pct=req.get("close_filter_pct",0.3), max_hold=req.get("max_hold",4),
            sub_candle_tf=req.get("sub_candle_tf"))
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/backtest/deret-statistik/sweep")
def run_deret_sweep(req: dict, _=Security(verify_token)):
    try:
        pairs = req.get("pairs", ["ETHUSDT","SOLUSDT","AVAXUSDT","DOGEUSDT","LINKUSDT","XRPUSDT","BTCUSDT"])
        tfs = req.get("timeframes", ["15m","1h","4h"])
        results = []; best_per = {}
        for sym in pairs:
            for tf in tfs:
                best = None
                for buf in req.get("buffers",[0.3,0.5,0.8,1.0]):
                    for tp in req.get("tps",[0.5,0.8,1.0,1.5]):
                        for sl in req.get("sls",[0.5,0.8,1.0,1.5]):
                            r = backtest_deret_statistik(db_path=DB_PATH, symbol=sym, timeframe=tf,
                                window=req.get("window",5), buffer_pct=buf, tp_pct=tp, sl_pct=sl,
                                days=req.get("days",1825), max_hold=req.get("max_hold",4),
                                sub_candle_tf=req.get("sub_candle_tf","1m"))
                            if r.get("status") != "ok": continue
                            results.append(r)
                            if r["win_rate"] >= 75 and r["total_trades"] >= 10 and r["profit_per_day"] >= 2.0:
                                if not best or r["profit_per_day"] > best["profit_per_day"]: best = r
                if best: best_per[f"{sym}_{tf}"] = best
        passed = [r for r in results if r["win_rate"]>=75 and r["total_trades"]>=10 and r["profit_per_day"]>=2.0]
        return {"ok": True, "total_tested": len(results), "passed": len(passed), "best_per_combo": best_per,
            "top_10": sorted(passed, key=lambda x: x["profit_per_day"], reverse=True)[:10]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── DCA ──
@router.post("/backtest/dca")
def run_dca_backtest(req: dict, _=Security(verify_token)):
    try:
        dca_cfg = DCAConfig(symbol=req.get("symbol","ETHUSDT").upper(), timeframe=req.get("timeframe","4h"),
            entry_logic=req.get("entry_logic","ema_cross"), entry_logic_2=req.get("entry_logic_2"),
            entry_usd=req.get("entry_usd",1.0), leverage=req.get("leverage",50),
            max_levels=req.get("max_levels",5), tp_pct=req.get("tp_pct",1.0),
            cut_pct=req.get("cut_pct",2.0), capital_pool=req.get("capital_pool",100.0),
            days=req.get("days",1825), direction=req.get("direction","both"))
        if req.get("spacing"): dca_cfg.spacing = req["spacing"]
        return {"ok": True, **backtest_dca(DB_PATH, dca_cfg, rule_filter=req.get("rule_filter") or req.get("rule") or None)}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


# ── Clustering ──
@router.post("/backtest/clustering")
def run_clustering(req: dict, _=Security(verify_token)):
    try:
        return {"ok": True, **analyze_deviation_clusters(db_path=DB_PATH, symbol=req.get("symbol","SOLUSDT").upper(),
            timeframe=req.get("timeframe","4h"), window=req.get("window",10), days=req.get("days",1825),
            buffer_pct=req.get("buffer_pct",0.8))}
    except Exception as e:
        return {"ok": False, "error": str(e)}
