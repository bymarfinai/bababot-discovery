#!/usr/bin/env python3
from __future__ import annotations

import io
import zipfile

import numpy as np
import pandas as pd
import requests

import bnb_b29_b2s_prospective_shadow as core

BASE = "https://data.binance.vision/data/futures/um/daily/klines"


def fetch_day(day: pd.Timestamp) -> pd.DataFrame | None:
    ds = day.strftime("%Y-%m-%d")
    url = f"{BASE}/{core.SYMBOL}/5m/{core.SYMBOL}-5m-{ds}.zip"
    r = requests.get(url, timeout=60, headers={"User-Agent": "bababot-b29-b2s-shadow-vision/1.0"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh,
                header=None,
                usecols=[0, 1, 2, 3, 4],
                names=["ts", "open", "high", "low", "close"],
            )


def fetch_recent_5m_vision() -> tuple[pd.DataFrame, dict]:
    safe_now = core.utcnow_floor_safe()
    frames = []
    missing_days = []
    d = core.FETCH_START.normalize()
    last_day = safe_now.normalize()
    while d <= last_day:
        z = fetch_day(d)
        if z is None or not len(z):
            missing_days.append(str(d.date()))
        else:
            frames.append(z)
        d += pd.Timedelta(days=1)

    if not frames:
        raise RuntimeError("no prospective Binance Vision BNBUSDT 5m files available")

    q = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(q["ts"], errors="coerce")
    # Binance Vision has used both millisecond and microsecond timestamps historically.
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    q["ts"] = pd.to_datetime(t, unit="ms", utc=True, errors="coerce")
    for c in ["open", "high", "low", "close"]:
        q[c] = pd.to_numeric(q[c], errors="coerce")
    q = q.dropna(subset=["ts", "open", "high", "low", "close"])
    q = q.drop_duplicates("ts").sort_values("ts")
    q = q[(q["ts"] >= core.FETCH_START) & ((q["ts"] + core.BAR) <= safe_now)]
    x = q.set_index("ts")[["open", "high", "low", "close"]].astype(float)

    if x.empty or x.index.has_duplicates or not x.index.is_monotonic_increasing:
        raise RuntimeError("prospective Binance Vision raw index invalid")

    diffs = x.index.to_series().diff().dropna()
    gaps = diffs[diffs != core.BAR]
    expected = int((x.index[-1] - x.index[0]) / core.BAR) + 1
    coverage = len(x) / expected
    diag = {
        "source": "Binance Vision USD-M Futures daily 5m",
        "rows": int(len(x)),
        "first_open": x.index[0].isoformat(),
        "last_open": x.index[-1].isoformat(),
        "last_close": (x.index[-1] + core.BAR).isoformat(),
        "coverage": float(coverage),
        "gap_count": int(len(gaps)),
        "safe_now": safe_now.isoformat(),
        "missing_daily_files": missing_days,
    }
    if coverage < 0.99999 or len(gaps) != 0:
        raise RuntimeError(f"prospective Binance Vision continuity failure: {diag}")
    return x, diag


def main():
    # Tooling-only feed substitution. Scientific rules/checkpoint remain in core.
    core.fetch_recent_5m = fetch_recent_5m_vision
    core.main()


if __name__ == "__main__":
    main()
