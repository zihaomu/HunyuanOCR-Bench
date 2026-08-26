#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VENDOR=${1:?usage: new-machine-branch.sh amd|nvidia MACHINE_ID}
MACHINE_ID=${2:?usage: new-machine-branch.sh amd|nvidia MACHINE_ID}
[[ "$VENDOR" == amd || "$VENDOR" == nvidia ]] || { printf 'ERROR: vendor must be amd or nvidia\n' >&2; exit 1; }
[[ "$MACHINE_ID" =~ ^${VENDOR}-[a-z0-9][a-z0-9-]{2,60}$ ]] \
    || { printf 'ERROR: machine id must start with %s- and use lowercase kebab-case\n' "$VENDOR" >&2; exit 1; }
[[ -z "$(git -C "$ROOT" status --short)" ]] || { printf 'ERROR: worktree must be clean\n' >&2; exit 1; }
git -C "$ROOT" show-ref --verify --quiet refs/heads/kickoff \
    || { printf 'ERROR: local kickoff branch does not exist\n' >&2; exit 1; }
git -C "$ROOT" switch -c "machine/$MACHINE_ID" kickoff
cp "$ROOT/machines/templates/$VENDOR.json" "$ROOT/machines/$MACHINE_ID.json"
python3 - "$ROOT/machines/$MACHINE_ID.json" "$MACHINE_ID" <<'PY'
import json,sys
from pathlib import Path
path=Path(sys.argv[1]); payload=json.loads(path.read_text()); payload['machine_id']=sys.argv[2]
path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
PY
printf 'Created branch machine/%s and profile machines/%s.json\n' "$MACHINE_ID" "$MACHINE_ID"
