# Speed Leaderboard

Only rows with the same speed profile are directly comparable. Page/s is the primary cross-hardware metric.

## Published Speed Results

| Machine | Accelerator | Framework | Method | Profile | Avg latency (s)↓ | P95 (s)↓ | Page/s↑ | Token/s* |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| nvidia-rtx4090-amd-sys-741ge-tnrt | 1× NVIDIA GeForce RTX 4090 | vLLM | ar | quick9-c1 | 1.682 | 4.569 | 0.5944 | 392.7 |
| amd-r9700-workstation-sh | 1× AMD Radeon AI PRO R9700 (gfx1201) | vLLM | ar | quick9-c1 | 2.457 | 6.879 | 0.4070 | 267.4 |
| amd-w7900d-gpu1-xw-k8s-test-m-001 | 1× AMD Radeon PRO W7900D (gfx1100) | vLLM | ar | quick9-c1 | 4.662 | 21.929 | 0.2145 | 90.7 |
| amd-strix-halo-halo3 | 1× AMD Ryzen AI Max+ 395 w/ Radeon 8060S (gfx1151) | vLLM | ar | quick9-c1 | 4.962 | 14.020 | 0.2015 | 132.2 |
| nvidia-gb10-spark2-shanghai | 1× NVIDIA GB10 | vLLM | ar | quick9-c1 | 5.397 | 15.168 | 0.1853 | 122.0 |

## Non-comparable References

These diagnostic or sampled results are shown for visibility only. They must not be ranked against published rows.

| Machine | Accelerator | Framework | Method | Profile/sample | Status | Avg latency (s) | P95 (s) | Page/s | Token/s* |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| amd-strix-halo-halo3 | 1× AMD Ryzen AI Max+ 395 w/ Radeon 8060S (gfx1151) | vLLM | ar | full1651-c1 | FAIL | 18.473 | 86.535 | 0.0541 | 54.7 |
| amd-strix-halo-halo3 | 1× AMD Ryzen AI Max+ 395 w/ Radeon 8060S (gfx1151) | vLLM | ar | sampled-30-from-584 | SAMPLED | 10.371 | 32.408 | 0.0964 | 80.9 |

\* Token/s is diagnostic only and is not comparable across different tokenizers.
