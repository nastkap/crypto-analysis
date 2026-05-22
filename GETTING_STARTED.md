# 🚀 Getting Started - ECIES Crypto Benchmark System

## Szybki start w 5 minut

### Krok 1: Wymagania systemowe

```bash
# Sprawdź czy masz zainstalowane:
minikube version
kubectl version --client
docker --version
```

**Jeśli brakuje:**
- **Minikube**: https://minikube.sigs.k8s.io/docs/start/
- **kubectl**: https://kubernetes.io/docs/tasks/tools/
- **Docker**: https://www.docker.com/products/docker-desktop

**Minimalne zasoby:**
- 4+ CPU cores
- 8GB+ RAM
- 20GB+ dysku

---

### Krok 2: Klonowanie projektu

```bash
git clone https://github.com/[TwójaOrganizacja]/crypto-analysis.git
cd crypto-analysis
```

---

### Krok 3: Uruchomienie Minikube

```bash
# Zainstaluj Minikube z Calico (dla Network Policies)
minikube start --cni=calico --cpus=4 --memory=8192

# Włącz Ingress addon
minikube addons enable ingress

# Weryfikacja
kubectl get nodes
```

**Spodziewany wynik:**
```
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   2m    v1.28.0
```

---

### Krok 4: Deploy systemu Kubernetes

```bash
# Przejdź do katalogu k8s
cd k8s

# Deploy wszystkich zasobów (kustomize)
kubectl apply -k .

# Czekaj ~30 sekund na uruchomienie się podów
kubectl get pods -n crypto-perf -w

# Sprawdzenie statusu
kubectl get all -n crypto-perf
```

**Spodziewany wynik - wszystkie pody powinny być RUNNING:**
```
NAME                                 READY   STATUS    RESTARTS
pod/postgres-xyz                     1/1     Running   0
pod/redis-abc                        1/1     Running   0
pod/benchmark-controller-def         1/1     Running   0
pod/node-py-crypto-ghi               1/1     Running   0
pod/node-py-pycryptodome-jkl         1/1     Running   0
pod/node-cpp-openssl-mno             1/1     Running   0
pod/node-cpp-cryptopp-pqr            1/1     Running   0
```

---

### Krok 5: Dostęp do API

```bash
# Port-forward do Controller API
kubectl port-forward svc/benchmark-controller 8000:8000 -n crypto-perf

# W innym terminalu - test API
curl http://localhost:8000/api/benchmark

# Spodziewany wynik - OK response
```

---

### Krok 6: Weryfikacja systemu

```bash
# 1. Sprawdź Deployments
kubectl get deployments -n crypto-perf
# Powinno być: 7 deploymentów (1/1 ready każdy)

# 2. Sprawdzenie Resource Usage
kubectl top pods -n crypto-perf
# Powinno być: CPU w millicores, Memory w MB

# 3. Sprawdzenie Network Policies
kubectl get networkpolicies -n crypto-perf
# Powinno być: 6 policies

# 4. Test PostgreSQL
kubectl run -it test-db --image=alpine -n crypto-perf -- \
  sh -c "apk add postgresql-client; \
  psql -h postgres -U benchmark -d benchmark -c 'SELECT 1'"
# Spodziewany wynik: ?column? = 1
```

---

### Krok 7: Uruchomienie testów K6 (opcjonalnie)

```bash
# Zainstaluj K6
# Windows: choco install k6
# Mac: brew install k6
# Linux: apt-get install k6

cd ../perf

# Uruchom performance testy
./run_performance_k6.ps1

# Czekaj na wyniki (~5-10 minut)
# Raporty w: perf/results/performance/
```

---

## 📊 Analiza wyników

### Gdzie znaleźć wyniki?

```
perf/
├── results/
│   ├── performance/
│   │   ├── CPP_CryptoPP-perf-1-*.json
│   │   ├── CPP_OpenSSL-perf-1-*.json
│   │   ├── Python_Cryptography-perf-1-*.json
│   │   └── Python_PyCryptodome-perf-1-*.json
│   └── reports/
│       └── performance-report.html
```

### Jak generować raporty?

```bash
# Przejdź do katalogu perf/dashboard
cd perf/dashboard

# Generuj HTML report
python build_performance_report.py

# Otwórz w przeglądarce
# performance-report.html
```

---

## 🧹 Czyszczenie

```bash
# Usunięcie całego namespace Kubernetes
kubectl delete namespace crypto-perf

# Zatrzymanie Minikube
minikube stop

# Usunięcie Minikube (jeśli chcesz całkowicie wyczyścić)
minikube delete
```

---

## ⚡ Automatyzacja - Uruchomienie całego benchmarku

### Szybki start za jedną komendę

```bash
# Wszystko naraz (minikube + K8s + testy + raporty)
./run_complete_benchmark.ps1

# Czeka ~15-20 minut na wyniki
```

**Co robi:**
1. ✅ Uruchamia Minikube
2. ✅ Deployuje K8s system
3. ✅ Czeka aż pody się uruchomią
4. ✅ Uruchamia K6 performance testy
5. ✅ Zbiera wyniki do PostgreSQL
6. ✅ Generuje HTML report
7. ✅ Otwiera raport w przeglądarce

**Plik:** `run_complete_benchmark.ps1`

---

## 📚 Dodatkowe dokumenty

| Plik | Opis |
|------|------|
| [k8s/INTEGRATION_GUIDE.md](k8s/INTEGRATION_GUIDE.md) | Jak K6 testy korzystają z K8s |
| [k8s/KUBERNETES_ARCHITECTURE.md](k8s/KUBERNETES_ARCHITECTURE.md) | Pełna architektura systemu |
| [k8s/QUICKSTART.md](k8s/QUICKSTART.md) | Szczegółowe instrukcje wdrażania |
| [k8s/ADVANCED_MECHANISMS.md](k8s/ADVANCED_MECHANISMS.md) | Resource Limits, Network Policies, Scheduling |
| [k8s/ZADANIE_3_PREZENTACJA.md](k8s/ZADANIE_3_PREZENTACJA.md) | Testowanie i weryfikacja |
| [DEPLOYMENT_GUIDE.md](k8s/DEPLOYMENT_GUIDE.md) | Wdrażanie na AWS/Azure/GCP |
| [README.md](README.md) | Przegląd projektu |

---

## 🔧 Troubleshooting

### Problem: Pody się nie startują (CrashLoopBackOff)

```bash
# Sprawdź logi
kubectl logs <pod-name> -n crypto-perf --previous

# Sprawdzenie details
kubectl describe pod <pod-name> -n crypto-perf

# Możliwe przyczyny:
# - Image nie znaleziony
# - Out of memory
# - Database connection error
```

### Problem: Brak dostępu do API

```bash
# Sprawdzenie port-forward
kubectl port-forward svc/benchmark-controller 8000:8000 -n crypto-perf

# Testowanie bezpośredniego dostępu
kubectl exec -it <controller-pod> -n crypto-perf -- curl localhost:8000/health

# Sprawdzenie Network Policies
kubectl get networkpolicies -n crypto-perf
```

### Problem: Brak pamięci (OOM)

```bash
# Zwiększ RAM w Minikube
minikube stop
minikube start --memory=12288  # 12GB zamiast 8GB
```

### Problem: PostgreSQL nie łączy się

```bash
# Sprawdzenie PostgreSQL poda
kubectl logs deployment/postgres -n crypto-perf

# Test połączenia
kubectl port-forward svc/postgres 5432:5432 -n crypto-perf
# W innym terminalu:
psql -h localhost -U benchmark -d benchmark
```

---

## ✅ Checklist - Czy system działa?

- [ ] `kubectl get nodes` - Minikube ready
- [ ] `kubectl get pods -n crypto-perf` - 7 podów RUNNING
- [ ] `kubectl top pods -n crypto-perf` - CPU/Memory widoczny
- [ ] `curl http://localhost:8000/api/benchmark` - API responds
- [ ] `kubectl get networkpolicies -n crypto-perf` - 6 policies
- [ ] PostgreSQL test - SELECT 1 zwraca wynik
- [ ] K6 testy - wyniki w JSON

---

## 📞 Wsparcie

Jeśli napotkasz problem:

1. Sprawdź dokumentację: [k8s/KUBERNETES_ARCHITECTURE.md](k8s/KUBERNETES_ARCHITECTURE.md)
2. Uruchom troubleshooting komendy z sekcji wyżej
3. Sprawdzą logi: `kubectl logs <pod> -n crypto-perf`
4. Otwórz issue na GitHub

---

## 🎯 Co się dzieje pod spodem?

```
1. Minikube uruchamia Kubernetes cluster
2. kubectl apply -k k8s/ deployuje:
   - PostgreSQL (baza danych)
   - Redis (message broker)
   - Benchmark Controller (orkiestracja)
   - 4 Crypto Nodes (implementacje bibliotek)
3. Ingress router kieruje HTTP traffic
4. Network Policies izolują ruch
5. K6 testy wysyłają żądania do Controller
6. Wyniki zapisywane do PostgreSQL
7. Raporty generowane z wyników
```

---

## 🚀 Następne kroki

### Jeśli system działa ✅

1. **Uruchom testy**: `perf/run_all_k6.ps1`
2. **Generuj raporty**: `perf/dashboard/build_performance_report.py`
3. **Analizuj wyniki**: Otwórz `perf/dashboard/*.html`

### Jeśli chcesz eksperymentować

1. Zmień resource limits w `k8s/nodes.yaml`
2. Dodaj nowe Network Policies
3. Skaluj pody: `kubectl scale deployment <name> --replicas=2 -n crypto-perf`
4. Monitoruj: `kubectl top pods -n crypto-perf -w`

### Jeśli chcesz wdrożyć na produkcję

1. Przeczytaj: [k8s/DEPLOYMENT_GUIDE.md](k8s/DEPLOYMENT_GUIDE.md)
2. Zmień storage provisioner
3. Zmień Ingress controller
4. Ustaw monitoring/logging

---

**Gotowy do testowania?** ✨

Uruchom:
```bash
minikube start --cni=calico --cpus=4 --memory=8192
kubectl apply -k k8s/
kubectl get pods -n crypto-perf -w
```

**Powodzenia! 🎉**
