#!/usr/bin/env python3
from __future__ import annotations

import io
import zipfile

import pandas as pd
import requests

import sol_orb_reference_fidelity_v1 as detector


def fetch_one_with_volume(url: str):
    r = requests.get(
        url,
        timeout=90,
        headers={'User-Agent': 'bababot-sol-orb-reference-fidelity-v1/1.0'},
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith('.csv')]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh,
                header=None,
                usecols=[0, 1, 2, 3, 4, 5],
                names=['ts', 'open', 'high', 'low', 'close', 'volume'],
            )


def main():
    # The canonical loader intentionally keeps only OHLC.  This experiment
    # needs actual Binance base-asset volume for the literal VWAP condition,
    # so override only the downloader used by this isolated runner.  The
    # underlying time/coverage/partition logic remains unchanged.
    detector.base.fetch_one = fetch_one_with_volume
    detector.main()


if __name__ == '__main__':
    main()
