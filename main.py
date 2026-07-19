"""
BabaBot Main — Thin wrapper that applies live_fixes before starting.
Procfile points here: uvicorn main:app
"""

# Step 1: Apply all 4 critical live trading fixes (monkey-patch)
_live_fixes_status = "not_loaded"
_live_fixes_error = None

try:
    import live_fixes.integrate
    _live_fixes_status = "loaded"
    print("[MAIN] ✅ Live fixes applied successfully")
except Exception as e:
    import traceback
    _live_fixes_error = traceback.format_exc()
    _live_fixes_status = f"error: {e}"
    print(f"[MAIN] ❌ live_fixes FAILED: {e}")
    print(_live_fixes_error)

# Step 2: Import the main FastAPI app
from app import app

# Step 3: Mount the new endpoints
_endpoints_status = "not_loaded"
try:
    from live_fixes.endpoints import router as live_fixes_router
    app.include_router(live_fixes_router)
    _endpoints_status = "mounted"
    print("[MAIN] ✅ Live fixes endpoints mounted")
except Exception as e:
    import traceback
    _endpoints_status = f"error: {e}"
    print(f"[MAIN] ❌ Endpoints FAILED: {e}")
    print(traceback.format_exc())

# Step 4: Debug endpoint
@app.get("/live-fixes/status")
def live_fixes_debug():
    return {
        "fixes": _live_fixes_status,
        "endpoints": _endpoints_status,
        "error": _live_fixes_error,
    }
