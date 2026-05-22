Param(
    [switch]$SkipTests,
    [string]$ResultsDir = "perf/results",
    [string]$DashboardOutput = "perf/dashboard/index.html"
)

$ErrorActionPreference = "Stop"

if (-not $SkipTests) {
    Write-Host "[1/4] Performance tests"
    powershell -ExecutionPolicy Bypass -File "perf/run_performance_k6.ps1"

    Write-Host "[2/4] Stability tests"
    powershell -ExecutionPolicy Bypass -File "perf/run_stability_k6.ps1"

    Write-Host "[3/4] Scalability tests"
    powershell -ExecutionPolicy Bypass -File "perf/run_scalability_k6.ps1"
}

Write-Host "[4/4] Building reports"
python "perf/dashboard/build_performance_report.py" --results-dir "$ResultsDir" --output "perf/dashboard/performance-report.html"
python "perf/dashboard/build_stability_report.py" --results-dir "$ResultsDir" --output "perf/dashboard/stability-report.html"
python "perf/dashboard/build_scalability_report.py" --results-dir "$ResultsDir" --output "perf/dashboard/scalability-report.html"
python "perf/dashboard/build_dashboard.py" --results-dir "$ResultsDir" --output "$DashboardOutput"

Write-Host "Report pipeline completed. Dashboard: $DashboardOutput"
