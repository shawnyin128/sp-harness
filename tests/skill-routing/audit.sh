#!/usr/bin/env bash
# Skill Routing Audit — run each scenario in corpus/ 3 times against headless
# Claude CLI, then pass results to tally.py for verdict classification.
#
# Usage:
#   ./audit.sh                        # run all scenarios
#   ./audit.sh --scenario=<id>        # run one scenario (id or filename stem)
#
# Dependencies:
#   - `claude` CLI on PATH (the Claude Code headless runner)
#   - python3 3.9+ (stdlib only, handles parsing, JSON, timeout, tally.py)
#
# Exit code: propagated from tally.py (0 = clean, 1 = any FAIL/FLAKY).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORPUS_DIR="$SCRIPT_DIR/corpus"
TEMPLATE="$SCRIPT_DIR/prompt-template.txt"
TALLY="$SCRIPT_DIR/tally.py"

VOTES_PER_SCENARIO=3
TIMEOUT_SECONDS=30

# --- preflight ---

if ! command -v claude >/dev/null 2>&1; then
  echo "error: \`claude\` CLI not found on PATH. Install Claude Code or adjust PATH." >&2
  exit 2
fi

if [[ ! -f "$TEMPLATE" ]]; then
  echo "error: prompt template not found at $TEMPLATE" >&2
  exit 2
fi

if [[ ! -f "$TALLY" ]]; then
  echo "error: tally.py not found at $TALLY" >&2
  exit 2
fi

# --- arg parsing ---

FILTER_ID=""
for arg in "$@"; do
  case "$arg" in
    --scenario=*) FILTER_ID="${arg#--scenario=}" ;;
    -h|--help)
      sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "error: unknown arg $arg" >&2; exit 2 ;;
  esac
done

# --- scenario discovery ---

shopt -s nullglob
# Initialize explicitly — on bash 3.2 with nullglob, assigning from an empty
# glob can leave the array unset, which trips `set -u` at first reference.
ALL_SCENARIOS=()
ALL_SCENARIOS=("$CORPUS_DIR"/*.md)

SCENARIOS=()
if [[ -n "$FILTER_ID" ]]; then
  # --scenario filter: error if no match, regardless of empty-corpus status.
  if [[ ${#ALL_SCENARIOS[@]} -gt 0 ]]; then
    for f in "${ALL_SCENARIOS[@]}"; do
      stem=$(basename "$f" .md)
      if [[ "$stem" == "$FILTER_ID" ]]; then
        SCENARIOS+=("$f")
      fi
    done
  fi
  if [[ ${#SCENARIOS[@]} -eq 0 ]]; then
    echo "error: no scenario matches --scenario=$FILTER_ID" >&2
    exit 2
  fi
elif [[ ${#ALL_SCENARIOS[@]} -eq 0 ]]; then
  echo "no scenarios in $CORPUS_DIR (expected corpus/*.md)"
  echo '{"scenarios": []}' | python3 "$TALLY"
  exit $?
else
  SCENARIOS=("${ALL_SCENARIOS[@]}")
fi

# --- main loop ---

TMPDIR_RUN="$(mktemp -d -t skill-routing-audit-XXXXXX)"
trap 'rm -rf "$TMPDIR_RUN"' EXIT

# We accumulate per-scenario JSON records into results.json, one per line.
# After the loop, a small python pass wraps them in the outer schema.
RECORDS="$TMPDIR_RUN/records.ndjson"
: > "$RECORDS"

for scenario_file in "${SCENARIOS[@]}"; do
  stem=$(basename "$scenario_file" .md)

  # Extract id, expected, body via python (no shell-quoted interpolation).
  parsed_json=$(python3 - "$scenario_file" <<'PYEOF'
import sys, re, pathlib, json
p = pathlib.Path(sys.argv[1])
txt = p.read_text()
m = re.match(r"^---\n(.*?)\n---\n(.*)\Z", txt, re.DOTALL)
if not m:
    sys.stderr.write(f"malformed frontmatter in {p}\n"); sys.exit(1)
fm, body = m.group(1), m.group(2)
sid = re.search(r"^id:\s*(.+)$", fm, re.MULTILINE)
sex = re.search(r"^expected:\s*(.+)$", fm, re.MULTILINE)
if not (sid and sex):
    sys.stderr.write(f"missing id or expected in {p}\n"); sys.exit(1)
print(json.dumps({
    "id": sid.group(1).strip(),
    "expected": sex.group(1).strip(),
    "body": body.strip(),
}))
PYEOF
)

  # Pull fields via a small python filter (no bash eval of arbitrary content).
  sid=$(echo "$parsed_json" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
  sexpected=$(echo "$parsed_json" | python3 -c "import sys, json; print(json.load(sys.stdin)['expected'])")

  # Build the scenario-specific prompt by reading template + body from env.
  prompt_file="$TMPDIR_RUN/prompt-$sid.txt"
  SCENARIO_JSON="$parsed_json" \
  TEMPLATE_PATH="$TEMPLATE" \
  PROMPT_OUT="$prompt_file" \
    python3 - <<'PYEOF'
import os, json, pathlib
data = json.loads(os.environ["SCENARIO_JSON"])
tmpl = pathlib.Path(os.environ["TEMPLATE_PATH"]).read_text()
out = tmpl.replace("{{SCENARIO}}", data["body"])
pathlib.Path(os.environ["PROMPT_OUT"]).write_text(out)
PYEOF

  echo "→ $sid (expected=$sexpected) ..."

  # Spawn 3 parallel votes via a Python helper that handles timeouts.
  PROMPT_FILE="$prompt_file" \
  SCENARIO_ID="$sid" \
  SCENARIO_EXPECTED="$sexpected" \
  VOTES_PER_SCENARIO="$VOTES_PER_SCENARIO" \
  TIMEOUT_SECONDS="$TIMEOUT_SECONDS" \
    python3 - >> "$RECORDS" <<'PYEOF'
import os, re, json, subprocess, concurrent.futures, pathlib

prompt_text = pathlib.Path(os.environ["PROMPT_FILE"]).read_text()
sid = os.environ["SCENARIO_ID"]
expected = os.environ["SCENARIO_EXPECTED"]
n = int(os.environ["VOTES_PER_SCENARIO"])
timeout = int(os.environ["TIMEOUT_SECONDS"])

# Cheap parseability check (no JSON parsing here — tally.py is authoritative).
# If no fenced JSON block is present we retry once before giving up.
FENCED_JSON_RE = re.compile(r"```json\s*\{.*?\}\s*```", re.DOTALL)

def _call_once() -> dict:
    try:
        proc = subprocess.run(
            ["claude", "--print", "--max-turns", "1"],
            input=prompt_text, capture_output=True, text=True, timeout=timeout,
        )
        return {"output": proc.stdout, "exit_code": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"output": "", "exit_code": 124}
    except Exception as e:
        return {"output": f"(spawn error: {e})", "exit_code": -1}

def vote() -> dict:
    result = _call_once()
    # Retry once if the response has no fenced JSON block or CLI errored.
    if result["exit_code"] != 0 or not FENCED_JSON_RE.search(result["output"] or ""):
        result = _call_once()
    return result

with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
    votes = list(pool.map(lambda _: vote(), range(n)))

print(json.dumps({"id": sid, "expected": expected, "votes": votes}))
PYEOF
done

# --- wrap records + tally ---

python3 - "$RECORDS" <<'PYEOF' | python3 "$TALLY"
import sys, json, pathlib
lines = [json.loads(l) for l in pathlib.Path(sys.argv[1]).read_text().splitlines() if l.strip()]
print(json.dumps({"scenarios": lines}))
PYEOF
