"""P2 Cron — background pipeline 2 + sweep + seed processing."""
import os
import time
import threading
from fastapi import APIRouter
import requests as _requests

router = APIRouter()

_p2_cron_running = False
_p2_cron_lock = threading.Lock()
_p2_interval = int(os.environ.get("P2_CRON_INTERVAL", "60"))
_p2_worker_url = os.environ.get("P2_WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev/discovery/marthias/run-next")


def _p2_cron_loop():
    global _p2_cron_running
    print(f"[P2 Cron] Started, interval={_p2_interval}s")
    while _p2_cron_running:
        try:
            base_url = _p2_worker_url.replace('/marthias/run-next', '')

            # ── Sweep jobs ──
            try:
                try: _requests.post(f"{base_url}/sweep/reset", json={"auto": True}, timeout=5)
                except: pass
                sweep_resp = _requests.post(f"{base_url}/sweep/process-next", json={}, timeout=10)
                sweep_data = sweep_resp.json()
                if sweep_data.get("ok") and not sweep_data.get("queue_empty"):
                    job = sweep_data
                    symbol, tf = job["symbol"], job["timeframe"]
                    entry_logic = job["entry_logic"]
                    entry_logic_2 = job.get("entry_logic_2")
                    days = job.get("days", 1825)
                    print(f"[Sweep] Processing {symbol}·{tf} {entry_logic}")

                    from shared import bt, BacktestRequest
                    from backtesting_core import StrategyConfig
                    results = []
                    for sl in [0.4, 0.6, 0.8]:
                        for tp in [1.0, 1.5, 2.0]:
                            try:
                                config = StrategyConfig(symbol=symbol, timeframe=tf,
                                    entry_logic=entry_logic, entry_logic_2=entry_logic_2,
                                    sl_pct=sl, tp_pct=tp, days=days, direction="both")
                                result = bt.run(config)
                                r = result.to_dict()
                                r.update({"sl_pct": sl, "tp_pct": tp, "symbol": symbol,
                                    "timeframe": tf, "entry_logic": entry_logic, "entry_logic_2": entry_logic_2})
                                r.pop("equity_curve", None)
                                if r.get("status") == "ok" and r.get("total_trades", 0) >= 5:
                                    results.append(r)
                            except: pass
                    results.sort(key=lambda x: (-x.get("win_rate", 0), -x.get("profit_per_day", 0)))
                    results = results[:20]
                    best_wr = results[0]["win_rate"] if results else 0
                    print(f"[Sweep] {'⭐' if best_wr >= 55 else '✅' if best_wr >= 50 else '❌'} {symbol}·{tf}: WR={best_wr:.1f}%")
                    try:
                        _requests.post(f"{base_url}/sweep/save-result", json={
                            "job_id": job["job_id"], "session_id": job["session_id"],
                            "entry_logic": entry_logic, "entry_logic_2": entry_logic_2,
                            "symbol": symbol, "timeframe": tf, "results": results,
                        }, timeout=15)
                    except: pass
                    time.sleep(5)
            except Exception as e:
                print(f"[Sweep] Error: {e}")

            # ── Auto seed ──
            try:
                seed_resp = _requests.post(f"{base_url}/marthias/seed-queue", json={}, timeout=15)
                seed_data = seed_resp.json()
                if seed_data.get("queued", 0) > 0:
                    print(f"[Seed] 🌱 {seed_data['queued']} new combos queued")
            except: pass

            # ── Pipeline 2 ──
            with _p2_cron_lock:
                resp = _requests.post(_p2_worker_url, json={}, timeout=300)
                data = resp.json()
                status = data.get("status", "?")
                combo = data.get("combo", "")
                if status == "ok":
                    best = data.get("best_rule", {})
                    print(f"[P2 Cron] OK: {combo} | WR {best.get('wr','?')}%")
                elif status == "queue_empty":
                    print("[P2 Cron] Queue empty")
                else:
                    print(f"[P2 Cron] {status}: {combo}")
        except Exception as e:
            print(f"[P2 Cron] Error: {e}")
        time.sleep(_p2_interval)


def start_p2_cron():
    global _p2_cron_running
    if _p2_cron_running:
        return
    _p2_cron_running = True
    t = threading.Thread(target=_p2_cron_loop, daemon=True)
    t.start()
    print(f"[P2 Cron] Auto-started (includes sweep)")


@router.get("/p2-cron/start")
def p2_cron_start():
    global _p2_cron_running
    if _p2_cron_running:
        return {"ok": True, "message": "Already running"}
    start_p2_cron()
    return {"ok": True, "message": f"P2 cron started, interval={_p2_interval}s"}

@router.get("/p2-cron/stop")
def p2_cron_stop():
    global _p2_cron_running
    _p2_cron_running = False
    return {"ok": True, "message": "P2 cron stopped"}

@router.get("/p2-cron/status")
def p2_cron_status():
    return {"running": _p2_cron_running, "interval": _p2_interval, "url": _p2_worker_url}

@router.get("/sweep-cron/status")
def sweep_cron_status():
    return {"info": "Sweep integrated into P2 cron", "p2_running": _p2_cron_running}
