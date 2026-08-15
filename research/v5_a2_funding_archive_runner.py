#!/usr/bin/env python3
"""Run frozen V5-A2 with funding sourced from official Binance public archives.

This only replaces the inaccessible REST funding transport. All V5-A2 event,
feature, causality, and descriptive-statistics definitions remain unchanged.
Completed months use monthly archives; an unpublished/open month falls back to
official daily fundingRate archives.
"""
import csv
import io
import zipfile
from datetime import datetime, timezone, timedelta

import v5_a2_derivatives_forensic as base

MONTHLY = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
DAILY = "https://data.binance.vision/data/futures/um/daily/fundingRate"


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


def _parse_zip(raw, symbol, label, start, end):
    z = zipfile.ZipFile(io.BytesIO(raw))
    txt = z.read(z.namelist()[0]).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(txt))
    fields = reader.fieldnames or []
    time_field = next((x for x in ("calc_time", "fundingTime", "funding_time", "timestamp", "time") if x in fields), None)
    rate_field = next((x for x in ("last_funding_rate", "fundingRate", "funding_rate", "rate") if x in fields), None)
    if not time_field or not rate_field:
        raise RuntimeError(f"Unexpected funding archive schema {symbol} {label}: {fields}")
    out = []
    for r in reader:
        t = _parse_time(r.get(time_field))
        rate = base.finite(r.get(rate_field))
        if t is not None and rate is not None and start <= t <= end:
            out.append({"t": t, "rate": rate})
    return out


def _daily_dates_for_month(y, m, start, end):
    d = datetime(y, m, 1, tzinfo=timezone.utc).date()
    if m == 12:
        next_month = datetime(y + 1, 1, 1, tzinfo=timezone.utc).date()
    else:
        next_month = datetime(y, m + 1, 1, tzinfo=timezone.utc).date()
    lo = max(d, start.date())
    hi = min(next_month - timedelta(days=1), end.date())
    cur = lo
    while cur <= hi:
        yield cur
        cur += timedelta(days=1)


def fetch_funding_archive(symbol, start, end):
    out = []
    for y, m in _months(start, end):
        ym = f"{y:04d}-{m:02d}"
        monthly_url = f"{MONTHLY}/{symbol}/{symbol}-fundingRate-{ym}.zip"
        try:
            raw = base.http_bytes(monthly_url, tries=2)
            out.extend(_parse_zip(raw, symbol, ym, start, end))
            continue
        except Exception:
            pass

        # Current/incomplete month may not have a monthly ZIP yet.
        for day in _daily_dates_for_month(y, m, start, end):
            ds = day.isoformat()
            url = f"{DAILY}/{symbol}/{symbol}-fundingRate-{ds}.zip"
            try:
                raw = base.http_bytes(url, tries=2)
                out.extend(_parse_zip(raw, symbol, ds, start, end))
            except Exception:
                # Some dates may legitimately have no archive; do not fabricate.
                continue

    # de-duplicate exact timestamps if monthly/daily overlap ever occurs.
    dedup = {x["t"]: x for x in out}
    rows = sorted(dedup.values(), key=lambda x: x["t"])
    if not rows:
        raise RuntimeError(f"No funding archive rows for {symbol} in requested range")
    return rows


base.fetch_funding = fetch_funding_archive
base.main()
