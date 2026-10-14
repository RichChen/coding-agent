#!/usr/bin/env python3
"""Offline evidence audit: no model calls, no candidate execution, no Docker."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.eval.contracts import EvaluationSpec, canonical_hash
from src.eval.deepseek_demo import usage_report
from src.eval.grader import decode_snapshot, regenerate_report, save_json, tree_hash
from src.harness.factory import load_config
from src.runtime.session import RunSession
from src.tracing.store import EventStore


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--check-key-config", help="Optional exact-key leak scan; never prints the key")
    args = parser.parse_args()
    rows, attempts, models, identities = [], [], set(), set()
    for directory in sorted(args.evidence_root.glob("deepseek-*-attempt-*")):
        run_dir = directory / "run"
        if not (run_dir / "manifest.json").exists():
            failure = load(directory / "preparation.json")
            require(failure["status"] == "invalid_env" and failure["model_calls"] == 0, "unaccounted preflight failure")
            rows.append(dict(attempt=directory.name, status="invalid_env", phase="source_preparation", model_calls=0))
            continue
        manifest, run = load(run_dir / "manifest.json"), load(run_dir / "run-result.json")
        spec = EvaluationSpec.from_mapping(load(directory / "private-spec.json"))
        base = decode_snapshot(load(run_dir / "base.json"))
        require(tree_hash(base) == spec.base_hash == manifest["base_hash"], "base hash mismatch")
        require(spec.manifest()["private_spec_hash"] == manifest["private_spec_hash"], "private spec changed")
        require(canonical_hash(load(run_dir / "public-task.json")) == manifest["public_task_hash"], "public task changed")
        identities.add((spec.base_hash, manifest["private_spec_hash"], manifest["public_task_hash"]))
        state = RunSession.replay(run_dir / "session")
        require(state.terminal == run, "terminal evidence differs from replay")
        with EventStore(run_dir / "session", readonly=True) as store:
            events = store.read_events()
        # JSONL is delimited by LF, not every Unicode separator in string values.
        exported = [json.loads(line) for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").split("\n") if line]
        require(events == exported, "JSONL export differs from authoritative SQLite")
        evaluation = load(run_dir / "evaluation-result.json")
        require(load(run_dir / "evaluation" / "results.json") == [evaluation], "evaluation bundle differs")
        if (run_dir / "candidate.json").exists():
            candidate = decode_snapshot(load(run_dir / "candidate.json"))
            require(tree_hash(candidate) == run["execution"]["candidate_hash"] == evaluation["manifest"]["candidate_hash"],
                    "candidate identity differs across run/grader")
            require(evaluation["manifest"]["private_spec_hash"] == manifest["private_spec_hash"], "grader used a different spec")
            require([c["case_id"] for c in evaluation["cases"]] == [c.case_id for c in spec.cases], "case identities differ")
        baseline = load(directory / "baseline-evaluation.json")
        require(baseline["manifest"]["candidate_hash"] == spec.base_hash and baseline["failed"] > 0,
                "baseline does not reproduce the defect")
        require(baseline["manifest"]["private_spec_hash"] == manifest["private_spec_hash"], "baseline spec differs")
        require(run["execution"]["cleanup_ok"], "agent container cleanup unverified")
        require(len(run["llm_attempts"]) == run["model_budget"]["calls_started"], "model attempts omitted")
        usage = usage_report(run["llm_attempts"], manifest["model"])
        require(usage == load(directory / "usage.json"), "usage report differs from provider attempts")
        report_path = run_dir / "evaluation" / "report.md"
        before = report_path.read_bytes()
        regenerate_report(run_dir / "evaluation")
        require(report_path.read_bytes() == before, "offline report is not reproducible")
        attempts.extend(run["llm_attempts"])
        models.add(manifest["model"])
        rows.append(dict(attempt=directory.name, status=evaluation["status"],
            baseline_passed=baseline["passed"], candidate_passed=evaluation["passed"], collected=evaluation["collected"],
            model_calls=len(run["llm_attempts"]), provider_tokens=usage["provider_totals"]["total_tokens"],
            replay_equal=True, jsonl_equal=True, cleanup_ok=True,
            report_sha256=hashlib.sha256(before).hexdigest()))
    require(rows and len(models) == 1 and len(identities) == 1, "requires one frozen task/model with recorded attempts")
    leak_scan = "not_requested"
    if args.check_key_config:
        key = load_config(args.check_key_config)["llm"]["api_key"]
        require(bool(key), "key unavailable for leak scan")
        for path in args.evidence_root.rglob("*"):
            if path.is_file():
                require(key.encode() not in path.read_bytes(), "configured API key found in evidence")
        leak_scan = "configured_key_absent_from_all_evidence_files"
    result = dict(attempts=rows, total_attempts=len(rows), passed_attempts=sum(r["status"] == "pass" for r in rows),
                  usage_all_paid_attempts=usage_report(attempts, next(iter(models))), credential_scan=leak_scan,
                  scope="single public module-slice demo, not a success-rate benchmark")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    save_json(args.output_dir / "audit.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
