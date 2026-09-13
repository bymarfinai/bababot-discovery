#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import sol_economic_first_h00_long_07_08wib_character as engine

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_H23_STRUCT_V1"
OUT_OCC = ROOT / f"{PFX}_Occurrences.csv"
OUT_SUM = ROOT / f"{PFX}_FeatureSummary.csv"
OUT_SUB = ROOT / f"{PFX}_SubgroupConsistency.csv"
OUT_MD = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = (1380, 1395, 1410, 1425)
LOOKBACK = 15
HOLD = 120
RULE = "DRIVE_DOWN__STR_B80_100"
NOTIONAL = 500.0
FEE = 0.75
OBS_BARS = 6  # +15m through +45m, six completed 5m bars
RANGE_BARS = 3  # first 15m after frozen parent activation
YEARS = (2022, 2023, 2024)
FEATURES = (
    "break_high",
    "high_break_first",
    "break_retest_hold",
    "sweep_low_before_high_break",
    "reclaim_low_then_high_break",
    "failed_high_break",
    "higher_low_after_high_break",
)


def structural_events(x5: pd.DataFrame, entry_ix: int) -> dict | None:
    end_needed = entry_ix + RANGE_BARS + OBS_BARS
    if entry_ix < 0 or end_needed > len(x5):
        return None
    # Require an unbroken 5m path through the observation window.
    idx = x5.index[entry_ix:end_needed]
    if len(idx) != RANGE_BARS + OBS_BARS:
        return None
    expected = pd.date_range(idx[0], periods=len(idx), freq="5min", tz="UTC")
    if not idx.equals(expected):
        return None

    rr = x5.iloc[entry_ix:entry_ix + RANGE_BARS]
    obs = x5.iloc[entry_ix + RANGE_BARS:end_needed]
    orh = float(rr.high.max())
    orl = float(rr.low.min())
    width = orh - orl
    if not width > 0:
        return None

    high_break_pos = None
    low_break_pos = None
    for j, (_, bar) in enumerate(obs.iterrows()):
        cl = float(bar.close)
        if high_break_pos is None and cl > orh:
            high_break_pos = j
        if low_break_pos is None and cl < orl:
            low_break_pos = j

    break_high = high_break_pos is not None
    break_low = low_break_pos is not None
    high_break_first = bool(
        break_high and (not break_low or int(high_break_pos) < int(low_break_pos))
    )
    low_break_first = bool(
        break_low and (not break_high or int(low_break_pos) < int(high_break_pos))
    )

    sweep_pos = None
    reclaim_pos = None
    if break_high:
        for j in range(int(high_break_pos)):
            bar = obs.iloc[j]
            # A sweep is wick-only relative to the lower boundary; a prior strict
            # close below ORL is a true low break and disqualifies this sequence.
            if float(bar.close) < orl:
                break
            if sweep_pos is None and float(bar.low) < orl:
                sweep_pos = j
            if sweep_pos is not None and j >= sweep_pos and float(bar.close) >= orl:
                reclaim_pos = j
        if low_break_pos is not None and int(low_break_pos) < int(high_break_pos):
            sweep_pos = None
            reclaim_pos = None

    sweep_low_before_high_break = sweep_pos is not None
    reclaim_low_then_high_break = bool(
        sweep_pos is not None and reclaim_pos is not None and int(reclaim_pos) < int(high_break_pos)
    )

    retest_pos = None
    hold_pos = None
    failed_high_break = False
    higher_low_after_high_break = False
    breakout_disp = np.nan
    retest_depth = np.nan
    if break_high:
        hb = int(high_break_pos)
        breakout_disp = (float(obs.iloc[hb].close) - orh) / width
        after = obs.iloc[hb + 1:]
        if len(after):
            higher_low_after_high_break = bool(float(after.low.min()) > orl)
        for j in range(hb + 1, len(obs)):
            bar = obs.iloc[j]
            if retest_pos is None and float(bar.low) <= orh and float(bar.close) >= orh:
                retest_pos = j
                retest_depth = max(0.0, (orh - float(bar.low)) / width)
                if j + 1 < len(obs) and float(obs.iloc[j + 1].close) >= orh:
                    hold_pos = j + 1
                    break
            if float(bar.close) < orh:
                failed_high_break = True
                # Keep searching only to record retest if it later occurs; failure
                # remains true because the breakout lost the boundary first.
        if hold_pos is not None:
            # Failed means boundary was lost before the valid hold completed.
            failed_high_break = any(
                float(obs.iloc[j].close) < orh for j in range(hb + 1, int(hold_pos) + 1)
            )

    break_retest_hold = bool(break_high and retest_pos is not None and hold_pos is not None and not failed_high_break)
    minutes_to_high_break = np.nan if not break_high else float((int(high_break_pos) + 1) * 5 + 15)

    return {
        "response_high": orh,
        "response_low": orl,
        "response_width_pct": width / float(rr.iloc[0].open),
        "break_high": bool(break_high),
        "break_low": bool(break_low),
        "high_break_first": bool(high_break_first),
        "low_break_first": bool(low_break_first),
        "sweep_low_before_high_break": bool(sweep_low_before_high_break),
        "reclaim_low_then_high_break": bool(reclaim_low_then_high_break),
        "retest_after_high_break": bool(retest_pos is not None),
        "hold_after_retest": bool(hold_pos is not None and not failed_high_break),
        "break_retest_hold": bool(break_retest_hold),
        "failed_high_break": bool(failed_high_break),
        "higher_low_after_high_break": bool(higher_low_after_high_break),
        "minutes_to_high_break": minutes_to_high_break,
        "breakout_displacement_rr": breakout_disp,
        "retest_depth_rr": retest_depth,
    }


def selected_occurrences(x5: pd.DataFrame) -> pd.DataFrame:
    part_start, part_end = engine.base.PARTS["development"]
    rows = []
    for clock in CLOCKS:
        frame = engine.state_frame(x5, clock, LOOKBACK)
        masks = engine.masks_for_frame(frame)
        exit_ts, valid, returns = engine.hold_returns(x5, frame, HOLD)
        entry_ts = pd.DatetimeIndex(frame.entry_ts)
        pre_ts = pd.DatetimeIndex(frame.pre_ts)
        selected = (
            valid
            & (pre_ts >= part_start)
            & (entry_ts >= part_start)
            & (exit_ts < part_end)
            & masks[RULE]
        )
        for pos in np.flatnonzero(selected):
            net = NOTIONAL * float(returns[pos]) - FEE
            entry_ix = int(frame.entry_ix.iloc[pos])
            ev = structural_events(x5, entry_ix)
            if ev is None:
                continue
            ts = pd.Timestamp(entry_ts[pos])
            rows.append({
                "entry_ts": ts,
                "year": int(ts.year),
                "clock": int(clock),
                "anchor_utc": f"{clock // 60:02d}:{clock % 60:02d}",
                "entry_ix": entry_ix,
                "parent_return": float(returns[pos]),
                "parent_net": net,
                "win": bool(net > 0),
                **ev,
            })
    out = pd.DataFrame(rows).sort_values(["entry_ts", "clock"]).reset_index(drop=True)
    return out


def odds_ratio_haldane(event: pd.Series, win: pd.Series) -> float:
    e = event.astype(bool).to_numpy()
    w = win.astype(bool).to_numpy()
    a = int(np.sum(e & w))
    b = int(np.sum((~e) & w))
    c = int(np.sum(e & (~w)))
    d = int(np.sum((~e) & (~w)))
    return float(((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5)))


def prevalence_delta(q: pd.DataFrame, feature: str) -> tuple[float, float, float] | None:
    wins = q[q.win]
    losses = q[~q.win]
    if len(wins) == 0 or len(losses) == 0:
        return None
    pw = float(wins[feature].astype(bool).mean())
    pl = float(losses[feature].astype(bool).mean())
    return pw, pl, pw - pl


def feature_summary(occ: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    subrows = []
    n_win = int(occ.win.sum())
    n_loss = int((~occ.win).sum())
    for feature in FEATURES:
        pooled = prevalence_delta(occ, feature)
        if pooled is None:
            continue
        pw, pl, delta = pooled
        oratio = odds_ratio_haldane(occ[feature], occ.win)
        sign = 1 if delta > 0 else (-1 if delta < 0 else 0)

        anchor_same = 0
        anchor_eval = 0
        for clock in CLOCKS:
            q = occ[occ.clock == clock]
            z = prevalence_delta(q, feature)
            if z is None:
                continue
            aw, al, ad = z
            anchor_eval += 1
            same = bool(sign != 0 and np.sign(ad) == sign)
            anchor_same += int(same)
            subrows.append({
                "feature": feature, "dimension": "anchor", "group": str(clock),
                "n": len(q), "wins": int(q.win.sum()), "losses": int((~q.win).sum()),
                "win_prevalence": aw, "loss_prevalence": al, "delta": ad, "same_direction": same,
            })

        year_same = 0
        year_eval = 0
        for year in YEARS:
            q = occ[occ.year == year]
            z = prevalence_delta(q, feature)
            if z is None:
                continue
            yw, yl, yd = z
            year_eval += 1
            same = bool(sign != 0 and np.sign(yd) == sign)
            year_same += int(same)
            subrows.append({
                "feature": feature, "dimension": "year", "group": str(year),
                "n": len(q), "wins": int(q.win.sum()), "losses": int((~q.win).sum()),
                "win_prevalence": yw, "loss_prevalence": yl, "delta": yd, "same_direction": same,
            })

        gate = bool(
            len(occ) >= 160
            and n_win >= 40
            and n_loss >= 40
            and abs(delta) >= 0.15
            and (oratio >= 1.50 or oratio <= 0.67)
            and anchor_eval == 4
            and anchor_same >= 3
            and year_eval == 3
            and year_same == 3
        )
        rows.append({
            "feature": feature,
            "n": len(occ),
            "wins": n_win,
            "losses": n_loss,
            "win_prevalence": pw,
            "loss_prevalence": pl,
            "delta": delta,
            "delta_pp": 100.0 * delta,
            "odds_ratio_haldane": oratio,
            "anchor_same": anchor_same,
            "anchor_evaluable": anchor_eval,
            "year_same": year_same,
            "year_evaluable": year_eval,
            "structural_gate": gate,
        })
    summary = pd.DataFrame(rows).sort_values("delta_pp", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)
    subs = pd.DataFrame(subrows)
    return summary, subs


def pct(x: float) -> str:
    return f"{100.0 * float(x):.1f}%"


def render(occ: pd.DataFrame, summary: pd.DataFrame, coverage: float) -> str:
    passed = summary[summary.structural_gate]
    status = "STRUCTURAL_DISCRIMINATOR_FOUND_V1" if len(passed) else "NO_REPEATABLE_EARLY_ORB_LIKE_DISCRIMINATOR_V1"
    lines = [
        "# SOL-H23-STRUCT-V1 Result",
        "",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.",
        "Discovery partition: **Development 2022–2024 only**. Reference/OOS and August were not evaluated.",
        f"Frozen parent: **{RULE} / LB{LOOKBACK} / hold{HOLD}m**, four H23 quarter-hour anchors.",
        "Structural observation: first 15m response range, then fixed +15..+45m event window; parent outcome remains +120m.",
        "",
        "## Parent cohort reproduced",
        "",
        f"N **{len(occ)}**, WIN **{int(occ.win.sum())}**, LOSS **{int((~occ.win).sum())}**, WR **{pct(occ.win.mean())}**.",
        "",
        "## Frozen structural grammar",
        "",
        "| Feature | WIN prev | LOSS prev | Delta pp | Odds ratio | Anchors same | Years same | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in summary.iterrows():
        lines.append(
            f"| {r.feature} | {pct(r.win_prevalence)} | {pct(r.loss_prevalence)} | {r.delta_pp:+.1f} | "
            f"{r.odds_ratio_haldane:.2f} | {int(r.anchor_same)}/{int(r.anchor_evaluable)} | "
            f"{int(r.year_same)}/{int(r.year_evaluable)} | {'PASS' if r.structural_gate else 'NO'} |"
        )
    lines += ["", "## Verdict", ""]
    if len(passed):
        names = ", ".join(f"`{x}`" for x in passed.feature.tolist())
        lines += [
            f"**{status}**",
            "",
            f"Preregistered structural discriminators: {names}.",
            "These are discovery findings only. They may be promoted only to a new preregistered causal/delayed-entry execution experiment; they are not live rules.",
        ]
    else:
        lines += [
            f"**{status}**",
            "",
            "No frozen early ORB-like sequence met the V1 effect-size plus anchor/year consistency gate. Do not retune this experiment after inspection.",
        ]
    lines += [
        "",
        "Important: the 15m range here is a **post-activation response range**, not a claim that SOL follows a conventional session ORB. V1 asks whether an early breakout/retest sequence distinguishes the already-frozen H23 winners from losers.",
        "",
        "Research/shadow only.",
    ]
    OUT_STATUS.write_text(status + "\n")
    return "\n".join(lines) + "\n"


def main() -> None:
    x5, coverage = engine.base.load5("SOLUSDT")
    occ = selected_occurrences(x5)
    if len(occ) != 306:
        raise AssertionError(f"parent cohort reproduction failed: expected 306, got {len(occ)}")
    if int(occ.win.sum()) != 184:
        raise AssertionError(f"parent winner count reproduction failed: expected 184, got {int(occ.win.sum())}")
    summary, subs = feature_summary(occ)
    occ.to_csv(OUT_OCC, index=False)
    summary.to_csv(OUT_SUM, index=False)
    subs.to_csv(OUT_SUB, index=False)
    result = render(occ, summary, coverage)
    OUT_MD.write_text(result)
    print(result)


if __name__ == "__main__":
    main()
