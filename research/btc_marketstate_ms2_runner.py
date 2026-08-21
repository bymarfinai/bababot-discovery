#!/usr/bin/env python3
import pandas as pd
import btc_marketstate_ms2_positioning as ms2

_orig = pd.merge_asof

def _merge_asof(left, right, *args, **kwargs):
    on = kwargs.get('on')
    if on and on in left.columns and on in right.columns:
        left = left.copy(); right = right.copy()
        left[on] = pd.to_datetime(left[on], utc=True).astype('datetime64[ns, UTC]')
        right[on] = pd.to_datetime(right[on], utc=True).astype('datetime64[ns, UTC]')
    return _orig(left, right, *args, **kwargs)

ms2.pd.merge_asof = _merge_asof

if __name__ == '__main__':
    ms2.main()
