#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MACHINE=${1:?usage: run-accuracy-inference.sh MACHINE_PROFILE RUN_ID}
RUN_ID=${2:?usage: run-accuracy-inference.sh MACHINE_PROFILE RUN_ID}
ASSETS_DIR=${ASSETS_DIR:-$ROOT/assets}
WORK_DIR=${WORK_DIR:-$ROOT/work}
PYTHON_BIN=${PYTHON_BIN:-python3}
OUTPUT=$WORK_DIR/$RUN_ID/predictions
GT=$ASSETS_DIR/data/OmniDocBench_v1_6/OmniDocBench.json

[[ ! -e "$OUTPUT" ]] || { printf 'ERROR: output already exists: %s\n' "$OUTPUT" >&2; exit 1; }
"$ROOT/scripts/check-endpoint.sh" "$MACHINE"
BASE_URL=$(PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli profile-get --machine "$MACHINE" runtime.base_url)
MODEL=$(PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli profile-get --machine "$MACHINE" runtime.served_model_name)
endpoint_json=$(PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli accuracy-endpoints --machine "$MACHINE")
HOST=$(jq -r .host <<< "$endpoint_json")
PORTS=$(jq -r '.ports | join(",")' <<< "$endpoint_json")
CONCURRENCY=$(jq -r .concurrency <<< "$endpoint_json")

IFS=',' read -r -a accuracy_ports <<< "$PORTS"
for port in "${accuracy_ports[@]}"; do
    body=$(curl --noproxy '*' -fsS --max-time 10 "http://$HOST:$port/v1/models")
    [[ "$(jq -r .data[0].id <<< "$body")" == "$MODEL" ]] \
        || { printf 'ERROR: model mismatch on port %s\n' "$port" >&2; exit 1; }
done

mkdir -p "$OUTPUT"
PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" "$ASSETS_DIR/src/HunyuanOCR/inference/vLLM/batch_infer.py" \
    --image-dir "$ASSETS_DIR/data/OmniDocBench_v1_6/images" \
    --out-dir "$OUTPUT" \
    --host "$HOST" \
    --ports "$PORTS" \
    --model "$MODEL" \
    --task-type doc_parse \
    --max-tokens 32768 \
    --repetition-penalty 1.08 \
    --concurrency "$CONCURRENCY"

PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli verify-predictions \
    --gt "$GT" \
    --prediction-dir "$OUTPUT" \
    --output "$WORK_DIR/$RUN_ID/prediction-verification.json"
