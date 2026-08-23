param(
    [string]$EnvFile = "",
    [switch]$ShowOnly
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
if ([string]::IsNullOrWhiteSpace($EnvFile)) {
    $EnvFile = Join-Path $root "env.example"
}

if (-not (Test-Path $EnvFile)) {
    throw "Environment template not found: $EnvFile"
}

Write-Host "Loading environment template from: $EnvFile"

foreach ($line in Get-Content $EnvFile) {
    if ($line.Trim().StartsWith("#") -or [string]::IsNullOrWhiteSpace($line.Trim())) {
        continue
    }

    $parts = $line.Split("=", 2)
    if ($parts.Count -ne 2) {
        continue
    }

    $name = $parts[0].Trim()
    $value = $parts[1].Trim()

    if ($name -match "PASSWORD$" -and $value -like "REPLACE*") {
        Write-Host "Skipping unset placeholder for $name"
        continue
    }

    if ($ShowOnly) {
        Write-Host "$name=$value"
        continue
    }

    [Environment]::SetEnvironmentVariable($name, $value, "Process")
    Write-Host "Set $name"
}

if (-not $ShowOnly) {
    Write-Host ""
    Write-Host "Environment variables are now available in this PowerShell session."
    Write-Host "Copy the real values into a .env file, then load them with your shell or IDE." 
}
