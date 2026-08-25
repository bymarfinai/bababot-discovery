#!/usr/bin/env python3
from __future__ import annotations

import btc_f85_long_b27do_live_executable_exit_b27dq as dq
import btc_f85_long_b27do_live_executable_exit_b27dq_fix as fx


def main():
    original_parity = dq.dn.dl.baseline_parity

    def checked_baseline_parity(stream):
        df = original_parity(stream)
        if 'pass' not in df.columns or not bool(df['pass'].all()):
            raise AssertionError('B27DK fixed-E20 baseline parity failed')
        # dq.main already records saved-B27DO parity separately; avoid pandas
        # itertuples keyword-column renaming for the literal column name `pass`.
        return df.rename(columns={'pass': 'verified'})

    dq.dn.dl.baseline_parity = checked_baseline_parity
    dq.do.build_hybrid = fx.safe_build_old_hybrid
    dq.build_live_hybrid = fx.safe_build_live_hybrid
    dq.main()


if __name__ == '__main__':
    main()
