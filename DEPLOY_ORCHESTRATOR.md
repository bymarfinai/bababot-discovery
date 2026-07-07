# MANUAL PATCH INSTRUCTIONS FOR app.py
# 
# To activate the 3-state trading orchestrator + BULL/BEAR tools,
# add these 4 lines to app.py (near line 68, after the MTF import):
#
# ══════════════════════════════════════════════════════════════
# ── Orchestrator v1.0 (added 7 Jul 2026) ────────────────────
# try:
#     from orchestrator_endpoint import router as orch_router
#     app.include_router(orch_router)
#     print("[INIT] Orchestrator v1.0 endpoints mounted (/mtf/bull_backtest, /mtf/bear_backtest, /mtf/orchestrator_backtest)")
# except Exception as _e:
#     print(f"[WARN] orchestrator_endpoint not available: {_e}")
# ══════════════════════════════════════════════════════════════
#
# After adding + git commit + push:
# - Railway auto-redeploys
# - Test endpoints:
#   GET /mtf/bull_backtest?symbol=BTCUSDT&days=30
#   GET /mtf/bear_backtest?symbol=BTCUSDT&days=30
#   GET /mtf/orchestrator_backtest?symbol=BTCUSDT&days=30

DEPLOYMENT_STATUS = "manual_patch_required"
