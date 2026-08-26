#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MACHINE=${1:?usage: check-endpoint.sh MACHINE_PROFILE}
BASE_URL=$(PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli profile-get --machine "$MACHINE" runtime.base_url)
MODEL=$(PYTHONPATH="$ROOT/src" python3 -m hunyuanocr_bench.cli profile-get --machine "$MACHINE" runtime.served_model_name)

python3 - "$BASE_URL" "$MODEL" <<'PY'
import json
import sys
from urllib.request import ProxyHandler, Request, build_opener

base_url, expected = sys.argv[1].rstrip('/'), sys.argv[2]
request = Request(base_url + '/models', headers={'Authorization': 'Bearer EMPTY'})
with build_opener(ProxyHandler({})).open(request, timeout=10) as response:
    payload = json.load(response)
models = [item.get('id') for item in payload.get('data', [])]
if expected not in models:
    raise SystemExit(f'ERROR: expected model {expected!r}, found {models}')
print(f'PASS: endpoint={base_url} model={expected}')
PY
