"""
BabaBot DCA Mode — Ultron Autonomous Discovery Loop
File: dca_bot.py (separate from live_bot.py per V10 spec)

When DCA mode is ON, Pipeline 1 SL/TP is OFF (Railway can't parallel).

Flow:
  Round 1: Backtest combos with default DCA config
    → Ultron (MiniMax) analyze results, adjust spacing/TP for failed pairs
  Round 2: Re-run with adjusted config
    → Ultron fine-tune
  Round N: CONVERGE when improvement < 1%
    → Save to dca_knowledge
    → Jarvis review → Boss approve → deploy
"""

import os
import time
import json
import threading
import traceback
import requests
from collections import deque
from datetime import datetime, timezone

from backtesting_core import (
    DCAConfig, backtest_dca, ENTRY_LOGICS,
)

# ============================================================
# CONFIG
# ============================================================

ULTRON_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
ULTRON_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")
ULTRON_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")
DB_PATH = os.environ.get("DB_PATH", "market_data.db")
WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")

# DCA pairs — BTC excluded per V10
DCA_PAIRS = ["ETHUSDT", "SOLUSDT", "AVAXUSDT", "BNBUSDT", "XRPUSDT",
             "DOGEUSDT", "LINKUSDT", "YFIUSDT", "1000PEPEUSDT"]
DCA_TIMEFRAMES = ["15m", "1h", "4h"]

# State
_dca_running = False
_dca_thread = None
_dca_round = 0
_dca_log = deque(maxlen=200)
_dca_results = {}  # round → results list
_dca_knowledge = {}  # pair → optimal config

# ============================================================
# LOGGING
# ============================================================

def _log(icon: str, category: str, message: str, detail: dict = None):
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "icon": icon, "category": category,
        "message": message, "detail": detail or {},
    }
    _dca_log.appendleft(entry)
    print(f"[DCA {category}] {icon} {message}")


# ============================================================
# ULTRON DCA ANALYZER — MiniMax reasons about results
# ============================================================

ULTRON_DCA_SYSTEM = """You are Ultron, BabaBot's autonomous DCA optimizer.

You receive DCA backtest results for a batch of strategies. Your job:
1. Analyze which combos worked and which failed
2. For failed combos: suggest config adjustments (wider spacing, different TP, regime gate)
3. Track improvement across rounds

Context:
- DCA tests how signals behave when allowed to average down instead of hard SL
- Purpose: discover optimal SL/TP parameters, NOT trade DCA directly
- Goal: find combos where DCA WR ≥ 75% with positive net profit
- Each combo = entry_logic × pair × timeframe

Respond ONLY with JSON:
{
  "analysis": "2-3 sentences overall assessment",
  "adjustments": [
    {"symbol": "ETHUSDT", "timeframe": "4h", "entry_logic": "ema_cross",
     "new_tp_pct": 2.0, "new_spacing": [0, 1.5, 2.5, 4.0, 6.0],
     "regime_gate": "bull,sideways", "reason": "why"}
  ],
  "promising": ["ETHUSDT_4h_ema_cross", ...],
  "drop": ["BTCUSDT_15m_cci_ob_os", ...],
  "confidence": 0.0-1.0
}"""


def call_ultron_dca(context: str) -> dict:
    """Send DCA results to Ultron for analysis"""
    if not ULTRON_API_KEY:
        _log("⚠️", "Ultron", "Offline (no API key)")
        return None
    try:
        resp = requests.post(f"{ULTRON_BASE_URL}/v1/messages",
            headers={"Content-Type": "application/json",
                     "x-api-key": ULTRON_API_KEY,
                     "anthropic-version": "2023-06-01"},
            json={"model": ULTRON_MODEL, "max_tokens": 1000,
                  "system": ULTRON_DCA_SYSTEM,
                  "messages": [{"role": "user", "content": context}]},
            timeout=30)
        if resp.status_code != 200:
            _log("⚠️", "Ultron", f"API error {resp.status_code}")
            return None
        text = ""
        for block in resp.json().get("content", []):
            if block.get("type") == "text":
                text = block.get("text", "")
                break
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(text)
    except Exception as e:
        _log("❌", "Ultron", f"Parse error: {e}")
        return None


# ============================================================
# DCA AUTONOMOUS LOOP — Ultron drives rounds
# ============================================================

def _run_dca_round(round_num: int, configs: list) -> list:
    """Run one round of DCA backtests for all configs"""
    results = []
    total = len(configs)

    for idx, cfg in enumerate(configs):
        if not _dca_running:
            break

        combo = f"{cfg.symbol}_{cfg.timeframe}_{cfg.entry_logic}"
        _log("🔬", "DCA", f"Round {round_num} [{idx+1}/{total}] {combo}...")

        try:
            r = backtest_dca(DB_PATH, cfg)
            if r.get("status") == "ok" and r.get("total_sessions", 0) > 0:
                r["combo"] = combo
                results.append(r)
                _log("✅", "DCA", f"{combo}: WR={r['win_rate']}% ({r['total_sessions']}s) net=${r['net_profit']}")
            else:
                _log("⏭️", "DCA", f"{combo}: {r.get('status', 'no data')}")
        except Exception as e:
            _log("❌", "DCA", f"{combo}: error {e}")

    return results


def _build_ultron_context(round_num: int, results: list, prev_results: list = None) -> str:
    """Format results as context for Ultron analysis"""
    lines = [f"ROUND {round_num} RESULTS ({len(results)} combos tested):"]
    lines.append("")

    # Summary
    profitable = [r for r in results if r.get("net_profit", 0) > 0]
    high_wr = [r for r in results if r.get("win_rate", 0) >= 75]
    lines.append(f"Profitable: {len(profitable)}/{len(results)}")
    lines.append(f"WR ≥ 75%: {len(high_wr)}/{len(results)}")
    if results:
        avg_wr = sum(r.get("win_rate", 0) for r in results) / len(results)
        lines.append(f"Avg WR: {avg_wr:.1f}%")
    lines.append("")

    # Top 10 and bottom 10
    sorted_r = sorted(results, key=lambda x: x.get("win_rate", 0), reverse=True)

    lines.append("TOP 10:")
    for r in sorted_r[:10]:
        lines.append(f"  {r['combo']}: WR={r['win_rate']}% sessions={r['total_sessions']} "
                     f"net=${r['net_profit']} PF={r.get('profit_factor',0)} "
                     f"lvls={r.get('avg_levels_used',0)} "
                     f"adverse_p90={r.get('drawdown_stats',{}).get('p90',0)}% "
                     f"favorable_p75={r.get('recovery_stats',{}).get('p75',0)}%")

    lines.append("")
    lines.append("BOTTOM 10:")
    for r in sorted_r[-10:]:
        lines.append(f"  {r['combo']}: WR={r['win_rate']}% sessions={r['total_sessions']} "
                     f"net=${r['net_profit']}")

    # Improvement from previous round
    if prev_results:
        prev_avg = sum(r.get("win_rate", 0) for r in prev_results) / len(prev_results) if prev_results else 0
        curr_avg = sum(r.get("win_rate", 0) for r in results) / len(results) if results else 0
        improvement = curr_avg - prev_avg
        lines.append(f"\nIMPROVEMENT from Round {round_num-1}: {improvement:+.1f}% avg WR")

    return "\n".join(lines)


def _dca_loop():
    """Main DCA autonomous loop — runs rounds until convergence"""
    global _dca_running, _dca_round

    try:
        _log("🤖", "DCA", "Ultron DCA Discovery started")
        _log("📊", "DCA", f"Scope: {len(DCA_PAIRS)} pairs × {len(DCA_TIMEFRAMES)} TFs × top 10 logics")

        # Default configs for Round 1
        top_logics = ENTRY_LOGICS[:10]  # top 10 entry logics
        configs = []
        for pair in DCA_PAIRS:
            for tf in DCA_TIMEFRAMES:
                for logic in top_logics:
                    configs.append(DCAConfig(
                        symbol=pair, timeframe=tf, entry_logic=logic, days=1825,
                    ))

        _log("🔢", "DCA", f"Total combos: {len(configs)} (max ~270 per round)")

        prev_results = None
        max_rounds = 10

        for round_num in range(1, max_rounds + 1):
            if not _dca_running:
                break

            _dca_round = round_num
            _log("🔄", "DCA", f"=== ROUND {round_num} starting ({len(configs)} combos) ===")

            # Run backtests
            results = _run_dca_round(round_num, configs)
            _dca_results[round_num] = results

            if not results:
                _log("❌", "DCA", f"Round {round_num}: no results")
                break

            # Summary
            profitable = len([r for r in results if r.get("net_profit", 0) > 0])
            avg_wr = sum(r.get("win_rate", 0) for r in results) / len(results)
            _log("📊", "DCA", f"Round {round_num}: {profitable}/{len(results)} profitable, avg WR={avg_wr:.1f}%")

            # Check convergence
            if prev_results:
                prev_avg = sum(r.get("win_rate", 0) for r in prev_results) / len(prev_results)
                improvement = avg_wr - prev_avg
                _log("📈", "DCA", f"Improvement: {improvement:+.1f}%")

                if abs(improvement) < 1.0:
                    _log("✅", "DCA", f"CONVERGED at Round {round_num} — improvement <1%")
                    break

            # Ask Ultron to analyze and suggest adjustments
            context = _build_ultron_context(round_num, results, prev_results)
            _log("⚡", "Ultron", f"Analyzing Round {round_num} results...")
            ultron = call_ultron_dca(context)

            if ultron:
                _log("⚡", "Ultron", f"Analysis: {ultron.get('analysis', 'N/A')}")
                _log("⚡", "Ultron", f"Promising: {len(ultron.get('promising', []))} combos")
                _log("⚡", "Ultron", f"Drop: {len(ultron.get('drop', []))} combos")

                # Apply Ultron's adjustments to configs for next round
                adjustments = ultron.get("adjustments", [])
                drop_list = ultron.get("drop", [])

                new_configs = []
                for cfg in configs:
                    combo = f"{cfg.symbol}_{cfg.timeframe}_{cfg.entry_logic}"

                    # Skip dropped combos
                    if combo in drop_list:
                        continue

                    # Apply adjustments
                    adjusted = False
                    for adj in adjustments:
                        if (adj.get("symbol") == cfg.symbol and
                            adj.get("timeframe") == cfg.timeframe and
                            adj.get("entry_logic") == cfg.entry_logic):
                            new_cfg = DCAConfig(
                                symbol=cfg.symbol, timeframe=cfg.timeframe,
                                entry_logic=cfg.entry_logic,
                                entry_logic_2=cfg.entry_logic_2,
                                tp_pct=adj.get("new_tp_pct", cfg.tp_pct),
                                spacing=adj.get("new_spacing", cfg.spacing),
                                days=cfg.days,
                            )
                            new_configs.append(new_cfg)
                            adjusted = True
                            break

                    if not adjusted:
                        new_configs.append(cfg)

                configs = new_configs
                _log("🔧", "DCA", f"Next round: {len(configs)} combos ({len(adjustments)} adjusted, {len(drop_list)} dropped)")

                # Save knowledge
                for combo_name in ultron.get("promising", []):
                    _dca_knowledge[combo_name] = {
                        "round": round_num,
                        "ultron_analysis": ultron.get("analysis"),
                    }
            else:
                _log("⚠️", "Ultron", "No response — continuing with same configs")

            prev_results = results

        # Final summary
        if _dca_results:
            last_round = max(_dca_results.keys())
            last_results = _dca_results[last_round]
            profitable = len([r for r in last_results if r.get("net_profit", 0) > 0])
            high_wr = len([r for r in last_results if r.get("win_rate", 0) >= 75])
            _log("🏁", "DCA", f"COMPLETE — {_dca_round} rounds, {profitable} profitable, {high_wr} WR≥75%")
            _log("📋", "DCA", f"Knowledge base: {len(_dca_knowledge)} promising combos")
            _log("🤖", "DCA", "Awaiting Jarvis review → Boss approval → deploy")

    except Exception as e:
        _log("💀", "DCA", f"Loop crashed: {e}")
        traceback.print_exc()
    finally:
        _dca_running = False
        _log("🛑", "DCA", f"Stood down after {_dca_round} rounds")


# ============================================================
# START / STOP / STATUS — Called from app.py
# ============================================================

def start_dca():
    global _dca_running, _dca_thread, _dca_round
    if _dca_running and _dca_thread and _dca_thread.is_alive():
        return {"ok": True, "message": "DCA already running"}
    if _dca_running and _dca_thread and not _dca_thread.is_alive():
        _dca_running = False

    _dca_running = True
    _dca_round = 0
    _dca_thread = threading.Thread(target=_dca_loop, daemon=True)
    _dca_thread.start()
    return {"ok": True, "message": f"DCA Discovery started — {len(DCA_PAIRS)} pairs × {len(DCA_TIMEFRAMES)} TFs"}


def stop_dca():
    global _dca_running
    _dca_running = False
    return {"ok": True, "message": "DCA Discovery stopping..."}


def dca_status():
    thread_alive = _dca_thread.is_alive() if _dca_thread else False
    return {
        "running": _dca_running,
        "thread_alive": thread_alive,
        "round": _dca_round,
        "results_by_round": {k: len(v) for k, v in _dca_results.items()},
        "knowledge_count": len(_dca_knowledge),
        "promising_combos": list(_dca_knowledge.keys())[:20],
    }


def get_dca_log(limit: int = 100) -> list:
    return list(_dca_log)[:limit]


def get_dca_results(round_num: int = None) -> list:
    if round_num and round_num in _dca_results:
        return _dca_results[round_num]
    elif _dca_results:
        return _dca_results[max(_dca_results.keys())]
    return []
