Param(
    [string]$OutDir = "perf/results",
     [int[]]$Payloads = @(2, 10000000,50000000),
    [string]$Duration = "60s"
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
        $rawFile = Join-Path $OutDir "$($target.Name)-perf1-$payload-$timestamp-raw.json"

        Write-Host "[PERFS1] Running $($target.Name), payload=$payload bytes, duration=$Duration"

        k6 run `
            -e TARGET_URL=$($target.Url) `
            -e NODE_NAME=$($target.Name) `
            -e PAYLOAD_BYTES=$payload `
            -e DURATION=$Duration `
            -e VUS=1 `
            --out json=$rawFile `
            perf/k6/benchmark.js 
        
        
    }
}


