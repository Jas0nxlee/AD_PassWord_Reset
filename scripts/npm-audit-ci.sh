#!/usr/bin/env bash
set -uo pipefail

attempts="${NPM_AUDIT_ATTEMPTS:-3}"
timeout_seconds="${NPM_AUDIT_TIMEOUT_SECONDS:-60}"

for attempt in $(seq 1 "$attempts"); do
  audit_output="$(mktemp)"
  set +e
  python3 - "$timeout_seconds" "$audit_output" <<'PY'
import subprocess
import sys

timeout_seconds = int(sys.argv[1])
output_path = sys.argv[2]
try:
    result = subprocess.run(
        ['npm', 'audit'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    output = result.stdout or ''
    status = result.returncode
except subprocess.TimeoutExpired as error:
    output = error.stdout or ''
    if isinstance(output, bytes):
        output = output.decode('utf-8', errors='replace')
    output += f'\nnpm audit timed out after {timeout_seconds} seconds\n'
    status = 124

with open(output_path, 'w', encoding='utf-8') as output_file:
    output_file.write(output)
print(output, end='')
sys.exit(status)
PY
  audit_status="$?"
  set -e

  if [ "$audit_status" -eq 0 ]; then
    rm -f "$audit_output"
    exit 0
  fi

  if [ "$audit_status" -eq 124 ] || grep -Eqi 'socket hang up|ECONNRESET|ETIMEDOUT|EAI_AGAIN|ENETUNREACH|audit endpoint returned an error' "$audit_output"; then
    rm -f "$audit_output"
    if [ "$attempt" -lt "$attempts" ]; then
      echo "npm audit advisory service unavailable; retrying (${attempt}/${attempts})"
      sleep 10
      continue
    fi
    echo '::warning::npm audit advisory service was unavailable after all retries; continuing with the locked dependency set.'
    exit 0
  fi

  rm -f "$audit_output"
  exit "$audit_status"
done
