#!/usr/bin/env python3
"""SOL Options Wall Control Test V1.

Prospective control study for options concentration walls versus:
- deterministic distance-matched pseudo-random levels;
- fixed $5 round-number levels;
- causal confirmed 1H price pivots.

The confirmatory sample starts strictly after the preregistered timestamp.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / "research" / "data" / "sol_options_v1"
OUT_CSV = ROOT / "SOL_OPTIONS_WALL_CONTROL_TEST_V1_Observations.csv"
OUT_MD = ROOT / "SOL_OPTIONS_WALL_CONTROL_TEST_V1_Result.md"

MAP_VERSION = "SOL_OPTIONS_LIQUIDITY_MAP_V1"
CONTROL_START_ISO = "2026-09-23T04:46:00+00:00"
CONTROL_START_MS = int(datetime.fromisoformat(CONTROL_START_ISO).timestamp() * 1000)
HORIZON_MIN = 240
BANDS = (0.0025, 0.0050, 0.0100)
POST_TOUCH_WINDOWS = (15, 30, 60)
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
SYMBOL = "SOLUSDT"
BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 20260923


def load_snapshots() -> list[dict]:
    out = []
    for p in sorted(SNAP_DIR.glob("*.json")):
        x = json.loads(p.read_text(encoding="utf-8"))
        if x.get("map_version") != MAP_VERSION:
            continue
        x["snapshot_time_ms"] = int(x["snapshot_time_ms"])
        x["_path"] = str(p.relative_to(ROOT))
        out.append(x)
    out.sort(key=lambda x: x["snapshot_time_ms"])
    return out


def regime_key(s: dict) -> tuple:
    return (
        tuple(x["code"] for x in s["expiries"]),
        tuple(float(x["strike"]) for x in s["lower_put_concentration"][:3]),
        tuple(float(x["strike"]) for x in s["upper_call_concentration"][:3]),
    )


def make_anchor_series(snaps: list[dict], eligible: bool) -> list[dict]:
    if not snaps:
        return []

    anchors = [snaps[0]]
    for s in snaps[1:]:
        prev = anchors[-1]
        elapsed = s["snapshot_time_ms"] - prev["snapshot_time_ms"]
        regime_changed = regime_key(s) != regime_key(prev)
        if regime_changed or elapsed >= HORIZON_MIN * 60_000:
            anchors.append(s)

    for a in anchors:
        a["_confirmatory"] = eligible
    return anchors


def build_anchors(snaps: list[dict]) -> list[dict]:
    exploratory = [s for s in snaps if s["snapshot_time_ms"] < CONTROL_START_MS]
    confirmatory = [s for s in snaps if s["snapshot_time_ms"] >= CONTROL_START_MS]

    anchors = []
    if exploratory:
        anchors.extend(make_anchor_series(exploratory, False))
    if confirmatory:
        # Confirmatory anchoring restarts at prereg start. This guarantees the
        # first saved post-prereg snapshot becomes the first eligible anchor.
        anchors.extend(make_anchor_series(confirmatory, True))

    anchors.sort(key=lambda x: x["snapshot_time_ms"])
    return anchors


def fetch_klines(interval: str, start_ms: int, end_ms: int, limit: int = 1000) -> list[list]:
    out = []
    cursor = int(start_ms)
    while cursor <= end_ms:
        params = {
            "symbol": SYMBOL,
            "interval": interval,
            "startTime": cursor,
            "endTime": int(end_ms),
            "limit": min(limit, 1000),
        }
        r = requests.get(BINANCE_KLINES, params=params, timeout=20)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        step = 60_000 if interval == "1m" else 3_600_000
        nxt = int(batch[-1][0]) + step
        if nxt <= cursor:
            break
        cursor = nxt
        if len(batch) < 1000:
            break
        time.sleep(0.05)
    return out


def get_price_path(start_ms: int, end_ms: int) -> list[dict]:
    return [
        {
            "open_time_ms": int(k[0]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
        }
        for k in fetch_klines("1m", start_ms, end_ms)
    ]


def get_completed_hourly_before(anchor_ms: int) -> list[dict]:
    end_ms = (anchor_ms // 3_600_000) * 3_600_000 - 1
    start_ms = end_ms - (80 * 3_600_000)
    raw = fetch_klines("1h", start_ms, end_ms)
    rows = [
        {
            "open_time_ms": int(k[0]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close_time_ms": int(k[6]),
        }
        for k in raw
        if int(k[6]) < anchor_ms
    ]
    return rows[-76:]


def confirmed_pivots(anchor_ms: int, spot: float) -> tuple[list[float], list[float]]:
    rows = get_completed_hourly_before(anchor_ms)
    lows = []
    highs = []

    for i in range(2, len(rows) - 2):
        # Require two right-side candles to have completed before anchor.
        if rows[i + 2]["close_time_ms"] >= anchor_ms:
            continue
        lo = rows[i]["low"]
        hi = rows[i]["high"]
        if all(lo < rows[j]["low"] for j in (i - 2, i - 1, i + 1, i + 2)):
            if lo < spot:
                lows.append(lo)
        if all(hi > rows[j]["high"] for j in (i - 2, i - 1, i + 1, i + 2)):
            if hi > spot:
                highs.append(hi)

    # Nearest distinct levels. Round only for deduplication, retain price precision.
    low_unique = {}
    for x in lows:
        low_unique.setdefault(round(x, 4), x)
    high_unique = {}
    for x in highs:
        high_unique.setdefault(round(x, 4), x)

    lower = sorted(low_unique.values(), key=lambda x: abs(spot - x))[:3]
    upper = sorted(high_unique.values(), key=lambda x: abs(x - spot))[:3]
    return lower, upper


def deterministic_u(text: str) -> float:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    n = int.from_bytes(h[:8], "big")
    return n / float((1 << 64) - 1)


def random_matched_levels(anchor: dict, side: str, option_levels: list[dict]) -> list[dict]:
    spot = float(anchor["spot"])
    actual = [float(x["strike"]) for x in option_levels]
    out = []

    for rank, opt in enumerate(option_levels, start=1):
        wall = float(opt["strike"])
        d = abs(wall / spot - 1.0)
        chosen = None

        for attempt in range(50):
            salt = f'{anchor["snapshot_id"]}|{side}|{rank}|RANDOM_MATCHED_V1|{attempt}'
            u = deterministic_u(salt)
            mult = 0.75 + 0.50 * u
            dist = d * mult
            level = spot * (1.0 - dist if side == "LOWER" else 1.0 + dist)
            level = round(level, 2)

            correct_side = level < spot if side == "LOWER" else level > spot
            collision_actual = any(abs(level - a) / spot * 100.0 < 0.10 for a in actual)
            collision_random = any(abs(level - x["level"]) < 0.005 for x in out)

            if correct_side and not collision_actual and not collision_random:
                chosen = {
                    "level": level,
                    "rank": rank,
                    "source": "RANDOM_MATCHED",
                    "matched_option_strike": wall,
                    "distance_multiplier": mult,
                    "overlap_options": False,
                }
                break

        if chosen is not None:
            out.append(chosen)

    return out


def round5_levels(spot: float, side: str, actual: list[float]) -> list[dict]:
    if side == "LOWER":
        first = math.floor(spot / 5.0) * 5.0
        if first >= spot:
            first -= 5.0
        vals = [first - 5.0 * i for i in range(3)]
    else:
        first = math.ceil(spot / 5.0) * 5.0
        if first <= spot:
            first += 5.0
        vals = [first + 5.0 * i for i in range(3)]

    return [
        {
            "level": float(v),
            "rank": i + 1,
            "source": "ROUND_5",
            "matched_option_strike": None,
            "distance_multiplier": None,
            "overlap_options": any(abs(v - a) < 1e-9 for a in actual),
        }
        for i, v in enumerate(vals)
    ]


def option_levels(anchor: dict, side: str) -> list[dict]:
    key = "lower_put_concentration" if side == "LOWER" else "upper_call_concentration"
    return [
        {
            "level": float(x["strike"]),
            "rank": i + 1,
            "source": "OPTIONS",
            "matched_option_strike": float(x["strike"]),
            "distance_multiplier": 1.0,
            "overlap_options": True,
            "concentration_score": float(x["concentration_score"]),
            "mean_oi_share": float(x["mean_oi_share"]),
            "mean_gamma_share": float(x["mean_gamma_share"]),
            "iv_confluence": x.get("confluence_label"),
            "nearest_iv_expiry": (x.get("nearest_iv_band") or {}).get("expiry"),
            "nearest_iv_distance_pct_spot": (x.get("nearest_iv_band") or {}).get("distance_pct_spot"),
        }
        for i, x in enumerate(anchor[key][:3])
    ]


def pivot_levels(anchor_ms: int, spot: float, side: str) -> list[dict]:
    lower, upper = confirmed_pivots(anchor_ms, spot)
    vals = lower if side == "LOWER" else upper
    return [
        {
            "level": float(v),
            "rank": i + 1,
            "source": "PRICE_PIVOT_1H",
            "matched_option_strike": None,
            "distance_multiplier": None,
            "overlap_options": False,
        }
        for i, v in enumerate(vals)
    ]


def first_touch(candles: list[dict], level: float) -> int | None:
    for i, c in enumerate(candles):
        if c["low"] <= level <= c["high"]:
            return i
    return None


def reaction_metrics(candles: list[dict], touch_i: int, level: float, side: str, n: int | None):
    xs = candles[touch_i:] if n is None else candles[touch_i : touch_i + n]
    if not xs:
        return None

    # A named N-minute metric requires the full forward window.
    if n is not None and len(xs) < n:
        return None

    hi = max(x["high"] for x in xs)
    lo = min(x["low"] for x in xs)
    close = xs[-1]["close"]

    if side == "LOWER":
        mfe = (hi / level - 1.0) * 100.0
        mae = max(0.0, (1.0 - lo / level) * 100.0)
        close_disp = (close / level - 1.0) * 100.0
    else:
        mfe = (1.0 - lo / level) * 100.0
        mae = max(0.0, (hi / level - 1.0) * 100.0)
        close_disp = (1.0 - close / level) * 100.0

    return {
        "mfe_pct": mfe,
        "mae_pct": mae,
        "net_reaction": mfe - mae,
        "close_disp_pct": close_disp,
    }


def first_passage(candles: list[dict], touch_i: int, level: float, side: str, band: float) -> str:
    fav = level * (1.0 + band) if side == "LOWER" else level * (1.0 - band)
    adv = level * (1.0 - band) if side == "LOWER" else level * (1.0 + band)

    for c in candles[touch_i:]:
        fav_hit = c["high"] >= fav if side == "LOWER" else c["low"] <= fav
        adv_hit = c["low"] <= adv if side == "LOWER" else c["high"] >= adv
        if fav_hit and adv_hit:
            return "SAME_BAR_BOTH"
        if fav_hit:
            return "FAVORABLE_FIRST"
        if adv_hit:
            return "ADVERSE_FIRST"
    return "NONE"


def passage_score(v: str) -> int:
    if v == "FAVORABLE_FIRST":
        return 1
    if v == "ADVERSE_FIRST":
        return -1
    return 0


def evaluate_candidate(anchor: dict, candles: list[dict], candidate: dict, side: str, end_ms: int, anchor_censored: bool) -> dict:
    level = float(candidate["level"])
    ti = first_touch(candles, level)

    row = {
        "anchor_time_utc": datetime.fromtimestamp(anchor["snapshot_time_ms"] / 1000, tz=timezone.utc).isoformat(),
        "anchor_snapshot_id": anchor["snapshot_id"],
        "confirmatory_eligible": bool(anchor["_confirmatory"]),
        "anchor_censored": bool(anchor_censored),
        "spot": float(anchor["spot"]),
        "side": side,
        "source": candidate["source"],
        "rank": int(candidate["rank"]),
        "level": level,
        "matched_option_strike": candidate.get("matched_option_strike"),
        "distance_multiplier": candidate.get("distance_multiplier"),
        "overlap_options": bool(candidate.get("overlap_options", False)),
        "concentration_score": candidate.get("concentration_score"),
        "mean_oi_share": candidate.get("mean_oi_share"),
        "mean_gamma_share": candidate.get("mean_gamma_share"),
        "iv_confluence": candidate.get("iv_confluence"),
        "nearest_iv_expiry": candidate.get("nearest_iv_expiry"),
        "nearest_iv_distance_pct_spot": candidate.get("nearest_iv_distance_pct_spot"),
        "window_end_utc": datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).isoformat(),
        "touched": ti is not None,
        "touch_time_utc": "",
    }

    if ti is None:
        return row

    row["touch_time_utc"] = datetime.fromtimestamp(candles[ti]["open_time_ms"] / 1000, tz=timezone.utc).isoformat()

    for n in POST_TOUCH_WINDOWS:
        m = reaction_metrics(candles, ti, level, side, n)
        if m is not None:
            row[f"mfe_{n}m_pct"] = m["mfe_pct"]
            row[f"mae_{n}m_pct"] = m["mae_pct"]
            row[f"net_reaction_{n}m"] = m["net_reaction"]
            row[f"close_disp_{n}m_pct"] = m["close_disp_pct"]

    endm = reaction_metrics(candles, ti, level, side, None)
    if endm is not None:
        row["mfe_end_pct"] = endm["mfe_pct"]
        row["mae_end_pct"] = endm["mae_pct"]
        row["net_reaction_end"] = endm["net_reaction"]
        row["close_disp_end_pct"] = endm["close_disp_pct"]

    for b in BANDS:
        tag = str(b * 100).rstrip("0").rstrip(".").replace(".", "p")
        row[f"first_passage_{tag}pct"] = first_passage(candles, ti, level, side, b)

    return row


def median_or_none(xs: list[float]):
    return statistics.median(xs) if xs else None


def bootstrap_median_diff(a: list[float], b: list[float]) -> tuple[float | None, float | None]:
    if not a or not b:
        return None, None
    rng = random.Random(BOOTSTRAP_SEED)
    diffs = []
    for _ in range(BOOTSTRAP_N):
        aa = [a[rng.randrange(len(a))] for _ in range(len(a))]
        bb = [b[rng.randrange(len(b))] for _ in range(len(b))]
        diffs.append(statistics.median(aa) - statistics.median(bb))
    diffs.sort()
    lo = diffs[int(0.05 * (len(diffs) - 1))]
    hi = diffs[int(0.95 * (len(diffs) - 1))]
    return lo, hi


def fmt(v, digits=4) -> str:
    if v is None:
        return "NA"
    return f"{float(v):.{digits}f}"


def main() -> int:
    snaps = load_snapshots()
    if not snaps:
        print("CONTROL_NO_SNAPSHOTS")
        return 2

    anchors = build_anchors(snaps)
    if not anchors:
        print("CONTROL_NO_ANCHORS")
        return 2

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    observations = []

    for i, anchor in enumerate(anchors):
        natural_end = anchor["snapshot_time_ms"] + HORIZON_MIN * 60_000

        # End early only if the next anchor is caused by a regime change before
        # the natural horizon. Non-overlap anchors at >=240m naturally coincide.
        next_anchor_ms = anchors[i + 1]["snapshot_time_ms"] if i + 1 < len(anchors) else None
        if next_anchor_ms is not None and next_anchor_ms < natural_end:
            end_ms = next_anchor_ms - 1
        else:
            end_ms = natural_end

        end_ms = min(end_ms, now_ms)
        anchor_censored = end_ms < natural_end and (
            next_anchor_ms is None or next_anchor_ms >= natural_end
        )

        candles = get_price_path(anchor["snapshot_time_ms"], end_ms)
        if not candles:
            continue

        spot = float(anchor["spot"])
        lower_opts = option_levels(anchor, "LOWER")
        upper_opts = option_levels(anchor, "UPPER")
        lower_actual = [x["level"] for x in lower_opts]
        upper_actual = [x["level"] for x in upper_opts]

        candidates = {
            "LOWER": (
                lower_opts
                + random_matched_levels(anchor, "LOWER", lower_opts)
                + round5_levels(spot, "LOWER", lower_actual)
                + pivot_levels(anchor["snapshot_time_ms"], spot, "LOWER")
            ),
            "UPPER": (
                upper_opts
                + random_matched_levels(anchor, "UPPER", upper_opts)
                + round5_levels(spot, "UPPER", upper_actual)
                + pivot_levels(anchor["snapshot_time_ms"], spot, "UPPER")
            ),
        }

        for side, xs in candidates.items():
            for c in xs:
                observations.append(
                    evaluate_candidate(anchor, candles, c, side, end_ms, anchor_censored)
                )

    fields = []
    for row in observations:
        for k in row:
            if k not in fields:
                fields.append(k)

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(observations)

    # Confirmatory primary sample: rank-1 touched observations with a complete
    # 60-minute reaction window.
    primary = [
        r for r in observations
        if r["confirmatory_eligible"]
        and r["rank"] == 1
        and r["touched"]
        and r.get("net_reaction_60m") not in (None, "")
    ]

    by_source = {}
    for source in ("OPTIONS", "RANDOM_MATCHED", "ROUND_5", "PRICE_PIVOT_1H"):
        rows = [r for r in primary if r["source"] == source]
        by_source[source] = rows

    opt_vals = [float(r["net_reaction_60m"]) for r in by_source["OPTIONS"]]
    rnd_vals = [float(r["net_reaction_60m"]) for r in by_source["RANDOM_MATCHED"]]
    piv_vals = [float(r["net_reaction_60m"]) for r in by_source["PRICE_PIVOT_1H"]]
    rnd_ci = bootstrap_median_diff(opt_vals, rnd_vals)

    confirmatory_anchor_ids = {
        r["anchor_snapshot_id"] for r in observations if r["confirmatory_eligible"]
    }

    minimum_ready = (
        len(opt_vals) >= 20
        and len(rnd_vals) >= 20
        and len(piv_vals) >= 10
        and len(confirmatory_anchor_ids) >= 10
    )

    band_tags = ("0p25", "0p5", "1")
    band_advantages = {}
    for tag in band_tags:
        k = f"first_passage_{tag}pct"
        os = [passage_score(r.get(k, "NONE")) for r in by_source["OPTIONS"]]
        rs = [passage_score(r.get(k, "NONE")) for r in by_source["RANDOM_MATCHED"]]
        band_advantages[tag] = (
            (sum(os) / len(os) if os else None),
            (sum(rs) / len(rs) if rs else None),
        )

    med_opt = median_or_none(opt_vals)
    med_rnd = median_or_none(rnd_vals)
    med_piv = median_or_none(piv_vals)
    bands_not_contradicted = all(
        a is not None and b is not None and a >= b
        for a, b in band_advantages.values()
    )

    supported = (
        minimum_ready
        and med_opt is not None and med_rnd is not None and med_piv is not None
        and med_opt > med_rnd
        and med_opt > med_piv
        and rnd_ci[0] is not None and rnd_ci[0] > 0
        and bands_not_contradicted
    )

    if not minimum_ready:
        status = "CONTROL_SAMPLE_ACCUMULATING"
    elif supported:
        status = "CONTROL_EVIDENCE_SUPPORTED"
    else:
        status = "CONTROL_EVIDENCE_NOT_SUPPORTED"

    exploratory = [r for r in observations if not r["confirmatory_eligible"]]
    confirmatory = [r for r in observations if r["confirmatory_eligible"]]

    lines = [
        "# SOL Options Wall Control Test V1 — Result",
        "",
        f"**Status: {status}**",
        "",
        "## Sample state",
        "",
        f"- Control prereg start: {CONTROL_START_ISO}",
        f"- Saved options snapshots: {len(snaps)}",
        f"- Total anchors evaluated: {len(anchors)}",
        f"- Confirmatory anchors represented: {len(confirmatory_anchor_ids)}",
        f"- Exploratory observation rows: {len(exploratory)}",
        f"- Confirmatory observation rows: {len(confirmatory)}",
        "",
        "## Primary rank-1 confirmatory sample",
        "",
        "| Source | Complete touched N | Median NET_REACTION_60 |",
        "|---|---:|---:|",
    ]

    for source in ("OPTIONS", "RANDOM_MATCHED", "ROUND_5", "PRICE_PIVOT_1H"):
        vals = [float(r["net_reaction_60m"]) for r in by_source[source]]
        lines.append(f"| {source} | {len(vals)} | {fmt(median_or_none(vals))} |")

    lines += [
        "",
        f"- OPTIONS minus RANDOM_MATCHED bootstrap 90% CI: [{fmt(rnd_ci[0])}, {fmt(rnd_ci[1])}]",
        f"- Minimum sample reached: {minimum_ready}",
        "",
        "## First-passage directional scores",
        "",
        "FAVORABLE_FIRST=+1, ADVERSE_FIRST=-1, SAME_BAR_BOTH/NONE=0.",
        "",
        "| Band | OPTIONS | RANDOM_MATCHED |",
        "|---|---:|---:|",
    ]

    for tag, label in (("0p25", "0.25%"), ("0p5", "0.50%"), ("1", "1.00%")):
        a, b = band_advantages[tag]
        lines.append(f"| {label} | {fmt(a)} | {fmt(b)} |")

    lines += [
        "",
        "## Guardrail",
        "",
        "The known 2026-09-22 wall-116 reaction is exploratory only in this control study.",
        "It cannot contribute to confirmatory evidence because the control design was frozen afterward.",
        "",
        "ROUND_5 overlap with an OPTIONS strike is retained and flagged in the CSV; overlapping rows cannot establish independent options information.",
        "",
        "This test measures wall information content only. It does not by itself authorize a live trading rule.",
    ]

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(status)
    print("anchors", len(anchors), "confirmatory_anchors", len(confirmatory_anchor_ids))
    print("primary_counts", {k: len(v) for k, v in by_source.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
