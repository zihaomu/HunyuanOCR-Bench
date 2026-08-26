# Contributing Results

1. Base every hardware result branch on the same committed `kickoff` revision.
2. Name it `machine/<machine-id>` and keep the machine ID lowercase kebab-case.
3. Do not change protocol, source, tests, scripts, schema, or documentation on a
   machine branch.
4. Commit only `machines/<machine-id>.json` and `results/<machine-id>/`.
5. Include one canonical `result.json` per run and retain its verification files.
6. Do not hand-edit generated metric values or leaderboards.
7. State whether the run is AR or DFlash and report accelerator count.
8. Run `make check` and `./scripts/validate-machine-branch.sh` before pushing.

A pull request into `main` should explain the physical machine, runtime image
digest, endpoint method, and any observed departure from the paper reference.
