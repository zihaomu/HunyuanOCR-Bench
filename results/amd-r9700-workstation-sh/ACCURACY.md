# AMD Radeon AI PRO R9700 Accuracy Configuration

This page contains only the configuration behind the R9700 column in the root
accuracy table. The canonical run covered all 1,651 OmniDocBench v1.6 pages.

- [Pinned benchmark contract](../../protocol/benchmark-v1.json)
- [Machine profile](../../machines/amd-r9700-workstation-sh.json)
- [Canonical result](amd-r9700-workstation-sh-20260827T014842Z-ar/result.json)
- [Accuracy metrics](amd-r9700-workstation-sh-20260827T014842Z-ar/accuracy.json)

## Runtime

| Setting | Value |
| --- | --- |
| Accelerator | AMD Radeon AI PRO R9700 (`gfx1201`) |
| Serving framework | vLLM `0.1.dev1+g3775d5fca` |
| Precision | BF16 |
| Tensor parallelism | 1 per endpoint |
| Served model | `tencent/HunyuanOCR` |
| Base image | `ghcr.io/inferstation/vllm-rocm-r9700-main` |
| Base image digest | `sha256:2d3a6275b1000cc9dce4c105dae899edd95d77875ede0c4d5d9b9c53a29faaf1` |
| ROCm / PyTorch | ROCm 7.14 / PyTorch 2.13.0a0+rocm7.14.0a20260612 |
| Accuracy endpoints | HIP3:18017 and HIP2:18018 |
| Execution mode | Eager |
| Maximum model length / batched tokens | 51200 / 51200 |

## Required Image Patch

The base image pairs transformers 5.13.0 with a vLLM HunyuanVL image-processor
registration written for the transformers 4.x API. Build the derivative used
by the accuracy run with the patch below.

`patch_hyvl.py`:

```python
from pathlib import Path

path = Path(
    "/usr/local/lib/python3.12/site-packages/vllm/transformers_utils/"
    "processors/hunyuan_vl_image.py"
)
source = path.read_text()
old = 'AutoImageProcessor.register("HunYuanVLImageProcessor", HunYuanVLImageProcessor)'
new = (
    "try:\n"
    "    from vllm.transformers_utils.configs.hunyuan_vl import "
    "HunYuanVLConfig as _HYVLCfg\n"
    "    try:\n"
    "        AutoImageProcessor.register(_HYVLCfg, "
    "image_processor_classes={\"torchvision\": HunYuanVLImageProcessor}, "
    "exist_ok=True)\n"
    "    except TypeError:\n"
    "        AutoImageProcessor.register(_HYVLCfg, HunYuanVLImageProcessor, "
    "exist_ok=True)\n"
    "except Exception:\n"
    "    pass\n"
)
if old not in source:
    if "image_processor_classes={" in source:
        raise SystemExit(0)
    raise SystemExit("registration pattern not found")
path.write_text(source.replace(old, new))
```

```dockerfile
FROM ghcr.io/inferstation/vllm-rocm-r9700-main@sha256:2d3a6275b1000cc9dce4c105dae899edd95d77875ede0c4d5d9b9c53a29faaf1
COPY patch_hyvl.py /opt/patch_hyvl.py
RUN python /opt/patch_hyvl.py
```

```bash
docker build -t local/hyocr-r9700:v1 .
```

## Accuracy Endpoints

Create `hyocr_serve_accuracy.sh`:

```bash
#!/usr/bin/env bash
set -e
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export MIOPEN_FIND_MODE=2
export MIOPEN_USER_DB_PATH=/tmp/miopen-db
export MIOPEN_CUSTOM_CACHE_DIR=/tmp/miopen-cache
mkdir -p "$MIOPEN_USER_DB_PATH" "$MIOPEN_CUSTOM_CACHE_DIR"
exec vllm serve /model \
  --served-model-name tencent/HunyuanOCR \
  -tp 1 \
  --limit-mm-per-prompt '{"image":4,"video":0}' \
  --trust-remote-code \
  --enforce-eager \
  --skip-mm-profiling \
  --port "${PORT:-8000}" \
  --gpu-memory-utilization 0.75 \
  --max-model-len 51200 \
  --max-num-batched-tokens 51200
```

Start the two independent TP=1 replicas:

```bash
ASSETS=$PWD/assets
for pair in "3:18017" "2:18018"; do
  GPU=${pair%%:*}
  PORT=${pair##*:}
  docker run -d --name "hyocr-accuracy-p${PORT}" \
    --device=/dev/kfd --device=/dev/dri \
    --group-add video --group-add render \
    --security-opt seccomp=unconfined --ipc=host --shm-size=16g --network host \
    -e HIP_VISIBLE_DEVICES="$GPU" -e PORT="$PORT" \
    -v "$ASSETS/models/HunyuanOCR:/model:ro" \
    -v "$PWD/hyocr_serve_accuracy.sh:/hyocr_serve_accuracy.sh:ro" \
    --entrypoint bash local/hyocr-r9700:v1 /hyocr_serve_accuracy.sh
done
```

## Run Accuracy

```bash
HF_ENDPOINT=https://hf-mirror.com ./scripts/prepare-assets.sh

RUN_ID=reproduce-r9700-accuracy
PYTHON_BIN=/path/to/hunyuan-runtime/bin/python
mkdir -p "work/$RUN_ID/predictions"
PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" \
  assets/src/HunyuanOCR/inference/vLLM/batch_infer.py \
  --image-dir assets/data/OmniDocBench_v1_6/images \
  --out-dir "work/$RUN_ID/predictions" \
  --host 127.0.0.1 --ports 18017,18018 \
  --model tencent/HunyuanOCR --task-type doc_parse \
  --max-tokens 32768 --repetition-penalty 1.08 --concurrency 32
PYTHONPATH=src python3 -m hunyuanocr_bench.cli verify-predictions \
  --gt assets/data/OmniDocBench_v1_6/OmniDocBench.json \
  --prediction-dir "work/$RUN_ID/predictions" \
  --output "work/$RUN_ID/prediction-verification.json"
./scripts/run-evaluation.sh "$RUN_ID"
PYTHONPATH=src python3 -m hunyuanocr_bench.cli accuracy-report \
  --machine machines/amd-r9700-workstation-sh.json \
  --source "$(<work/$RUN_ID/evaluator-summary.path)" \
  --output "work/$RUN_ID/accuracy.json"
```

The published run sent requests to both ports with client concurrency 32. Each
request uses document parsing, `max_tokens=32768`, `temperature=0`, `top_p=1`,
`top_k=-1`, `repetition_penalty=1.08`, and official document post-processing.
These defaults are set by the pinned upstream batch client; the command records
the non-default repetition penalty and concurrency.
