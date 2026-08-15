#!/usr/bin/env python3
"""Run frozen V5-A2 with funding sourced from official Binance public archives.

This only replaces the inaccessible REST funding transport. All V5-A2 event,
feature, causality, and descriptive-statistics definitions remain unchanged.
"""
import csv
import io
import zipfile
from datetime import datetime, timezone

import v5_a2_derivatives_forensic as base

FUNDING_DATA = "https://data.binance.vision/data/futures/um/monthly/fundingRate"


def _months(start, end):
    y, m = start.year, start.month
    ey, em = end.year, end.month
    out = []
    while (y, m) <= (ey, em):
        out.append((y, m))
        if m == 12:
            y += 1; m = 1
        else:
            m += 1
    return out


def _parse_time(v):
    if v is None:
        return None
    s = str(v).strip()
    try:
        x = float(s)
        if x > 1e12:
            return datetime.fromtimestamp(x / 1000.0, tz=timezone.utc)
        if x > 1e9:
            return datetime.fromtimestamp(x, tz=timezone.utc)
    except Exception:
        pass
    try:
        z = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if z.tzinfo is None:
            z = z.replace(tzinfo=timezone.utc)
        return z.astimezone(timezone.utc)
    except Exception:
        return None


def fetch_funding_archive(symbol, start, end):
    out = []
    for y, m in _months(start, end):
        ym = f"{y:04d}-{m:02d}"
        url = f"{FUNDING_DATA}/{symbol}/{symbol}-fundingRate-{ym}.zip"
        raw = base.http_bytes(url)
        z = zipfile.ZipFile(io.BytesIO(raw))
        txt = z.read(z.namelist()[0]).decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(txt))
        fields = reader.fieldnames or []
        time_field = next((x for x in ("calc_time", "fundingTime", "funding_time", "timestamp", "time") if x in fields), None)
        rate_field = next((x for x in ("last_funding_rate", "fundingRate", "funding_rate", "rate") if x in fields), None)
        if not time_field or not rate_field:
            raise RuntimeError(f"Unexpected funding archive schema {symbol} {ym}: {fields}")
        for r in reader:
            t = _parse_time(r.get(time_field))
            rate = base.finite(r.get(rate_field))
            if t is not None and rate is not None and start <= t <= end:
                out.append({"t": t, "rate": rate})
    out.sort(key=lambda x: x["t"])
    return out


base.fetch_funding = fetch_funding_archive
base.main()
