#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
  "${PYTHON:-python3}" -m venv .venv
fi
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
PLAYWRIGHT_SKIP_BROWSER_GC=1 .venv/bin/python -m playwright install chromium
exec .venv/bin/python build.py "$@"
