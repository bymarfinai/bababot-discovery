#!/usr/bin/env python3
"""Command-line entry point for reproducible SOL discovery plumbing."""

from __future__ import annotations

import argparse
import json
import sys

from sol_experiment_harness import (
    ProtocolError,
    finalize_experiment,
    load_registry,
    prepare_experiment,
    run_experiment,
    status_payload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "SOL discovery operational tooling. Scientific hypothesis design and "
            "verdicts remain manual/reasoned."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="validate the frozen SOL registry and invariants")
    sub.add_parser("status", help="show current registered frontier and file state")

    prepare = sub.add_parser(
        "prepare",
        help="create only a preregistration scaffold for the registered next experiment",
    )
    prepare.add_argument("experiment_id")
    prepare.add_argument("--name", required=True)

    run = sub.add_parser("run", help="execute a preregistered experiment implementation")
    run.add_argument("experiment_id")

    finalize = sub.add_parser(
        "finalize",
        help="validate persisted scientific artifacts and write a deterministic manifest",
    )
    finalize.add_argument("experiment_id")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "validate":
            registry = load_registry()
            print(json.dumps({
                "status": "ok",
                "pair": registry["pair"],
                "latest_completed_experiment": registry["latest_completed_experiment"],
                "next_available_experiment": registry["next_available_experiment"],
            }, indent=2))
        elif args.command == "status":
            print(json.dumps(status_payload(), indent=2))
        elif args.command == "prepare":
            path = prepare_experiment(args.experiment_id, args.name)
            print(path)
            print(
                "Scaffold only. Author all scientific fields, then commit the "
                "preregistration before creating experiment.py."
            )
        elif args.command == "run":
            print(run_experiment(args.experiment_id))
        elif args.command == "finalize":
            print(finalize_experiment(args.experiment_id))
        else:
            raise AssertionError(f"Unhandled command: {args.command}")
        return 0
    except ProtocolError as exc:
        print(f"PROTOCOL ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
