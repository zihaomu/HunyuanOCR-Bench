#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
PYTHONPATH=src python3 -m hunyuanocr_bench.cli aggregate --results-root results --output-dir leaderboards
