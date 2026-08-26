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
read -r HOST PORT < <(python3 - "$BASE_URL" <<'PY'
import sys
from urllib.parse import urlparse
url=urlparse(sys.argv[1])
if url.scheme != 'http' or not url.hostname or not url.port or url.path.rstrip('/') != '/v1':
    raise SystemExit('accuracy inference requires a local http://HOST:PORT/v1 endpoint')
print(url.hostname, url.port)
PY
)

mkdir -p "$OUTPUT"
PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" "$ASSETS_DIR/src/HunyuanOCR/inference/vLLM/batch_infer.py" \
    --image-dir "$ASSETS_DIR/data/OmniDocBench_v1_6/images" \
    --out-dir "$OUTPUT" \
    --host "$HOST" \
    --ports "$PORT" \
    --model "$MODEL" \
    --task-type doc_parse \
    --max-tokens 32768 \
    --repetition-penalty 1.08 \
    --concurrency 1

PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli verify-predictions \
    --gt "$GT" \
    --prediction-dir "$OUTPUT" \
    --output "$WORK_DIR/$RUN_ID/prediction-verification.json"
