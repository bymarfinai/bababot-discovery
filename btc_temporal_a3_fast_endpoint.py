"""Optimized runner for BTC Temporal A3 dynamic-direction research.

Same methodology as btc_temporal_a3_direction_endpoint, but kNN normalization is
computed once per walk-forward prediction instead of once per analogue pair.
"""

import math
from datetime import timezone, timedelta

from fastapi import APIRouter, Query

from btc_temporal_a2_sequence_endpoint import _load, _local_dt, HORIZONS
from btc_temporal_a3_direction_endpoint import (
    _build_occurrence, _predict_state, _evaluate, FEATURE_SETS, _mean, _r,
)

router = APIRouter(prefix="/research/btc-temporal-a3-fast", tags=["btc_temporal_a3_fast"])


def _predict_knn_fast(train, cur, horizon, names, k):
    stats = {}
    for name in names:
        vals = [x["features"][name] for x in train]
        mu = _mean(vals) or 0.0
        var = _mean([(v - mu) ** 2 for v in vals]) or 0.0
        stats[name] = (mu, math.sqrt(var))

    ranked = []
    for old in train:
        lab = old["labels"][horizon]
        if lab == 0:
            continue
        s = 0.0
        used = 0
        for name in names:
            mu, sd = stats[name]
            if sd < 1e-9:
                continue
            d = (cur["features"][name] - old["features"][name]) / sd
            s += d * d
            used += 1
        dist = math.sqrt(s / used) if used else 0.0
        ranked.append((dist, lab))
    ranked.sort(key=lambda z: z[0])
    nbrs = ranked[:min(k, len(ranked))]
    if not nbrs:
        return -1, 0.0, 0
    score = den = 0.0
    for dist, lab in nbrs:
        w = 1.0 / (0.25 + dist)
        score += w * lab
        den += w
    pred = 1 if score > 0 else -1 if score < 0 else -1
    return pred, abs(score) / den if den else 0.0, len(nbrs)


@router.get("")
def run(days: int = Query(971, ge=240, le=1500), blocks: int = Query(8, ge=4, le=12), warmup: int = Query(20, ge=12, le=60)):
    rows, start_ms, end_ms = _load(days)
    if not rows:
        return {"error": "No BTCUSDT 15m data"}
    tz = timezone(timedelta(hours=7))
    span = max(1, end_ms - start_ms)
    occs = []
    for idx, row in enumerate(rows):
        ts = int(row[0])
        dt = _local_dt(ts, tz)
        if dt.weekday() != 1 or dt.hour != 6 or dt.minute != 0:
            continue
        block = min(blocks - 1, max(0, int((ts - start_ms) * blocks / span)))
        occ = _build_occurrence(rows, idx, tz, block)
        if occ is not None:
            occs.append(occ)

    engines = []
    eval_occ = occs[warmup:]
    for horizon in HORIZONS:
        # Same-entry controls.
        controls = {
            "BASE_ALWAYS_SELL": lambda e: -1,
            "OBS_MOMENTUM": lambda e: 1 if e["features"]["obs_ret"] >= 0 else -1,
            "OBS_REVERSAL": lambda e: -1 if e["features"]["obs_ret"] >= 0 else 1,
        }
        for name, fn in controls.items():
            preds = [{"ts":e["ts"], "pred":fn(e), "confidence":0.0, "support":0} for e in eval_occ]
            engines.append({"engine":name, "horizon_min":horizon, **_evaluate(preds, occs, horizon, blocks)})

        for support in (3, 5, 8):
            preds = []
            for i in range(warmup, len(occs)):
                train, cur = occs[:i], occs[i]
                pred, conf, n, level = _predict_state(train, cur, horizon, support)
                preds.append({"ts":cur["ts"], "pred":pred, "confidence":conf, "support":n, "state_level":level})
            engines.append({"engine":f"WF_STATE_MIN{support}", "horizon_min":horizon, **_evaluate(preds, occs, horizon, blocks)})

        for fs_name, names in FEATURE_SETS.items():
            for k in (5, 9, 15, 21):
                preds = []
                for i in range(warmup, len(occs)):
                    train, cur = occs[:i], occs[i]
                    pred, conf, n = _predict_knn_fast(train, cur, horizon, names, k)
                    preds.append({"ts":cur["ts"], "pred":pred, "confidence":conf, "support":n})
                engines.append({"engine":f"WF_KNN_{fs_name}_K{k}", "horizon_min":horizon, **_evaluate(preds, occs, horizon, blocks)})

    by_dir = sorted(engines, key=lambda x: (x["wr_pct"] or -1, x["n"], x["positive_blocks_gt50"]), reverse=True)
    by05 = sorted(engines, key=lambda x: (x["first_touch_symmetric_pct"]["0.5"]["wr_pct"] or -1, x["first_touch_symmetric_pct"]["0.5"]["decisive_n"], x["wr_pct"] or -1), reverse=True)
    by08 = sorted(engines, key=lambda x: (x["first_touch_symmetric_pct"]["0.8"]["wr_pct"] or -1, x["first_touch_symmetric_pct"]["0.8"]["decisive_n"], x["wr_pct"] or -1), reverse=True)

    expected = max(1, int((end_ms-start_ms)/(15*60*1000)))
    return {
        "status":"BTC_TEMPORAL_A3_FAST_WALKFORWARD",
        "data":{
            "days":days,"rows_15m":len(rows),"expected_rows_15m":expected,"coverage_pct":_r(100*len(rows)/expected,2),
            "tuesday_occurrences":len(occs),"warmup_occurrences":warmup,"walkforward_predictions":max(0,len(occs)-warmup),
            "historical_eval_coverage_pct":_r(100*max(0,len(occs)-warmup)/len(occs),2) if occs else None,
            "post_warmup_trade_coverage_pct":100.0,"decision_time_wib":"06:30","entry":"06:30 open"
        },
        "engine_count":len(engines),
        "baseline":[x for x in engines if x["engine"]=="BASE_ALWAYS_SELL"],
        "target70_directional":[x for x in by_dir if (x["wr_pct"] or 0)>=70],
        "target70_ft05":[x for x in by05 if (x["first_touch_symmetric_pct"]["0.5"]["wr_pct"] or 0)>=70 and x["first_touch_symmetric_pct"]["0.5"]["decisive_n"]>=30],
        "target70_ft08":[x for x in by08 if (x["first_touch_symmetric_pct"]["0.8"]["wr_pct"] or 0)>=70 and x["first_touch_symmetric_pct"]["0.8"]["decisive_n"]>=30],
        "top_directional":by_dir[:20],"top_ft05":by05[:20],"top_ft08":by08[:20],
        "notes":[
            "All post-warmup Tuesdays are traded BUY or SELL; no WAIT filter.",
            "Predictions are walk-forward using earlier Tuesdays only.",
            "Observation is completed 06:00 and 06:15 candles; decision and entry are at 06:30 open.",
        ]
    }
