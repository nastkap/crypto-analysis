# Performance Automation (k6 + Kubernetes + JSON + Dashboard)

Ten katalog wdraza porownanie bibliotek wg kryteriow:
- wydajnosc
- stabilnosc
- skalowalnosc

Zakres payloadu:
- 1 bajt
- 10 MB (10485760 B)
- 100 MB (104857600 B)

## 1. Kubernetes manifests

Manifesty sa w katalogu `k8s`.

Wdrozenie:

```powershell
kubectl apply -k k8s
kubectl get pods -n crypto-perf
```

Serwisy w klastrze:
- `node-py-crypto.crypto-perf.svc.cluster.local:8000`
- `node-py-pycryptodome.crypto-perf.svc.cluster.local:8000`
- `node-cpp-openssl.crypto-perf.svc.cluster.local:8000`
- `node-cpp-cryptopp.crypto-perf.svc.cluster.local:8000`

### PostgreSQL

Wdrozenie obejmuje teraz tez baze `PostgreSQL`:
- service: `postgres.crypto-perf.svc.cluster.local:5432`
- db: `benchmark`
- user: `benchmark`

Kontroler benchmarkow zapisuje kazde uruchomienie do DB (run + wyniki iteracji).

## 1a. Docker Compose z PostgreSQL

W `docker-compose.yml` dodany jest serwis `postgres` oraz `DATABASE_URL` w `benchmark-controller`.

Start lokalny:

```powershell
docker compose up -d --build
```

## 1b. Endpointy historii (PostgreSQL)

Nowe endpointy kontrolera:
- `GET /runs` - lista uruchomien benchmarkow z bazy
- `GET /runs/{run_id}` - szczegoly jednego uruchomienia
- `GET /runs/{run_id}/results` - szczegolowe pomiary z uruchomienia

Po `POST /benchmark` odpowiedz zawiera:
- `run_id`
- `stored_in_db`

## 2. Test wydajnosci (k6)

Skrypt glowny: `perf/k6/benchmark.js`

Przyklad uruchomienia:

```powershell
k6 run `
  -e TARGET_URL=http://localhost:8001 `
  -e NODE_NAME=Python_Cryptography `
  -e PAYLOAD_BYTES=10485760 `
  -e DURATION=1m `
  --summary-export=perf/results/summary.json `
  --out json=perf/results/raw.json `
  perf/k6/benchmark.js
```

Automatyczny batch dla 4 bibliotek x 3 payloady:

```powershell
powershell -ExecutionPolicy Bypass -File perf/run_performance_k6.ps1
```

## 3. Test stabilnosci (k6)

Skrypt: `perf/run_stability_k6.ps1`

Domyslnie wykonuje 3 powtorzenia dla kazdej biblioteki i payloadu,
co ulatwia wykrycie timeoutow i niestabilnych wynikow.

Uruchomienie:

```powershell
powershell -ExecutionPolicy Bypass -File perf/run_stability_k6.ps1
```

## 4. Test skalowalnosci (ramping VUs)

Skrypt scenariusza: `perf/k6/scalability.js`

Skrypt uruchamiajacy wszystkie biblioteki i payloady: `perf/run_scalability_k6.ps1`

Przyklad:

```powershell
k6 run `
  -e TARGET_URL=http://localhost:8003 `
  -e PAYLOAD_BYTES=10485760 `
  -e TARGET_VUS_1=5 `
  -e TARGET_VUS_2=15 `
  -e TARGET_VUS_3=30 `
  --summary-export=perf/results/scalability-summary.json `
  perf/k6/scalability.js
```

Lub pelny batch:

```powershell
powershell -ExecutionPolicy Bypass -File perf/run_scalability_k6.ps1
```

## 5. Skrypt zbiorczy (legacy)

Skrypt `perf/run_all_k6.ps1` nadal dziala i uruchamia scenariusz `benchmark.js`
na payloadach 1B, 10MB, 100MB. Zalecane jest jednak uzycie osobnych skryptow:

- `perf/run_performance_k6.ps1`
- `perf/run_stability_k6.ps1`
- `perf/run_scalability_k6.ps1`

## 6. CI/CD (GitHub Actions)

Workflow: `.github/workflows/k6-benchmark.yml`

Ustaw w repo Variables:
- `PY_CRYPTO_URL`
- `PY_PYCRYPTODOME_URL`
- `CPP_OPENSSL_URL`
- `CPP_CRYPTOPP_URL`

Workflow uruchamia matrix:
- 4 biblioteki
- 3 payloady (1B, 10MB, 100MB)
- wynik JSON jako artifact

## 7. Prosty dashboard HTML z JSON

Generator: `perf/dashboard/build_dashboard.py`

Uruchom:

```powershell
python perf/dashboard/build_dashboard.py --results-dir perf/results --output perf/dashboard/index.html
```

Potem otworz:
- `perf/dashboard/index.html`

Dashboard pokazuje teraz:
- porownania bibliotek per payload (1B, 10MB, 100MB)
- przelacznik: wydajnosc / stabilnosc / skalowalnosc
- automatyczne karty "najszybsza", "najwyzszy throughput", "najbardziej niezawodna"

## 7a. Pelna automatyzacja pod sprawozdanie

Jedna komenda uruchamia testy i buduje wszystkie raporty + dashboard:

```powershell
powershell -ExecutionPolicy Bypass -File perf/run_report_pipeline.ps1
```

Jesli masz juz wyniki i chcesz tylko odswiezyc wykresy:

```powershell
powershell -ExecutionPolicy Bypass -File perf/run_report_pipeline.ps1 -SkipTests
```

## 7b. Dashboard Stability per-library

Po przeprowadzeniu testów stability (`run_stability_k6.ps1`), wygeneruj raport per-library:

```powershell
python perf/dashboard/build_stability_report.py --results-dir perf/results --output-dir perf/dashboard/stability-reports
```

Raporty będą w `perf/dashboard/stability-reports/`.

Każdy raport pokazuje:
- **Tabelę repeaty** - porównanie Repeat 1, 2, 3 dla każdego payload'u
- **Wykresy** - liniowe porównanie p95, fail%, mismatch% między repeatami
- **Color coding** - zielony (OK), pomarańczowy (warn), czerwony (bad)

## 7c. Unified Reports z Library Dropdown

Zamiast per-library raportów, możesz wygenerować trzy ujednolicone raporty z dropdownem biblioteki:

### Performance Report
```powershell
python perf/dashboard/build_performance_report.py --results-dir perf/results --output perf/dashboard/performance-report.html
```

Raport pokazuje:
- Dropdown dla wybranej biblioteki
- Tabelę z metrykami: p50, p95, p99, avg, throughput, fail%
- Dla każdego payload'u (1B, 10MB, 100MB)

### Stability Report (Unified)
```powershell
python perf/dashboard/build_stability_report.py --results-dir perf/results --output perf/dashboard/stability-report.html
```

Raport pokazuje:
- Dropdown dla wybranej biblioteki
- Porównanie wszystkich repeatów dla każdego payload'u
- Wykresy liniowe: p95[ms] vs Fail%, Mismatch%
- Color coding metryk

### Scalability Report
```powershell
python perf/dashboard/build_scalability_report.py --results-dir perf/results --output perf/dashboard/scalability-report.html
```

Raport pokazuje:
- Dropdown dla wybranej biblioteki
- Wyniki testu VU ramping
- Tabela: Max VU, p95, throughput, fail%
- Dla każdego payload'u

## 7d. Dashboard Hub

Główny dashboard (`perf/dashboard/index.html`) zawiera teraz linki do wszystkich 3 raportów:
- **Performance Report** - Szczegółowa analiza wydajności
- **Stability Report** - Testy stabilności z multiplymi powtórzeniami
- **Scalability Report** - Testy skalowalności z ramping VU

Uruchom generator głównego dashboarda:
```powershell
python perf/dashboard/build_dashboard.py --results-dir perf/results --output perf/dashboard/index.html
```

## 7e. Pełna automatyzacja - generowanie wszystkich raportów

Polecenie do wygenerowania wszystkich raportów naraz:

```powershell
# Wygeneruj 3 raporty + główny dashboard
python perf/dashboard/build_performance_report.py; `
python perf/dashboard/build_stability_report.py; `
python perf/dashboard/build_scalability_report.py; `
python perf/dashboard/build_dashboard.py
```

Lub jeśli chcesz to w jednym skrypcie PowerShell, użyj `perf/run_report_pipeline.ps1`.

## 8. Metodologia porownania bibliotek

Ponizej jest minimalna metodologia pod raport:

### Wydajnosc
- Metryki glowne: `http_req_duration` (p50/p95/p99), `encrypt_duration_ms`, `decrypt_duration_ms`, `http_reqs`.
- Dla kazdej biblioteki uruchom ten sam scenariusz i te same payloady.
- Porownuj przede wszystkim p95 (nie sama srednia), bo lepiej pokazuje realna jakosc odpowiedzi pod obciazeniem.

### Stabilnosc
- Metryki glowne: `http_req_failed`, `decrypt_mismatch_rate`.
- Stabilny wynik oznacza:
  - bardzo niski `http_req_failed` (docelowo blisko 0),
  - `decrypt_mismatch_rate == 0` (brak blednych deszyfracji),
  - brak restartow podow i timeoutow podczas testu.

### Skalowalnosc
- Uzywaj `perf/k6/scalability.js` (ramping VUs).
- Obserwuj jak zmienia sie p95 oraz fail rate przy wzroscie liczby VU.
- Punkt zalamania to moment, w ktorym p95 i bledy rosna nieliniowo.

## 9. Profile testowe dla 1B, 10MB, 100MB

Praktyczny zestaw startowy (na ten projekt):

1. `1B` (`PAYLOAD_BYTES=1`)
  - Cel: narzut frameworka i biblioteki.
  - Sugestia: `VUS=20`, `DURATION=1m`.

2. `10MB` (`PAYLOAD_BYTES=10485760`)
  - Cel: typowe obciazenie aplikacyjne.
  - Sugestia: `VUS=5`, `DURATION=1m`.

3. `100MB` (`PAYLOAD_BYTES=104857600`)
  - Cel: graniczny przypadek pamiec/czas.
  - Sugestia: `VUS=1`, `DURATION=1m`.

W skrypcie `perf/k6/benchmark.js` jest juz automatyczny dobor VUS zaleznosci od rozmiaru payloadu (1B/10MB/100MB),
ale mozna go nadpisac przez `-e VUS=...`.

## 10. Gotowy schemat raportowania



