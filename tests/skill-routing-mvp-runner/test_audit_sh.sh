#!/usr/bin/env bash
# Evaluator tests for tests/skill-routing/audit.sh.
# Exercises error paths and CLI arg handling that don't require `claude` CLI.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AUDIT="$REPO_ROOT/tests/skill-routing/audit.sh"

pass=0
fail=0
fails=()

assert_eq() {
  local actual="$1" expected="$2" label="$3"
  if [[ "$actual" == "$expected" ]]; then
    pass=$((pass + 1))
    echo "✓ $label"
  else
    fail=$((fail + 1))
    fails+=("$label: expected=$expected actual=$actual")
    echo "✗ $label (expected=$expected actual=$actual)"
  fi
}

assert_contains() {
  local haystack="$1" needle="$2" label="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    pass=$((pass + 1))
    echo "✓ $label"
  else
    fail=$((fail + 1))
    fails+=("$label: missing '$needle' in output")
    echo "✗ $label (missing '$needle')"
  fi
}

# --- test 1: bash -n syntax check ---

if bash -n "$AUDIT" 2>/dev/null; then
  pass=$((pass + 1)); echo "✓ bash -n syntax clean"
else
  fail=$((fail + 1)); fails+=("syntax check"); echo "✗ bash -n syntax clean"
fi

# --- test 2: unknown arg exits non-zero with error ---

out=$("$AUDIT" --no-such-flag 2>&1 || true)
rc=$?
assert_contains "$out" "error" "unknown arg emits error"

out2=$("$AUDIT" --bad 2>&1) && rc2=0 || rc2=$?
if [[ $rc2 -ne 0 ]]; then
  pass=$((pass + 1)); echo "✓ unknown arg exits non-zero"
else
  fail=$((fail + 1)); fails+=("unknown arg exit"); echo "✗ unknown arg exits non-zero"
fi

# --- test 3: --help prints docs and exits zero ---

out=$("$AUDIT" --help 2>&1) && rc=0 || rc=$?
assert_eq "$rc" "0" "--help exits 0"
assert_contains "$out" "Skill Routing Audit" "--help contains title"
assert_contains "$out" "--scenario" "--help mentions --scenario"

# --- test 4: --scenario with nonexistent id errors clearly ---

out=$("$AUDIT" --scenario=definitely-not-a-real-scenario-xyz 2>&1) && rc=0 || rc=$?
if [[ $rc -ne 0 ]]; then
  pass=$((pass + 1)); echo "✓ bogus --scenario exits non-zero"
else
  fail=$((fail + 1)); fails+=("bogus --scenario exit")
  echo "✗ bogus --scenario exits non-zero (got rc=$rc)"
fi
assert_contains "$out" "no scenario matches" "bogus --scenario error is clear"

# --- test 5: preflight fails clearly when claude is not on PATH ---

out=$(PATH=/usr/bin:/bin "$AUDIT" --scenario=anything 2>&1) && rc=0 || rc=$?
if [[ $rc -ne 0 ]]; then
  pass=$((pass + 1)); echo "✓ missing claude CLI exits non-zero"
else
  fail=$((fail + 1)); fails+=("preflight exit"); echo "✗ preflight exit"
fi
assert_contains "$out" "claude" "preflight error names claude"

# --- summary ---

echo ""
echo "tests: $pass passed, $fail failed"
if [[ $fail -gt 0 ]]; then
  printf 'FAIL: %s\n' "${fails[@]}"
  exit 1
fi
exit 0
