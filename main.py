"""
BabaBot Main — Thin wrapper that applies live_fixes before starting.
Procfile points here: uvicorn main:app

This avoids modifying the 113KB app.py file directly.
"""

# Step 1: Apply all 4 critical live trading fixes (monkey-patch)
try:
    import live_fixes.integrate  # patches baret_live automatically
    print("[MAIN] Live fixes applied successfully")
except Exception as e:
    print(f"[MAIN] WARNING: live_fixes not loaded: {e}")

# Step 2: Import the main FastAPI app
from app import app

# Step 3: Mount the new endpoints (exchange-positions, close-position, close-all)
try:
    from live_fixes.endpoints import router as live_fixes_router
    app.include_router(live_fixes_router)
    print("[MAIN] Live fixes endpoints mounted (exchange-positions, close-position, close-all)")
except Exception as e:
    print(f"[MAIN] WARNING: live_fixes endpoints not mounted: {e}")
