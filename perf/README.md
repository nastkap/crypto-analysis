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

##

## 7a. Unified Reports z Library Dropdown

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





