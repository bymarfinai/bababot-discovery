"""
BabaBot — Baret Discovery Bot (Ultron Autonomous Loop)
Discovers optimal buffer/TP/SL per pair×TF for Deret Statistik strategy.

Mode A (baret): single entry at predicted extreme + buffer
Mode B (baret_dca): L1 + L2 DCA at deeper buffer

Supports multi-timeframe: 15m, 1h, 4h
"""

import os
import time
import json
import threading
from datetime import datetime, timezone
from collections import deque
from backtesting_core import backtest_deret_statistik

# ── Config ──
WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")
MINIMAX_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")

BARET_PAIRS = ["SOLUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "XRPUSDT", "ETHUSDT", "1000PEPEUSDT", "ADAUSDT", "BNBUSDT", "BTCUSDT", "NEARUSDT", "YFIUSDT", "APTUSDT", "ARBUSDT", "SUIUSDT"]
BARET_TFS = ["15m", "1h", "4h"]

# ── State ──
_baret_running = False
_baret_thread = None
_baret_log = deque(maxlen=500)
_baret_state = {
    "round": 0,
    "mode": "baret",
    "total_combos": 0,
    "completed": 0,
    "promising": [],
    "converged": False,
    "started_at": None,
}

ULTRON_BARET_SYSTEM = """You are Ultron, BabaBot's Baret optimizer.
You receive Baret backtest results for all pair×TF combos. Your job:
1. Analyze which combos are profitable (WR ≥ 75%, profit/day ≥ $2, trades ≥ 10)
2. For underperforming combos: suggest adjusted buffer, TP, SL, window
3. Track improvement across rounds

PROVEN KNOWLEDGE from prior testing (use as starting guidance):
- Buffer 0.8-1.5% works best (NOT 0.3-0.5%, too shallow)
- TP 1.0-1.5% is the sweet spot (NOT 0.5% too small, NOT 2%+ too greedy)
- SL 0.5-1.2% works (tight SL is OK because buffer ensures good entries)
- Higher buffer = higher WR but fewer trades. Balance is key.
- Each pair has DIFFERENT optimal: SOL likes buf=0.8, LINK likes buf=1.5, DOGE likes buf=0.7

EXPLORATION RULES:
- Do NOT make tiny adjustments (0.1% changes are useless). Make BOLD moves: ±0.3% minimum per parameter.
- If WR < 70%, try MUCH bigger buffer (jump to 1.0-1.5%)
- If WR > 80% but profit low, try bigger TP (jump to 1.5%)  
- If WR dropped from last round, GO OPPOSITE direction (don't keep pushing same way)
- NEVER drop a pair just because one round was bad. Try different params first.
- Test extreme configs sometimes: buf=1.5% + TP=2% or buf=0.5% + SL=0.5%

Available adjustments per combo:
- buffer_pct: L1 entry distance (0.3-2.0%)
- buffer2_pct: L2 DCA distance (MUST be larger than buffer_pct)
- tp_pct: TP percentage (0.5-2.5%)
- sl_pct: SL percentage (0.3-2.0%)
- window: ratio window (3, 5, 10, 20)
- close_filter_pct: min gap predicted_close vs predicted_low (0.1-1.0%, baret_marfin mode only)

IMPORTANT: buffer2_pct MUST always be bigger than buffer_pct.

Respond ONLY with valid JSON (no markdown, no preamble):
{
  "analysis": "2-3 sentences about what worked and what didn't",
  "adjustments": [
    {
      "symbol": "SOLUSDT", "timeframe": "4h",
      "buffer_pct": 0.8, "tp_pct": 1.5, "sl_pct": 0.8, "window": 5,
      "buffer2_pct": 1.5, "close_filter_pct": 0.3,
      "reason": "why this adjustment"
    }
  ],
  "promising": ["SOLUSDT_4h", "AVAXUSDT_4h"],
  "drop": [],
  "confidence": 0.8
}"""


def _log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    _baret_log.append(entry)
    print(f"[Baret] {entry}")


def _call_ultron(context: str) -> dict:
    """Call MiniMax M2.7 for analysis."""
    import requests as _req
    if not MINIMAX_API_KEY:
        _log("⚠️ No MINIMAX_API_KEY — skipping Ultron analysis")
        return {}
    try:
        resp = _req.post(
            f"{MINIMAX_BASE_URL}/v1/messages",
            headers={"Authorization": f"Bearer {MINIMAX_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MINIMAX_MODEL,
                "max_tokens": 2000,
                "system": ULTRON_BARET_SYSTEM,
                "messages": [{"role": "user", "content": context}],
            },
            timeout=60,
        )
        data = resp.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except Exception as e:
        _log(f"⚠️ Ultron call failed: {e}")
        return {}


def _save_to_d1(endpoint: str, data: dict):
    """POST result to Workers → D1."""
    import requests as _req
    try:
        resp = _req.post(f"{WORKER_URL}/{endpoint}", json=data, timeout=15)
        if resp.status_code != 200:
            _log(f"⚠️ D1 save failed ({endpoint}): {resp.status_code}")
    except Exception as e:
        _log(f"⚠️ D1 save error ({endpoint}): {e}")


def _baret_loop(db_path: str, mode: str = "baret", timeframes: list = None):
    """Main discovery loop — sweep → Ultron analyze → adjust → re-sweep → converge."""
    global _baret_running, _baret_state

    # Full sweep mode: test ALL combinations, no Ultron
    if mode.startswith("sweep_"):
        _baret_sweep_all(db_path, mode, timeframes)
        return

    sweep_tfs = timeframes or BARET_TFS
    _baret_state["mode"] = mode
    _baret_state["started_at"] = datetime.now(timezone.utc).isoformat()
    _baret_state["converged"] = False

    # Default configs per combo
    configs = {}
    for symbol in BARET_PAIRS:
        for tf in sweep_tfs:
            key = f"{symbol}_{tf}"
            configs[key] = {
                "symbol": symbol, "timeframe": tf,
                "buffer_pct": 0.8, "tp_pct": 1.5, "sl_pct": 0.8,
                "window": 5, "buffer2_pct": 1.5, "close_filter_pct": 0.3,
            }

    prev_avg_wr = 0
    max_rounds = 10

    for round_num in range(1, max_rounds + 1):
        if not _baret_running:
            _log("⏹ Stopped by user")
            break

        _baret_state["round"] = round_num
        _baret_state["total_combos"] = len(configs)
        _baret_state["completed"] = 0

        _log(f"═══ ROUND {round_num} ═══ {len(configs)} combos, mode={mode}, TFs={sweep_tfs}")

        round_results = []

        for key, cfg in list(configs.items()):
            if not _baret_running:
                break

            symbol = cfg["symbol"]
            tf = cfg["timeframe"]

            try:
                r = backtest_deret_statistik(
                    db_path=db_path,
                    symbol=symbol, timeframe=tf,
                    window=cfg["window"], buffer_pct=cfg["buffer_pct"],
                    tp_pct=cfg["tp_pct"], sl_pct=cfg["sl_pct"],
                    days=1825, position_usd=100.0, leverage=50, fee_pct=0.10,
                    mode=mode, buffer2_pct=cfg.get("buffer2_pct", 1.0),
                    close_filter_pct=cfg.get("close_filter_pct", 0.3),
                    max_hold=4,
                )

                wr = r.get("win_rate", 0)
                ppd = r.get("profit_per_day", 0)
                tt = r.get("total_trades", 0)
                icon = "⭐" if wr >= 75 else "⚠️" if wr >= 60 else "❌"
                _log(f"  {icon} {key}: WR={wr:.1f}% trades={tt} $/day=${ppd:.2f} DD={r.get('max_drawdown',0):.1f}%")

                result_entry = {
                    "round": round_num, "symbol": symbol, "timeframe": tf,
                    "mode": mode, **{k: cfg[k] for k in ["window", "buffer_pct", "tp_pct", "sl_pct", "buffer2_pct"]},
                    "win_rate": wr, "total_trades": tt, "net_profit": r.get("net_profit", 0),
                    "profit_per_day": ppd, "profit_factor": r.get("profit_factor", 0),
                    "max_drawdown": r.get("max_drawdown", 0), "dca_rate": r.get("dca_rate", 0),
                    "both_hit_pct": round(r.get("both_hit_count", 0) / tt * 100, 1) if tt else 0,
                    "long_trades": r.get("long_trades", 0), "long_wr": r.get("long_wr", 0),
                    "short_trades": r.get("short_trades", 0), "short_wr": r.get("short_wr", 0),
                    "exit_tp": r.get("exit_reasons", {}).get("TP", 0),
                    "exit_sl": r.get("exit_reasons", {}).get("SL", 0),
                    "exit_close": r.get("exit_reasons", {}).get("CLOSE", 0),
                    "max_hold": 4,
                    "stability": r.get("stability", {}),
                }
                round_results.append(result_entry)
                _save_to_d1("baret/save-result", result_entry)

            except Exception as e:
                _log(f"  ❌ {key}: Error — {e}")

            _baret_state["completed"] += 1

        if not _baret_running or not round_results:
            break

        wrs = [r["win_rate"] for r in round_results]
        avg_wr = sum(wrs) / len(wrs) if wrs else 0
        passed = sum(1 for r in round_results if r["win_rate"] >= 75 and r["profit_per_day"] >= 2 and r["total_trades"] >= 10)
        improvement = avg_wr - prev_avg_wr if round_num > 1 else 0

        _log(f"  📊 Round {round_num}: avg WR={avg_wr:.1f}%, {passed} PASS, improvement={improvement:+.1f}%")

        round_results.sort(key=lambda x: -x["profit_per_day"])
        promising = [f"{r['symbol']}_{r['timeframe']}" for r in round_results if r["win_rate"] >= 75]
        _baret_state["promising"] = promising

        best_r = round_results[0] if round_results else {}
        round_summary = {
            "round": round_num, "profitable_combos": passed,
            "failed_combos": len(round_results) - passed,
            "avg_wr": round(avg_wr, 2),
            "best_combo": f"{best_r.get('symbol','')}_{best_r.get('timeframe','')}",
            "best_wr": best_r.get("win_rate", 0),
            "improvement_pct": round(improvement, 2),
            "converged": improvement < 1 and round_num > 1,
        }
        _save_to_d1("baret/save-round", round_summary)

        if round_num > 3 and abs(improvement) < 1.0 and avg_wr > prev_avg_wr - 2:
            _log(f"  ✅ CONVERGED — improvement {improvement:+.1f}% < 1% (after 3+ rounds)")
            _baret_state["converged"] = True
            break

        if round_num > 1 and improvement < -5:
            _log(f"  ⚠️ WR dropped {improvement:.1f}% — reverting to wider exploration")

        prev_avg_wr = avg_wr

        ultron = _call_ultron(
            f"Round {round_num} results (mode={mode}):\n"
            f"Average WR: {avg_wr:.1f}%, {passed}/{len(round_results)} passed\n\n"
            f"TOP 5:\n" + "\n".join(
                f"  {r['symbol']}_{r['timeframe']}: WR={r['win_rate']:.1f}% $/day=${r['profit_per_day']:.2f} "
                f"buf={r['buffer_pct']}% tp={r['tp_pct']}% sl={r['sl_pct']}% w={r['window']}"
                for r in round_results[:5]
            ) + "\n\nBOTTOM 5:\n" + "\n".join(
                f"  {r['symbol']}_{r['timeframe']}: WR={r['win_rate']:.1f}% $/day=${r['profit_per_day']:.2f} "
                f"buf={r['buffer_pct']}% tp={r['tp_pct']}% sl={r['sl_pct']}% w={r['window']}"
                for r in round_results[-5:]
            )
        )
        if ultron:
            _log(f"  🤖 Ultron: {ultron.get('analysis', 'no analysis')}")
            for adj in ultron.get("adjustments", []):
                akey = f"{adj['symbol']}_{adj.get('timeframe', '4h')}"
                if akey in configs:
                    for field in ["buffer_pct", "tp_pct", "sl_pct", "window", "buffer2_pct", "close_filter_pct"]:
                        if field in adj:
                            configs[akey][field] = adj[field]
                    _log(f"    → Adjusted {akey}: buf={configs[akey]['buffer_pct']} tp={configs[akey]['tp_pct']} sl={configs[akey]['sl_pct']}")
            for drop_key in ultron.get("drop", []):
                if drop_key in configs:
                    del configs[drop_key]
                    _log(f"    → Dropped {drop_key}")
        else:
            _log("  ⚠️ Ultron unavailable — trying broader sweep next round")
            for r in round_results[-5:]:
                key = f"{r['symbol']}_{r['timeframe']}"
                if key in configs:
                    configs[key]["buffer_pct"] = min(configs[key]["buffer_pct"] + 0.2, 2.0)
                    configs[key]["tp_pct"] = max(configs[key]["tp_pct"] - 0.2, 0.3)

        time.sleep(2)

    _log(f"═══ DISCOVERY COMPLETE ═══ {_baret_state['round']} rounds")
    _baret_running = False


def _baret_sweep_all(db_path: str, mode: str = "sweep_all", timeframes: list = None):
    """Full grid sweep — test ALL buffer/TP/SL/window combinations. No Ultron.
    Supports multi-timeframe via timeframes param.
    """
    global _baret_running, _baret_state

    if mode == "sweep_marfin":
        backtest_mode = "baret_marfin"
    elif mode == "sweep_dca":
        backtest_mode = "baret_dca"
    else:
        backtest_mode = "baret"

    sweep_tfs = timeframes or BARET_TFS
    
    buffers = [0.3, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0]
    tps = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]
    sls = [0.3, 0.5, 0.8, 1.0, 1.2, 1.5]
    windows = [3, 5, 10]
    
    if mode == "sweep_marfin":
        close_filters = [0.2, 0.3, 0.5, 0.8]
        buf2s = [0]
    elif mode == "sweep_dca":
        close_filters = [0]
        buf2s = [0.8, 1.0, 1.5, 2.0]
    else:
        close_filters = [0]
        buf2s = [0]

    combos_per_tf = len(BARET_PAIRS) * len(buffers) * len(tps) * len(sls) * len(windows) * max(len(close_filters), len(buf2s))
    total = combos_per_tf * len(sweep_tfs)
    
    _baret_state["mode"] = mode
    _baret_state["round"] = 1
    _baret_state["total_combos"] = total
    _baret_state["completed"] = 0
    _baret_state["converged"] = False
    _baret_state["started_at"] = datetime.now(timezone.utc).isoformat()

    _log(f"═══ FULL SWEEP START ═══ {total} combinations, mode={backtest_mode}, TFs={sweep_tfs}")
    
    best_per_pair = {}
    count = 0

    for tf in sweep_tfs:
        if not _baret_running:
            break
        _log(f"  ═══ Timeframe: {tf} ═══")
        
        for symbol in BARET_PAIRS:
            if not _baret_running:
                break
            for w in windows:
                for buf in buffers:
                    for tp in tps:
                        for sl in sls:
                            extras = close_filters if mode == "sweep_marfin" else buf2s if mode == "sweep_dca" else [0]
                            for extra in extras:
                                if not _baret_running:
                                    break
                                
                                if mode == "sweep_dca" and extra <= buf:
                                    count += 1
                                    _baret_state["completed"] = count
                                    continue
                                
                                count += 1
                                try:
                                    cf = extra if mode == "sweep_marfin" else 0.3
                                    b2 = extra if mode == "sweep_dca" else buf + 0.5
                                    
                                    r = backtest_deret_statistik(
                                        db_path=db_path,
                                        symbol=symbol, timeframe=tf,
                                        window=w, buffer_pct=buf,
                                        tp_pct=tp, sl_pct=sl,
                                        days=1825, position_usd=100.0, leverage=50, fee_pct=0.10,
                                        mode=backtest_mode, buffer2_pct=b2,
                                        close_filter_pct=cf,
                                        max_hold=4,
                                    )
                                    
                                    wr = r.get("win_rate", 0)
                                    ppd = r.get("profit_per_day", 0)
                                    tt = r.get("total_trades", 0)
                                    
                                    result_entry = {
                                        "round": 1, "symbol": symbol, "timeframe": tf,
                                        "mode": backtest_mode,
                                        "window": w, "buffer_pct": buf, "tp_pct": tp, "sl_pct": sl,
                                        "buffer2_pct": b2, "close_filter_pct": cf,
                                        "win_rate": wr, "total_trades": tt,
                                        "net_profit": r.get("net_profit", 0),
                                        "profit_per_day": ppd,
                                        "profit_factor": r.get("profit_factor", 0),
                                        "max_drawdown": r.get("max_drawdown", 0),
                                        "dca_rate": r.get("dca_rate", 0),
                                        "both_hit_pct": round(r.get("both_hit_count", 0) / tt * 100, 1) if tt else 0,
                                        "long_trades": r.get("long_trades", 0), "long_wr": r.get("long_wr", 0),
                                        "short_trades": r.get("short_trades", 0), "short_wr": r.get("short_wr", 0),
                                        "exit_tp": r.get("exit_reasons", {}).get("TP", 0),
                                        "exit_sl": r.get("exit_reasons", {}).get("SL", 0),
                                        "exit_close": r.get("exit_reasons", {}).get("CLOSE", 0),
                                        "max_hold": 4,
                                        "stability": r.get("stability", {}),
                                    }
                                    
                                    _save_to_d1("baret/save-result", result_entry)
                                    
                                    if wr >= 75 and ppd >= 2 and tt >= 10:
                                        key = f"{symbol}_{tf}"
                                        if key not in best_per_pair or ppd > best_per_pair[key]["profit_per_day"]:
                                            best_per_pair[key] = result_entry
                                    
                                    if count % 50 == 0:
                                        pct = count * 100 // total if total else 0
                                        _log(f"  📊 Progress: {count}/{total} ({pct}%) — {tf} {symbol} buf={buf} tp={tp} sl={sl} w={w}")
                                    
                                except Exception as e:
                                    _log(f"  ❌ {tf} {symbol} buf={buf} tp={tp} sl={sl}: {e}")
                                
                                _baret_state["completed"] = count

    _baret_state["converged"] = True
    promising = list(best_per_pair.keys())
    _baret_state["promising"] = promising
    
    _log(f"═══ FULL SWEEP DONE ═══ {count} tested, {len(best_per_pair)} combos PASS")
    for key in sorted(best_per_pair, key=lambda k: -best_per_pair[k]["profit_per_day"]):
        b = best_per_pair[key]
        _log(f"  ⭐ {key}: WR={b['win_rate']:.1f}% ${b['profit_per_day']:.2f}/day buf={b['buffer_pct']} tp={b['tp_pct']} sl={b['sl_pct']} w={b['window']}")
    
    _baret_running = False


# ── Public API ──

def start_baret(db_path: str, mode: str = "baret", timeframes: list = None):
    global _baret_running, _baret_thread
    if _baret_running:
        return {"ok": True, "message": "Already running", "round": _baret_state["round"]}
    _baret_running = True
    tfs = timeframes or BARET_TFS
    _baret_thread = threading.Thread(target=_baret_loop, args=(db_path, mode, tfs), daemon=True)
    _baret_thread.start()
    return {"ok": True, "message": f"Baret discovery started, mode={mode}, TFs={tfs}"}


def stop_baret():
    global _baret_running
    _baret_running = False
    return {"ok": True, "message": "Baret discovery stopped"}


def baret_status():
    return {
        "ok": True,
        "running": _baret_running,
        "thread_alive": _baret_thread.is_alive() if _baret_thread else False,
        **_baret_state,
    }


def get_baret_log(limit: int = 200):
    return list(_baret_log)[-limit:]
