#!/usr/bin/env python3
"""Technical wrapper for E16A.

The preregistered design is unchanged. The original E16A runner prepared the E12
cache before installing the expanded timing grid, so newly preregistered horizons
were absent from the cache. This wrapper only ensures prep() sees the full
preregistered LOOKBACKS/HOLDS superset, then delegates all baseline assertions,
search logic, gates, ranking, diagnostics, and outputs to the frozen runner.
"""
from __future__ import annotations

import eth_e16a_long_02_03wib_rediscovery as study

_original_prep = study.e12.prep


def prep_preregistered_superset(x5):
    study.e12.LOOKBACKS = study.LOOKBACKS
    study.e12.HOLDS = study.HOLDS
    return _original_prep(x5)


study.e12.prep = prep_preregistered_superset

if __name__ == "__main__":
    study.main()
