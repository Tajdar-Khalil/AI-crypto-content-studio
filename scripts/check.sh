#!/usr/bin/env sh
set -eu
python -m compileall -q app.py content_studio tests
python -m pytest -q
python -m ruff check .
python -m mypy content_studio
printf '\nAll checks passed.\n'
