#!/usr/bin/env pwsh
# run_complete_benchmark.ps1
# Automatyczne uruchomienie pełnego benchmarku: Minikube + K8s + K6 + Raporty

param(
    [switch]$SkipMinikube,
    [switch]$SkipK6,
    [switch]$SkipReports
)

# Kolory wyjścia
function Write-Step { Write-Host "▶ $args" -ForegroundColor Cyan }
function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Error-Custom { Write-Host "✗ $args" -ForegroundColor Red }
function Write-Info { Write-Host "ℹ $args" -ForegroundColor Yellow }

# Krok 1: Sprawdzenie wymaganych narzędzi
Write-Step "Sprawdzanie wymaganych narzędzi..."

$tools = @('minikube', 'kubectl', 'k6', 'docker')
$missing_tools = @()

foreach ($tool in $tools) {
    try {
        if ($tool -eq 'minikube') { $version = minikube version 2>&1 }
        elseif ($tool -eq 'kubectl') { $version = kubectl version --client --short 2>&1 }
        elseif ($tool -eq 'k6') { $version = k6 version 2>&1 }
        elseif ($tool -eq 'docker') { $version = docker --version 2>&1 }
        
        Write-Success "$tool zainstalowany: $($version.Split([Environment]::NewLine)[0])"
    } catch {
        $missing_tools += $tool
        Write-Error-Custom "$tool nie znaleziony! Zainstaluj go zanim uruchomisz ten skrypt."
    }
}

if ($missing_tools.Count -gt 0) {
    Write-Error-Custom "Brakujące narzędzia: $($missing_tools -join ', ')"
    exit 1
}

Write-Success "Wszystkie narzędzia zainstalowane!"

# Krok 2: Uruchomienie Minikube
if (-not $SkipMinikube) {
    Write-Step "Uruchamianie Minikube..."
    
    # Sprawdzenie czy Minikube już działa
    $minikube_status = minikube status 2>&1
    if ($minikube_status -like "*Running*") {
        Write-Info "Minikube już działa"
    } else {
        Write-Info "Startowanie Minikube (może to potrwać ~1-2 minuty)..."
        minikube start --cni=calico --cpus=4 --memory=8192 --disk-size=20gb
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Błąd przy uruchamianiu Minikube!"
            exit 1
        }
        
        Write-Success "Minikube uruchomiony!"
    }
    
    # Włączenie Ingress addon
    Write-Info "Włączanie Ingress addon..."
    minikube addons enable ingress
    Write-Success "Ingress enabled!"
}

# Krok 3: Deploy K8s
Write-Step "Deployowanie systemu Kubernetes..."

$current_dir = Get-Location
$k8s_dir = Join-Path $current_dir "k8s"

if (-not (Test-Path $k8s_dir)) {
    Write-Error-Custom "Katalog k8s/ nie znaleziony!"
    exit 1
}

Write-Info "Aplikowanie manifestów z kustomize..."
kubectl apply -k $k8s_dir

if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Błąd przy deployowaniu K8s!"
    exit 1
}

# Czekanie aż pody się uruchomią
Write-Step "Czekanie na uruchomienie się podów (max 2 minuty)..."
$timeout = 120
$start_time = Get-Date
$all_ready = $false

while ((Get-Date) -lt $start_time.AddSeconds($timeout)) {
    $pods = kubectl get pods -n crypto-perf --no-headers 2>&1
    $total = $pods.Count
    $running = ($pods | Select-String "Running").Count
    
    Write-Info "Pody: $running/$total running"
    
    if ($running -eq 7) {
        $all_ready = $true
        break
    }
    
    Start-Sleep -Seconds 3
}

if (-not $all_ready) {
    Write-Error-Custom "Timeout! Nie wszystkie pody się uruchomiły w ciągu 2 minut."
    Write-Info "Sprawdź: kubectl get pods -n crypto-perf"
    exit 1
}

Write-Success "Wszystkie pody running!"

# Czekanie na Ingress
Write-Step "Czekanie na Ingress..."
Start-Sleep -Seconds 5

kubectl get pods -n crypto-perf
Write-Success "System Kubernetes gotowy!"

# Krok 4: Uruchomienie K6 testów
if (-not $SkipK6) {
    Write-Step "Port-forward do Controller API..."
    
    # Uruchomienie port-forward w tle
    $pf_job = Start-Process -NoNewWindow -PassThru kubectl -ArgumentList "port-forward svc/benchmark-controller 8000:8000 -n crypto-perf"
    Write-Success "Port-forward uruchomiony (PID: $($pf_job.Id))"
    
    # Czekanie na dostęp
    Write-Info "Czekanie na dostęp do API..."
    $wait_count = 0
    while ($wait_count -lt 30) {
        try {
            $response = curl.exe -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/benchmark -X POST
            if ($response -eq "200") {
                Write-Success "API dostępny!"
                break
            }
        } catch {}
        
        Start-Sleep -Seconds 1
        $wait_count++
    }
    
    if ($wait_count -eq 30) {
        Write-Error-Custom "API niedostępny po 30 sekundach"
        Stop-Process -Id $pf_job.Id
        exit 1
    }
    
    # Uruchomienie K6 testów
    Write-Step "Uruchamianie K6 performance testów..."
    Write-Info "Będzie to trwać ~2 godziny..."
    
    $perf_dir = Join-Path $current_dir "perf"
    $k6_script = Join-Path $perf_dir "k6\benchmark.js"
    
    if (-not (Test-Path $k6_script)) {
        Write-Error-Custom "Skrypt K6 nie znaleziony: $k6_script"
        Stop-Process -Id $pf_job.Id
        exit 1
    }
    
    k6 run $k6_script
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "K6 testy nie przeszły pomyślnie!"
        Stop-Process -Id $pf_job.Id
        exit 1
    }
    
    Write-Success "K6 testy zakończone!"
    
    # Zatrzymanie port-forward
    Stop-Process -Id $pf_job.Id
    Write-Success "Port-forward zatrzymany"
}

# Krok 5: Generowanie raportów
if (-not $SkipReports) {
    Write-Step "Generowanie raportów..."
    
    $dashboard_dir = Join-Path $current_dir "perf\dashboard"
    $report_script = Join-Path $dashboard_dir "build_performance_report.py"
    
    if (-not (Test-Path $report_script)) {
        Write-Error-Custom "Skrypt raportu nie znaleziony: $report_script"
        exit 1
    }
    
    Write-Info "Budowanie performance report..."
    python $report_script
    
    if ($LASTEXITCODE -eq 0) {
        $report_html = Join-Path $dashboard_dir "performance-report.html"
        if (Test-Path $report_html) {
            Write-Success "Raport wygenerowany: $report_html"
            
            # Otworzenie raportu w przeglądarce
            Write-Info "Otwieranie raportu w przeglądarce..."
            Start-Process $report_html
        }
    } else {
        Write-Error-Custom "Błąd przy generowaniu raportu"
    }
}


