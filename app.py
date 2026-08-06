""" 
BabaBot — Main App (Thin Orchestrator)
"""
import os, sqlite3
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = os.environ.get("DB_PATH", "market_data.db")
app = FastAPI(title="BabaBot Backtesting API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def _try_mount(module_name, label=None):
    try:
        mod = __import__(module_name)
        if hasattr(mod, 'router'):
            app.include_router(mod.router)
        if hasattr(mod, 'router_sweep'):
            app.include_router(mod.router_sweep)
        print(f"[INIT] ✅ {label or module_name}")
        return True
    except Exception as e:
        print(f"[INIT] ⚠️ {label or module_name}: {e}")
        return False

_try_mount("endpoints_backtest", "Backtest")
_try_mount("endpoints_data", "Data")
_try_mount("endpoints_tick", "Tick Discovery")
_try_mount("endpoints_live", "Live + Ultron + Baret")
_try_mount("endpoints_p2_cron", "P2 Cron")
_try_mount("mode3_api", "Mode3 DRC")
_try_mount("mode3_eval_predictor", "Mode3 Eval Predictor")
_try_mount("mode3_regime_api", "Mode3 Regime")
_try_mount("mtf_analyze_endpoint", "MTF Analyze")
_try_mount("mode3_backtest_endpoint", "Mode3 Clean")
_try_mount("mode3_bbc_endpoint", "Mode3 BBC backtest")
_try_mount("causal_bbc_endpoint", "Causal BBC")
_try_mount("same_hour_bbc_endpoint", "Same-hour BBC")
_try_mount("causal_sniper_endpoint", "Causal sniper")
_try_mount("causal_parity_endpoint", "Causal parity")
_try_mount("causal_state_reject_endpoint", "Causal state reject")
_try_mount("causal_state_mtf_reject_endpoint", "Causal state MTF reject")
_try_mount("bbc_sweep_endpoint", "BBC Sweep")
_try_mount("bbc_limit_sim", "BBC Limit Sim")
_try_mount("honest_15m_endpoint", "Honest 15m")
_try_mount("filtered_reclaim_endpoint", "Filtered Reclaim")
_try_mount("filtered_switcher_endpoint", "Filtered Switcher")
_try_mount("v4_sweep_endpoint", "V4 Frozen Sweep")
_try_mount("orchestrator_endpoint", "Orchestrator")
_try_mount("bbc_live_endpoint", "BBC Live")

@app.get("/")
def root():
    return {"service": "BabaBot Backtesting API", "version": "2.0.0", "status": "running"}

@app.get("/health")
def health():
    db_ok = Path(DB_PATH).exists(); cc = 0
    if db_ok:
        try: conn = sqlite3.connect(DB_PATH); cc = conn.execute("SELECT COUNT(*) FROM klines").fetchone()[0]; conn.close()
        except: pass
    return {"status": "ok", "db_exists": db_ok, "total_candles": cc, "db_path": DB_PATH}

@app.get("/server-ip")
def server_ip():
    try:
        import requests
        return {"ok": True, "ip": requests.get("https://api.ipify.org?format=json", timeout=5).json().get("ip")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.on_event("startup")
def _auto_start():
    if os.environ.get("P2_CRON_ENABLED", "true").lower() == "true":
        try:
            from endpoints_p2_cron import start_p2_cron; start_p2_cron()
        except Exception as e: print(f"[INIT] P2 Cron: {e}")
    if os.environ.get("BARET_LIVE_ENABLED", "false").lower() == "true":
        try:
            from baret_live import start_baret_live
            start_baret_live(mode=os.environ.get("BARET_LIVE_MODE", "baret"), position_usd=float(os.environ.get("BARET_LIVE_POSITION", "10")))
        except Exception as e: print(f"[INIT] Baret Live: {e}")
