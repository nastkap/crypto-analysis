# Opis rozwiązań infrastrukturalnych i manifestów Kubernetes

Niniejszy dokument stanowi szczegółowy opis oraz uzasadnienie techniczne dla architektury wdrożenia systemu benchmarkingu wydajności algorytmów kryptograficznych w środowisku Kubernetes (K8s). System składa się z aplikacji frontendowej, centralnego kontrolera orkiestracji, brokera wiadomości (Redis), relacyjnej bazy danych (PostgreSQL) oraz rozproszonych węzłów obliczeniowych realizujących testy kryptograficzne w środowiskach Python oraz C++.

---

 ## Pliki opisujące strukturę obrazów (Dockerfiles)

| Komponent | Plik | Lokalizacja | Opis |
|-----------|------|-------------|------|
| **PostgreSQL** | `postgres:16-alpine` | Obraz publiczny | Baza danych (bez custom Dockerfile) |
| **Redis** | `redis:7-alpine` | Obraz publiczny | Message broker (bez custom Dockerfile) |
| **Benchmark Controller** | [Dockerfile](../benchmark-controller/Dockerfile) | `benchmark-controller/Dockerfile` | Python 3.11 + FastAPI/Uvicorn |
| **Python Cryptography Node** | [Dockerfile](../node-py-crypto/Dockerfile) | `node-py-crypto/Dockerfile` | Python 3.11 + cryptography |
| **Python PyCryptodome Node** | [Dockerfile](../node-py-pycryptodome/Dockerfile) | `node-py-pycryptodome/Dockerfile` | Python 3.11 + pycryptodome |
| **C++ OpenSSL Node** | [Dockerfile](../node-cpp-openssl/Dockerfile) | `node-cpp-openssl/Dockerfile` | Alpine + C++17 + OpenSSL |
| **C++ CryptoPP Node** | [Dockerfile](../node-cpp-cryptopp/Dockerfile) | `node-cpp-cryptopp/Dockerfile` | Alpine + C++17 + Crypto++ |
|**Frontend**| [Dockerfile](../frontend/Dockerfile) | `frontend/Dockerfile`|Node 20 Alpine|


---
## Manifesty

###  Namespace

**Plik manifestu:** `namespace.yaml`

Wszystkie zasoby wchodzące w skład systemu są wdrażane w dedykowanej przestrzeni nazw o nazwie `crypto-perf`.

#### Uzasadnienie:
* **Izolacja zasobów:** Wydzielenie osobnego namespace'u logicznie izoluje środowisko badawcze od domyślnych zasobów klastra (`default`, `kube-system`), zapobiegając konfliktom nazw i nieautoryzowanemu dostępowi.
* **Zarządzanie bezpieczeństwem:** Umożliwia precyzyjne stosowanie polityk sieciowych (`NetworkPolicy`) oraz limitów zasobów (`ResourceQuota`) specyficznych dla tego projektu, co jest kluczowe w architekturze typu *Multi-Tenant*.

---

### Deployments / StatefulSets / DaemonSets

W systemie zastosowano obiekt typu **Deployment** do zarządzania cyklem życia wszystkich mikroserwisów. 

#### Zestawienie komponentów i replikacji:

| Mikroserwis | Typ obiektu | Liczba replik | Uzasadnienie doboru rodzaju obiektu i replikacji |
| :--- | :--- | :--- | :--- |
| **postgres** | Deployment | 1 | Zarządza relacyjną bazą danych PostgreSQL. Ze względu na to, że baza działa w konfiguracji jednoinstancyjnej z podmontowanym trwałym wolumenem przez PVC, uruchomienie więcej niż 1 repliki doprowadziłoby do błędu blokady zapisu na dysku oraz problemu *race conditions* przy jednoczesnym zapisie wyników testów. |
| **message-broker** | Deployment | 1 | Odpowiada za instancję serwera Redis. Z perspektywy architektury benchmarku, Redis służy jako bezstanowy broker zadań i kolejka FIFO. Trwałość danych transakcyjnych zapewniana jest przez PostgreSQL, więc Redis nie wymaga złożonej koordynacji stanu sieciowego właściwej dla StatefulSet. 1 replika jest w pełni wystarczająca dla środowiska testowego. |
| **benchmark-controller** | Deployment | 1 | Centralna jednostka sterująca, odpowiadająca za orkiestrację testów wydajnościowych. Logika działania aplikacji wymaga jednej instancji zarządzającej, aby zachować sekwencyjność i spójność rozsyłania zadań do węzłów oraz uniknąć duplikowania zleceń. |
| **node-py-crypto**<br>**node-py-pycryptodome**<br>**node-cpp-openssl**<br>**node-cpp-cryptopp** | Deployment | 1 (dla każdego węzła) | Węzły obliczeniowe wykonujące operacje kryptograficzne. Każdy węzeł reprezentuje inną bibliotekę i technologię (Python vs C++). Muszą one działać jako niezależne, pojedyncze instancje, aby pomiary wydajnościowe odzwierciedlały czystą wydajność danej biblioteki, bez rozpraszania ruchu na kopie tego samego podu. |
| **frontend** | Deployment | 2 | Interfejs użytkownika (React UI). Zastosowano **2 repliki**, aby zapewnić wysoką dostępność (High Availability) warstwy prezentacji. W przypadku awarii jednego z podów lub jego restartu, drugi pod natychmiast przejmuje obsługę żądań HTTP użytkownika. |


#### Dlaczego wybrano Deployment zamiast StatefulSet lub DaemonSet?
1. **Brak potrzeby sztywnej identyfikacji sieciowej:** Pody aplikacji, kontrolera i węzłów są całkowicie bezstanowe. Komunikują się przez wewnętrzne serwisy K8s, które automatycznie balansują ruch (brak wymogu stałych nazw typu `pod-0`, `pod-1` oferowanych przez `StatefulSet`). Choć Postgres i Redis przechowują dane, dzięki powiązaniu z PVC wolumen podąża za podem w przypadku jego odtworzenia, co pozwala na stabilne działanie w oparciu o elastyczny Deployment.
2. **Brak potrzeby pokrycia każdego węzła (DaemonSet):** System nie jest agentem systemowym ani demonem monitorującym, który musiałby fizycznie działać na każdym węźle roboczym klastra.
3. **Strategia aktualizacji:** Deployment umożliwia bezprzerwowe wdrażanie poprawek kodu za pomocą strategii `RollingUpdate` (wartości `maxSurge: 1` i `maxUnavailable: 0` gwarantują, że nowy pod wstaje przed ubiciem starego).

---

### Services
Każdy mikroserwis w klastrze posiada dedykowany obiekt `Service` o typie **ClusterIP**. 

#### Zestawienie usług:

| Nazwa serwisu | Typ serwisu | Port wewnętrzny | Powiązany komponent (Pod) | Rola i uzasadnienie typu serwisu |
| :--- | :--- | :--- | :--- | :--- |
| `postgres` | ClusterIP | 5432 | `postgres` | Zapewnia stały punkt adresowy (DNS) dla bazy danych. Typ ClusterIP gwarantuje, że baza jest całkowicie odcięta od świata zewnętrznego, a dostęp do niej ma wyłącznie kontroler. |
| `message-broker` | ClusterIP | 6379 | `message-broker` | Udostępnia instancję Redisa. Typ ClusterIP izoluje brokera wewnątrz sieci klastra, zezwalając na połączenia jedynie autoryzowanym węzłom kryptograficznym i kontrolerowi. |
| `benchmark-controller` | ClusterIP | 8000 | `benchmark-controller` | Eksponuje REST API kontrolera. ClusterIP pozwala na wewnętrzne mapowanie ruchu z kontrolera Ingress oraz bezpośrednią komunikację z frontendem i węzłami. |
| `frontend` | ClusterIP | 3000 | `frontend` | Udostępnia serwer aplikacji webowej. Ruch do tego serwisu jest kierowany bezpośrednio z Ingressa. |
| `node-py-crypto`<br>`node-py-pycryptodome`<br>`node-cpp-openssl`<br>`node-cpp-cryptopp` | ClusterIP | 8000 | Odpowiednie pody węzłów szyfrujących | Każdy węzeł eksponuje własny endpoint `/health`, przez który kontroler weryfikuje ich status gotowości. ClusterIP zabezpiecza te porty wewnątrz klastra. |

**Uzasadnienie:**
`ClusterIP` jest wystarczający, ponieważ mikroserwisy mają być dostępne wewnątrz klastra, a wejście z zewnątrz realizuje warstwa `Ingress`.

---

### Ingress / LoadBalancer / Gateway

**Plik manifestu:** `ingress.yaml`

Do zapewnienia kontrolowanego dostępu użytkowników z sieci zewnętrznej do systemu wykorzystano obiekt **Ingress** oparty na kontrolerze `ingress-nginx`.

### Opis konfiguracji i Path-Based Routing:
Reguły routingu Ingress mapują zapytania kierowane na adres `localhost` i rozdzielają je na poziomie warstwy 7 (aplikacji) w zależności od ścieżki URL (*Path-Based Routing*):
1. Ścieżka `/` (Prefix) przekazuje ruch do serwisu `frontend` na port `3000` (obsługa interfejsu React).
2. Ścieżki `/api` oraz `/api/benchmark` przekazują żądania do `benchmark-controller` na port `8000` (obsługa zapytań backendowych i sterujących testami).
3. Ścieżki dedykowane, takie jak `/api/node-cpp-openssl` czy `/api/node-py-crypto`, pozwalają na bezpośrednie odpytanie metryk zdrowia konkretnych węzłów kryptograficznych z zewnątrz w celach diagnostycznych.

#### Adnotacje i parametry (Annotations):
* `nginx.ingress.kubernetes.io/rewrite-target: /` – Automatycznie przepisuje ścieżki URL przesyłane do podów docelowych, dzięki czemu aplikacje wewnątrz kontenerów mogą obsługiwać ruch na swoich domyślnych ścieżkach bazowych.
* Polityka **CORS** (`cors-allow-methods`, `cors-allow-origin: "*"`) – Umożliwia bezpieczne wykonywanie asynchronicznych zapytań HTTP (AJAX/Fetch) przez przeglądarkę użytkownika z poziomu frontendu bezpośrednio do API kontrolera bez blokad przeglądarki.

#### Uzasadnienie wyboru Ingress zamiast LoadBalancer / NodePort:
* **Ekonomia zasobów i kosztów:** Zamiast tworzyć osobne, kosztowne publiczne adresy IP (lub zewnętrzne LoadBalancery dostawców chmurowych) osobno dla frontendu i osobno dla kontrolera API, Ingress agreguje cały ruch za pomocą jednego, współdzielonego punktu wejścia.
* **Centralizacja zarządzania:** Pozwala na wygodne konfigurowanie reguł CORS, przepisywania nagłówków oraz potencjalnego wdrażania certyfikatów SSL/TLS w jednym miejscu architektury sieciowej.

---

### PV / PVC / StorageClass

**Plik manifestu:** `storage.yaml`

Aby wyniki generowane przez benchmarki nie ulegały bezpowrotnemu skasowaniu w momencie restartu, awarii lub relokacji podów bazodanowych, wdrożono architekturę trwałego przechowywania danych (*Persistent Storage*).

#### Komponenty pamięci masowej:
1. **StorageClass (`crypto-storage`):** Definiuje abstrakcję i parametry techniczne zasobów dyskowych. Wykorzystuje provisioner `k8s.io/minikube-hostpath`, który fizycznie zapisuje dane w wyznaczonym katalogu na maszynie wirtualnej Minikube. Posiada flagę `allowVolumeExpansion: true`, co umożliwia elastyczne zwiększanie rozmiaru dysku w przyszłości bez przerw w działaniu bazy.
2. **PersistentVolumeClaim dla PostgreSQL (`postgres-pvc`):** Żądanie przydziału wolumenu o rozmiarze `2Gi` w trybie dostępu `ReadWriteOnce` (RWO - wolumen może być montowany z prawem do zapisu tylko przez jeden węzeł roboczy jednocześnie, co zabezpiecza integralność struktury plików PostgreSQL). Wolumen montowany jest wewnątrz kontenera bazy danych pod ścieżką `/var/lib/postgresql/data`.
3. **PersistentVolumeClaim dla Redis (`redis-pvc`):** Żądanie przydziału wolumenu o rozmiarze `1Gi`. Służy do składowania plików dziennika zmian Redisa (*Append Only File - AOF*), co pozwala na odtworzenie struktury kolejek zadań w brokerze po nagłym restarcie kontenera.


---

### ConfigMap / Secrets

**Plik manifestu:** `configmap-secrets.yaml`

Zgodnie z pryncypiami *12-Factor App*, konfiguracja systemu została całkowicie odseparowana od kodu źródłowego aplikacji i jest wstrzykiwana do kontenerów w czasie ich uruchamiania przez Kubernetes.

#### ConfigMap (`crypto-config`)
Przechowuje jawne, publiczne zmienne konfiguracyjne wspólne dla całego środowiska:
* Zmienne adresowe baz i brokerów (`DATABASE_HOST: postgres`, porty).
* Parametry zachowania aplikacji (`LOG_LEVEL: INFO`, limity timeoutów połączeń sieciowych, interwały dla health-checków).

#### Secret (`crypto-secrets`)
Przechowuje dane wrażliwe w obiekcie typu `Opaque` (standardowy, niejawny sekret):
* Dane uwierzytelniające dla bazy danych (`POSTGRES_USER`, `POSTGRES_PASSWORD`).
* Pełne connection stringi zawierające hasła (`DATABASE_URL`, `BROKER_URL` z hasłem do autoryzacji w Redis).
* Klucze kryptograficzne aplikacji (`SECRET_KEY`, `ALGORITHM`) używane do zabezpieczania sesji.

#### Mechanizm wstrzykiwania (Injection Mechanism):
W manifestach podów zastosowano konstrukcję `envFrom`:
```yaml
envFrom:
- configMapRef:
    name: crypto-config
- secretRef:
    name: crypto-secrets
 ```   
Podczas inicjalizacji poda, Kubernetes mapuje wszystkie pary klucz-wartość z obiektów ConfigMap i Secret bezpośrednio na zmienne środowiskowe systemu Linux wewnątrz kontenera. Dzięki temu aplikacje w Pythonieoraz w C++ uzyskują bezpośredni i ujednolicony dostęp do parametrów konfiguracyjnych


Pliki manifestów znajdują się w katalogu `k8s/` i tworzą pełny zestaw wdrożeniowy systemu w Kubernetes.


## Opis zaawansowanych mechanizmów i narzędzi Kubernetes

### Ograniczenie wykorzystywanych zasobów

Zarządzanie zasobami sprzętowymi (CPU i RAM) zrealizowano wielowarstwowo, aby zapewnić stabilność klastra podczas intensywnych testów wydajnościowych.

**1. Limity na poziomie kontenerów (Requests & Limits)**
W każdym manifeście `Deployment` zdefiniowano blok `resources`. 
* **Requests**  gwarantują, że dany węzeł szyfrujący otrzyma niezbędne minimum zasobów do startu. 
* **Limits**  stanowią "twardy sufit" (hard limit). Węzeł C++ wykonujący intensywne operacje matematyczne (OpenSSL/Crypto++) nie zawiesi fizycznego serwera (*Node*), ponieważ *OOMKilled* (Out Of Memory) lub *CPU Throttling* zatrzyma kontener po przekroczeniu limitu.

**2. Quoty na poziomie przestrzeni nazw (ResourceQuota)**
**Plik:** `resource-quota.yaml` (obiekt `crypto-quota`)
Ograniczono sumaryczne zużycie zasobów w całym namespace `crypto-perf` .
* **Uzasadnienie:** Chroni to klaster w środowisku współdzielonym (*Multi-Tenant*) przed zjawiskiem "Noisy Neighbor". Błędy w kodzie testowym skutkujące nieskończoną pętlą nie doprowadzą do "zagłodzenia" innych aplikacji w klastrze.

**3. Domyślne ramy zasobów (LimitRange)**
**Plik:** `resource-quota.yaml` (obiekt `crypto-limits`)
* **Uzasadnienie:** Działa jako "mechanizm bezpieczeństwa". Jeśli w przyszłości zostanie wdrożony nowy pod bez zdefiniowanych limitów, `LimitRange` automatycznie przypisze mu domyślne granice, zapobiegając niekontrolowanej konsumpcji zasobów.

---

### Zdefiniowanie polityki sieciowej (Network Policies)

**Plik:** `network-policy.yaml`

Zabezpieczenie komunikacji wewnątrz klastra oparto na modelu **Zero Trust Architecture** z domyślnym odrzucaniem ruchu sieciowego.

**1. Default Deny All (`crypto-deny-all-ingress`)**
Polityka z pustym selektorem podów (`podSelector: {}`). Oznacza to, że żaden pod w przestrzeni `crypto-perf` domyślnie nie może odbierać żadnego ruchu sieciowego. Jest to fundamentalna linia obrony.

**2. Explicit Allow (Reguły wyjątków)**
Zdefiniowano precyzyjne ścieżki komunikacji (*Least Privilege*):
* `postgres-allow-from-apps`: Dostęp do bazy (port 5432) ma **wyłącznie** `benchmark-controller`. Żaden inny komponent (w tym frontend czy węzły szyfrujące) nie może nawiązać połączenia z bazą.
* `redis-allow-from-apps`: Dostęp do brokera wiadomości mają tylko Controller oraz węzły kryptograficzne (`matchExpressions` wskazujące na etykiety węzłów).
* `frontend-allow-external`: Pozwala na ruch przychodzący do frontendu z zewnątrz, ale ogranicza ruch wychodzący (*Egress*) tylko do serwera DNS klastra (port 53) oraz kontrolera API.
* `controller-allow-ingress`: Pozwala na ruch przychodzący do centralnego kontrolera (port 8000) z innych podów w klastrze (niezbędne do odbierania żądań z frontendu oraz komunikacji zwrotnej).
* `crypto-nodes-allow-ingress`: Zezwala na ruch przychodzący na port 8000 węzłów szyfrujących (Python/C++) wyłącznie z podów kontrolera, co zabezpiecza endpointy testowe przed nieautoryzowanym odpytywaniem.

  **Uzasadnienie:** 
Takie podejście drastycznie ogranicza wektor ataku (blast radius). Nawet jeśli atakujący skompromituje kontener Frontendu, Network Policy na poziomie wirtualnej sieci K8s zablokuje mu możliwość skanowania portów lub ataku bezpośrednio na bazę danych PostgreSQL czy węzły szyfrujące.
---

