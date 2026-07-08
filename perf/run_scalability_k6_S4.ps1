Param(
    [string]$OutDir = "perf/results",
    [int[]]$Payloads = @(1, 102400, 1048576, 10485760),  
    [int]$VUs = 5,
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
        
        if ($payload -lt 1024) {
            $sizeLabel = "$payload B"
        } elseif ($payload -lt 1048576) {
            $sizeLabel = "$([Math]::Round($payload / 1024, 1)) KB"
        } elseif ($payload -lt 1073741824) {
            $sizeLabel = "$([Math]::Round($payload / 1048576, 1)) MB"
        } else {
            $sizeLabel = "$([Math]::Round($payload / 1073741824, 1)) GB"
        }
        
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $rawFile = Join-Path $OutDir "$($target.Name)-scalabilitys4-$payload-$timestamp-raw.json"
        
        Write-Host "   Payload: $sizeLabel (bytes: $payload)"
        Write-Host "      File: $($rawFile | Split-Path -Leaf)"
        k6 run `
            -e TARGET_URL=$($target.Url) `
            -e NODE_NAME=$($target.Name) `
            -e PAYLOAD_BYTES=$payload `
            -e DURATION=$Duration `
            -e VUS=$VUs `
            --out json=$rawFile `
            perf/k6/benchmark.js 
       
    }
}

