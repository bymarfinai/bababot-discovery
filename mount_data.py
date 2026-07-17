# Mode3 BBC + Data endpoints mount helper
# Import this AFTER mode3_bbc_endpoint import in app.py

_DATA_ENDPOINTS_AVAILABLE = False
try:
    from data_endpoints import router as data_ep_router
    _DATA_ENDPOINTS_AVAILABLE = True
    print("[INIT] Data endpoints (FR/OI) module loaded")
except Exception as _e:
    print(f"[WARN] data_endpoints not available: {_e}")

def mount_data_endpoints(app):
    if _DATA_ENDPOINTS_AVAILABLE:
        app.include_router(data_ep_router)
        print("[INIT] Data endpoints mounted at /data/funding_rate, /data/open_interest")
