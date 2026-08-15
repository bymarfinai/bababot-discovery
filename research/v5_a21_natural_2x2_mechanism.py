#!/usr/bin/env python3
"""V5-A2.1 — frozen natural-sign 2x2 derivatives mechanism test.

No tuning. Every resolved V4-B trade is classified using two predeclared axes:
1) Crowd 60m move relative to intended trade, split at natural zero.
2) Current taker aggression relative to intended trade, split at natural zero.

Hypothesis frozen before reading results:
CROWD_NOT_TOWARD + TAKER_AGAINST should be the strongest reaction state.

Definitions at the guarded pre-entry cutoff from V5-A2:
- crowd_signed_60m = side_sign * global_delta_60m
  >0 = crowd positioning moved toward intended trade; <=0 = did not.
- taker_bias_toward_trade = side_sign * ln(taker long/short volume ratio)
  >0 = taker aggression toward intended trade; <=0 = against/neutral.

Research only. No trade filter, no threshold sweep, no live integration.
"""
import json
from datetime import timedelta

import v5_a2_derivatives_forensic as base

DESIRED = "CROWD_NOT_TOWARD__TAKER_AGAINST"
STATES = [
    "CROWD_NOT_TOWARD__TAKER_AGAINST",
    "CROWD_NOT_TOWARD__TAKER_TOWARD",
    "CROWD_TOWARD__TAKER_AGAINST",
    "CROWD_TOWARD__TAKER_TOWARD",
]


def stat(rows):
    n = len(rows)
    w = sum(r["outcome"] == "BOUNCE" for r in rows)
    return {
        "n": n,
        "wins": w,
        "losses": n - w,
        "wr_pct": round(100.0 * w / n, 2) if n else None,
    }


def classify(r):
    gd = base.finite(r.get("global_delta_60m"))
    tb = base.finite(r.get("taker_bias_toward_trade"))
    if gd is None or tb is None:
        return None
    side_sign = 1.0 if r["side"] == "DEMAND" else -1.0
    crowd_signed = side_sign * gd
    crowd = "CROWD_TOWARD" if crowd_signed > 0.0 else "CROWD_NOT_TOWARD"
    taker = "TAKER_TOWARD" if tb > 0.0 else "TAKER_AGAINST"
    r["crowd_signed_60m"] = crowd_signed
    r["state"] = crowd + "__" + taker
    return r["state"]


def time_blocks(rows):
    if not rows:
        return {}
    ts = [base.dt(r["confirm_time"]) for r in rows]
    end = max(ts)
    half_cut = end - timedelta(days=60)
    out = {
        "first_60d": stat([r for r in rows if base.dt(r["confirm_time"]) < half_cut]),
        "last_60d": stat([r for r in rows if base.dt(r["confirm_time"]) >= half_cut]),
    }
    q = []
    for i in range(4):
        lo = end - timedelta(days=120 - 30*i)
        hi = end - timedelta(days=90 - 30*i)
        xs = [r for r in rows if lo <= base.dt(r["confirm_time"]) < hi] if i < 3 else [r for r in rows if lo <= base.dt(r["confirm_time"]) <= hi]
        z = stat(xs)
        z["start"] = lo.isoformat()
        z["end"] = hi.isoformat()
        q.append(z)
    out["quarters_30d"] = q
    out["anchor_end"] = end.isoformat()
    out["half_cut"] = half_cut.isoformat()
    return out


def main():
    events = []
    baseline = {}
    errors = {}
    for p in base.PAIRS:
        try:
            ev, st = base.fetch_v4_events(p)
            events.extend(ev)
            baseline[p] = st
        except Exception as e:
            errors[p] = f"V4 fetch: {e}"

    if not events:
        raise SystemExit("NO_V4_EVENTS")

    enriched = []
    for i, e in enumerate(events, 1):
        try:
            # Funding is intentionally irrelevant to this frozen 2x2 test.
            x = base.enrich(e, [])
            if x is not None and classify(x) is not None:
                enriched.append(x)
        except Exception as ex:
            errors[f"event_{i}_{e['symbol']}"] = str(ex)

    state_stats = {s: stat([r for r in enriched if r["state"] == s]) for s in STATES}
    by_state_pair = {
        s: {p: stat([r for r in enriched if r["state"] == s and r["symbol"] == p]) for p in base.PAIRS}
        for s in STATES
    }
    by_state_side = {
        s: {d: stat([r for r in enriched if r["state"] == s and r["side"] == d]) for d in ("DEMAND", "SUPPLY")}
        for s in STATES
    }
    by_state_time = {s: time_blocks([r for r in enriched if r["state"] == s]) for s in STATES}

    cand = [r for r in enriched if r["state"] == DESIRED]
    cs = stat(cand)
    pair_ok = sum(
        1 for p in base.PAIRS
        if by_state_pair[DESIRED][p]["n"] >= 3
        and (by_state_pair[DESIRED][p]["wr_pct"] or 0) > 50.0
    )
    side_ok = all(
        by_state_side[DESIRED][d]["n"] >= 5
        and (by_state_side[DESIRED][d]["wr_pct"] or 0) > 50.0
        for d in ("DEMAND", "SUPPLY")
    )
    th = by_state_time[DESIRED]
    time_ok = all(
        th[k]["n"] >= 5 and (th[k]["wr_pct"] or 0) > 50.0
        for k in ("first_60d", "last_60d")
    ) if th else False

    result = {
        "phase": "V5-A2.1",
        "status": "NATURAL_SIGN_2X2_MECHANISM_TEST",
        "frozen_definition": {
            "base_signal": "V4-B 1H structural zone + 5m reaction/absorption, confirm_bars=3, RR=1",
            "history_days": 120,
            "crowd_axis": "side_sign * global_delta_60m; >0 toward trade, <=0 not toward",
            "taker_axis": "taker_bias_toward_trade = side_sign*ln(taker_lsr); >0 toward trade, <=0 against/neutral",
            "cutoffs": "natural zero only",
            "desired_state_predeclared": DESIRED,
            "threshold_sweep": False,
            "trade_filtering": False,
            "funding_used": False,
            "causality_guard": "same V5-A2 guarded metrics cutoff <= confirmation 5m candle OPEN; entry decision after candle close",
        },
        "predeclared_candidate_gate": {
            "overall_wr_pct": ">=70",
            "candidate_n": ">=20",
            "pair_distribution": ">=3 of 4 pairs each n>=3 and WR>50",
            "both_sides": "each n>=5 and WR>50",
            "both_60d_halves": "each n>=5 and WR>50",
        },
        "baseline_reported_by_endpoint": baseline,
        "events_before_join": stat(events),
        "events_classified": stat(enriched),
        "unclassified_n": len(events) - len(enriched),
        "states": state_stats,
        "by_state_pair": by_state_pair,
        "by_state_side": by_state_side,
        "by_state_time": by_state_time,
        "desired_state_assessment": {
            "state": DESIRED,
            "stats": cs,
            "pairs_passing_distribution_check": pair_ok,
            "side_check": side_ok,
            "time_check": time_ok,
            "earns_v5_a3": bool(
                cs["n"] >= 20
                and (cs["wr_pct"] or 0) >= 70.0
                and pair_ok >= 3
                and side_ok
                and time_ok
            ),
        },
        "errors": errors,
        "notes": {
            "interpretation": "This is a frozen mechanism check, not an optimization. No alternate sign convention or threshold may be selected after seeing results.",
            "next": "Only if the predeclared desired state passes does it earn a separate V5-A3 frozen-rule validation.",
        },
    }
    print("V5_A21_RESULT", json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
