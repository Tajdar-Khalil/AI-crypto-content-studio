$ErrorActionPreference = "Stop"

$commands = @(
    @{ Name = "Python syntax"; Args = @("-m", "compileall", "-q", "app.py", "content_studio", "tests") },
    @{ Name = "Pytest"; Args = @("-m", "pytest", "-q") },
    @{ Name = "Ruff lint"; Args = @("-m", "ruff", "check", ".") },
    @{ Name = "Mypy"; Args = @("-m", "mypy", "content_studio") }
)

foreach ($command in $commands) {
    Write-Host "`n== $($command.Name) ==" -ForegroundColor Cyan
    $argsList = $command.Args
    & python @argsList
    if ($LASTEXITCODE -ne 0) {
        Write-Host "$($command.Name) failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "`nAll checks passed." -ForegroundColor Green
