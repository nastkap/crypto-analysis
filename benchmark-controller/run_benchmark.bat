@echo off
echo ===================================================
echo   URUCHAMIANIE BENCHMARKU DLA PRACY MAGISTERSKIEJ
echo ===================================================

:: Aktywacja środowiska wirtualnego
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Srodowisko wirtualne aktywowane.
) else (
    echo UWAGA: Nie znaleziono srodowiska 'venv'. Testy moga sie nie udac.
)

:: Uruchomienie skryptu Pythona (1000 iteracji)
echo Rozpoczynam zbieranie danych. Prosze czekac...
python benchmark.py --iter 1000

echo.
echo ===================================================
echo ZAKONCZONO. Wcisnij dowolny klawisz, aby wyjsc.
pause >nul