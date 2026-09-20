#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_full_character_long_v1 as fc1
import sol_structure_library_v1 as lib
import sol_reset_winner_first_v1 as wf1
import sol_sell_structural_character_v2_adaptive as v2

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_SELL_STRUCTURAL_CHARACTER_V4_H4_CONFLUENCE"
YEARS = (2020, 2021, 2022, 2023, 2024)
DEV_YEARS = (2020, 2021, 2022)
CONF_YEARS = (2023, 2024)
H4_ORIGIN_LOOKBACK = 8


def build_h4(x5: pd.DataFrame) -> pd.DataFrame:
    h1 = fc1.build_h1(x5)
    h4 = h1.resample("4h", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        n=("close", "count"),
    )
    return h4[h4.n == 4].drop(columns=["n"]).dropna()


def detect_h4_bearish_zones(x5: pd.DataFrame) -> pd.DataFrame:
    h4 = build_h4(x5)
    idx = h4.index
    op = h4.open.astype(float).to_numpy()
    hi = h4.high.astype(float).to_numpy()
    lo = h4.low.astype(float).to_numpy()
    cl = h4.close.astype(float).to_numpy()

    lows_by_confirm, _ = lib.compute_pivots(hi, lo)
    low_hist = []
    consumed = set()
    rows = []

    for i in range(3, len(h4)):
        low_hist.extend(lows_by_confirm.get(i, []))
        if not low_hist:
            continue

        sl = None
        for x in reversed(low_hist):
            if int(x["pivot_i"]) not in consumed:
                sl = x
                break
        if sl is None:
            continue
        if int(sl["confirm_i"]) >= i:
            continue

        level = float(sl["price"])
        if not (cl[i - 1] >= level and cl[i] < level):
            continue

        consumed.add(int(sl["pivot_i"]))

        start = max(0, i - H4_ORIGIN_LOOKBACK)
        origin_i = None
        for k in range(i - 1, start - 1, -1):
            if cl[k] > op[k]:
                origin_i = int(k)
                break
        if origin_i is None:
            continue

        zlo = float(lo[origin_i])
        zhi = float(hi[origin_i])
        if not (np.isfinite(zlo) and np.isfinite(zhi) and zhi > zlo):
            continue

        bos_close_time = idx[i] + pd.Timedelta(hours=4)
        invalidation_close_time = pd.NaT
        invalidation_i = -1
        for j in range(i + 1, len(h4)):
            if cl[j] > zhi:
                invalidation_i = int(j)
                invalidation_close_time = idx[j] + pd.Timedelta(hours=4)
                break

        rows.append({
            "h4_zone_id": f"H4S-{idx[i]}-{origin_i}",
            "h4_bos_i": int(i),
            "h4_bos_time": idx[i],
            "h4_bos_close_time": bos_close_time,
            "h4_broken_low": level,
            "h4_broken_low_pivot_i": int(sl["pivot_i"]),
            "h4_broken_low_confirm_i": int(sl["confirm_i"]),
            "h4_bos_close": float(cl[i]),
            "h4_bos_extension_pct": float((level - cl[i]) / level * 100.0) if level > 0 else np.nan,
            "h4_origin_i": origin_i,
            "h4_origin_time": idx[origin_i],
            "h4_zone_low": zlo,
            "h4_zone_high": zhi,
            "h4_zone_width_pct": float((zhi - zlo) / zlo * 100.0) if zlo > 0 else np.nan,
            "h4_invalidation_i": invalidation_i,
            "h4_invalidation_close_time": invalidation_close_time,
        })

    return pd.DataFrame(rows)


def annotate_confluence(stage_d: pd.DataFrame, h4zones: pd.DataFrame) -> pd.DataFrame:
    if stage_d.empty:
        return stage_d.copy()

    out = []
    h4z = h4zones.sort_values("h4_bos_close_time").reset_index(drop=True)

    for _, r in stage_d.iterrows():
        rt = pd.Timestamp(r.first_return_time)
        h1lo = float(r.zone_low)
        h1hi = float(r.zone_high)
        h1w = h1hi - h1lo

        eligible = h4z[h4z.h4_bos_close_time <= rt].copy()
        if len(eligible):
            active_mask = eligible.h4_invalidation_close_time.isna() | (eligible.h4_invalidation_close_time > rt)
            eligible = eligible[active_mask]

        best = None
        if len(eligible):
            matches = []
            for _, z in eligible.iterrows():
                ov = min(h1hi, float(z.h4_zone_high)) - max(h1lo, float(z.h4_zone_low))
                if ov > 0:
                    matches.append((pd.Timestamp(z.h4_bos_close_time), ov, z))
            if matches:
                matches.sort(key=lambda x: x[0], reverse=True)
                best = matches[0]

        row = r.to_dict()
        if best is None:
            row.update({
                "h4_confluent": 0,
                "h4_zone_id": "",
                "h4_overlap_width": 0.0,
                "h4_overlap_frac_h1": 0.0,
                "h4_overlap_frac_h4": 0.0,
                "h4_zone_age_hours": np.nan,
                "h4_bos_extension_pct": np.nan,
                "h4_zone_low": np.nan,
                "h4_zone_high": np.nan,
            })
        else:
            _, ov, z = best
            h4w = float(z.h4_zone_high) - float(z.h4_zone_low)
            row.update({
                "h4_confluent": 1,
                "h4_zone_id": str(z.h4_zone_id),
                "h4_overlap_width": float(ov),
                "h4_overlap_frac_h1": float(ov / h1w) if h1w > 0 else np.nan,
                "h4_overlap_frac_h4": float(ov / h4w) if h4w > 0 else np.nan,
                "h4_zone_age_hours": float((rt - pd.Timestamp(z.h4_bos_close_time)).total_seconds() / 3600.0),
                "h4_bos_extension_pct": float(z.h4_bos_extension_pct),
                "h4_zone_low": float(z.h4_zone_low),
                "h4_zone_high": float(z.h4_zone_high),
            })
        out.append(row)

    return pd.DataFrame(out)


def resolved_rate(g: pd.DataFrame) -> float:
    x = g[g.outcome.isin(["CONTINUATION", "INVALIDATED"])].copy()
    if x.empty:
        return np.nan
    return float((x.outcome == "CONTINUATION").mean())


def yearly_table(annotated: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in YEARS:
        base = annotated[(annotated.year == y) & annotated.outcome.isin(["CONTINUATION", "INVALIDATED"])].copy()
        conf = base[base.h4_confluent == 1].copy()
        br = resolved_rate(base)
        cr = resolved_rate(conf)
        rows.append({
            "year": y,
            "baseline_n": len(base),
            "baseline_continuation_rate": br,
            "h4_confluent_n": len(conf),
            "h4_confluent_continuation_rate": cr,
            "lift": cr - br if np.isfinite(cr) and np.isfinite(br) else np.nan,
        })
    return pd.DataFrame(rows)


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    _, stage_a, stage_b = v2.detect_h1_family(x5)
    _, stage_d = v2.resolve_return_and_response(stage_b, x5)
    h4zones = detect_h4_bearish_zones(x5)
    annotated = annotate_confluence(stage_d, h4zones)

    resolved = annotated[annotated.outcome.isin(["CONTINUATION", "INVALIDATED"])].copy()
    dev = resolved[resolved.year.isin(DEV_YEARS)].copy()
    conf = resolved[resolved.year.isin(CONF_YEARS)].copy()
    dev_h4 = dev[dev.h4_confluent == 1].copy()
    conf_h4 = conf[conf.h4_confluent == 1].copy()

    dev_base_rate = resolved_rate(dev)
    dev_h4_rate = resolved_rate(dev_h4)
    conf_base_rate = resolved_rate(conf)
    conf_h4_rate = resolved_rate(conf_h4)
    conf_lift = conf_h4_rate - conf_base_rate if np.isfinite(conf_h4_rate) else np.nan

    yearly = yearly_table(annotated)
    y23 = yearly[yearly.year == 2023].iloc[0]
    y24 = yearly[yearly.year == 2024].iloc[0]

    gates = {
        "confirmation_n_ge_25": len(conf_h4) >= 25,
        "confirmation_rate_ge_45pct": bool(np.isfinite(conf_h4_rate) and conf_h4_rate >= .45),
        "confirmation_lift_ge_10pp": bool(np.isfinite(conf_lift) and conf_lift >= .10),
        "year_2023_above_baseline": bool(
            np.isfinite(y23.h4_confluent_continuation_rate)
            and y23.h4_confluent_continuation_rate > y23.baseline_continuation_rate
        ),
        "year_2024_above_baseline": bool(
            np.isfinite(y24.h4_confluent_continuation_rate)
            and y24.h4_confluent_continuation_rate > y24.baseline_continuation_rate
        ),
    }
    verdict = "H4_STRUCTURAL_CHARACTER" if all(gates.values()) else "REJECTED_AS_DEFINED"

    diagnostics = pd.DataFrame([{
        "coverage": coverage,
        "h4_zone_n": len(h4zones),
        "v2_return_n": len(annotated),
        "resolved_n": len(resolved),
        "h4_confluent_resolved_n": int((resolved.h4_confluent == 1).sum()),
        "development_baseline_n": len(dev),
        "development_baseline_rate": dev_base_rate,
        "development_h4_n": len(dev_h4),
        "development_h4_rate": dev_h4_rate,
        "development_lift": dev_h4_rate - dev_base_rate if np.isfinite(dev_h4_rate) else np.nan,
        "confirmation_baseline_n": len(conf),
        "confirmation_baseline_rate": conf_base_rate,
        "confirmation_h4_n": len(conf_h4),
        "confirmation_h4_rate": conf_h4_rate,
        "confirmation_lift": conf_lift,
        "median_overlap_frac_h1": float(conf_h4.h4_overlap_frac_h1.median()) if len(conf_h4) else np.nan,
        "median_overlap_frac_h4": float(conf_h4.h4_overlap_frac_h4.median()) if len(conf_h4) else np.nan,
        "median_h4_zone_age_hours": float(conf_h4.h4_zone_age_hours.median()) if len(conf_h4) else np.nan,
        **{f"gate_{k}": v for k, v in gates.items()},
        "verdict": verdict,
    }])

    h4zones.to_csv(ROOT / f"{PFX}_H4Zones.csv", index=False)
    annotated.to_csv(ROOT / f"{PFX}_AnnotatedReturns.csv", index=False)
    resolved.to_csv(ROOT / f"{PFX}_Resolved.csv", index=False)
    yearly.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    diagnostics.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

    def pct(v):
        return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"

    s = diagnostics.iloc[0]
    lines = [
        "# SOL SELL Structural Character V4 — H4 Confluence Result",
        "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        "- Parent H1 grammar: frozen V2 adaptive structural family.",
        "- H4 context: causal bearish BOS -> last bullish H4 origin candle -> active supply block.",
        "- No entry, TP, SL, hour, indicator, or execution optimization.",
        "- 2025+ CLOSED.",
        "",
        "## Development description — 2020-2022",
        "",
        f"- V2 resolved baseline: N={len(dev)}, continuation={pct(dev_base_rate)}",
        f"- H4-confluent: N={len(dev_h4)}, continuation={pct(dev_h4_rate)}",
        f"- Lift: **{(dev_h4_rate-dev_base_rate)*100:.2f} pp**" if np.isfinite(dev_h4_rate) else "- Lift: n/a",
        "",
        "## Frozen confirmation — 2023-2024",
        "",
        f"- V2 resolved baseline: N={len(conf)}, continuation={pct(conf_base_rate)}",
        f"- H4-confluent: N={len(conf_h4)}, continuation={pct(conf_h4_rate)}",
        f"- Lift: **{conf_lift*100:.2f} pp**" if np.isfinite(conf_lift) else "- Lift: n/a",
        "",
        "| Year | Baseline N | Baseline continuation | H4-confluent N | H4-confluent continuation | Lift |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for _, y in yearly.iterrows():
        lift = f"{y.lift*100:.2f} pp" if np.isfinite(y.lift) else "n/a"
        lines.append(
            f"| {int(y.year)} | {int(y.baseline_n)} | {pct(y.baseline_continuation_rate)} | "
            f"{int(y.h4_confluent_n)} | {pct(y.h4_confluent_continuation_rate)} | {lift} |"
        )

    lines += [
        "",
        "## H4 overlap anatomy in frozen confirmation",
        "",
        f"- Median H1-zone overlap covered by H4 zone: **{pct(float(s.median_overlap_frac_h1))}**",
        f"- Median H4-zone overlap covered by H1 zone: **{pct(float(s.median_overlap_frac_h4))}**",
        f"- Median H4 zone age at H1 return: **{float(s.median_h4_zone_age_hours):.1f} hours**" if np.isfinite(s.median_h4_zone_age_hours) else "- Median H4 zone age: n/a",
        "",
        "## Frozen gate audit",
        "",
    ]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    lines += [
        "",
        f"**VERDICT: {verdict}**",
        "",
        "## Interpretation",
        "",
        "This test asks whether the H1 bearish return is materially stronger when it lands inside a still-active, independently-created H4 bearish break-block/supply area.",
        "It does not define an entry candle, stop-loss, take-profit, or trade horizon.",
        "",
        "2025_PLUS=CLOSED",
    ]

    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(
        f"VERDICT={verdict}\nCONFIRMATION_N={len(conf_h4)}\n2025_PLUS=CLOSED\n",
        encoding="utf-8",
    )
    print(text)


if __name__ == "__main__":
    main()
