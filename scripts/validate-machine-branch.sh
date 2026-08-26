#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BASE_REF=${BASE_REF:-kickoff}
BRANCH=${MACHINE_BRANCH:-${GITHUB_HEAD_REF:-${GITHUB_REF_NAME:-$(git -C "$ROOT" branch --show-current)}}}
[[ "$BRANCH" =~ ^machine/([a-z0-9][a-z0-9-]{2,63})$ ]] \
    || { printf 'ERROR: not a machine branch: %s\n' "$BRANCH" >&2; exit 1; }
MACHINE_ID=${BASH_REMATCH[1]}
mapfile -t changed < <(
    {
        git -C "$ROOT" diff --name-only "$BASE_REF...HEAD"
        git -C "$ROOT" diff --name-only
        git -C "$ROOT" diff --cached --name-only
        git -C "$ROOT" ls-files --others --exclude-standard
    } | sort -u
)
for path in "${changed[@]}"; do
    case "$path" in
        "machines/$MACHINE_ID.json"|"results/$MACHINE_ID/"*) ;;
        *) printf 'ERROR: machine branch changed shared path: %s\n' "$path" >&2; exit 1 ;;
    esac
done
printf 'PASS: machine branch only changes profile/results for %s\n' "$MACHINE_ID"
