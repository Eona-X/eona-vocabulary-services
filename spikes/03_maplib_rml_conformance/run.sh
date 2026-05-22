#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Pin the rml-test-cases commit so re-runs hash-stable. Bump deliberately.
SUITE_COMMIT="${SUITE_COMMIT:-master}"
TARGET="inputs/rml-test-cases"

mkdir -p inputs
if [[ "${1:-}" == "--refresh-tests" ]] || [[ ! -d "$TARGET" ]]; then
  rm -rf "$TARGET"
  git clone --depth 1 https://github.com/kg-construct/rml-test-cases.git "$TARGET"
  (cd "$TARGET" && git fetch --depth 1 origin "$SUITE_COMMIT" && git checkout "$SUITE_COMMIT")
  echo "$SUITE_COMMIT" > inputs/.suite_commit
fi

# Morph-KGC is launched per-test via `uv run --isolated`; the spike's own
# venv has uv installed at spikes/venv/bin, but it isn't on PATH by
# default. Prepend it so run_suite.py's subprocess.run(["uv", ...]) works.
export PATH="$(cd .. && pwd)/venv/bin:$PATH"
exec ../.venv/bin/python run_suite.py
