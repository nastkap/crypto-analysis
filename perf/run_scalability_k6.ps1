Param(
    [string]$OutDir = "perf/results/scalability",
    [int[]]$Payloads = @(1, 10485760, 104857600),
    [string]$RampUp1 = "45s",
    [string]$RampUp2 = "45s",
    [string]$RampUp3 = "45s",
    [string]$Hold = "45s",
    [string]$RampDown = "30s"
)

$ErrorActionPreference = "Stop"

$targets = @(
    @{ Name = "Python_Cryptography"; Url = "http://localhost:8001" },
    @{ Name = "Python_PyCryptodome"; Url = "http://localhost:8002" },
    @{ Name = "CPP_OpenSSL"; Url = "http://localhost:8003" },
    @{ Name = "CPP_CryptoPP"; Url = "http://localhost:8004" }
)

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

foreach ($target in $targets) {
    foreach ($payload in $Payloads) {
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $summaryFile = Join-Path $OutDir "$($target.Name)-scalability-$payload-$timestamp-summary.json"

        Write-Host "[SCALABILITY] Running $($target.Name), payload=$payload bytes"

        k6 run `
            -e TARGET_URL=$($target.Url) `
            -e NODE_NAME=$($target.Name) `
            -e PAYLOAD_BYTES=$payload `
            -e RAMP_UP_1=$RampUp1 `
            -e RAMP_UP_2=$RampUp2 `
            -e RAMP_UP_3=$RampUp3 `
            -e HOLD=$Hold `
            -e RAMP_DOWN=$RampDown `
            --summary-export=$summaryFile `
            perf/k6/scalability.js
    }
}

Write-Host "Scalability tests completed. Results in: $OutDir"
