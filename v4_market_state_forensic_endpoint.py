"""V4-B6 — market-state forensic for the recent 86% Fibonacci window.

Question
--------
Why did the already-frozen V4-B + 61.8%-70.5% Fibonacci subset jump from
~46% historically to ~87% in the most recent 120 days?

This endpoint is descriptive only. It DOES NOT add a trading filter.
It reuses the frozen V4-B/B2 event construction and measures causal market
state observable at each 5m confirmation close:
- own-pair 4h / 24h / 7d directional return relative to trade side;
- 1h ATR regime versus the trailing 7-day baseline;
- 24h / 7d trend efficiency;
- four-pair 24h/7d directional synchronization and breadth;
- market-wide volatility / ATR expansion.

A feature is only interesting if historical observations with a recent-like
state also show better WR. No threshold sweep is performed here.
"""

import bisect
import math
import statistics
from datetime import datetime, timezone, timedelta

import numpy as np
from fastapi import APIRouter, Query

from v4_structural_zone_endpoint import _load, _atr
from v4_context_fib_forensic_endpoint import context_fib_forensic

router = APIRouter(prefix="/v4/market-state-forensic", tags=["v4_market_state_forensic"])

MARKET_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
FROZEN_BAND = "61.8-70.5"
HOUR_MS = 3_600_000
FIVE_MIN_MS = 300_000


def _stat(rows):
    n = len(rows)
    w = sum(int(r.get("win", 0)) for r in rows)
    return {"n": n, "wins": w, "losses": n - w, "wr_pct": round(100.0 * w / n, 2) if n else None}


def _median(xs):
    vals = []
    for x in xs:
        try:
            x = float(x)
            if math.isfinite(x):
                vals.append(x)
        except Exception:
            pass
    return round(float(statistics.median(vals)), 6) if vals else None


def _q(vals, p):
    vals = sorted(float(x) for x in vals if x is not None and math.isfinite(float(x)))
    if not vals:
        return None
    pos = (len(vals) - 1) * p
    lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)


def _sign(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def _ret(C, i, bars):
    if i < bars or C[i - bars] == 0:
        return None
    return float(C[i] / C[i - bars] - 1.0)


def _trend_eff(C, i, bars):
    if i < bars:
        return None
    net = abs(float(C[i] - C[i - bars]))
    path = 0.0
    for k in range(i - bars + 1, i + 1):
        path += abs(float(C[k] - C[k - 1]))
    return float(net / path) if path > 0 else 0.0


def _std_returns(C, a, b):
    # returns for k in [a,b], each using k-1; caller guarantees a>=1
    if b < a:
        return None
    vals = []
    for k in range(a, b + 1):
        p = float(C[k - 1]); c = float(C[k])
        if p > 0:
            vals.append(c / p - 1.0)
    if len(vals) < 4:
        return None
    return float(np.std(np.asarray(vals, dtype=float), ddof=0))


def _series(symbol, days):
    rows = _load(symbol, "1h", days)
    T = [int(r[0]) for r in rows]
    H = np.asarray([r[2] for r in rows], dtype=float)
    L = np.asarray([r[3] for r in rows], dtype=float)
    C = np.asarray([r[4] for r in rows], dtype=float)
    ATR = _atr(H, L, C, 14)
    atr_pct = np.asarray([(100.0 * ATR[i] / C[i]) if C[i] > 0 else 0.0 for i in range(len(C))], dtype=float)
    return {"T": T, "C": C, "ATR_PCT": atr_pct}


def _latest_completed_index(T, event_close_ms):
    # 1h bar with open_time + 1h <= event close
    return bisect.bisect_right(T, int(event_close_ms) - HOUR_MS) - 1


def _pair_state(series, i):
    C = series["C"]; atrp = series["ATR_PCT"]
    if i < 192:
        return None
    r4 = _ret(C, i, 4)
    r24 = _ret(C, i, 24)
    r168 = _ret(C, i, 168)
    eff24 = _trend_eff(C, i, 24)
    eff168 = _trend_eff(C, i, 168)

    prior_atr = [float(x) for x in atrp[max(0, i - 168):i] if float(x) > 0]
    atr_base = statistics.median(prior_atr) if prior_atr else None
    atr_ratio = float(atrp[i] / atr_base) if atr_base and atr_base > 0 else None

    rv24 = _std_returns(C, i - 23, i)
    rv_prior = _std_returns(C, i - 191, i - 24)
    rv_ratio = float(rv24 / rv_prior) if rv24 is not None and rv_prior and rv_prior > 0 else None

    return {
        "ret4h": r4,
        "ret24h": r24,
        "ret7d": r168,
        "atr1h_pct": float(atrp[i]),
        "atr_ratio_7d": atr_ratio,
        "rv24_vs_prior7d": rv_ratio,
        "trend_eff24h": eff24,
        "trend_eff7d": eff168,
    }


def _market_state(all_series, event_close_ms, trade_dir):
    states = {}
    for p, ser in all_series.items():
        i = _latest_completed_index(ser["T"], event_close_ms)
        st = _pair_state(ser, i) if i >= 0 else None
        if st:
            states[p] = st
    if len(states) < 3:
        return {}

    r24 = [st["ret24h"] for st in states.values() if st.get("ret24h") is not None]
    r7 = [st["ret7d"] for st in states.values() if st.get("ret7d") is not None]
    ar = [st["atr_ratio_7d"] for st in states.values() if st.get("atr_ratio_7d") is not None]
    rv = [st["rv24_vs_prior7d"] for st in states.values() if st.get("rv24_vs_prior7d") is not None]
    atrp = [st["atr1h_pct"] for st in states.values() if st.get("atr1h_pct") is not None]

    signs24 = [_sign(x) for x in r24 if _sign(x) != 0]
    signs7 = [_sign(x) for x in r7 if _sign(x) != 0]
    sync24 = abs(sum(signs24)) / len(signs24) if signs24 else None
    sync7 = abs(sum(signs7)) / len(signs7) if signs7 else None
    align24 = sum(1 for x in r24 if _sign(x) == trade_dir) / len(r24) if r24 else None
    align7 = sum(1 for x in r7 if _sign(x) == trade_dir) / len(r7) if r7 else None

    btc = states.get("BTCUSDT", {})
    return {
        "market_sync24h": sync24,
        "market_sync7d": sync7,
        "market_alignment24h": align24,
        "market_alignment7d": align7,
        "market_avg_abs_ret24h_pct": 100.0 * statistics.mean(abs(x) for x in r24) if r24 else None,
        "market_avg_abs_ret7d_pct": 100.0 * statistics.mean(abs(x) for x in r7) if r7 else None,
        "market_avg_atr1h_pct": statistics.mean(atrp) if atrp else None,
        "market_avg_atr_ratio_7d": statistics.mean(ar) if ar else None,
        "market_avg_rv24_ratio": statistics.mean(rv) if rv else None,
        "market_expanding_breadth": sum(1 for x in ar if x > 1.0) / len(ar) if ar else None,
        "market_rv_expanding_breadth": sum(1 for x in rv if x > 1.0) / len(rv) if rv else None,
        "btc_signed_ret24h_pct": 100.0 * float(btc.get("ret24h", 0.0)) * trade_dir if btc else None,
        "btc_signed_ret7d_pct": 100.0 * float(btc.get("ret7d", 0.0)) * trade_dir if btc else None,
    }


def _feature_report(recent, hist, features):
    compare = {}
    historical_match = {}
    for f in features:
        rv = [r.get(f) for r in recent if r.get(f) is not None]
        hv = [r.get(f) for r in hist if r.get(f) is not None]
        rm = _median(rv); hm = _median(hv)
        q1 = _q(rv, .25); q3 = _q(rv, .75)
        matched = []
        if q1 is not None and q3 is not None:
            for r in hist:
                try:
                    v = float(r.get(f))
                    if q1 <= v <= q3:
                        matched.append(r)
                except Exception:
                    pass
        compare[f] = {
            "recent_median": rm,
            "historical_median": hm,
            "recent_q25": round(q1, 6) if q1 is not None else None,
            "recent_q75": round(q3, 6) if q3 is not None else None,
            "median_shift_pct": round(100.0 * (rm - hm) / abs(hm), 2) if rm is not None and hm not in (None, 0) else None,
        }
        historical_match[f] = _stat(matched)
    return compare, historical_match


def _state_stats(rows):
    def subset(fn):
        return _stat([r for r in rows if fn(r)])
    return {
        "own_24h_aligned": subset(lambda r: (r.get("own_signed_ret24h_pct") or 0) > 0),
        "own_7d_aligned": subset(lambda r: (r.get("own_signed_ret7d_pct") or 0) > 0),
        "own_24h_and_7d_aligned": subset(lambda r: (r.get("own_signed_ret24h_pct") or 0) > 0 and (r.get("own_signed_ret7d_pct") or 0) > 0),
        "market_3of4_or_more_aligned_24h": subset(lambda r: (r.get("market_alignment24h") or 0) >= 0.75),
        "market_3of4_or_more_aligned_7d": subset(lambda r: (r.get("market_alignment7d") or 0) >= 0.75),
        "own_atr_expanding": subset(lambda r: (r.get("own_atr_ratio_7d") or 0) > 1.0),
        "market_atr_majority_expanding": subset(lambda r: (r.get("market_expanding_breadth") or 0) >= 0.75),
        "market_rv_majority_expanding": subset(lambda r: (r.get("market_rv_expanding_breadth") or 0) >= 0.75),
        "direction_and_market_alignment_24h": subset(lambda r: (r.get("own_signed_ret24h_pct") or 0) > 0 and (r.get("market_alignment24h") or 0) >= 0.75),
        "direction_and_atr_expansion": subset(lambda r: (r.get("own_signed_ret24h_pct") or 0) > 0 and (r.get("own_atr_ratio_7d") or 0) > 1.0),
    }


@router.get("")
def market_state_forensic(
    days: int = Query(971, ge=240, le=1500),
    recent_days: int = Query(120, ge=30, le=365),
    rr: float = Query(1.0, ge=1.0, le=3.0),
    confirm_bars: int = Query(3, ge=1, le=12),
    sample_limit: int = Query(200, ge=0, le=500),
):
    # Load market context once. 1h bars are sufficient for all frozen state metrics.
    all_series = {p: _series(p, days) for p in MARKET_PAIRS}

    selected = []
    errors = {}
    for p in MARKET_PAIRS:
        try:
            d = context_fib_forensic(symbols=p, days=days, rr=rr, confirm_bars=confirm_bars, sample_limit=500)
            if d.get("errors"):
                errors[p] = d.get("errors")
            if int((d.get("overall") or {}).get("n", 0) or 0) > len(d.get("sample", [])):
                errors[p] = f"sample truncated: overall={d.get('overall')} sample={len(d.get('sample', []))}"
                continue
            for x in d.get("sample", []):
                if x.get("fib_band") != FROZEN_BAND or x.get("outcome") not in {"BOUNCE", "BREAK"}:
                    continue
                z = dict(x)
                z["pair"] = p
                z["win"] = 1 if z["outcome"] == "BOUNCE" else 0
                dt = datetime.fromisoformat(z["confirm_time"])
                event_close_ms = int(dt.timestamp() * 1000) + FIVE_MIN_MS
                own_i = _latest_completed_index(all_series[p]["T"], event_close_ms)
                own = _pair_state(all_series[p], own_i) if own_i >= 0 else None
                if not own:
                    continue
                trade_dir = 1 if z.get("side") == "DEMAND" else -1
                z.update({
                    "own_signed_ret4h_pct": 100.0 * own["ret4h"] * trade_dir if own.get("ret4h") is not None else None,
                    "own_signed_ret24h_pct": 100.0 * own["ret24h"] * trade_dir if own.get("ret24h") is not None else None,
                    "own_signed_ret7d_pct": 100.0 * own["ret7d"] * trade_dir if own.get("ret7d") is not None else None,
                    "own_atr1h_pct": own.get("atr1h_pct"),
                    "own_atr_ratio_7d": own.get("atr_ratio_7d"),
                    "own_rv24_vs_prior7d": own.get("rv24_vs_prior7d"),
                    "own_trend_eff24h": own.get("trend_eff24h"),
                    "own_trend_eff7d": own.get("trend_eff7d"),
                })
                z.update(_market_state(all_series, event_close_ms, trade_dir))
                z["_dt"] = dt
                selected.append(z)
        except Exception as e:
            errors[p] = str(e)

    selected.sort(key=lambda r: r["_dt"])
    cutoff = datetime.now(timezone.utc) - timedelta(days=recent_days)
    recent = [r for r in selected if r["_dt"] >= cutoff]
    hist = [r for r in selected if r["_dt"] < cutoff]

    features = [
        "own_signed_ret4h_pct", "own_signed_ret24h_pct", "own_signed_ret7d_pct",
        "own_atr1h_pct", "own_atr_ratio_7d", "own_rv24_vs_prior7d",
        "own_trend_eff24h", "own_trend_eff7d",
        "market_sync24h", "market_sync7d", "market_alignment24h", "market_alignment7d",
        "market_avg_abs_ret24h_pct", "market_avg_abs_ret7d_pct",
        "market_avg_atr1h_pct", "market_avg_atr_ratio_7d", "market_avg_rv24_ratio",
        "market_expanding_breadth", "market_rv_expanding_breadth",
        "btc_signed_ret24h_pct", "btc_signed_ret7d_pct",
    ]
    compare, match = _feature_report(recent, hist, features)

    # Historical similarity to the full recent multivariate state: count how many
    # recent IQRs each old trade falls inside. This is descriptive, not a filter search.
    bounds = {}
    for f in features:
        rv = [r.get(f) for r in recent if r.get(f) is not None]
        if rv:
            bounds[f] = (_q(rv, .25), _q(rv, .75))
    sim_rows = []
    for r in hist:
        score = 0; total = 0
        for f, (a, b) in bounds.items():
            try:
                v = float(r[f]); total += 1
                if a <= v <= b:
                    score += 1
            except Exception:
                pass
        q = dict(r); q["_similarity"] = score; q["_similarity_total"] = total
        sim_rows.append(q)
    thresholds = [5, 8, 10, 12, 14]
    similarity = {str(k): _stat([r for r in sim_rows if r["_similarity"] >= k]) for k in thresholds}

    def clean(r):
        out = {k: v for k, v in r.items() if k != "_dt"}
        for k, v in list(out.items()):
            if isinstance(v, float) and math.isfinite(v):
                out[k] = round(v, 6)
        return out

    return {
        "phase": "V4-B6",
        "status": "RECENT_MARKET_STATE_FORENSIC",
        "question": "Which causal market state explains the recent 86.67% WR of frozen V4-B + Fib 61.8-70.5?",
        "definition": {
            "strategy_filter_added": False,
            "frozen_band": "61.8%-70.5%",
            "baseline_signal": "V4-B 1H structural zone + first 5m absorption/reclaim confirmation",
            "rr": rr,
            "confirm_bars": confirm_bars,
            "recent_days": recent_days,
            "market_pairs": MARKET_PAIRS,
            "market_state_data": "causal completed 1h bars only; 4h/24h/7d metrics derived from them",
        },
        "overall": _stat(selected),
        "recent": _stat(recent),
        "historical": _stat(hist),
        "recent_vs_historical_features": compare,
        "historical_wr_when_matching_recent_iqr_one_feature": match,
        "predeclared_state_buckets": {
            "recent": _state_stats(recent),
            "historical": _state_stats(hist),
        },
        "historical_multivariate_recent_similarity": similarity,
        "errors": errors,
        "recent_sample": [clean(r) for r in recent[-sample_limit:]] if sample_limit else [],
    }
