Replace the BBC mount + security section in app.py with this (search for the unique string below):

OLD:
```
if _MODE3_BBC_AVAILABLE:
    app.include_router(mode3_bbc_router)
    print("[INIT] Mode3 BBC mounted at /mode3_bbc/backtest, /mode3_bbc/health")
      
security = HTTPBearer(auto_error=False)
```

NEW:
```
if _MODE3_BBC_AVAILABLE:
    app.include_router(mode3_bbc_router)
    print("[INIT] Mode3 BBC mounted at /mode3_bbc/backtest, /mode3_bbc/health")

# ── Data endpoints (FR/OI) ─────────────────────────────────
try:
    from data_endpoints import router as data_ep_router
    app.include_router(data_ep_router)
    print("[INIT] Data endpoints mounted at /data/funding_rate, /data/open_interest")
except Exception as _e:
    print(f"[WARN] data_endpoints not available: {_e}")
# ────────────────────────────────────────────────────────────
      
security = HTTPBearer(auto_error=False)
```
