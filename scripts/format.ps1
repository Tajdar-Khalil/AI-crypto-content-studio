$ErrorActionPreference = "Stop"

python -m ruff format .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
