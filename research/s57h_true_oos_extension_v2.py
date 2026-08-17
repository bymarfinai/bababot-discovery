#!/usr/bin/env python3
"""S5.7H dtype/data-source-safe runner.

Only the August-2026 funding data source is changed versus s57h_true_oos_extension:
Binance Futures public funding-history API is used because Binance Vision has no
published daily fundingRate archive at the attempted path. Trading rules, OOS
window, completed kline cutoff, fees, notional, funding formula, and frozen
NO_BULL_TOP_Q_30 management are unchanged.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import requests

import s50_saturday_parent_forensics as s50
import s57h_true_oos_extension as h


def load_recent_funding_api() -> pd.DataFrame:
    start = int(pd.Timestamp("2026-08-01 00:00:00", tz="UTC").timestamp() * 1000)
    end = int(pd.Timestamp("2026-08-17 00:00:00", tz="UTC").timestamp() * 1000) - 1
    params = {"symbol": h.SYMBOL, "startTime": start, "endTime": end, "limit": 1000}
    endpoints = [
        "https://fapi.binance.com/fapi/v1/fundingRate",
        "https://www.binance.com/fapi/v1/fundingRate",
    ]
    errors = []
    for url in endpoints:
        try:
            r = requests.get(url, params=params, timeout=60, headers={"User-Agent": "bababot-discovery-s57h/1.0"})
            if r.status_code != 200:
                errors.append(f"{url}: HTTP {r.status_code} {r.text[:200]}")
                continue
            data = r.json()
            if not isinstance(data, list) or not data:
                errors.append(f"{url}: empty/non-list response")
                continue
            df = pd.DataFrame(data)
            if "fundingTime" not in df.columns or "fundingRate" not in df.columns:
                errors.append(f"{url}: unexpected columns {df.columns.tolist()}")
                continue
            out = pd.DataFrame({
                "ts": pd.to_datetime(pd.to_numeric(df["fundingTime"], errors="coerce"), unit="ms", utc=True),
                "rate": pd.to_numeric(df["fundingRate"], errors="coerce"),
            }).dropna()
            out = out[(out.ts >= pd.Timestamp("2026-08-01", tz="UTC")) & (out.ts < pd.Timestamp("2026-08-17", tz="UTC"))]
            if len(out) < 40:  # normally 3 settlements/day -> about 48 in 16 days
                errors.append(f"{url}: suspiciously few funding rows {len(out)}")
                continue
            return out.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
        except Exception as e:
            errors.append(f"{url}: {type(e).__name__}: {e}")
    raise RuntimeError("unable to obtain August funding history: " + " | ".join(errors))


def load_extended_v2():
    hist_k = s50.load_klines().reset_index(drop=True)[
        ["ts", "open", "high", "low", "close", "quote_volume", "taker_buy_quote"]
    ]
    daily_k = [h.parse_kline_zip(d) for d in h.days(h.DAILY_START, h.DAILY_END)]
    k = pd.concat([hist_k, *daily_k], ignore_index=True)
    k = k.dropna(subset=["ts", "open", "high", "low", "close"]).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    k["ema20"] = k["close"].ewm(span=20, adjust=False).mean()
    k["ema7"] = k["close"].ewm(span=7, adjust=False).mean()
    k["taker_imb"] = np.where(k["quote_volume"] > 0, 2 * k["taker_buy_quote"] / k["quote_volume"] - 1.0, np.nan)
    k = k.set_index("ts", drop=False)

    hist_f = s50.load_funding()
    recent_f = load_recent_funding_api()
    f = pd.concat([hist_f, recent_f], ignore_index=True).dropna().drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    return k, f


if __name__ == "__main__":
    h.load_extended = load_extended_v2
    h.main()
