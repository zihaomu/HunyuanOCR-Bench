# NVIDIA GeForce RTX 4090 Serving Configuration

This page records the serving parameters associated with the published RTX 4090
speed and accuracy evidence.

- [Machine profile](../../machines/nvidia-rtx4090-amd-sys-741ge-tnrt.json)
- [Quick9 speed evidence](interim-speed-quick9-c1/speed.json)
- [1,651-page accuracy evidence](local-evaluator-accuracy-20260826T063000Z-ar/README.md)

The accuracy run used the pinned HunyuanOCR and OmniDocBench revisions and the
pinned evaluator source/config, but not the protocol-pinned evaluator image. It
is therefore complete comparison evidence, not a canonical leaderboard result.

## Captured Runtime

| Setting | Value |
| --- | --- |
| Accelerator | NVIDIA GeForce RTX 4090 |
| Serving framework | vLLM `0.26.1rc1.dev457+gc810e5ee9` |
| Precision | BF16 |
| Tensor parallelism | 1 per endpoint |
| Served model | `tencent/HunyuanOCR` |
| Container image | `ghcr.io/inferstation/vllm-cuda-4090:latest` |
| Container digest | `sha256:6877023dee3a2456e00f468813607fd4ec21cd92c6386e5433e2f7422bf087a8` |
| CUDA / PyTorch | CUDA 13.0 / PyTorch 2.13.0+cu130 |
| Speed endpoint | physical GPU0, port 18081 |
| Accuracy endpoints | independent TP=1 replicas on GPU0:18081 and GPU1:18082 |
| Maximum model length | 131072 |
| Maximum batched tokens | 131072 |
| GPU memory utilization | 0.9 |

## Server Startup

The committed machine capture records the resolved parameters above, but not the
original host shell command. The equivalent command below uses the official
launcher from the pinned HunyuanOCR source revision. Run it once per GPU in the
CUDA 13 unified inference environment or recorded container image:

```bash
HUNYUAN_ROOT=/path/to/HunyuanOCR
MODEL_PATH=/path/to/HunyuanOCR-weights

MODEL_PATH="$MODEL_PATH" \
GPU=0 PORT=18081 GPU_MEM_UTIL=0.9 MAX_MODEL_LEN=131072 \
LOG=vllm_18081.log \
bash "$HUNYUAN_ROOT/inference/vLLM/serve.sh"

MODEL_PATH="$MODEL_PATH" \
GPU=1 PORT=18082 GPU_MEM_UTIL=0.9 MAX_MODEL_LEN=131072 \
LOG=vllm_18082.log \
bash "$HUNYUAN_ROOT/inference/vLLM/serve.sh"
```

The official launcher resolves to:

```bash
CUDA_VISIBLE_DEVICES="$GPU" vllm serve "$MODEL_PATH" \
  --served-model-name tencent/HunyuanOCR \
  -tp 1 \
  --limit-mm-per-prompt '{"image":4,"video":0}' \
  --trust-remote-code \
  --port "$PORT" \
  --gpu-memory-utilization 0.9 \
  --max-model-len 131072 \
  --max-num-batched-tokens 131072
```

Check both accuracy endpoints before inference:

```bash
curl -fsS http://127.0.0.1:18081/v1/models
curl -fsS http://127.0.0.1:18082/v1/models
```

## Accuracy Request Contract

The 1,651-page run used document parsing with `max_tokens=32768`,
`temperature=0`, `top_k=-1`, `repetition_penalty=1.08`, and official document
post-processing. The two endpoints are independent replicas for throughput;
each individual request remains single-stream AR inference on one GPU.

## Provenance Note

The recorded local evaluator used the same evaluator source revision and config
as the protocol, but ran in a version-aligned local toolchain. See the
[runtime manifest](local-evaluator-accuracy-20260826T063000Z-ar/manifest.json)
for both the actual and protocol-pinned evaluator image digests.
