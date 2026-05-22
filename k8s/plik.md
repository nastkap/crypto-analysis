# Opis rozwiązań zgodnie z p.1 oraz 2

## Zadanie 1

 ### A) Pliki opisujące strukturę obrazów (Dockerfiles)

| Komponent | Plik | Lokalizacja | Opis |
|-----------|------|-------------|------|
| **PostgreSQL** | `postgres:16-alpine` | Obraz publiczny | Baza danych (bez custom Dockerfile) |
| **Redis** | `redis:7-alpine` | Obraz publiczny | Message broker (bez custom Dockerfile) |
| **Benchmark Controller** | [Dockerfile](../benchmark-controller/Dockerfile) | `benchmark-controller/Dockerfile` | Python 3.11 + FastAPI/Uvicorn |
| **Python Cryptography Node** | [Dockerfile](../node-py-crypto/Dockerfile) | `node-py-crypto/Dockerfile` | Python 3.11 + cryptography |
| **Python PyCryptodome Node** | [Dockerfile](../node-py-pycryptodome/Dockerfile) | `node-py-pycryptodome/Dockerfile` | Python 3.11 + pycryptodome |
| **C++ OpenSSL Node** | [Dockerfile](../node-cpp-openssl/Dockerfile) | `node-cpp-openssl/Dockerfile` | Alpine + C++17 + OpenSSL |
| **C++ CryptoPP Node** | [Dockerfile](../node-cpp-cryptopp/Dockerfile) | `node-cpp-cryptopp/Dockerfile` | Alpine + C++17 + Crypto++ |



---

### B) Manifesty Kubernetes

#### B1. Namespace 

**Plik**: [k8s/namespace.yaml](namespace.yaml)

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: crypto-perf
```

**Uzasadnienie**: Dedykowana przestrzeń nazw izoluje zasoby systemu od reszty klastra



#### B2. Deployments / StatefulSets / DaemonSets 

| Typ | Komponent | Plik | Repliki | Uzasadnienie typu                                                                                                                                                                                                   | Uzasadnienie repliki                                   |
|-----|-----------|------|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| **Deployment** | PostgreSQL | [postgres.yaml](postgres.yaml) | 1 | Baza danych singleton, nie wymaga identity sieciowej                                                                                                                                                                |Baza danych wymaga single instancji bez race conditions |
| **Deployment** | Redis | [redis.yaml](redis.yaml) | 1 | Message broker, bezstatowy z perspektywy aplikacji; dane w Redis to tylko tymczasowe wiadomości (asynchroniczna komunikacja); utrata danych Redis nie powoduje utraty stanu systemu (baza danych jest w PostgreSQL) |                                                        |
| **Deployment** | Benchmark Controller | [nodes.yaml](nodes.yaml) | 1 | Orkiestracja centralna, brak potrzeby wielu instancji                                                                                                                                                               |   logika orkiestracji wymaga jednej instancji kontrolera                                          |
| **Deployment** | Python Cryptography | [nodes.yaml](nodes.yaml) | 1 | Węzeł testowy, skalowalne niezależnie       ;  węzeł ma własny Service do komunikacji z kontrolerem                                                                                                            |       węzeł powinien być unikalny w systemie testowym                                            |
| **Deployment** | Python PyCryptodome | [nodes.yaml](nodes.yaml) | 1 | Węzeł testowy, skalowalne niezależnie  ;  węzeł ma własny Service do komunikacji z kontrolerem                                                                                                                 |      węzeł powinien być unikalny w systemie testowym                                             |
| **Deployment** | C++ OpenSSL | [nodes.yaml](nodes.yaml) | 1 | Węzeł testowy, skalowalne niezależnie ; węzeł ma własny Service do komunikacji z kontrolerem                                                                                                                  |       węzeł powinien być unikalny w systemie testowym                                            |
| **Deployment** | C++ CryptoPP | [nodes.yaml](nodes.yaml) | 1 | Węzeł testowy, skalowalne niezależnie      ; węzeł ma własny Service do komunikacji z kontrolerem                                                                                                             |      węzeł powinien być unikalny w systemie testowym                                             |


**Dlaczego Deployment, nie StatefulSet?**
- Pody mogą być niszczone/tworzone w dowolnej kolejności
- Nie potrzebujemy stabilnych nazw sieciowych
- Upgrade'owanie obrazu nie wymaga sekwencyjności

**Dlaczego nie DaemonSet?**
- System nie wymaga instancji na każdym node
- Mamy Minikube single-node (1 node)

**Dlaczego 1 replika (w Minikube)?**
- PostgreSQL: Singleton baza danych
- Redis: Singleton message broker
- Controller: Centralna orkiestracja
- Węzły: Testowe, każdy unikalny (Python vs C++, różne biblioteki)

**W produkcji możliwe zwiększenie: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#replicas)**



#### B3. Services 

**Plik**: [postgres.yaml](postgres.yaml), [redis.yaml](redis.yaml), [nodes.yaml](nodes.yaml)

| Service | Typ | Port | Uzasadnienie |
|---------|-----|------|-----------|
| **postgres** | ClusterIP | 5432 | Komunikacja wewnątrz klastra (interne, nie external) |
| **message-broker** | ClusterIP | 6379 | Komunikacja wewnątrz klastra (interne, nie external) |
| **benchmark-controller** | ClusterIP | 8000 | API dostępna przez Ingress/LoadBalancer |
| **node-py-crypto** | ClusterIP | 8001 | Komunikacja z controllerem |
| **node-py-pycryptodome** | ClusterIP | 8002 | Komunikacja z controllerem |
| **node-cpp-openssl** | ClusterIP | 8003 | Komunikacja z controllerem |
| **node-cpp-cryptopp** | ClusterIP | 8004 | Komunikacja z controllerem |


**Uzasadnienie ClusterIP**:
- Komunikacja tylko wewnątrz klastra
- DNS rozwiązywany do service IP
- Każdy pod może kontaktować się z innym poprzez `[service-name].[namespace].svc.cluster.local`
- **Przykład**: `postgresql://benchmark:benchmark@postgres.crypto-perf.svc.cluster.local:5432/benchmark`



#### B4. Ingress / LoadBalancer / Gateway 

**Plik**: [ingress.yaml](ingress.yaml)



Wybór Ingress zamiast LoadBalancer uzasadniają:

1. **Architektura systemu**: 7 usług (Controller + 4 Nodes + DB + Redis)
   wymaga zaawansowanego routingu

2. **Path-based routing**: Różne endpointy (/api/benchmark, /api/node-*)
   obsługiwane przez jeden Ingress Controller

3. **Koszt**: 1 Ingress Controller vs. 5 LoadBalancerów = 60-80% oszczędności

4. **Management**: Centralne zarządzanie SSL/TLS w jednym miejscu

5. **Skalowalność**: Łatwe dodanie nowych usług bez tworzenia nowych LB

6. **Best Practice**: Ingress to standard dla multi-service aplikacji w K8s




#### B5. Persistent Storage (PV / PVC / StorageClass) 

**Plik**: [storage.yaml](storage.yaml)

**StorageClass** (definiuje typ przechowywania):

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: crypto-storage
provisioner: kubernetes.io/host-path
```


**Uzasadnienie**:
- Definiuje typ przechowywania dostępny w klastrze
- **host-path**: dla Minikube (dane na dysku maszyny wirtualnej)
- **Production**: zmienić na:
  - AWS EBS: `ebs.csi.aws.com`
  - Azure Disk: `disk.csi.azure.com`
  - GCP PD: `pd.csi.storage.gke.io`

### PersistentVolumeClaim (PVC)

#### PostgreSQL PVC
```yaml
metadata:
  name: postgres-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: crypto-storage
  resources:
    requests:
      storage: 2Gi
```

**Uzasadnienie**:
- **ReadWriteOnce**: Tylko jeden node może mocować jednocześnie (standard dla statefulnych baz)
- **2Gi**: Wystarczające dla benchmark danych
- **Mounted at**: `/var/lib/postgresql/data` (w kontenerze)

#### Redis PVC
```yaml
metadata:
  name: redis-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: crypto-storage
  resources:
    requests:
      storage: 1Gi
```

**Uzasadnienie**:
- Redis przechowuje tymczasowe dane (AOF log)
- 1Gi wystarczające dla asynchronicznego messaging
- Utrata danych Redis ≠ utrata stanu systemu

### Persistent Storage Flow

1. `StorageClass` → definiuje jak przechowywać dane
2. `PVC` → żądanie pewnego ilości storage
3. `PV` (automatyczne) → faktycznie utworzone storage backend
4. `Pod` → mountuje PVC w określonym miejscu

---

## ConfigMaps i Secrets

**Plik**: `configmap-secrets.yaml`

### ConfigMap - Niezagwarantowana konfiguracja

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: crypto-config
data:
  DATABASE_HOST: postgres
  REDIS_HOST: message-broker
  LOG_LEVEL: INFO
```

**Zawartość**:
- Publiczne zmienne konfiguracyjne
- Hosty Services (DNS)
- Porty
- Level logowania

**Mechanizm wstrzykiwania**:
```yaml
envFrom:
- configMapRef:
    name: crypto-config
```

Wszystkie klucze w ConfigMap stają się zmiennymi środowiskowymi w podzie.

### Secrets - Poufne dane

```yaml
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: crypto-secrets
stringData:
  POSTGRES_PASSWORD: benchmark
  BROKER_URL: redis://message-broker:6379
```

**Zawartość**:
- Hasła do bazy danych
- Connection strings
- API keys
- Secret key do JWT

**Mechanizm wstrzykiwania**:
```yaml
envFrom:
- secretRef:
    name: crypto-secrets
```

**Bezpieczeństwo**:
- ⚠️ Secrets przechowywane w etcd są base64-encoded (NIEKONIECZNIE szyfrowane)
- **Best practice**: W produkcji użyć `--encryption-provider-config` w apiserver
- **Best practice**: Secrets mogą być przechowywane w HashiCorp Vault, AWS Secrets Manager, itp.

---

## RBAC

**Plik**: `rbac.yaml`

### Role-Based Access Control

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: crypto-system
  namespace: crypto-perf
```

**Uzasadnienie**:
- Każdy pod ma tożsamość (ServiceAccount)
- Uprawnienia są przypisane do tej tożsamości
- Segmentacja dostępu (least privilege principle)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: crypto-system-role
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
```

**Uprawnienia**:
- Odczyt ConfigMaps i Secrets
- Obserwacja Services
- Obserwacja Pods

**Dlaczego te uprawnienia?**
- Pody mogą przeczytać swoją konfigurację z etcd
- Service discovery (znalezienie DNS adresów innych komponentów)
- Health monitoring wewnątrz klastra

**ClusterRoleBinding**:
```yaml
kind: ClusterRoleBinding
roleRef:
  kind: ClusterRole
  name: crypto-system-role
subjects:
- kind: ServiceAccount
  name: crypto-system
  namespace: crypto-perf
```

Wiąże uprawnienia do ServiceAccount.

---


