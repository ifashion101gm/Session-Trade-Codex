param(
    [string[]]$Symbols = @("EURUSD", "GBPUSD", "USDJPY", "XAUUSD.crp"),
    [string]$Config = "",
    [string]$Output = ""
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$entrypoint = Join-Path $projectRoot "sspf.py"
if (-not $Config) { $Config = Join-Path $projectRoot "config\strategy.yaml" }
if (-not $Output) { $Output = Join-Path $projectRoot "outputs" }

& python $entrypoint --config $Config health
if ($LASTEXITCODE -ne 0) { throw "SSPF health check failed with exit code $LASTEXITCODE" }

& python $entrypoint --config $Config readiness
if ($LASTEXITCODE -ne 0) { throw "SSPF readiness check failed with exit code $LASTEXITCODE" }

foreach ($symbol in $Symbols) {
    & python $entrypoint --config $Config analyze --symbol $symbol --output $Output
    if ($LASTEXITCODE -notin @(0, 3)) {
        throw "SSPF analysis failed for $symbol with exit code $LASTEXITCODE"
    }
}
