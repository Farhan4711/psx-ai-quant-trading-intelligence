#!/usr/bin/env bash
# Phase 5 Step 69 — automated security scan.
#
# Runs:
#   1. pip-audit on the Python deps
#   2. pnpm audit on the Node deps
#   3. ruff with the bandit (S) rule set on the backend source
#   4. basic curl checks of the production headers
#
# Exit non-zero on critical findings so CI can block merges.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FAILED=0
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

section() {
  echo
  echo "─── $1 ─────────────────────────────────────────────"
}

ok() {
  echo -e "${GREEN}✓${NC} $1"
}

warn() {
  echo -e "${YELLOW}⚠${NC} $1"
}

fail() {
  echo -e "${RED}✗${NC} $1"
  FAILED=$((FAILED + 1))
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    warn "$1 not installed — skipping the section that needs it. Install: $2"
    return 1
  }
}

# 1) Python deps -----------------------------------------------------------
section "Python deps (pip-audit)"
if require_cmd pip-audit "pip install pip-audit"; then
  cd "$REPO_ROOT/psx-api"
  if pip-audit --strict; then
    ok "No known CVEs in Python deps"
  else
    fail "pip-audit reported known CVEs"
  fi
  cd "$REPO_ROOT"
fi

# 2) Node deps -------------------------------------------------------------
section "Node deps (pnpm audit)"
if require_cmd pnpm "corepack enable && corepack prepare pnpm@9 --activate"; then
  cd "$REPO_ROOT/psx-web"
  if pnpm audit --audit-level high; then
    ok "No high+ severity issues in Node deps"
  else
    fail "pnpm audit reported high/critical issues"
  fi
  cd "$REPO_ROOT"
fi

# 3) Ruff bandit rules -----------------------------------------------------
section "Python source — ruff (bandit S rules)"
if require_cmd ruff "pip install ruff"; then
  cd "$REPO_ROOT/psx-api"
  if ruff check --select S psx_api/; then
    ok "No dangerous patterns flagged by ruff/bandit S rules"
  else
    fail "ruff/bandit flagged dangerous code"
  fi
  cd "$REPO_ROOT"
fi

# 4) Production header sanity check ----------------------------------------
section "Production headers"
PROD_URL="${PROD_URL:-https://psxai.example}"
if curl --silent --fail --head --max-time 10 "$PROD_URL" >/tmp/headers 2>/dev/null; then
  for h in "Strict-Transport-Security" "X-Content-Type-Options" "X-Frame-Options"; do
    if grep -qi "^$h:" /tmp/headers; then
      ok "$h present"
    else
      fail "$h missing on $PROD_URL"
    fi
  done
  rm -f /tmp/headers
else
  warn "Could not reach $PROD_URL — skipping header check (set PROD_URL env)"
fi

# Summary ------------------------------------------------------------------
echo
if [ "$FAILED" -eq 0 ]; then
  echo -e "${GREEN}All checks passed.${NC}"
  exit 0
else
  echo -e "${RED}${FAILED} check(s) failed. See SECURITY.md for triage steps.${NC}"
  exit 1
fi
