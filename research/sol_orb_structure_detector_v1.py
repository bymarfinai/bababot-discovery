"""SOL ORB Structure Detector v1.

Purpose: detect tradeable ORB price-action states, not optimize TP/SL.
Initial lineage: SOL H23 / 23:00-00:00 UTC (06:00-07:00 WIB).
Development-only research. OOS must remain closed.

Input CSV must contain timestamp/open/high/low/close and may contain volume.
One row per 5-minute SOLUSDT candle.

State model:
BUILD_ORB -> WAIT_BREAK -> BREAK_HIGH -> RETEST_HIGH -> ACCEPT_HIGH -> LONG_ENTRY
with FAILED_BREAK_HIGH and NO_SETUP outcomes.

The first 15 minutes of the habitat define ORB. A breakout requires a 5m close
above ORB high. Retest is deliberately detected geometrically rather than with
an optimized percentage: after breakout, a candle trades back to ORB high or
inside the ORB while still closing at/above the ORB midpoint. Acceptance is the
first subsequent close back above ORB high. LONG_ENTRY is next candle open.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
import pandas as pd

ORB_BARS = 3              # 15m on 5m data
MAX_RETEST_BARS = 6       # 30m observation window; fixed v1 hypothesis

@dataclass
class Detection:
    session: str
    orb_high: float
    orb_low: float
    orb_mid: float
    orb_range_pct: float
    breakout_time: str | None
    retest_time: str | None
    acceptance_time: str | None
    entry_time: str | None
    entry_price: float | None
    structure: str
    signal: str


def _ts(df: pd.DataFrame) -> pd.Series:
    for c in ("timestamp", "datetime", "time", "open_time"):
        if c in df.columns:
            return pd.to_datetime(df[c], utc=True)
    raise ValueError("CSV needs timestamp/datetime/time/open_time")


def detect_session(day: pd.DataFrame) -> Detection | None:
    day = day.sort_values("timestamp").reset_index(drop=True)
    if len(day) < ORB_BARS + 2:
        return None
    orb = day.iloc[:ORB_BARS]
    oh, ol = float(orb.high.max()), float(orb.low.min())
    om = (oh + ol) / 2.0
    op = float(orb.iloc[0].open)
    rp = (oh - ol) / op * 100.0
    base = dict(session=str(day.iloc[0].timestamp.date()), orb_high=oh,
                orb_low=ol, orb_mid=om, orb_range_pct=rp)

    after = day.iloc[ORB_BARS:].reset_index(drop=True)
    breaks = after.index[after.close > oh].tolist()
    if not breaks:
        return Detection(**base, breakout_time=None, retest_time=None,
                         acceptance_time=None, entry_time=None, entry_price=None,
                         structure="NO_BREAK_HIGH", signal="NONE")

    bi = breaks[0]
    bt = after.iloc[bi].timestamp
    window = after.iloc[bi + 1: bi + 1 + MAX_RETEST_BARS]
    # A meaningful retest must touch the boundary/inside the ORB, while avoiding
    # immediate deep failure below the midpoint.
    candidates = window[(window.low <= oh) & (window.close >= om)]
    if candidates.empty:
        failed = not window.empty and (window.close < om).any()
        return Detection(**base, breakout_time=str(bt), retest_time=None,
                         acceptance_time=None, entry_time=None, entry_price=None,
                         structure="FAILED_BREAK_HIGH" if failed else "BREAK_HIGH_NO_RETEST",
                         signal="NONE")

    ri = candidates.index[0]
    rt = after.loc[ri].timestamp
    # Acceptance cannot be the same candle as the retest: require a later close
    # above the boundary so the sequence is observable without look-ahead.
    later = after.loc[ri + 1: bi + MAX_RETEST_BARS]
    accepts = later.index[later.close > oh].tolist()
    if not accepts:
        return Detection(**base, breakout_time=str(bt), retest_time=str(rt),
                         acceptance_time=None, entry_time=None, entry_price=None,
                         structure="RETEST_NO_ACCEPT", signal="NONE")
    ai = accepts[0]
    at = after.loc[ai].timestamp
    if ai + 1 >= len(after):
        return Detection(**base, breakout_time=str(bt), retest_time=str(rt),
                         acceptance_time=str(at), entry_time=None, entry_price=None,
                         structure="ACCEPT_HIGH_NO_NEXT_BAR", signal="NONE")
    entry = after.loc[ai + 1]
    return Detection(**base, breakout_time=str(bt), retest_time=str(rt),
                     acceptance_time=str(at), entry_time=str(entry.timestamp),
                     entry_price=float(entry.open),
                     structure="BREAK_RETEST_ACCEPT_LONG", signal="LONG")


def run(path: Path, hour: int = 23) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    df["timestamp"] = _ts(df)
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="raise")
    habitat = df[df.timestamp.dt.hour == hour].copy()
    out = []
    for _, g in habitat.groupby(habitat.timestamp.dt.date):
        d = detect_session(g)
        if d:
            out.append(asdict(d))
    return pd.DataFrame(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--hour", type=int, default=23)
    p.add_argument("--out", type=Path, default=Path("SOL_ORB_STRUCTURE_DETECTOR_V1.csv"))
    a = p.parse_args()
    result = run(a.csv, a.hour)
    result.to_csv(a.out, index=False)
    print(result.structure.value_counts(dropna=False).to_string())
    print(f"sessions={len(result)} long_signals={(result.signal == 'LONG').sum() if len(result) else 0}")
    print(f"saved={a.out}")

if __name__ == "__main__":
    main()
