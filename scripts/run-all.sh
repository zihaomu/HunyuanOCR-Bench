#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MACHINE=${1:?usage: run-all.sh MACHINE_PROFILE [SPEED_PROFILE]}
SPEED_PROFILE=${2:-full1651-c1}
ASSETS_DIR=${ASSETS_DIR:-$ROOT/assets}
WORK_DIR=${WORK_DIR:-$ROOT/work}
MACHINE_ID=$(PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli profile-get --machine "$MACHINE" machine_id)
METHOD=$(PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli profile-get --machine "$MACHINE" runtime.inference_method)
RUN_ID=${RUN_ID:-${MACHINE_ID}-$(date -u +%Y%m%dT%H%M%SZ)-${METHOD}}
BRANCH=$(git -C "$ROOT" branch --show-current)

[[ "$BRANCH" == "machine/$MACHINE_ID" ]] \
    || { printf 'ERROR: run on branch machine/%s, current=%s\n' "$MACHINE_ID" "$BRANCH" >&2; exit 1; }
[[ ! -e "$WORK_DIR/$RUN_ID" ]] || { printf 'ERROR: run already exists: %s\n' "$RUN_ID" >&2; exit 1; }
mkdir -p "$WORK_DIR/$RUN_ID"

PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli verify-assets \
    --assets-dir "$ASSETS_DIR" \
    --output "$WORK_DIR/$RUN_ID/assets-verification.json"
PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli capture-machine \
    --machine "$MACHINE" \
    --output "$WORK_DIR/$RUN_ID/machine-capture.json"

"$ROOT/scripts/run-speed.sh" "$MACHINE" "$RUN_ID" "$SPEED_PROFILE"
"$ROOT/scripts/run-accuracy-inference.sh" "$MACHINE" "$RUN_ID"
"$ROOT/scripts/run-evaluation.sh" "$RUN_ID"

SUMMARY=$(<"$WORK_DIR/$RUN_ID/evaluator-summary.path")
PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli accuracy-report \
    --machine "$MACHINE" \
    --source "$SUMMARY" \
    --output "$WORK_DIR/$RUN_ID/accuracy.json"

PUBLISH_DIR=$ROOT/results/$MACHINE_ID/$RUN_ID
[[ ! -e "$PUBLISH_DIR" ]] || { printf 'ERROR: publish directory exists\n' >&2; exit 1; }
mkdir -p "$PUBLISH_DIR"
cp "$MACHINE" "$PUBLISH_DIR/machine.json"
cp "$WORK_DIR/$RUN_ID/machine-capture.json" "$PUBLISH_DIR/machine-capture.json"
cp "$WORK_DIR/$RUN_ID/accuracy.json" "$PUBLISH_DIR/accuracy.json"
cp "$WORK_DIR/$RUN_ID/speed/summary.json" "$PUBLISH_DIR/speed.json"
cp "$WORK_DIR/$RUN_ID/assets-verification.json" "$PUBLISH_DIR/assets-verification.json"
cp "$WORK_DIR/$RUN_ID/prediction-verification.json" "$PUBLISH_DIR/prediction-verification.json"
cp "$SUMMARY" "$PUBLISH_DIR/evaluator-summary.json"
cp "$WORK_DIR/$RUN_ID/speed/records.jsonl" "$PUBLISH_DIR/speed-records.jsonl"

PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli assemble-result \
    --machine "$MACHINE" \
    --run-id "$RUN_ID" \
    --accuracy "$PUBLISH_DIR/accuracy.json" \
    --speed "$PUBLISH_DIR/speed.json" \
    --machine-capture "$PUBLISH_DIR/machine-capture.json" \
    --assets-verification "$PUBLISH_DIR/assets-verification.json" \
    --prediction-verification "$PUBLISH_DIR/prediction-verification.json" \
    --evaluator-summary "$PUBLISH_DIR/evaluator-summary.json" \
    --speed-records "$PUBLISH_DIR/speed-records.jsonl" \
    --machine-profile "$PUBLISH_DIR/machine.json" \
    --output "$PUBLISH_DIR/result.json"
PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli validate-result "$PUBLISH_DIR/result.json"
printf 'PASS: publishable result at %s\n' "$PUBLISH_DIR"
