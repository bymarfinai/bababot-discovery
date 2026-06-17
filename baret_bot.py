"""
BabaBot — Baret Discovery Bot (Ultron Autonomous Loop)
Discovers optimal buffer/TP/SL per pair×TF for Deret Statistik strategy.

Mode A (baret): single entry at predicted extreme + buffer
Mode B (baret_dca): L1 + L2 DCA at deeper buffer

Mirrors dca_bot.py structure.
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

BARET_PAIRS = ["SOLUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "XRPUSDT", "ETHUSDT", "1000PEPEUSDT"]
BARET_TFS = ["4h"]  # Only 4h validated

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
3. Compare modes if both baret and baret_dca are tested
4. Track improvement across rounds

Available adjustments per combo:
- buffer_pct: L1 entry distance (0.1-2.0%)
- buffer2_pct: L2 DCA distance (MUST be larger than buffer_pct, e.g. if buffer_pct=0.5 then buffer2_pct=1.0+)
- tp_pct: TP percentage (0.3-3.0%)
- sl_pct: SL percentage (0.3-3.0%)
- window: ratio window (3, 5, 10, 20)

IMPORTANT: buffer2_pct is the DEEPER DCA level. It MUST always be bigger than buffer_pct.
Example: buffer_pct=0.5%, buffer2_pct=1.0% means L1 at -0.5%, L2 DCA at -1.0% (deeper).

Respond ONLY with valid JSON (no markdown, no preamble):
{
  "analysis": "2-3 sentences about what worked and what didn't",
  "adjustments": [
    {
      "symbol": "SOLUSDT", "timeframe": "4h",
      "buffer_pct": 0.8, "tp_pct": 0.8, "sl_pct": 1.0, "window": 5,
      "buffer2_pct": 1.5,
      "reason": "why this adjustment"
    }
  ],
  "promising": ["SOLUSDT_4h", "AVAXUSDT_4h"],
  "drop": ["BTCUSDT_4h"],
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
        # Parse JSON from response
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


def _baret_loop(db_path: str, mode: str = "baret"):
    """Main discovery loop — sweep → Ultron analyze → adjust → re-sweep → converge."""
    global _baret_running, _baret_state

    _baret_state["mode"] = mode
    _baret_state["started_at"] = datetime.now(timezone.utc).isoformat()
    _baret_state["converged"] = False

    # Default configs per combo
    configs = {}
    for symbol in BARET_PAIRS:
        for tf in BARET_TFS:
            key = f"{symbol}_{tf}"
            configs[key] = {
                "symbol": symbol, "timeframe": tf,
                "buffer_pct": 0.5, "tp_pct": 1.0, "sl_pct": 1.0,
                "window": 5, "buffer2_pct": 1.0,
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

        _log(f"═══ ROUND {round_num} ═══ {len(configs)} combos, mode={mode}")

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
                    days=1825, position_usd=1.0, leverage=50, fee_pct=0.10,
                    mode=mode, buffer2_pct=cfg.get("buffer2_pct", 1.0),
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
                    "long_trades": r.get("long_trades", 0), "long_wr": r.get("long_wr", 0),
                    "short_trades": r.get("short_trades", 0), "short_wr": r.get("short_wr", 0),
                    "exit_tp": r.get("exit_reasons", {}).get("TP", 0),
                    "exit_sl": r.get("exit_reasons", {}).get("SL", 0),
                    "exit_close": r.get("exit_reasons", {}).get("CLOSE", 0),
                }
                round_results.append(result_entry)

                # Save each result to D1
                _save_to_d1("baret/save-result", result_entry)

            except Exception as e:
                _log(f"  ❌ {key}: Error — {e}")

            _baret_state["completed"] += 1

        if not _baret_running or not round_results:
            break

        # ── Round summary ──
        wrs = [r["win_rate"] for r in round_results]
        avg_wr = sum(wrs) / len(wrs) if wrs else 0
        passed = sum(1 for r in round_results if r["win_rate"] >= 75 and r["profit_per_day"] >= 2 and r["total_trades"] >= 10)
        improvement = avg_wr - prev_avg_wr if round_num > 1 else 0

        _log(f"  📊 Round {round_num}: avg WR={avg_wr:.1f}%, {passed} PASS, improvement={improvement:+.1f}%")

        # Sort to find best
        round_results.sort(key=lambda x: -x["profit_per_day"])
        promising = [f"{r['symbol']}_{r['timeframe']}" for r in round_results if r["win_rate"] >= 75]
        _baret_state["promising"] = promising

        # Save round summary to D1
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

        # ── Check convergence ──
        if round_num > 1 and abs(improvement) < 1.0:
            _log(f"  ✅ CONVERGED — improvement {improvement:+.1f}% < 1%")
            _baret_state["converged"] = True
            break

        prev_avg_wr = avg_wr

        # ── Call Ultron for adjustments ──
        top_5 = round_results[:5]
        bottom_5 = round_results[-5:] if len(round_results) > 5 else []
        context = (
            f"Round {round_num} results (mode={mode}):\n"
            f"Average WR: {avg_wr:.1f}%, {passed}/{len(round_results)} passed\n\n"
            f"TOP 5:\n" + "\n".join(
                f"  {r['symbol']}_{r['timeframe']}: WR={r['win_rate']:.1f}% $/day=${r['profit_per_day']:.2f} "
                f"buf={r['buffer_pct']}% tp={r['tp_pct']}% sl={r['sl_pct']}% w={r['window']}"
                for r in top_5
            ) + "\n\nBOTTOM 5:\n" + "\n".join(
                f"  {r['symbol']}_{r['timeframe']}: WR={r['win_rate']:.1f}% $/day=${r['profit_per_day']:.2f} "
                f"buf={r['buffer_pct']}% tp={r['tp_pct']}% sl={r['sl_pct']}% w={r['window']}"
                for r in bottom_5
            )
        )

        ultron = _call_ultron(context)
        if ultron:
            _log(f"  🤖 Ultron: {ultron.get('analysis', 'no analysis')}")
            # Apply adjustments
            for adj in ultron.get("adjustments", []):
                akey = f"{adj['symbol']}_{adj.get('timeframe', '4h')}"
                if akey in configs:
                    for field in ["buffer_pct", "tp_pct", "sl_pct", "window", "buffer2_pct"]:
                        if field in adj:
                            configs[akey][field] = adj[field]
                    _log(f"    → Adjusted {akey}: buf={configs[akey]['buffer_pct']} tp={configs[akey]['tp_pct']} sl={configs[akey]['sl_pct']}")
            # Drop combos Ultron says to drop
            for drop_key in ultron.get("drop", []):
                if drop_key in configs:
                    del configs[drop_key]
                    _log(f"    → Dropped {drop_key}")
        else:
            _log("  ⚠️ Ultron unavailable — trying broader sweep next round")
            # Fallback: try different params for worst performers
            for r in bottom_5:
                key = f"{r['symbol']}_{r['timeframe']}"
                if key in configs:
                    # Try wider buffer
                    configs[key]["buffer_pct"] = min(configs[key]["buffer_pct"] + 0.2, 2.0)
                    # Try lower TP
                    configs[key]["tp_pct"] = max(configs[key]["tp_pct"] - 0.2, 0.3)

        time.sleep(2)  # Brief pause between rounds

    _log(f"═══ DISCOVERY COMPLETE ═══ {_baret_state['round']} rounds")
    _baret_running = False


# ── Public API ──

def start_baret(db_path: str, mode: str = "baret"):
    global _baret_running, _baret_thread
    if _baret_running:
        return {"ok": True, "message": "Already running", "round": _baret_state["round"]}
    _baret_running = True
    _baret_thread = threading.Thread(target=_baret_loop, args=(db_path, mode), daemon=True)
    _baret_thread.start()
    return {"ok": True, "message": f"Baret discovery started, mode={mode}"}


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
