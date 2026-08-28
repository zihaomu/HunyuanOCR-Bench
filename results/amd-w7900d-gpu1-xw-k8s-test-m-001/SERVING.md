# AMD Radeon PRO W7900D Serving Configuration

This is the configuration used for the published W7900D result. Speed used one
compiled AR endpoint on physical GPU1. Accuracy used four independent TP=1
replicas with one in-flight request per replica and `MIOPEN_FIND_MODE=2`.

- [Machine profile](../../machines/amd-w7900d-gpu1-xw-k8s-test-m-001.json)
- [Canonical result](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/result.json)
- [Accuracy evidence](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/accuracy.json)
- [Speed evidence](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/speed.json)
- [Prediction quality](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/prediction-quality.json)

## Captured Runtime

| Setting | Value |
| --- | --- |
| Host accelerators | 8x AMD Radeon PRO W7900D (gfx1100), 48 GiB each |
| Serving framework | vLLM `0.27.0` |
| Precision | BF16 |
| Tensor parallelism | 1 per endpoint |
| Served model | `tencent/HunyuanOCR` |
| Container image | `hunyuanocr-base:rocm7.2.4-v0` |
| Container image digest | `sha256:83fef91f42e0306dbf81d2d225086234e7fbc770eeba16a02a9a11f57e17d335` |
| ROCm / PyTorch | ROCm 7.2.4 / PyTorch 2.10.0+rocm7.2.4.git3d3aa833 |
| Speed endpoint | Physical GPU1, port 18016, torch.compile enabled |
| Accuracy endpoints | GPU1:18016, GPU2:18017, GPU5:18020, GPU6:18021 |

GPU0 was excluded because it had a persistent competing workload. The speed
number is a single-GPU measurement; the four accuracy replicas only reduce the
wall time of the deterministic 1,651-page evaluation and are not used to claim
multi-GPU speed.

## Speed Endpoint

The published `quick9-c1` speed result used one visible W7900D, TP=1, and
request concurrency 1:

```bash
docker run -d --name hyocr-w7900-speed \
  --network host \
  --device=/dev/kfd --device=/dev/dri \
  --group-add 44 --group-add 993 \
  --security-opt seccomp=unconfined --ipc=host --shm-size=16g \
  -e HIP_VISIBLE_DEVICES=1 \
  -e HF_HOME=/workspace/cache/huggingface \
  -e PYTORCH_ROCM_ARCH=gfx1100 \
  -e VLLM_TARGET_DEVICE=rocm \
  -v "$WORKSPACE:/workspace" \
  --entrypoint vllm \
  hunyuanocr-base:rocm7.2.4-v0 \
  serve /workspace/models/HunyuanOCR \
  --served-model-name tencent/HunyuanOCR \
  -tp 1 \
  --limit-mm-per-prompt '{"image":4,"video":0}' \
  --trust-remote-code \
  --port 18016 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 131072 \
  --max-num-batched-tokens 131072 \
  --skip-mm-profiling
```

The speed client used `temperature=0`, `max_tokens=8000`, and `top_k=1`. Each
of the fixed nine pages was warmed once and measured three times, producing 27
successful requests:

| Metric | Result |
| --- | ---: |
| Average latency | 4.662196 s/page |
| P95 latency | 21.928563 s |
| Page throughput | 0.214491 page/s |
| Token throughput | 90.7059 token/s |

## Accuracy Endpoints

On this ROCm 7.2.4 + MIOpen 3.5.1 + gfx1100 stack, leaving the MIOpen find mode
unset caused systemic coordinate-placeholder outputs for some image shapes.
The corrected accuracy run therefore set `MIOPEN_FIND_MODE=2` before loading
PyTorch/MIOpen. A same-GPU single-variable A/B changed the fixed historical
failure set from 3/10 to 10/10.

Each accuracy replica used the original benchmark images and the following
service shape:

```bash
docker run -d --name "hyocr-miopen2-gpu${GPU}" \
  --network host \
  --device=/dev/kfd --device=/dev/dri \
  --group-add 44 --group-add 993 \
  --security-opt seccomp=unconfined --ipc=host --shm-size=16g \
  -e "HIP_VISIBLE_DEVICES=${GPU}" \
  -e MIOPEN_FIND_MODE=2 \
  -e HF_HOME=/workspace/cache/huggingface \
  -e PYTORCH_ROCM_ARCH=gfx1100 \
  -e VLLM_TARGET_DEVICE=rocm \
  -v "$WORKSPACE:/workspace" \
  --entrypoint vllm \
  hunyuanocr-base:rocm7.2.4-v0 \
  serve /workspace/models/HunyuanOCR \
  --served-model-name tencent/HunyuanOCR \
  -tp 1 \
  --limit-mm-per-prompt '{"image":4,"video":0}' \
  --trust-remote-code \
  --port "$PORT" \
  --gpu-memory-utilization 0.90 \
  --max-model-len 131072 \
  --max-num-batched-tokens 131072 \
  --skip-mm-profiling
```

The four fixed workers were mapped as follows:

| Physical GPU | Port | Completed pages |
| ---: | ---: | ---: |
| 1 | 18016 | 416 |
| 2 | 18017 | 407 |
| 5 | 18020 | 388 |
| 6 | 18021 | 440 |

Accuracy generation used `max_tokens=32768`, `temperature=0`, `top_p=1`,
`top_k=-1`, and `repetition_penalty=1.08`, followed by the official document
post-processing. The official OmniDocBench v1.6 evaluator produced Overall
95.593058 over all 1,651 pages.

`MIOPEN_FIND_MODE=2` is a verified workaround for this exact W7900D stack. The
full-model A/B localizes the issue to MIOpen find/solver selection, but a
standalone fixed-tensor reproduction has not yet identified a specific faulty
solver kernel.
