Param(
    [switch]$SkipTests,
    [string]$ResultsDir = "perf/results",
    [string]$DashboardOutput = "perf/dashboard/index.html"
)

$ErrorActionPreference = "Stop"







Write-Host " Zapisywanie wynikow do bazy PostgreSQL..."


$files = Get-ChildItem "$ResultsDir\*-raw.json"

foreach ($file in $files) {
    $baseName = $file.BaseName
    
    # 1. Wyciągnięcie nazwy biblioteki (pierwszy człon do myślnika)
    $lib = $baseName.Split('-')[0]
    
    # 2. Ustalenie typu testu
  
    if ($baseName -match "-perf1-") { $testType = "PerformanceS1" }
    elseif ($baseName -match "-perf2-") { $testType = "PerformanceS2" }
    elseif ($baseName -match "-scalabilitys3-") { $testType = "ScalabilityS3" }
    elseif ($baseName -match "-scalabilitys4-") { $testType = "ScalabilityS4" }
    elseif ($baseName -match "-stabilitys5-") { $testType = "StabilityS5" }
    else { continue } # Jeśli plik nie pasuje, pomiń go

    # 3. Wyciągnięcie rozmiaru (liczba znajdująca się przed datą np. "2026")
    $sizeMatch = [regex]::match($baseName, '-(\d+)-202\d')
    $size = 0
    
    if ($sizeMatch.Success) {
        $rawSize = [long]$sizeMatch.Groups[1].Value
        # Jeśli rozmiar jest ogromny (np. 10485760), przeliczamy bajty na MB
        if ($rawSize -gt 1000) { 
            $size = [math]::Round($rawSize / 1048576) 
        } else { 
            # Jeśli to już jest "1", to zostawiamy
            $size = $rawSize 
        }
    }

    Write-Host "-> Importuje dane: Biblioteka=$lib, Typ=$testType, Rozmiar=$size MB"
    
    # Uruchomienie skryptu Pythona ze wszystkimi argumentami
    python "perf/dashboard/import_k6_to_postgres.py" `
        --file $file.FullName `
        --type $testType `
        --lib $lib `
        --size $size
}

Write-Host "Potok testowy zakonczony."