# Mode3 — Clean Rebuild v0.21

BabaBot switcher + 3 tools (SIDEWAYS, BULL, BEAR) berdasarkan `BabaBot_Switcher_Spec_v0_21`.

## Files

- `config.py` — `Mode3Config` dataclass. Zero magic numbers.
- `indicators.py` — EMA20 + VA (percentile P85/P15, volume-weighted POC)
- `switcher.py` — State machine + 3 tools terintegrasi
- `../mode3_backtest_endpoint.py` — FastAPI endpoint `/mode3/backtest`

## Wiring ke app.py

Tambahkan 2 blok berikut ke `app.py`:

### 1. Import (setelah blok MTF import, sekitar baris 60)

```python
# Mode3 Clean Rebuild (spec v0.21)
try:
    from mode3_backtest_endpoint import router as mode3_clean_router
    _MODE3_CLEAN_AVAILABLE = True
    print("[INIT] Mode3 Clean (v0.21) module loaded")
except Exception as _e:
    print(f"[WARN] mode3_backtest_endpoint not available: {_e}")
    _MODE3_CLEAN_AVAILABLE = False
```

### 2. Mount (setelah `app.include_router(mtf_router)`, sekitar baris 95)

```python
# Mount Mode3 Clean router (spec v0.21)
if _MODE3_CLEAN_AVAILABLE:
    app.include_router(mode3_clean_router)
    print("[INIT] Mode3 Clean mounted at /mode3/backtest, /mode3/health")
```

## Kalau DB path beda

Edit `mode3_backtest_endpoint.py` line ~19, ganti `"klines.db"` ke path yg dipakai di Railway (misal env var `DB_PATH`).

## Test after deploy

```bash
curl "https://web-production-b6a05.up.railway.app/mode3/health"
# expected: {"status": "ok", "module": "mode3", "version": "0.21"}

curl "https://web-production-b6a05.up.railway.app/mode3/backtest?symbol=BTCUSDT&timeframe=1h&days=30"
# expected: JSON with trades, summary, per_tool stats
```

## Backtest 30 hari sample response

```json
{
  "summary": {
    "total_trades": <int>,
    "win_rate_pct": <float>,
    "total_pnl_usd": <float>,
    "capital_start": 100.0,
    "capital_end": <float>
  },
  "per_tool": {
    "SIDEWAYS": {"count": N, "wr_pct": X, "pnl_usd": Y},
    "BULL": {...},
    "BEAR": {...}
  },
  "trades": [...]
}
```

## Rule references (spec section numbers)

Setiap function di code punya docstring dengan spec section reference. Trace bug back to spec dengan mudah.
