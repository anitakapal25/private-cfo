#!/usr/bin/env bash
set -euo pipefail

repository_root="$(git rev-parse --show-toplevel)"
cd "$repository_root"

run() {
  printf '\n==> %s\n' "$1"
  shift
  "$@"
}

run 'Repository guardrails' python scripts/check_repository_guardrails.py
run 'Documentation integrity' python scripts/check_documentation.py
run 'Dependency health and deprecation audit' python scripts/check_dependency_health.py
run 'Backend tests' bash -c 'cd backend && python -m pytest -q'
run 'Frontend lint' bash -c 'cd frontend && npm run lint'
run 'Frontend type check' bash -c 'cd frontend && npm run type-check'
run 'Frontend production build' bash -c 'cd frontend && npm run build'
run 'Frontend browser journeys' bash -c 'cd frontend && CI=1 npm run test:e2e'

if command -v cargo >/dev/null 2>&1; then
  run 'Desktop formatter' bash -c 'cd frontend/src-tauri && cargo fmt --check'
  run 'Desktop tests' bash -c 'cd frontend/src-tauri && cargo test'
else
  printf '%s\n' 'cargo is required to verify the desktop companion.' >&2
  exit 1
fi

printf '\nAll local release checks passed.\n'
