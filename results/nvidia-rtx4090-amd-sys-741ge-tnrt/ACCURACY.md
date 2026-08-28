# NVIDIA GeForce RTX 4090 Accuracy Configuration

This page contains only the configuration behind the RTX 4090 column in the
root accuracy table. The run covered all 1,651 OmniDocBench v1.6 pages.

- [Pinned benchmark contract](../../protocol/benchmark-v1.json)
- [Machine profile](../../machines/nvidia-rtx4090-amd-sys-741ge-tnrt.json)
- [Accuracy evidence](local-evaluator-accuracy-20260826T063000Z-ar/README.md)
- [Accuracy metrics](local-evaluator-accuracy-20260826T063000Z-ar/accuracy.json)

## Runtime

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
| Accuracy endpoints | GPU0:18081 and GPU1:18082 |
| Maximum model length / batched tokens | 131072 / 131072 |

The run used the pinned HunyuanOCR code and weights revisions from the benchmark
contract. Start one independent TP=1 replica per GPU inside the recorded image
or an equivalent CUDA 13 unified inference environment:

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

The pinned launcher resolves to these accuracy-relevant vLLM arguments:

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

## Run Accuracy

Prepare the protocol-pinned assets once, then run inference and evaluation:

```bash
HF_ENDPOINT=https://hf-mirror.com ./scripts/prepare-assets.sh

MACHINE=machines/nvidia-rtx4090-amd-sys-741ge-tnrt.json
RUN_ID=reproduce-rtx4090-accuracy
PYTHON_BIN=/path/to/hunyuan-runtime/bin/python \
  ./scripts/run-accuracy-inference.sh "$MACHINE" "$RUN_ID"
./scripts/run-evaluation.sh "$RUN_ID"
PYTHONPATH=src python3 -m hunyuanocr_bench.cli accuracy-report \
  --machine "$MACHINE" \
  --source "$(<work/$RUN_ID/evaluator-summary.path)" \
  --output "work/$RUN_ID/accuracy.json"
```

The committed machine profile selects both endpoints, so client concurrency is
2. Each request uses document parsing, `max_tokens=32768`, `temperature=0`,
`top_p=1`, `top_k=-1`, `repetition_penalty=1.08`, and official document
post-processing.

The published score used the pinned evaluator source and configuration, but a
