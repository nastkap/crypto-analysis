# System bezpiecznej wymiany wiadomości ECIES 

System do porównania wydajności implementacji szyfrowania ECIES w czterech bibliotekach kryptograficznych (cryptography, PyCryptodome, OpenSSL, Crypto++) zbudowany w architekturze mikrousług Docker Compose

**Zrealizowane warunki:** Opracowana architektura 6 usług (kontroler FastAPI + 4 węzły crypto + Redis) oraz Dockerfiles dla każdego mikroserwisu zgodnie z best practices. Obrazy zbudowane i pushowane na DockerHub jako multi-architecture (amd64/arm64) z wbudowanym SBOM. Wszystkie obrazy przeskanowane Trivy

**Docker-Compose & Diagram:** Plik docker-compose.dev.yml zawiera 7 best practices (wersjonowanie, moduły, wolumeny, zmienne środowiskowe, sieci, limity zasobów, health checks). System został testowany - wszystkie 6 kontenerów startuje, API odpowiada, Redis działa. Diagram architektury wygenerowany compose-viz pokazuje wszystkie serwisy, wolumeny, sieć i dependencje

## Bezpieczenstwo sekretow (.env)

- Nie commituj plikow z haslami i sekretami (`.env`, `.env.dev`, itp.).
- W repo trzymaj tylko pliki przykladowe, np. `.env.dev.example`.
- Lokalnie utworz wlasny plik `.env.dev` na podstawie `.env.dev.example`.

Jesli `.env.dev` byl juz wczesniej dodany do gita, usun go z indeksu (bez kasowania lokalnego pliku):

```bash
git rm --cached .env.dev
```

Nastepnie zacommituj zmiany, aby `.env.dev` przestal byc sledzony.

---

## Kubernetes Deployment (Zadanie 1 & 2)

Pełna konfiguracja Kubernetes dla tego systemu z zaawansowanymi mechanizmami.

### 📁 Katalog: `/k8s`

Zawiera:
- **12 manifestów YAML** - kompletna konfiguracja K8s
- **7 dokumentów MD** - 30,000+ słów dokumentacji
- **Zadanie 1**: Architektura Kubernetes (namespace, deployments, services, storage, ingress, RBAC)
- **Zadanie 2**: Zaawansowane mechanizmy (resource limits, network policies, scheduling constraints)

### 📖 Dokumentacja

**START TUTAJ** → [k8s/INDEX.md](k8s/INDEX.md) - Pełny indeks wszystkich dokumentów

#### Dokumenty Zadania 1 (Architektura)
- [k8s/README.md](k8s/README.md) - Przegląd (2,000 słów)
- [k8s/KUBERNETES_ARCHITECTURE.md](k8s/KUBERNETES_ARCHITECTURE.md) - Pełna architektura (13,000 słów)
- [k8s/QUICKSTART.md](k8s/QUICKSTART.md) - Praktyczne instrukcje (3,000 słów)
- [k8s/REQUIREMENT_MAPPING.md](k8s/REQUIREMENT_MAPPING.md) - Mapowanie wymagań (2,000 słów)

#### Dokumenty Zadania 2 (Zaawansowane)
- [k8s/ADVANCED_MECHANISMS.md](k8s/ADVANCED_MECHANISMS.md) - Resource limits, network policies, scheduling (7,000 słów)
- [k8s/TASK_2_SUMMARY.md](k8s/TASK_2_SUMMARY.md) - Summary i checklist (3,000 słów)

#### Dodatkowe
- [k8s/DEPLOYMENT_GUIDE.md](k8s/DEPLOYMENT_GUIDE.md) - Wdrażanie w produkcji (AWS/Azure/GCP)

### 🚀 Szybki start

```bash
# 1. Zainstaluj Minikube
minikube start --cni=calico --cpus=4 --memory=8192

# 2. Wdrój całą konfigurację
kubectl apply -k k8s/

# 3. Dostęp do API
kubectl port-forward svc/benchmark-controller 8000:8000 -n crypto-perf
# http://localhost:8000/api/benchmark
```

Szczegółowe instrukcje: [k8s/QUICKSTART.md](k8s/QUICKSTART.md)

### ✨ Zaawansowane mechanizmy (Zadanie 2)

| Mechanizm | Implementacja | Status |
|-----------|---------------|--------|
| **A) Resource Limits** | CPU/memory requests + limits dla każdego komponentu | ✅ |
| **B) Network Policies** | 6 polityk (default deny + whitelist rules) | ✅ |
| **C) Scheduling Constraints** | Node affinity, pod affinity, taints, PDB | ✅ |

Szczegóły: [k8s/ADVANCED_MECHANISMS.md](k8s/ADVANCED_MECHANISMS.md)

### 📊 Statystyka

- **12 manifestów YAML** (~2,000 linii kodu)
- **30+ zasobów Kubernetes** (deployments, services, policies, storage, etc.)
- **7 dokumentów MD** (~2,500 linii, 30,000+ słów)
- **7 komponentów**: PostgreSQL, Redis, Controller, 4 Crypto Nodes
- **Produkcja-ready**: Resource limits, security, HA, monitoring

### 🎓 Komponenty systemu w K8s

```
Namespace: crypto-perf
├── PostgreSQL (5432)
├── Redis (6379)
├── Benchmark Controller (8000)
├── Py-Cryptography Node (8000)
├── Py-PyCryptodome Node (8000)
├── C++ OpenSSL Node (8000)
└── C++ CryptoPP Node (8000)
   + Ingress, Network Policies, Storage, RBAC, Scheduling
```

Pełna dokumentacja: [k8s/INDEX.md](k8s/INDEX.md)

---

## 🎨 React Frontend (NEW!)

Nowoczesny frontend React 18 do kontroli i monitorowania systemu benchmarku.

### 📁 Katalog: `/frontend`

Zawiera kompletną aplikację React z integracją do backendu.

### ✨ Funkcjonalności

**4 Strony:**
- **Dashboard** - Przegląd systemu i quick start
- **Run Benchmark** - Konfiguracja i uruchomienie testów
- **Results** - Wizualizacja wyników z 3 typami wykresów
- **Settings** - Konfiguracja i informacje o systemie

**4 Komponenty:**
- **Navbar** - Nawigacja z brandingiem
- **SystemStatus** - Monitorowanie podów K8s
- **BenchmarkForm** - Formularz do konfiguracji testów
- **ResultsChart** - Wykresy i tabele wyników

### 🚀 Szybki start

```bash
cd frontend
npm install
npm run dev
```

Dostęp: http://localhost:3000 (proxy do backendu na :8000)

### 🐳 Docker & Kubernetes

```bash
# Docker
docker build -t crypto-frontend:1.0.0 .
docker run -p 3000:3000 crypto-frontend:1.0.0

# Kubernetes (już zintegrowane w k8s/frontend.yaml)
kubectl apply -k k8s/
# Dostęp: http://localhost/ (via Ingress)
```

### 📚 Dokumentacja Frontendu

- [frontend/README.md](frontend/README.md) - Przegląd i instrukcje
- [frontend/FRONTEND_SETUP.md](frontend/FRONTEND_SETUP.md) - Szczegółowy setup guide
- [FRONTEND_SUMMARY.md](FRONTEND_SUMMARY.md) - Pełny summary funkcjonalności

### 🛠 Technology Stack

- **React 18.2** - UI library
- **Vite 5.0** - Build tool (szybki dev server)
- **Tailwind CSS 3.4** - Styling (responsywny design)
- **React Router 6.20** - Client-side routing
- **Axios 1.6** - HTTP client
- **Recharts 2.10** - Wykresy
- **Lucide React 0.294** - Ikony

### 🔌 API Integration

Frontend automatycznie łączy się z backend API:
- Proxy: `/api` → `http://localhost:8000/api` (dev)
- Endpoints: Status, Pods, Run Benchmark, Results, Download CSV

### 📊 Production Ready

✅ Multi-stage Docker build (~150-200KB gzipped)
✅ Kubernetes deployment (2 replicas, HA setup)
✅ Network policies (ingress/egress rules)
✅ Resource limits (CPU: 100m-500m, RAM: 256Mi-512Mi)
✅ Security context (non-root, read-only filesystem)
✅ Health checks (liveness + readiness probes)

---

## 📦 Docker Compose

Plik `docker-compose.yml` uruchamia cały system z 7 serwisami:

```bash
docker-compose up -d

# Dostęp:
# Frontend: http://localhost:3000
# API: http://localhost:8000/api
# Redis: localhost:6379
# PostgreSQL: localhost:5432
```

Serwisy:
1. **Redis** - Message broker
2. **Benchmark Controller** - FastAPI backend
3. **Python Cryptography Node**
4. **Python PyCryptodome Node**
5. **C++ OpenSSL Node**
6. **C++ CryptoPP Node**
7. **React Frontend** (NEW!)

---

## 📋 Projekt Overview

```
crypto-analysis/
├── k8s/                         # Kubernetes manifests & docs
│   ├── *.yaml                  # 12 YAML manifests
│   ├── *.md                    # 7 dokumenty (30,000+ słów)
│   └── ...
├── frontend/                    # React 18 frontend
│   ├── src/components/         # React components
│   ├── src/pages/              # Page components
│   ├── src/api/                # API client
│   ├── Dockerfile              # Multi-stage build
│   └── ...
├── benchmark-controller/        # FastAPI backend
├── node-py-crypto/             # Python Cryptography
├── node-py-pycryptodome/       # Python PyCryptodome
├── node-cpp-openssl/           # C++ OpenSSL
├── node-cpp-cryptopp/          # C++ CryptoPP
├── docker-compose.yml          # Full system (with frontend!)
├── docker-compose.dev.yml      # Dev configuration
├── README.md                   # This file
├── FRONTEND_SUMMARY.md         # Frontend overview
└── ...
```

---

## 🎯 Zadania

| Zadanie | Status | Dokumentacja |
|---------|--------|--------------|
| **Zadanie 1: Kubernetes Deployment** | ✅ Zrobione | [k8s/KUBERNETES_ARCHITECTURE.md](k8s/KUBERNETES_ARCHITECTURE.md) |
| **Zadanie 2: Zaawansowane mechanizmy** | ✅ Zrobione | [k8s/ADVANCED_MECHANISMS.md](k8s/ADVANCED_MECHANISMS.md) |
| **Zadanie 3: Prezentacja & Demo** | ✅ Zrobione | [k8s/PRESENTATION_CLEAN.html](k8s/PRESENTATION_CLEAN.html) |
| **Frontend (Bonus)** | ✅ Zrobione | [frontend/FRONTEND_SETUP.md](frontend/FRONTEND_SETUP.md) |

---

## 🔗 Szybkie Linki

- **K8s Setup**: [k8s/QUICKSTART.md](k8s/QUICKSTART.md)
- **Frontend Setup**: [frontend/FRONTEND_SETUP.md](frontend/FRONTEND_SETUP.md)
- **Deployment**: [k8s/DEPLOYMENT_GUIDE.md](k8s/DEPLOYMENT_GUIDE.md)
- **Architektura K8s**: [k8s/KUBERNETES_ARCHITECTURE.md](k8s/KUBERNETES_ARCHITECTURE.md)
- **Advanced K8s**: [k8s/ADVANCED_MECHANISMS.md](k8s/ADVANCED_MECHANISMS.md)
- **GitHub**: [GETTING_STARTED.md](GETTING_STARTED.md)

---

## 📝 Licencja

MIT - patrz plik LICENSE
