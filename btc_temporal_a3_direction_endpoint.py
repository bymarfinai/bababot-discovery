"""BTC Temporal A3 — high-coverage dynamic direction classification.

Goal
----
Turn the Tuesday temporal anomaly into a BUY/SELL decision engine rather than a
SELL filter.  The clock is only an event window.  At 06:30 WIB, after observing
completed 06:00 and 06:15 candles, the engine predicts BUY or SELL from the
current path and historical analogues.

Causality / anti-leakage
------------------------
- BTCUSDT 15m only, WIB/UTC+7.
- Observation window = completed 06:00 and 06:15 bars.
- Decision/entry = 06:30 open. No 06:30 candle information is used.
- Walk-forward only: each Tuesday prediction learns from PREVIOUS Tuesdays.
- Previous labels are fully known before the next weekly occurrence.
- No WAIT in primary engines: every post-warmup Tuesday receives BUY or SELL.
- Fixed feature sets and small predeclared k/state variants; no label-informed
  threshold sweep inside an occurrence.
- Outcomes are reported for 30/60/120/240m plus symmetric first-touch geometry.

Research only. Does not place orders or mutate live BBC state.
"""

import math
import statistics
from collections import defaultdict
from datetime import timezone, timedelta

from fastapi import APIRouter, Query

from btc_temporal_a2_sequence_endpoint import (
    _load, _local_dt, _context, _bar_features, _median,
    TF_MS, HORIZONS, H_BARS,
)

router = APIRouter(prefix="/research/btc-temporal-a3-direction", tags=["btc_temporal_a3_direction"])


def _r(x, n=4):
    return round(float(x), n) if x is not None and math.isfinite(float(x)) else None


def _mean(xs):
    xs = [float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return statistics.mean(xs) if xs else None


def _sign(x, eps=1e-12):
    if x > eps:
        return 1
    if x < -eps:
        return -1
    return 0


def _extended_context(rows, idx, base):
    entry = float(rows[idx][1])
    out = dict(base)
    for bars, name in ((96, "pre24_ret"), (672, "pre7d_ret")):
        if idx >= bars:
            old = float(rows[idx - bars][1])
            out[name] = 100.0 * (entry - old) / old
        else:
            out[name] = 0.0
    out["dist_daily_open_pct"] = 100.0 * (entry - out["daily_open"]) / out["daily_open"]
    return out


def _build_occurrence(rows, idx, tz, block):
    """Build features known at 06:30 and future paths starting 06:30."""
    if idx + 2 >= len(rows):
        return None
    ts = int(rows[idx][0])
    b0 = rows[idx]
    b1 = rows[idx + 1]
    entry_row = rows[idx + 2]
    if int(b1[0]) != ts + TF_MS or int(entry_row[0]) != ts + 2 * TF_MS:
        return None

    base = _context(rows, idx, tz)
    if base is None:
        return None
    ctx = _extended_context(rows, idx, base)
    f0 = _bar_features(b0)
    f1 = _bar_features(b1)

    wopen = float(b0[1])
    obs_close = float(b1[4])
    obs_high = max(float(b0[2]), float(b1[2]))
    obs_low = min(float(b0[3]), float(b1[3]))
    obs_ret = 100.0 * (obs_close - wopen) / wopen
    bar0_ret = 100.0 * (float(b0[4]) - float(b0[1])) / float(b0[1])
    bar1_ret = 100.0 * (float(b1[4]) - float(b1[1])) / float(b1[1])
    pre_med = max(1e-12, float(ctx["pre_range_median"]))
    obs_range = obs_high - obs_low

    hod_attack = obs_high > float(ctx["hod"])
    lod_attack = obs_low < float(ctx["lod"])
    hod_reclaim_down = hod_attack and obs_close < float(ctx["hod"])
    lod_reclaim_up = lod_attack and obs_close > float(ctx["lod"])
    prevh_high_attack = obs_high > float(ctx["prev1h_high"])
    prevh_low_attack = obs_low < float(ctx["prev1h_low"])
    close_above_prevh = obs_close > float(ctx["prev1h_high"])
    close_below_prevl = obs_close < float(ctx["prev1h_low"])

    seq = ("U" if f0["bull"] else "D" if f0["bear"] else "F") + ("U" if f1["bull"] else "D" if f1["bear"] else "F")
    pos = float(ctx["day_pos"])
    pos_bucket = "L" if pos < 1/3 else "M" if pos < 2/3 else "U"

    features = {
        "pre1_ret": float(ctx["pre1_ret"]),
        "pre4_ret": float(ctx["pre4_ret"]),
        "pre24_ret": float(ctx["pre24_ret"]),
        "pre7d_ret": float(ctx["pre7d_ret"]),
        "day_pos": pos,
        "dist_daily_open_pct": float(ctx["dist_daily_open_pct"]),
        "obs_ret": obs_ret,
        "bar0_ret": bar0_ret,
        "bar1_ret": bar1_ret,
        "bar0_body": float(f0["body_ratio"]),
        "bar1_body": float(f1["body_ratio"]),
        "bar0_close_loc": float(f0["close_loc"]),
        "bar1_close_loc": float(f1["close_loc"]),
        "obs_range_ratio": obs_range / pre_med,
        "close_vs_0600_pct": 100.0 * (obs_close - wopen) / wopen,
        "close_vs_prevh_mid_pct": 100.0 * (obs_close - (ctx["prev1h_high"] + ctx["prev1h_low"]) / 2.0) / wopen,
        "hod_attack": 1.0 if hod_attack else 0.0,
        "lod_attack": 1.0 if lod_attack else 0.0,
        "hod_reclaim_down": 1.0 if hod_reclaim_down else 0.0,
        "lod_reclaim_up": 1.0 if lod_reclaim_up else 0.0,
        "prevh_high_attack": 1.0 if prevh_high_attack else 0.0,
        "prevh_low_attack": 1.0 if prevh_low_attack else 0.0,
        "close_above_prevh": 1.0 if close_above_prevh else 0.0,
        "close_below_prevl": 1.0 if close_below_prevl else 0.0,
    }

    states = {
        "full": (
            _sign(ctx["pre24_ret"]), pos_bucket, _sign(obs_ret), seq,
            int(hod_reclaim_down), int(lod_reclaim_up),
            int(close_above_prevh), int(close_below_prevl),
        ),
        "medium": (_sign(ctx["pre24_ret"]), pos_bucket, _sign(obs_ret), seq),
        "coarse": (pos_bucket, _sign(obs_ret), seq),
        "minimal": (pos_bucket, _sign(obs_ret)),
        "sequence": (_sign(ctx["pre24_ret"]), _sign(obs_ret), seq),
    }

    entry = float(entry_row[1])
    paths = {}
    labels = {}
    returns = {}
    for h in HORIZONS:
        hb = H_BARS[h]
        path = rows[idx + 2: idx + 2 + hb]
        if len(path) != hb:
            continue
        if any(int(path[k][0]) != int(entry_row[0]) + k * TF_MS for k in range(hb)):
            continue
        ret = 100.0 * (float(path[-1][4]) - entry) / entry
        paths[h] = path
        returns[h] = ret
        labels[h] = 1 if ret > 0 else -1 if ret < 0 else 0

    if len(paths) != len(HORIZONS):
        return None
    return {
        "ts": ts,
        "block": block,
        "entry": entry,
        "features": features,
        "states": states,
        "paths": paths,
        "labels": labels,
        "returns": returns,
        "seq": seq,
        "pos_bucket": pos_bucket,
    }


FEATURE_SETS = {
    "OBS_ONLY": ["obs_ret", "bar0_ret", "bar1_ret", "bar0_body", "bar1_body", "bar0_close_loc", "bar1_close_loc", "obs_range_ratio"],
    "CONTEXT_SEQ": ["pre1_ret", "pre4_ret", "pre24_ret", "day_pos", "dist_daily_open_pct", "obs_ret", "bar0_ret", "bar1_ret", "obs_range_ratio", "close_vs_prevh_mid_pct"],
    "FULL_PATH": [
        "pre1_ret", "pre4_ret", "pre24_ret", "pre7d_ret", "day_pos", "dist_daily_open_pct",
        "obs_ret", "bar0_ret", "bar1_ret", "bar0_body", "bar1_body", "bar0_close_loc", "bar1_close_loc",
        "obs_range_ratio", "close_vs_prevh_mid_pct", "hod_attack", "lod_attack", "hod_reclaim_down", "lod_reclaim_up",
        "prevh_high_attack", "prevh_low_attack", "close_above_prevh", "close_below_prevl",
    ],
}


def _standardized_distance(a, b, train, names):
    s = 0.0
    for name in names:
        vals = [x["features"][name] for x in train]
        mu = _mean(vals) or 0.0
        var = _mean([(v - mu) ** 2 for v in vals]) or 0.0
        sd = math.sqrt(var)
        if sd < 1e-9:
            continue
        d = (a["features"][name] - b["features"][name]) / sd
        s += d * d
    return math.sqrt(s)


def _predict_knn(train, cur, horizon, names, k, weighted=True):
    ranked = []
    for old in train:
        lab = old["labels"][horizon]
        if lab == 0:
            continue
        dist = _standardized_distance(cur, old, train, names)
        ranked.append((dist, lab))
    ranked.sort(key=lambda x: x[0])
    nbrs = ranked[:min(k, len(ranked))]
    if not nbrs:
        return -1, 0.0, 0
    score = 0.0
    den = 0.0
    for dist, lab in nbrs:
        w = 1.0 / (0.25 + dist) if weighted else 1.0
        score += w * lab
        den += w
    pred = 1 if score > 0 else -1 if score < 0 else -1
    conf = abs(score) / den if den else 0.0
    return pred, conf, len(nbrs)


def _predict_state(train, cur, horizon, min_support):
    for level in ("full", "medium", "coarse", "sequence", "minimal"):
        key = cur["states"][level]
        matches = [x for x in train if x["states"][level] == key and x["labels"][horizon] != 0]
        if len(matches) >= min_support:
            score = sum(x["labels"][horizon] for x in matches)
            pred = 1 if score > 0 else -1 if score < 0 else -1
            conf = abs(score) / len(matches)
            return pred, conf, len(matches), level
    # High-coverage fallback remains dynamic-history based: majority of all prior Tuesdays.
    labs = [x["labels"][horizon] for x in train if x["labels"][horizon] != 0]
    score = sum(labs)
    pred = 1 if score > 0 else -1
    return pred, abs(score) / len(labs) if labs else 0.0, len(labs), "global"


def _first_touch(path, entry, direction, th):
    fav = entry * (1.0 + direction * th / 100.0)
    adv = entry * (1.0 - direction * th / 100.0)
    for row in path:
        hi, lo = float(row[2]), float(row[3])
        if direction > 0:
            hf, ha = hi >= fav, lo <= adv
        else:
            hf, ha = lo <= fav, hi >= adv
        if hf and ha:
            return "AMBIGUOUS"
        if hf:
            return "FAVORABLE"
        if ha:
            return "ADVERSE"
    return "NONE"


def _evaluate(preds, occurrences, horizon, blocks):
    rows = []
    by_ts = {x["ts"]: x for x in occurrences}
    for p in preds:
        e = by_ts[p["ts"]]
        direction = p["pred"]
        actual = e["labels"][horizon]
        signed_ret = direction * e["returns"][horizon]
        rows.append({**p, "block": e["block"], "actual": actual, "correct": actual != 0 and direction == actual, "signed_ret": signed_ret, "event": e})
    resolved = [x for x in rows if x["actual"] != 0]
    wins = sum(x["correct"] for x in resolved)
    losses = len(resolved) - wins
    block_stats = []
    for b in range(blocks):
        xs = [x for x in resolved if x["block"] == b]
        bw = sum(x["correct"] for x in xs)
        block_stats.append({"block": b+1, "n": len(xs), "wr_pct": _r(100*bw/len(xs),2) if xs else None})

    ft = {}
    for th in (0.3, 0.5, 0.8, 1.0):
        c = defaultdict(int)
        for x in rows:
            e = x["event"]
            c[_first_touch(e["paths"][horizon], e["entry"], x["pred"], th)] += 1
        dec = c["FAVORABLE"] + c["ADVERSE"]
        ft[str(th)] = {"favorable":c["FAVORABLE"],"adverse":c["ADVERSE"],"ambiguous":c["AMBIGUOUS"],"none":c["NONE"],"decisive_n":dec,"wr_pct":_r(100*c["FAVORABLE"]/dec,2) if dec else None}

    wrs = [x["wr_pct"] for x in block_stats if x["wr_pct"] is not None]
    buy_n = sum(x["pred"] > 0 for x in rows)
    sell_n = sum(x["pred"] < 0 for x in rows)
    return {
        "n": len(rows), "resolved": len(resolved), "wins": wins, "losses": losses,
        "wr_pct": _r(100*wins/len(resolved),2) if resolved else None,
        "buy_n": buy_n, "sell_n": sell_n,
        "avg_signed_return_pct": _r(_mean([x["signed_ret"] for x in rows]),4),
        "median_signed_return_pct": _r(_median([x["signed_ret"] for x in rows]),4),
        "avg_confidence": _r(_mean([x.get("confidence",0.0) for x in rows]),4),
        "positive_blocks_gt50": sum(1 for x in wrs if x > 50),
        "blocks_ge60": sum(1 for x in wrs if x >= 60),
        "min_block_wr_pct": _r(min(wrs),2) if wrs else None,
        "median_block_wr_pct": _r(_median(wrs),2),
        "blocks": block_stats,
        "first_touch_symmetric_pct": ft,
    }


@router.get("")
def dynamic_direction(
    days: int = Query(971, ge=240, le=1500),
    blocks: int = Query(8, ge=4, le=12),
    warmup: int = Query(20, ge=12, le=60),
):
    rows, start_ms, end_ms = _load(days)
    if not rows:
        return {"error":"No BTCUSDT 15m data"}
    tz = timezone(timedelta(hours=7))
    span = max(1, end_ms - start_ms)
    occurrences = []
    for idx, row in enumerate(rows):
        ts = int(row[0])
        dt = _local_dt(ts, tz)
        if dt.weekday() != 1 or dt.hour != 6 or dt.minute != 0:
            continue
        block = min(blocks-1, max(0, int((ts-start_ms)*blocks/span)))
        occ = _build_occurrence(rows, idx, tz, block)
        if occ is not None:
            occurrences.append(occ)

    engines = []
    for horizon in HORIZONS:
        eval_occ = occurrences[warmup:]

        # Baselines at same 06:30 entry.
        for name, pred_fn in (
            ("BASE_ALWAYS_SELL", lambda e: -1),
            ("OBS_MOMENTUM", lambda e: 1 if e["features"]["obs_ret"] >= 0 else -1),
            ("OBS_REVERSAL", lambda e: -1 if e["features"]["obs_ret"] >= 0 else 1),
        ):
            preds = [{"ts":e["ts"],"pred":pred_fn(e),"confidence":0.0,"support":0} for e in eval_occ]
            engines.append({"engine":name,"horizon_min":horizon,"coverage_eval_pct":100.0,**_evaluate(preds, occurrences, horizon, blocks)})

        for support in (3, 5, 8):
            preds = []
            for i in range(warmup, len(occurrences)):
                train = occurrences[:i]
                cur = occurrences[i]
                pred, conf, n, level = _predict_state(train, cur, horizon, support)
                preds.append({"ts":cur["ts"],"pred":pred,"confidence":conf,"support":n,"state_level":level})
            engines.append({"engine":f"WF_STATE_MIN{support}","horizon_min":horizon,"coverage_eval_pct":100.0,**_evaluate(preds, occurrences, horizon, blocks)})

        for fs_name, names in FEATURE_SETS.items():
            for k in (5, 9, 15, 21):
                preds = []
                for i in range(warmup, len(occurrences)):
                    train = occurrences[:i]
                    cur = occurrences[i]
                    pred, conf, n = _predict_knn(train, cur, horizon, names, k, weighted=True)
                    preds.append({"ts":cur["ts"],"pred":pred,"confidence":conf,"support":n})
                engines.append({"engine":f"WF_KNN_{fs_name}_K{k}","horizon_min":horizon,"coverage_eval_pct":100.0,**_evaluate(preds, occurrences, horizon, blocks)})

    ranked = sorted(engines, key=lambda x: (x["wr_pct"] or -1, x["first_touch_symmetric_pct"]["0.5"]["wr_pct"] or -1, x["n"]), reverse=True)
    ranked_ft05 = sorted(engines, key=lambda x: (x["first_touch_symmetric_pct"]["0.5"]["wr_pct"] or -1, x["first_touch_symmetric_pct"]["0.5"]["decisive_n"], x["wr_pct"] or -1), reverse=True)
    ranked_ft08 = sorted(engines, key=lambda x: (x["first_touch_symmetric_pct"]["0.8"]["wr_pct"] or -1, x["first_touch_symmetric_pct"]["0.8"]["decisive_n"], x["wr_pct"] or -1), reverse=True)

    baseline = [x for x in engines if x["engine"] == "BASE_ALWAYS_SELL"]
    expected = max(1, int((end_ms-start_ms)/(15*60*1000)))
    return {
        "status":"BTC_TEMPORAL_A3_DYNAMIC_DIRECTION_WALKFORWARD",
        "data":{
            "days":days,"rows_15m":len(rows),"expected_rows_15m":expected,"coverage_pct":_r(100*len(rows)/expected,2),
            "tuesday_occurrences":len(occurrences),"warmup_occurrences":warmup,"walkforward_predictions":max(0,len(occurrences)-warmup),
            "overall_history_coverage_pct":_r(100*max(0,len(occurrences)-warmup)/len(occurrences),2) if occurrences else None,
            "live_after_warmup_decision_coverage_pct":100.0,
            "decision_time_wib":"06:30","observation":"completed 06:00 + 06:15 bars","entry":"06:30 open",
        },
        "method":"Every post-warmup Tuesday receives BUY or SELL. Each prediction uses only earlier Tuesday outcomes and current causal 06:00-06:30 path.",
        "baseline_same_entry":baseline,
        "top_directional":ranked[:25],
        "top_first_touch_05":ranked_ft05[:25],
        "top_first_touch_08":ranked_ft08[:25],
        "candidate_engine_count":len(engines),
        "target70_directional":[x for x in ranked if (x["wr_pct"] or 0)>=70],
        "target70_ft05":[x for x in ranked_ft05 if (x["first_touch_symmetric_pct"]["0.5"]["wr_pct"] or 0)>=70 and x["first_touch_symmetric_pct"]["0.5"]["decisive_n"]>=30],
        "target70_ft08":[x for x in ranked_ft08 if (x["first_touch_symmetric_pct"]["0.8"]["wr_pct"] or 0)>=70 and x["first_touch_symmetric_pct"]["0.8"]["decisive_n"]>=30],
        "notes":[
            "This is walk-forward discovery, not in-sample state labeling.",
            "Primary engines force BUY/SELL after warmup; WAIT is not used to inflate WR.",
            "The first warmup Tuesdays are excluded from dynamic evaluation because a live learner would not yet have enough prior weekly examples.",
            "A3 is discovery. Any winning engine should be frozen and subjected to block/holdout robustness before production.",
        ],
    }
