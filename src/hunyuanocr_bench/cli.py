from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .accuracy import build_accuracy_report
from .aggregate import aggregate_results
from .config import DEFAULT_PROTOCOL, REPOSITORY_ROOT, accuracy_endpoint_config, dotted_get, load_machine, load_protocol
from .machine import capture_machine
from .results import assemble_result, load_and_validate_result, write_json
from .speed import run_speed
from .verify import verify_assets, verify_predictions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hyocr-bench")
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    subparsers = parser.add_subparsers(dest="command", required=True)

    profile_get = subparsers.add_parser("profile-get")
    profile_get.add_argument("--machine", type=Path, required=True)
    profile_get.add_argument("key")

    capture = subparsers.add_parser("capture-machine")
    capture.add_argument("--machine", type=Path, required=True)
    capture.add_argument("--output", type=Path, required=True)

    accuracy_endpoints = subparsers.add_parser("accuracy-endpoints")
    accuracy_endpoints.add_argument("--machine", type=Path, required=True)

    assets = subparsers.add_parser("verify-assets")
    assets.add_argument("--assets-dir", type=Path, default=Path("assets"))
    assets.add_argument("--output", type=Path)

    predictions = subparsers.add_parser("verify-predictions")
    predictions.add_argument("--gt", type=Path, required=True)
    predictions.add_argument("--prediction-dir", type=Path, required=True)
    predictions.add_argument("--output", type=Path)

    speed = subparsers.add_parser("speed")
    speed.add_argument("--machine", type=Path, required=True)
    speed.add_argument("--profile", choices=("quick9-c1", "full1651-c1", "paper930-c1"), required=True)
    speed.add_argument("--image-dir", type=Path, required=True)
    speed.add_argument("--gt", type=Path)
    speed.add_argument("--sample-list", type=Path)
    speed.add_argument("--output", type=Path, required=True)

    accuracy = subparsers.add_parser("accuracy-report")
    accuracy.add_argument("--machine", type=Path, required=True)
    accuracy.add_argument("--source", type=Path, required=True)
    accuracy.add_argument("--output", type=Path, required=True)

    assemble = subparsers.add_parser("assemble-result")
    assemble.add_argument("--machine", type=Path, required=True)
    assemble.add_argument("--run-id", required=True)
    assemble.add_argument("--accuracy", type=Path, required=True)
    assemble.add_argument("--speed", type=Path, required=True)
    assemble.add_argument("--machine-capture", type=Path, required=True)
    assemble.add_argument("--assets-verification", type=Path, required=True)
    assemble.add_argument("--prediction-verification", type=Path, required=True)
    assemble.add_argument("--evaluator-summary", type=Path, required=True)
    assemble.add_argument("--speed-records", type=Path, required=True)
    assemble.add_argument("--machine-profile", type=Path, required=True)
    assemble.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser("validate-result")
    validate.add_argument("path", type=Path)

    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--results-root", type=Path, default=Path("results"))
    aggregate.add_argument("--output-dir", type=Path, default=Path("leaderboards"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    protocol = load_protocol(args.protocol)
    try:
        if args.command == "profile-get":
            value = dotted_get(load_machine(args.machine), args.key)
            print(json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value)
        elif args.command == "capture-machine":
            write_json(args.output, capture_machine(load_machine(args.machine)))
        elif args.command == "accuracy-endpoints":
            host, ports = accuracy_endpoint_config(load_machine(args.machine))
            print(json.dumps({"host": host, "ports": ports, "concurrency": len(ports)}))
        elif args.command == "verify-assets":
            report = verify_assets(args.assets_dir, protocol)
            if args.output:
                write_json(args.output, report)
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
            return 0 if report["status"] == "PASS" else 1
        elif args.command == "verify-predictions":
            report = verify_predictions(args.gt, args.prediction_dir)
            if args.output:
                write_json(args.output, report)
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
            return 0 if report["status"] == "PASS" else 1
        elif args.command == "speed":
            profile = protocol["speed_profiles"][args.profile]
            if not args.sample_list and profile.get("sample_list"):
                args.sample_list = REPOSITORY_ROOT / profile["sample_list"]
            if args.profile == "paper930-c1" and not args.sample_list:
                raise ValueError("paper930-c1 requires --sample-list; the paper's list is not publicly shipped")
            if args.profile == "full1651-c1" and not args.gt:
                raise ValueError("full1651-c1 requires --gt")
            summary = run_speed(
                protocol,
                load_machine(args.machine),
                args.profile,
                args.image_dir,
                args.output,
                args.gt,
                args.sample_list,
            )
            print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
            return 0 if summary["status"] == "PASS" else 1
        elif args.command == "accuracy-report":
            report = build_accuracy_report(args.source, protocol, load_machine(args.machine))
            write_json(args.output, report)
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        elif args.command == "assemble-result":
            machine = load_machine(args.machine)
            result = assemble_result(
                Path.cwd(),
                args.run_id,
                machine,
                protocol,
                args.accuracy,
                args.speed,
                args.machine_capture,
                args.assets_verification,
                args.prediction_verification,
                args.evaluator_summary,
                args.speed_records,
                args.machine_profile,
            )
            write_json(args.output, result)
        elif args.command == "validate-result":
            load_and_validate_result(args.path)
            print(f"PASS: {args.path}")
        elif args.command == "aggregate":
            results = aggregate_results(args.results_root, args.output_dir)
            print(f"PASS: aggregated {len(results)} result(s)")
        return 0
    except (KeyError, ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
