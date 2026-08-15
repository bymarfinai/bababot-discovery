"""V5-A1 Derivatives Data Feasibility & Causality Audit.

No strategy logic. This endpoint only probes whether BabaBot can obtain causal
historical derivatives context from official Binance USD-M sources.

Datasets:
- funding rate history
- open-interest history
- global/top-trader long-short ratios
- official Binance public-data archives (funding/metrics/liquidation snapshot)
- liquidation stream documentation status is reported as live-capture-only

GET /v5/derivatives-feasibility
"""

from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Query

router = APIRouter(prefix="/v5", tags=["v5_derivatives"])

FAPI = "https://fapi.binance.com"
DATA = "https://data.binance.vision/data/futures/um"
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _iso_ms(v):
    try:
        return datetime.fromtimestamp(int(v) / 1000, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _get(path, params=None, timeout=12):
    url = FAPI + path
    try:
        r = requests.get(url, params=params or {}, timeout=timeout)
        payload = None
        try:
            payload = r.json()
        except Exception:
            payload = r.text[:500]
        return {"ok": r.status_code == 200, "status": r.status_code, "url_path": path, "payload": payload}
    except Exception as e:
        return {"ok": False, "status": None, "url_path": path, "error": str(e)}


def _head(url, timeout=10):
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        return {
            "exists": r.status_code == 200,
            "status": r.status_code,
            "content_length": r.headers.get("content-length"),
            "content_type": r.headers.get("content-type"),
        }
    except Exception as e:
        return {"exists": False, "status": None, "error": str(e)}


def _summarize_list(resp, ts_field="timestamp"):
    p = resp.get("payload")
    if not isinstance(p, list):
        return {"ok": resp.get("ok"), "status": resp.get("status"), "n": None, "error_payload": p}
    out = {"ok": resp.get("ok"), "status": resp.get("status"), "n": len(p)}
    if p:
        out["first_time"] = _iso_ms(p[0].get(ts_field)) if isinstance(p[0], dict) else None
        out["last_time"] = _iso_ms(p[-1].get(ts_field)) if isinstance(p[-1], dict) else None
        out["sample"] = p[-1] if isinstance(p[-1], dict) else p[-1]
    return out


def _probe_hist(path, symbol, period, start, end, ts_field="timestamp"):
    params = {"symbol": symbol, "period": period, "limit": 10, "startTime": _ms(start), "endTime": _ms(end)}
    return _summarize_list(_get(path, params), ts_field)


def _probe_funding(symbol, start, end):
    params = {"symbol": symbol, "limit": 100, "startTime": _ms(start), "endTime": _ms(end)}
    return _summarize_list(_get("/fapi/v1/fundingRate", params), "fundingTime")


@router.get("/derivatives-feasibility")
def derivatives_feasibility(
    symbols: str = Query("BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT"),
    period: str = Query("5m"),
):
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    syms = syms[:8]
    now = datetime.now(timezone.utc)

    # Probes intentionally frozen before reading responses.
    windows = {
        "recent": (now - timedelta(days=2), now),
        "45d_old": (now - timedelta(days=47), now - timedelta(days=45)),
        "120d_old": (now - timedelta(days=122), now - timedelta(days=120)),
        "971d_old": (now - timedelta(days=973), now - timedelta(days=971)),
    }

    result = {}
    for symbol in syms:
        current_oi_raw = _get("/fapi/v1/openInterest", {"symbol": symbol})
        current_oi = {
            "ok": current_oi_raw.get("ok"),
            "status": current_oi_raw.get("status"),
            "payload": current_oi_raw.get("payload") if current_oi_raw.get("ok") else current_oi_raw.get("payload"),
        }

        probes = {
            "funding": {},
            "open_interest_hist": {},
            "global_long_short": {},
            "top_trader_account_ratio": {},
            "top_trader_position_ratio": {},
        }
        for name, (a, b) in windows.items():
            probes["funding"][name] = _probe_funding(symbol, a, b)
            probes["open_interest_hist"][name] = _probe_hist("/futures/data/openInterestHist", symbol, period, a, b)
            probes["global_long_short"][name] = _probe_hist("/futures/data/globalLongShortAccountRatio", symbol, period, a, b)
            probes["top_trader_account_ratio"][name] = _probe_hist("/futures/data/topLongShortAccountRatio", symbol, period, a, b)
            probes["top_trader_position_ratio"][name] = _probe_hist("/futures/data/topLongShortPositionRatio", symbol, period, a, b)

        old_day = (now - timedelta(days=580)).date().isoformat()
        recent_day = (now - timedelta(days=5)).date().isoformat()
        old_month = (now - timedelta(days=971)).strftime("%Y-%m")
        archive = {
            "funding_month_971d": {
                "path": f"monthly/fundingRate/{symbol}/{symbol}-fundingRate-{old_month}.zip",
            },
            "metrics_old_day": {
                "path": f"daily/metrics/{symbol}/{symbol}-metrics-{old_day}.zip",
            },
            "metrics_recent_day": {
                "path": f"daily/metrics/{symbol}/{symbol}-metrics-{recent_day}.zip",
            },
            "liquidation_old_day": {
                "path": f"daily/liquidationSnapshot/{symbol}/{symbol}-liquidationSnapshot-{old_day}.zip",
            },
            "liquidation_recent_day": {
                "path": f"daily/liquidationSnapshot/{symbol}/{symbol}-liquidationSnapshot-{recent_day}.zip",
            },
        }
        for meta in archive.values():
            meta.update(_head(f"{DATA}/{meta['path']}"))

        result[symbol] = {
            "current_open_interest": current_oi,
            "rest_history_probes": probes,
            "official_public_archive_probes": archive,
        }

    # Causality rules are explicit so later V5 work cannot silently use future information.
    causality = {
        "funding_rate": "Use only funding rows with fundingTime <= decision timestamp. Never use a realized future fundingRate before its fundingTime.",
        "open_interest": "Use only statistics rows whose timestamp <= decision timestamp; compute OI delta only from already completed observations.",
        "long_short_ratios": "Use only ratio rows whose timestamp <= decision timestamp. No back-filling a period value into an earlier candle.",
        "liquidations": "Use event/order timestamps only after the liquidation event occurred. Official current USD-M docs expose market liquidation as WebSocket streams, so historical backtest requires a genuine archive; otherwise capture prospectively.",
        "alignment": "For a signal closing at t, derivatives features must come from latest published observation <= t. Never nearest-neighbor forward align.",
    }

    return {
        "phase": "V5-A1",
        "status": "DATA_FEASIBILITY_ONLY",
        "as_of": now.isoformat(),
        "symbols": syms,
        "period": period,
        "probe_windows": {k: [a.isoformat(), b.isoformat()] for k, (a, b) in windows.items()},
        "causality_lock": causality,
        "data": result,
        "notes": {
            "no_strategy_test": True,
            "no_threshold_tuning": True,
            "goal": "Determine which derivatives fields can support causal 120d/971d research before V5-A2 winner-vs-loser forensic.",
        },
    }
