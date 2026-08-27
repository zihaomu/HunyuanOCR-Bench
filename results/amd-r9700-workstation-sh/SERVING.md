# AMD Radeon AI PRO R9700 Serving Configuration

This is the configuration used for the canonical R9700 result. Speed used one
compiled AR endpoint. Accuracy used two independent eager TP=1 replicas so the
1,651 variable-resolution pages did not trigger per-shape recompilation.

- [Machine profile](../../machines/amd-r9700-workstation-sh.json)
- [Canonical result](amd-r9700-workstation-sh-20260827T014842Z-ar/result.json)
- [Accuracy evidence](amd-r9700-workstation-sh-20260827T014842Z-ar/accuracy.json)
- [Speed evidence](amd-r9700-workstation-sh-20260827T014842Z-ar/speed.json)

## Captured Runtime

| Setting | Value |
| --- | --- |
| Host accelerators | 4x AMD Radeon AI PRO R9700 (gfx1201), 32 GiB each |
| Serving framework | vLLM `0.1.dev1+g3775d5fca` |
| Precision | BF16 |
| Tensor parallelism | 1 per endpoint |
| Served model | `tencent/HunyuanOCR` |
| Base image | `ghcr.io/inferstation/vllm-rocm-r9700-main` |
| Base image digest | `sha256:2d3a6275b1000cc9dce4c105dae899edd95d77875ede0c4d5d9b9c53a29faaf1` |
| ROCm / PyTorch | ROCm 7.14 / PyTorch 2.13.0a0+rocm7.14.0a20260612 |
| Speed endpoint | HIP0, port 18016, torch.compile enabled |
| Accuracy endpoints | HIP3:18017 and HIP2:18018, eager mode |

## Required Image Patch

The base image pairs transformers 5.13.0 with a vLLM HunyuanVL image-processor
registration written for the transformers 4.x API. The reference run used a
local derivative with that registration ported to the config-class API.

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

## Speed Endpoint

`hyocr_serve.sh`:

```bash
#!/bin/bash
set -e
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
exec vllm serve /model \
  --served-model-name tencent/HunyuanOCR \
  -tp 1 \
  --limit-mm-per-prompt '{"image":4,"video":0}' \
  --trust-remote-code \
  --port "${PORT:-8000}" \
  --gpu-memory-utilization 0.9 \
  --max-model-len 131072 \
  --max-num-batched-tokens 131072
```

```bash
ASSETS=$PWD/assets
docker run -d --name hyocr_p18016 \
  --device=/dev/kfd --device=/dev/dri \
  --group-add video --group-add render \
  --security-opt seccomp=unconfined --ipc=host --shm-size=16g --network host \
  -e HIP_VISIBLE_DEVICES=0 -e PORT=18016 \
  -v "$ASSETS/models/HunyuanOCR:/model:ro" \
  -v "$PWD/hyocr_serve.sh:/hyocr_serve.sh:ro" \
  --entrypoint bash local/hyocr-r9700:v1 /hyocr_serve.sh
```

## Accuracy Endpoints

`hyocr_serve_eager.sh`:

```bash
#!/bin/bash
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

```bash
ASSETS=$PWD/assets
for pair in "3:18017" "2:18018"; do
  gpu=${pair%%:*}
  port=${pair##*:}
  docker run -d --name "hyocr_p${port}" \
    --device=/dev/kfd --device=/dev/dri \
    --group-add video --group-add render \
    --security-opt seccomp=unconfined --ipc=host --shm-size=16g --network host \
    -e HIP_VISIBLE_DEVICES="$gpu" -e PORT="$port" \
    -v "$ASSETS/models/HunyuanOCR:/model:ro" \
    -v "$PWD/hyocr_serve_eager.sh:/hyocr_serve.sh:ro" \
    --entrypoint bash local/hyocr-r9700:v1 /hyocr_serve.sh
done
```

The accuracy client used both ports with concurrency 32. Request generation was
`max_tokens=32768`, `temperature=0`, `top_k=-1`, and
`repetition_penalty=1.08`, followed by official document post-processing.

```bash
PYTHONDONTWRITEBYTECODE=1 ./venv/bin/python \
  assets/src/HunyuanOCR/inference/vLLM/batch_infer.py \
  --image-dir assets/data/OmniDocBench_v1_6/images \
  --out-dir work/amd-r9700-workstation-sh-20260827T014842Z-ar/predictions \
  --host 127.0.0.1 --ports 18017,18018 \
  --model tencent/HunyuanOCR --task-type doc_parse \
  --max-tokens 32768 --repetition-penalty 1.08 --concurrency 32
```
