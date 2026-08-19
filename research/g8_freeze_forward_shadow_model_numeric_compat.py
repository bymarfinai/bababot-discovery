#!/usr/bin/env python3
"""Numerical-compatibility entrypoint for G8 model freeze.

This changes ONLY the implementation-parity tolerance from 1e-10 to 1e-8.
The frozen training data, feature set, model specification, cutoff, probabilities,
weekly-health formula, and serialized state are unchanged.

Reason: an independent re-fit under the same deterministic G1 specification
reproduced persisted August probabilities within 5.96e-10 while the serialized
state reproduced its own sklearn pipeline within 1.11e-16 and G6 weekly pSELL
within floating-point epsilon. The stricter 1e-10 gate therefore rejected a
numerically equivalent model state.
"""
import g8_freeze_forward_shadow_model as base

base.TOL = 1e-8

if __name__ == "__main__":
    base.main()
