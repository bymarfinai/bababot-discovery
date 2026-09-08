#!/usr/bin/env python3
"""Reusable, pair-native experiment plumbing for the SOL discovery lineage.

Automation here owns reproducible mechanics only. It never chooses hypotheses,
features, thresholds, interventions, or scientific verdicts.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict

EXPERIMENT_ID_RE = re.compile(r"^A([1-9][0-9]*)$")

EXPECTED_EXECUTION_PARENT = {
    "range": "R360",
    "hour": "15UTC",
    "entry": "E0_RESTING_H",
    "target": "E40",
}
EXPECTED_PARTITIONS = {
    "Development": {"central_losses": 357, "l0": 37},
    "External Validation": {"central_losses": 166, "l0": 13},
    "Reference Validation": {"central_losses": 187, "l0": 26},
}
EXPECTED_TOTALS = {"central_losses_total": 710, "l0_total": 76}


class ProtocolError(RuntimeError):
    """Raised when a frozen scientific or operational invariant is violated."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def registry_path(root: Path | None = None) -> Path:
    root = root or repo_root()
    return root / "research" / "sol_experiment_registry.yaml"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProtocolError(f"Required file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProtocolError(
            f"{path} must remain JSON-compatible YAML; parse failed: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ProtocolError(f"{path} must contain a top-level object")
    return data


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "UNKNOWN"


def experiment_number(experiment_id: str) -> int:
    match = EXPERIMENT_ID_RE.fullmatch(experiment_id)
    if not match:
        raise ProtocolError(
            f"Invalid experiment id {experiment_id!r}; expected A followed by a positive integer"
        )
    return int(match.group(1))


def load_registry(root: Path | None = None) -> Dict[str, Any]:
    root = root or repo_root()
    registry = _load_json(registry_path(root))
    validate_registry(registry)
    return registry


def validate_registry(registry: Dict[str, Any]) -> None:
    if registry.get("schema_version") != 1:
        raise ProtocolError("Unsupported SOL registry schema_version")
    if registry.get("pair") != "SOL":
        raise ProtocolError("Registry pair must remain SOL")
    if registry.get("auto_advance_next_experiment") is not False:
        raise ProtocolError("Automatic experiment advancement must remain disabled")
    if registry.get("execution_parent") != EXPECTED_EXECUTION_PARENT:
        raise ProtocolError(
            "Frozen SOL execution parent changed: expected "
            f"{EXPECTED_EXECUTION_PARENT}, got {registry.get('execution_parent')}"
        )

    taxonomy = registry.get("loss_taxonomy", {})
    for key, expected in EXPECTED_TOTALS.items():
        if taxonomy.get(key) != expected:
            raise ProtocolError(
                f"Frozen taxonomy invariant {key} changed: expected {expected}, "
                f"got {taxonomy.get(key)}"
            )
    if taxonomy.get("l0_label") != "NEVER_BREAK_REFERENCE_INVALIDATION":
        raise ProtocolError("Frozen L0 label changed")
    if taxonomy.get("l0_mechanism") != "M0":
        raise ProtocolError("Frozen L0/M0 identity changed")

    partitions = registry.get("partitions")
    if not isinstance(partitions, dict):
        raise ProtocolError("Registry partitions must be an object")
    for name, expected in EXPECTED_PARTITIONS.items():
        actual = partitions.get(name)
        if not isinstance(actual, dict):
            raise ProtocolError(f"Missing frozen partition: {name}")
        for metric, expected_value in expected.items():
            if actual.get(metric) != expected_value:
                raise ProtocolError(
                    f"{name}.{metric} changed: expected {expected_value}, "
                    f"got {actual.get(metric)}"
                )

    if partitions["Development"].get("tuning_allowed") is not True:
        raise ProtocolError("Development must be the only tuning-eligible partition")
    for name in ("External Validation", "Reference Validation"):
        if partitions[name].get("tuning_allowed") is not False:
            raise ProtocolError(f"{name} must never be tuning-eligible")

    if sum(partitions[n]["central_losses"] for n in EXPECTED_PARTITIONS) != 710:
        raise ProtocolError("Partition CENTRAL loss counts do not reconcile to 710")
    if sum(partitions[n]["l0"] for n in EXPECTED_PARTITIONS) != 76:
        raise ProtocolError("Partition L0 counts do not reconcile to 76")

    protocol = registry.get("protocol", {})
    if protocol.get("post_hoc_retuning") != "prohibited":
        raise ProtocolError("Post-hoc retuning must remain prohibited")
    if protocol.get("validation_tuning") != "prohibited":
        raise ProtocolError("Validation tuning must remain prohibited")
    if protocol.get("descriptive_result_implies_executable_intervention") is not False:
        raise ProtocolError(
            "A descriptive result must never automatically imply an executable intervention"
        )

    latest = registry.get("latest_completed_experiment")
    next_id = registry.get("next_available_experiment")
    if experiment_number(next_id) != experiment_number(latest) + 1:
        raise ProtocolError(
            f"Registry next id must be exactly one after latest completed: {latest} -> {next_id}"
        )


def experiment_paths(experiment_id: str, root: Path | None = None) -> Dict[str, Path]:
    experiment_number(experiment_id)
    root = root or repo_root()
    base = root / "research" / "experiments" / experiment_id
    results = root / "research" / "results" / experiment_id
    return {
        "base": base,
        "prereg": base / "prereg.yaml",
        "implementation": base / "experiment.py",
        "results": results,
        "result_envelope": results / "result_envelope.json",
        "run_manifest": results / "run_manifest.json",
    }


def preregistration_scaffold(
    experiment_id: str, name: str, registry: Dict[str, Any]
) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "name": name,
        "pair": "SOL",
        "inherits": {
            "execution_parent": copy.deepcopy(registry["execution_parent"]),
            "loss_taxonomy": {
                "central_losses_total": registry["loss_taxonomy"]["central_losses_total"],
                "l0_label": registry["loss_taxonomy"]["l0_label"],
                "l0_mechanism": registry["loss_taxonomy"]["l0_mechanism"],
                "l0_total": registry["loss_taxonomy"]["l0_total"],
            },
            "partitions": {
                partition: {
                    "central_losses": values["central_losses"],
                    "l0": values["l0"],
                }
                for partition, values in registry["partitions"].items()
            },
        },
        "scientific_question": "TODO_BEFORE_PREREG_COMMIT",
        "hypothesis": "TODO_BEFORE_PREREG_COMMIT",
        "execution_mode": "descriptive_only",
        "finite_feature_set": [],
        "fixed_snapshots": [],
        "support_rules": {},
        "success_criteria": {},
        "retuning": "prohibited",
        "notes": [
            "Automation created this scaffold only; scientific fields must be authored before preregistration is committed.",
            "Do not implement experiment.py in the preregistration commit.",
            "Do not tune against External Validation or Reference Validation.",
            "A descriptive separator does not authorize an executable intervention.",
        ],
    }


def prepare_experiment(experiment_id: str, name: str, root: Path | None = None) -> Path:
    root = root or repo_root()
    registry = load_registry(root)
    expected_id = registry["next_available_experiment"]
    if experiment_id != expected_id:
        raise ProtocolError(
            f"Expected next available experiment {expected_id}, got {experiment_id}. "
            "Update scientific state explicitly rather than bypassing the registry."
        )
    paths = experiment_paths(experiment_id, root)
    if paths["base"].exists():
        raise ProtocolError(
            f"{paths['base']} already exists; refusing to overwrite an experiment"
        )
    _write_json(paths["prereg"], preregistration_scaffold(experiment_id, name, registry))
    return paths["prereg"]


def validate_preregistration(
    experiment_id: str, prereg: Dict[str, Any], registry: Dict[str, Any]
) -> None:
    if prereg.get("schema_version") != 1:
        raise ProtocolError("Unsupported preregistration schema_version")
    if prereg.get("experiment_id") != experiment_id:
        raise ProtocolError("Preregistration experiment_id does not match requested experiment")
    if prereg.get("pair") != "SOL":
        raise ProtocolError("Preregistration pair must remain SOL")
    if prereg.get("retuning") != "prohibited":
        raise ProtocolError("Preregistration must prohibit retuning")

    inherited = prereg.get("inherits", {})
    if inherited.get("execution_parent") != registry["execution_parent"]:
        raise ProtocolError("Preregistration changed the frozen execution parent")
    frozen_taxonomy = {
        "central_losses_total": registry["loss_taxonomy"]["central_losses_total"],
        "l0_label": registry["loss_taxonomy"]["l0_label"],
        "l0_mechanism": registry["loss_taxonomy"]["l0_mechanism"],
        "l0_total": registry["loss_taxonomy"]["l0_total"],
    }
    if inherited.get("loss_taxonomy") != frozen_taxonomy:
        raise ProtocolError("Preregistration changed the frozen loss taxonomy")
    expected_partitions = {
        partition: {
            "central_losses": values["central_losses"],
            "l0": values["l0"],
        }
        for partition, values in registry["partitions"].items()
    }
    if inherited.get("partitions") != expected_partitions:
        raise ProtocolError("Preregistration changed frozen partition identities/counts")

    question = prereg.get("scientific_question")
    hypothesis = prereg.get("hypothesis")
    if not isinstance(question, str) or not question.strip() or question.startswith("TODO_"):
        raise ProtocolError("Scientific question must be authored before execution")
    if not isinstance(hypothesis, str) or not hypothesis.strip() or hypothesis.startswith("TODO_"):
        raise ProtocolError("Hypothesis must be authored before execution")
    features = prereg.get("finite_feature_set")
    if not isinstance(features, list) or not features:
        raise ProtocolError("finite_feature_set must be preregistered and non-empty")
    if not isinstance(prereg.get("fixed_snapshots"), list):
        raise ProtocolError("fixed_snapshots must be explicit, even when intentionally empty")
    if not isinstance(prereg.get("support_rules"), dict) or not prereg["support_rules"]:
        raise ProtocolError("support_rules must be preregistered and non-empty")
    if not isinstance(prereg.get("success_criteria"), dict) or not prereg["success_criteria"]:
        raise ProtocolError("success_criteria must be preregistered and non-empty")


def validate_observed_invariants(
    observed: Dict[str, Any], registry: Dict[str, Any]
) -> None:
    if not isinstance(observed, dict):
        raise ProtocolError("Experiment result must contain an observed invariant object")
    if observed.get("execution_parent") != registry["execution_parent"]:
        raise ProtocolError("Observed execution parent does not match the frozen registry")
    if observed.get("central_losses_total") != 710:
        raise ProtocolError(
            f"Observed CENTRAL losses must equal 710, got {observed.get('central_losses_total')}"
        )
    if observed.get("l0_total") != 76:
        raise ProtocolError(f"Observed L0 count must equal 76, got {observed.get('l0_total')}")

    observed_partitions = observed.get("partitions")
    if not isinstance(observed_partitions, dict):
        raise ProtocolError("Observed partition counts are required")
    for name, expected in EXPECTED_PARTITIONS.items():
        actual = observed_partitions.get(name)
        if not isinstance(actual, dict):
            raise ProtocolError(f"Observed result is missing partition {name}")
        for metric, expected_value in expected.items():
            if actual.get(metric) != expected_value:
                raise ProtocolError(
                    f"Observed {name}.{metric} changed: expected {expected_value}, "
                    f"got {actual.get(metric)}"
                )


def _load_experiment_module(path: Path, experiment_id: str):
    spec = importlib.util.spec_from_file_location(
        f"sol_discovery_{experiment_id.lower()}", path
    )
    if spec is None or spec.loader is None:
        raise ProtocolError(f"Could not load experiment module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_experiment(experiment_id: str, root: Path | None = None) -> Path:
    root = root or repo_root()
    registry = load_registry(root)
    if experiment_id != registry["next_available_experiment"]:
        raise ProtocolError(
            f"{experiment_id} is not the registry's next available experiment "
            f"({registry['next_available_experiment']})"
        )
    paths = experiment_paths(experiment_id, root)
    prereg = _load_json(paths["prereg"])
    validate_preregistration(experiment_id, prereg, registry)
    if not paths["implementation"].is_file():
        raise ProtocolError(f"Missing implementation: {paths['implementation']}")

    module = _load_experiment_module(paths["implementation"], experiment_id)
    run_callable = getattr(module, "run", None)
    if not callable(run_callable):
        raise ProtocolError(f"{paths['implementation']} must expose run(context) -> dict")

    paths["results"].mkdir(parents=True, exist_ok=True)
    outcome = run_callable({
        "experiment_id": experiment_id,
        "repo_root": str(root),
        "results_dir": str(paths["results"]),
        "registry": copy.deepcopy(registry),
        "preregistration": copy.deepcopy(prereg),
    })
    if not isinstance(outcome, dict):
        raise ProtocolError("Experiment run(context) must return a dict")

    observed = outcome.get("observed")
    validate_observed_invariants(observed, registry)
    artifacts = outcome.get("artifacts")
    if not isinstance(artifacts, list):
        raise ProtocolError("Experiment outcome.artifacts must be a list of repo-relative result paths")
    if outcome.get("summary") is None:
        raise ProtocolError("Experiment outcome.summary is required")

    envelope = {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "git_sha": _git_sha(root),
        "registry_sha256": _fingerprint(registry_path(root)),
        "preregistration_sha256": _fingerprint(paths["prereg"]),
        "observed": observed,
        "summary": outcome["summary"],
        "artifacts": artifacts,
        "scientific_verdict": None,
        "state_advanced": False,
    }
    _write_json(paths["result_envelope"], envelope)
    return paths["result_envelope"]


def _resolve_artifact(root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ProtocolError(f"Artifact escapes repository root: {raw_path}") from exc
    return resolved


def finalize_experiment(experiment_id: str, root: Path | None = None) -> Path:
    root = root or repo_root()
    registry = load_registry(root)
    paths = experiment_paths(experiment_id, root)
    prereg = _load_json(paths["prereg"])
    validate_preregistration(experiment_id, prereg, registry)

    envelope = _load_json(paths["result_envelope"])
    if envelope.get("experiment_id") != experiment_id:
        raise ProtocolError("Result envelope experiment_id mismatch")
    if envelope.get("registry_sha256") != _fingerprint(registry_path(root)):
        raise ProtocolError("Registry changed after the experiment run")
    if envelope.get("preregistration_sha256") != _fingerprint(paths["prereg"]):
        raise ProtocolError("Preregistration changed after the experiment run")
    validate_observed_invariants(envelope.get("observed"), registry)

    artifacts = envelope.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ProtocolError(
            "At least one experiment-produced scientific artifact is required before finalize"
        )
    artifact_manifest = []
    for raw_path in artifacts:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ProtocolError("Artifact paths must be non-empty strings")
        artifact = _resolve_artifact(root, raw_path)
        if not artifact.is_file():
            raise ProtocolError(f"Declared artifact does not exist: {raw_path}")
        if artifact in {paths["result_envelope"], paths["run_manifest"]}:
            raise ProtocolError("Harness envelope/manifest cannot count as scientific artifacts")
        artifact_manifest.append({
            "path": str(artifact.relative_to(root)).replace("\\", "/"),
            "sha256": _fingerprint(artifact),
            "bytes": artifact.stat().st_size,
        })

    manifest = {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "git_sha_at_run": envelope.get("git_sha"),
        "registry_sha256": envelope["registry_sha256"],
        "preregistration_sha256": envelope["preregistration_sha256"],
        "artifacts": artifact_manifest,
        "scientific_verdict_required_separately": True,
        "state_advanced": False,
    }
    _write_json(paths["run_manifest"], manifest)
    return paths["run_manifest"]


def status_payload(root: Path | None = None) -> Dict[str, Any]:
    root = root or repo_root()
    registry = load_registry(root)
    next_id = registry["next_available_experiment"]
    paths = experiment_paths(next_id, root)
    return {
        "pair": registry["pair"],
        "latest_completed_experiment": registry["latest_completed_experiment"],
        "next_available_experiment": next_id,
        "current_frontier": registry.get("current_frontier"),
        "next_paths": {
            key: str(value.relative_to(root)).replace("\\", "/")
            for key, value in paths.items()
        },
        "exists": {
            "preregistration": paths["prereg"].is_file(),
            "implementation": paths["implementation"].is_file(),
            "result_envelope": paths["result_envelope"].is_file(),
            "run_manifest": paths["run_manifest"].is_file(),
        },
    }
