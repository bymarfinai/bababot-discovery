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
import time
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ── Shared config ──
DB_PATH = os.environ.get("DB_PATH", "market_data.db")
API_TOKEN = os.environ.get("BACKTEST_API_TOKEN", "")
security = HTTPBearer(auto_error=False)

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not API_TOKEN:
        return True
    if not credentials or credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return True

# ── App ──
app = FastAPI(title="BabaBot Backtesting API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ══════════════════════════════════════════════
# MOUNT ROUTERS (each in its own file)
# ══════════════════════════════════════════════

def _try_mount(module_name, router_attr="router", label=None):
    """Import module, get router, mount to app. Returns True if successful."""
    try:
        mod = __import__(module_name)
        router = getattr(mod, router_attr)
        app.include_router(router)
        print(f"[INIT] ✅ {label or module_name} mounted")
        return True
    except Exception as e:
        print(f"[INIT] ⚠️ {label or module_name} not available: {e}")
        return False

# ── Core routers (from refactored monolith) ──
_try_mount("endpoints_backtest", label="Backtest endpoints (/backtest/*)")
_try_mount("endpoints_data", label="Data endpoints (/data/*, /fetch-*)")
_try_mount("endpoints_tick", label="Tick Discovery (/tick/*)")
_try_mount("endpoints_live", label="Baret Live (/baret-live/*)")
_try_mount("endpoints_ultron", label="Ultron (/ultron/*)")
_try_mount("endpoints_p2_cron", label="P2 Cron (/p2-cron/*)")
_try_mount("endpoints_baret_discovery", label="Baret Discovery (/baret/*)")

# ── Mode 3 family ──
_try_mount("mode3_api", label="Mode3 DRC (/mode3/*)")
_try_mount("mode3_eval_predictor", label="Mode3 Eval Predictor")
_try_mount("mode3_regime_api", label="Mode3 Regime (/mode3/regime/*)")
_try_mount("mtf_analyze_endpoint", label="MTF Analyze (/mtf/*)")
_try_mount("mode3_backtest_endpoint", label="Mode3 Clean (/mode3/backtest)")
_try_mount("mode3_bbc_endpoint", label="Mode3 BBC backtest")
_try_mount("bbc_sweep_endpoint", label="BBC Sweep (/mode3_bbc/sweep/*)")
_try_mount("orchestrator_endpoint", label="Orchestrator (/mtf/orchestrator_backtest)")

# ── BBC Live Trading ──
_try_mount("bbc_live_endpoint", label="BBC Live (/bbc-live/*)")

# ══════════════════════════════════════════════
# MINIMAL ENDPOINTS (stay in app.py)
# ══════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "service": "BabaBot Backtesting API",
        "version": "2.0.0",
        "status": "running",
        "db_path": DB_PATH,
    }

@app.get("/health")
def health():
    db_ok = Path(DB_PATH).exists()
    candle_count = 0
    if db_ok:
        try:
            conn = sqlite3.connect(DB_PATH)
            candle_count = conn.execute("SELECT COUNT(*) FROM klines").fetchone()[0]
            conn.close()
        except:
            pass
    return {"status": "ok", "db_exists": db_ok, "total_candles": candle_count, "db_path": DB_PATH}

@app.get("/server-ip")
def server_ip():
    try:
        import requests
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return {"ok": True, "ip": r.json().get("ip")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ══════════════════════════════════════════════
# AUTO-START (startup events)
# ══════════════════════════════════════════════

@app.on_event("startup")
def _auto_start():
    # P2 Cron
    if os.environ.get("P2_CRON_ENABLED", "true").lower() == "true":
        try:
            from endpoints_p2_cron import start_p2_cron
            start_p2_cron()
        except Exception as e:
            print(f"[INIT] P2 Cron auto-start failed: {e}")
    
    # Baret Live
    if os.environ.get("BARET_LIVE_ENABLED", "false").lower() == "true":
        try:
            from baret_live import start_baret_live
            mode = os.environ.get("BARET_LIVE_MODE", "baret")
            pos_usd = float(os.environ.get("BARET_LIVE_POSITION", "10"))
            start_baret_live(mode=mode, position_usd=pos_usd)
        except Exception as e:
            print(f"[INIT] Baret Live auto-start failed: {e}")
