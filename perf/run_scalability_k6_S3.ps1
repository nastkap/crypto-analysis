Param(
    [string]$OutDir = "perf/results",
    [int]$Payload = 10485760,  
    [string]$RampUp1 = "5s",    
    [string]$RampUp2 = "30s",   
    [string]$RampUp3 = "60s",   
    [string]$Hold = "90s",     
    [string]$RampDown = "5s"    
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
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $rawFile = Join-Path $OutDir "$($target.Name)-scalabilitys3-$Payload-$timestamp-raw.json"
    
    Write-Host "[SCALABILITY] Running $($target.Name) with ramping VUs, payload=$Payload bytes (10MB)"
    Write-Host "  Faza 1: 1 VU dla $RampUp1"
    Write-Host "  Faza 2: 5 VU dla $RampUp2"
    Write-Host "  Faza 3: 10 VU dla $RampUp3"
    Write-Host "  Faza 4: 25 VU dla $Hold"
    Write-Host "  Ramp-down: $RampDown"
  
    k6 run `
        -e TARGET_URL=$($target.Url) `
        -e NODE_NAME=$($target.Name) `
        -e PAYLOAD_BYTES=$Payload `
        -e RAMP_UP_1=$RampUp1 `
        -e RAMP_UP_2=$RampUp2 `
        -e RAMP_UP_3=$RampUp3 `
        -e HOLD=$Hold `
        -e RAMP_DOWN=$RampDown `
        --out json=$rawFile `
        perf/k6/benchmark.js 
}

