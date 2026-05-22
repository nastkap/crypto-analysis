Param(
    [string]$OutDir = "perf/results/stability",
    [int[]]$Payloads = @(1, 10485760, 104857600),
    [string]$Duration = "5m",
    [int]$Repeats = 3
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

for ($i = 1; $i -le $Repeats; $i++) {
    foreach ($target in $targets) {
        foreach ($payload in $Payloads) {
            $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
            $summaryFile = Join-Path $OutDir "$($target.Name)-stability-r$i-$payload-$timestamp-summary.json"
            $rawFile = Join-Path $OutDir "$($target.Name)-stability-r$i-$payload-$timestamp-raw.json"

            Write-Host "[STABILITY] Run=$i/$Repeats, node=$($target.Name), payload=$payload bytes, duration=$Duration"

            k6 run `
                -e TARGET_URL=$($target.Url) `
                -e NODE_NAME=$($target.Name) `
                -e PAYLOAD_BYTES=$payload `
                -e DURATION=$Duration `
                --summary-export=$summaryFile `
                --out json=$rawFile `
                perf/k6/benchmark.js
        }
    }
}

Write-Host "Stability tests completed. Results in: $OutDir"
