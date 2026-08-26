#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RUN_ID=${1:?usage: run-evaluation.sh RUN_ID}
ASSETS_DIR=${ASSETS_DIR:-$ROOT/assets}
WORK_DIR=${WORK_DIR:-$ROOT/work}
PREDICTIONS=$WORK_DIR/$RUN_ID/predictions
OUTPUT=$WORK_DIR/$RUN_ID/evaluation
source "$ROOT/protocol/revisions.env"

[[ -s "$WORK_DIR/$RUN_ID/prediction-verification.json" ]] || { printf 'ERROR: prediction gate missing\n' >&2; exit 1; }
[[ "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$WORK_DIR/$RUN_ID/prediction-verification.json")" == PASS ]] \
    || { printf 'ERROR: prediction gate is not PASS\n' >&2; exit 1; }
[[ ! -e "$OUTPUT" ]] || { printf 'ERROR: evaluation output already exists: %s\n' "$OUTPUT" >&2; exit 1; }
mkdir -p "$OUTPUT"

docker image inspect "$EVALUATOR_IMAGE" >/dev/null 2>&1 || docker pull "$EVALUATOR_IMAGE"
docker run --rm \
    --entrypoint bash \
    --ipc=host \
    --shm-size=8g \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp/home \
    -v "$ASSETS_DIR/src/OmniDocBench:/source:ro" \
    -v "$ASSETS_DIR/data/OmniDocBench_v1_6:/benchmark_data:ro" \
    -v "$PREDICTIONS:/predictions:ro" \
    -v "$ROOT/protocol/omnidocbench-v1.6-end2end.yaml:/benchmark_config.yaml:ro" \
    -v "$OUTPUT:/evaluation_output" \
    "$EVALUATOR_IMAGE" \
    -lc '
        mkdir -p "$HOME" /tmp/OmniDocBench
        cp -a /source/. /tmp/OmniDocBench/
        cd /tmp/OmniDocBench
        python tools/test_environment_and_smoke.py
        python pdf_validation.py --config /benchmark_config.yaml
        cp -a result/. /evaluation_output/
    ' | tee "$WORK_DIR/$RUN_ID/evaluation.log"

summary=$(find "$OUTPUT" -maxdepth 1 -type f -name '*_run_summary.json' -print -quit)
if [[ -z "$summary" ]]; then
    summary=$(find "$OUTPUT" -maxdepth 1 -type f -name '*_metric_result.json' -print -quit)
fi
[[ -n "$summary" ]] || { printf 'ERROR: evaluator summary not found\n' >&2; exit 1; }
provenance_summary="$WORK_DIR/$RUN_ID/evaluator-summary.json"
python3 - "$summary" "$provenance_summary" "$OMNIDOCBENCH_DATA_REVISION" \
    "$OMNIDOCBENCH_CODE_REVISION" "$EVALUATOR_IMAGE" \
    "$ROOT/protocol/omnidocbench-v1.6-end2end.yaml" \
    "$ASSETS_DIR/data/OmniDocBench_v1_6/OmniDocBench.json" <<'PYPROV'
import hashlib
import json
import sys
from pathlib import Path

source, output, data_revision, code_revision, image, config_path, gt_path = sys.argv[1:]
def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(8*1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()

payload=json.loads(Path(source).read_text(encoding='utf-8'))
payload['benchmark_provenance']={
    'protocol_id':'hunyuanocr-1.5-omnidocbench-1.6-v1',
    'dataset_revision':data_revision,
    'dataset_pages':1651,
    'gt_sha256':sha256(gt_path),
    'evaluator_revision':code_revision,
    'evaluator_image':image,
    'config_sha256':sha256(config_path),
}
Path(output).write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
PYPROV
printf '%s\n' "$provenance_summary" > "$WORK_DIR/$RUN_ID/evaluator-summary.path"
