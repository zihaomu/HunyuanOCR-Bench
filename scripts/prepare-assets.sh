#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ASSETS_DIR=${ASSETS_DIR:-$ROOT/assets}
HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
DOWNLOAD_WORKERS=${DOWNLOAD_WORKERS:-4}
HUNYUANOCR_GIT_URL=${HUNYUANOCR_GIT_URL:-https://github.com/Tencent-Hunyuan/HunyuanOCR.git}
OMNIDOCBENCH_GIT_URL=${OMNIDOCBENCH_GIT_URL:-https://github.com/opendatalab/OmniDocBench.git}

source "$ROOT/protocol/revisions.env"

clone_fixed() {
    local url=$1 destination=$2 revision=$3
    if [[ -d "$destination/.git" ]]; then
        [[ "$(git -C "$destination" rev-parse HEAD)" == "$revision" ]] \
            || { printf 'ERROR: revision mismatch in %s\n' "$destination" >&2; return 1; }
        return
    fi
    [[ ! -e "$destination" ]] || { printf 'ERROR: refusing to overwrite %s\n' "$destination" >&2; return 1; }
    git clone --no-checkout "$url" "$destination"
    git -C "$destination" checkout --detach "$revision"
}

mkdir -p "$ASSETS_DIR/src" "$ASSETS_DIR/models" "$ASSETS_DIR/data" "$ASSETS_DIR/manifests"
clone_fixed "$HUNYUANOCR_GIT_URL" "$ASSETS_DIR/src/HunyuanOCR" "$HUNYUANOCR_CODE_REVISION"
clone_fixed "$OMNIDOCBENCH_GIT_URL" "$ASSETS_DIR/src/OmniDocBench" "$OMNIDOCBENCH_CODE_REVISION"

python3 "$ROOT/scripts/download_snapshot.py" \
    --repo tencent/HunyuanOCR \
    --repo-type model \
    --revision "$HUNYUANOCR_MODEL_REVISION" \
    --destination "$ASSETS_DIR/models/HunyuanOCR" \
    --endpoint "$HF_ENDPOINT" \
    --workers "$DOWNLOAD_WORKERS" \
    --expected-files 22 \
    --expected-images 0 \
    --exclude-prefix v1.0/

python3 "$ROOT/scripts/download_snapshot.py" \
    --repo opendatalab/OmniDocBench \
    --repo-type dataset \
    --revision "$OMNIDOCBENCH_DATA_REVISION" \
    --destination "$ASSETS_DIR/data/OmniDocBench_v1_6" \
    --endpoint "$HF_ENDPOINT" \
    --workers "$DOWNLOAD_WORKERS" \
    --expected-files 1659 \
    --expected-images 1651

PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli verify-assets \
    --assets-dir "$ASSETS_DIR" \
    --output "$ASSETS_DIR/manifests/assets-verification.json"
