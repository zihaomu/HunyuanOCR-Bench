#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MACHINE=${1:?usage: run-speed.sh MACHINE_PROFILE RUN_ID [PROFILE]}
RUN_ID=${2:?usage: run-speed.sh MACHINE_PROFILE RUN_ID [PROFILE]}
PROFILE=${3:-full1651-c1}
ASSETS_DIR=${ASSETS_DIR:-$ROOT/assets}
WORK_DIR=${WORK_DIR:-$ROOT/work}

args=(
    --machine "$MACHINE"
    --profile "$PROFILE"
    --image-dir "$ASSETS_DIR/data/OmniDocBench_v1_6/images"
    --output "$WORK_DIR/$RUN_ID/speed"
)
if [[ "$PROFILE" == full1651-c1 ]]; then
    args+=(--gt "$ASSETS_DIR/data/OmniDocBench_v1_6/OmniDocBench.json")
else
    [[ -n "${PAPER930_LIST:-}" ]] || { printf 'ERROR: PAPER930_LIST is required\n' >&2; exit 1; }
    args+=(--sample-list "$PAPER930_LIST")
fi

"$ROOT/scripts/check-endpoint.sh" "$MACHINE"
PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli speed "${args[@]}"
