""" 
BabaBot — Main App (Thin Orchestrator)
All endpoints live in separate router files. This file only:
1. Creates FastAPI app
2. Imports and mounts routers
3. Manages shared state (DB, auth, fetch)

REFACTORED: 29 Jul 2026
Original 113KB monolith → thin orchestrator + router files
"""

import os
import sqlite3
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = os.environ.get("DB_PATH", "market_data.db")

app = FastAPI(title="BabaBot Backtesting API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ══════════════════════════════════════════════
# MOUNT ROUTERS
# ══════════════════════════════════════════════

def _try_mount(module_name, label=None):
    try:
        mod = __import__(module_name)
        app.include_router(mod.router)
        print(f"[INIT] ✅ {label or module_name}")
        return True
    except Exception as e:
        print(f"[INIT] ⚠️ {label or module_name}: {e}")
        return False

# Core (refactored from monolith)
_try_mount("endpoints_backtest", "Backtest (/backtest/*)")
_try_mount("endpoints_data", "Data (/data/*, /fetch-*, /strategies)")
_try_mount("endpoints_tick", "Tick Discovery (/tick/*)")
_try_mount("endpoints_live", "Live + Ultron + Baret (/baret-live/*, /baret/*, /ultron/*)")
_try_mount("endpoints_p2_cron", "P2 Cron (/p2-cron/*)")

# Mode 3 family
_try_mount("mode3_api", "Mode3 DRC")
_try_mount("mode3_eval_predictor", "Mode3 Eval Predictor")
_try_mount("mode3_regime_api", "Mode3 Regime")
_try_mount("mtf_analyze_endpoint", "MTF Analyze")
_try_mount("mode3_backtest_endpoint", "Mode3 Clean")
_try_mount("mode3_bbc_endpoint", "Mode3 BBC backtest")
_try_mount("causal_bbc_endpoint", "Causal BBC backtest (/mode3_bbc/causal-backtest)")
_try_mount("same_hour_bbc_endpoint", "Causal BBC same-hour 3→4 backtest")
_try_mount("causal_sniper_endpoint", "Causal EMA7 sniper concepts")
_try_mount("causal_parity_endpoint", "Causal BBC parity backtest")
_try_mount("causal_state_reject_endpoint", "Causal 1H state + 15m EMA7 rejection")
_try_mount("causal_state_mtf_reject_endpoint", "Causal 1H state + 15m EMA rejection")
_try_mount("bbc_sweep_endpoint", "BBC Sweep")
_try_mount("bbc_limit_sim", "BBC Limit Order Sim (/mode3_bbc/limit_sim)")
_try_mount("orchestrator_endpoint", "Orchestrator")

# BBC Live Trading
_try_mount("bbc_live_endpoint", "BBC Live (/bbc-live/*)")

# ══════════════════════════════════════════════
# MINIMAL ENDPOINTS
# ══════════════════════════════════════════════

@app.get("/")
def root():
    return {"service": "BabaBot Backtesting API", "version": "2.0.0", "status": "running"}

@app.get("/health")
def health():
    db_ok = Path(DB_PATH).exists()
    candle_count = 0
    if db_ok:
        try:
            conn = sqlite3.connect(DB_PATH)
            candle_count = conn.execute("SELECT COUNT(*) FROM klines").fetchone()[0]
            conn.close()
        except: pass
    return {"status": "ok", "db_exists": db_ok, "total_candles": candle_count, "db_path": DB_PATH}

@app.get("/server-ip")
def server_ip():
    try:
        import requests
        return {"ok": True, "ip": requests.get("https://api.ipify.org?format=json", timeout=5).json().get("ip")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ══════════════════════════════════════════════
# AUTO-START
# ══════════════════════════════════════════════

@app.on_event("startup")
def _auto_start():
    if os.environ.get("P2_CRON_ENABLED", "true").lower() == "true":
        try:
            from endpoints_p2_cron import start_p2_cron
            start_p2_cron()
        except Exception as e:
            print(f"[INIT] P2 Cron auto-start failed: {e}")
    if os.environ.get("BARET_LIVE_ENABLED", "false").lower() == "true":
        try:
            from baret_live import start_baret_live
            start_baret_live(mode=os.environ.get("BARET_LIVE_MODE", "baret"),
                position_usd=float(os.environ.get("BARET_LIVE_POSITION", "10")))
        except Exception as e:
            print(f"[INIT] Baret Live auto-start failed: {e}")
