# AMD Strix Halo Serving Configuration

This is the configuration used for the Strix Halo `quick9-c1` speed result.
The endpoint ran on the integrated Radeon 8060S in an AMD Ryzen AI Max+ 395.

- [Machine profile](../../machines/amd-strix-halo-halo3.json)
- [Strix Halo result summary](README.md)
- [Quick9 speed summary](interim-speed-quick9-c1/speed.json)
- [Quick9 per-request records](interim-speed-quick9-c1/speed-records.jsonl)

## Captured Runtime

| Setting | Value |
| --- | --- |
| Host accelerator | 1x AMD Radeon 8060S (`gfx1151`), integrated in Ryzen AI Max+ 395 |
| Device memory visible to PyTorch | 120 GiB unified memory |
| Serving framework | vLLM `0.1.dev1+ga1274c75b.d20260807` |
| Precision | BF16 |
| Tensor parallelism | 1 |
| Served model | `tencent/HunyuanOCR` |
| Container image | `ghcr.io/inferstation/vllm-rocm-halo:latest` |
| Container image digest | `sha256:ff89ae6d0cc44eb70b9bada85b535652058c0daf3c2c2c542da844b6f592cae6` |
| ROCm / PyTorch | ROCm 7.15.0 / PyTorch `2.14.0a0+rocm7.15.0a20260719` |
| Endpoint | HIP0, port 8000 |
| KV cache | 32 GiB fixed allocation |
| Model context | 131,072 tokens |
| Maximum batched tokens / sequences | 131,072 / 8 |
| Multimodal startup profiling | Disabled with `--skip-mm-profiling` |

The machine profile and the earlier August 26 sampled/full-run captures record
a 16 GiB KV cache. The `quick9-c1` result on this page was measured on the live
endpoint above after its fixed KV cache was increased to 32 GiB; model weights,
precision, tensor parallelism, context length, and request settings were
unchanged.

## Speed Endpoint

An equivalent portable command for the measured container is:

```bash
BENCH_ROOT=/path/to/HunyuanOCR-Bench
RUNTIME_CACHE=/path/to/vllm-cache

docker run -d --name hunyuanocr-strix-halo-ar \
	--device=/dev/kfd --device=/dev/dri \
	--group-add 44 --group-add 992 \
	--security-opt seccomp=unconfined --security-opt label=disable \
	--ipc=host --shm-size=32g \
	-p 8000:8000 \
	-e HIP_VISIBLE_DEVICES=0 -e CUDA_VISIBLE_DEVICES=0 \
	-e HF_HOME=/runtime-cache/huggingface -e XDG_CACHE_HOME=/runtime-cache \
	-e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
	-v "$RUNTIME_CACHE:/runtime-cache" \
	-v "$BENCH_ROOT/assets/models/HunyuanOCR:/model:ro" \
	ghcr.io/inferstation/vllm-rocm-halo:latest \
		--model /model \
		--served-model-name tencent/HunyuanOCR \
		--tensor-parallel-size 1 \
		--dtype bfloat16 \
		--limit-mm-per-prompt '{"image":4,"video":0}' \
		--trust-remote-code \
		--kv-cache-memory-bytes 34359738368 \
		--skip-mm-profiling \
		--max-model-len 131072 \
		--max-num-batched-tokens 131072 \
		--max-num-seqs 8 \
		--host 0.0.0.0 \
		--port 8000
```

The `quick9-c1` benchmark used request concurrency 1, one warm-up for each of
the nine fixed pages, and three measured repetitions. Request generation used
`temperature=0`, `max_tokens=8000`, and `top_k=1`.

| Metric | Result |
| --- | ---: |
| Status | PASS |
| Measured requests | 27 |
| Successful / failed / truncated | 27 / 0 / 0 |
| Average latency | 4.962382 s/page |
| P95 latency | 14.019636 s |
| Page throughput | 0.201516 page/s |
| Token throughput | 132.217 token/s |

Evidence SHA-256:

```text
speed.json          3c140a35e823c18050e058d868971b36e56b26ac5e6a4158bd58db7c3925ce18
speed-records.jsonl 71a701b0d2eeb1da6c5bdbb3b4a53bbf3d3099c08f987d915b549712841f33a6
```