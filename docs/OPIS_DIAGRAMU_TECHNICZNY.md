

## Architektura i przepływ systemu

System bezpiecznej wymiany wiadomości ECIES (Elliptic Curve Integrated Encryption Scheme) zbudowany jest w oparciu o architekturę mikrousług. Jego głównym zadaniem jest umożliwienie porównania wydajności i poprawności implementacji szyfru ECIES w czterech różnych bibliotekach kryptograficznych: dwóch na Pythonie (cryptography i PyCryptodome) oraz dwóch na C++ (OpenSSL i Crypto++).

Centralnym orchestratorem całego systemu jest kontroler benchmark'u, który pełni rolę bramy HTTP i routera żądań. Wszystkie żądania od klienta trafiają do controllera, který następnie kieruje je do dostępnych węzłów szyfrowania. Każdy węzeł implementuje ten sam interfejs (FastAPI dla Pythona, httplib dla C++), ale używa innej biblioteki do faktycznego szyfrowania danych.

Komunikacja między węzłami, przechowywanie stanu oraz rejestracja kluczy publicznych odbywa się poprzez Redis - nostalny message broker i key-value store. Każdy węzeł przy starcie rejestruje swój publiczny klucz ECIES w Redis'ie pod kluczem z identyfikatorem serwisu. Kontroler i węzły komunikują się z Redis'em poprzez protokół rzeczywisty (TCP), co umożliwia szybką wymianę danych między kontenerami w sieci wewnętrznej Docker'a.

Cały system jest konteneryzowany i orkiestrowany za pomocą Docker Compose v3.9, co oznacza że wszystkie komponentu mogą być uruchamiane jedną komendą na dowolnej maszynie z zainstalowanym Docker'em. Kontenery są izolowane sieciowo w bridge network'u Docker'a (172.23.0.0/16), co zapewnia separację od pozostałych serwisów na hoście.

---

## Komponenty

### 1. Benchmark Controller
- **Framework:** FastAPI (Python 3.11)
- **Port:** 8000 (exposed to host)
- **Role:** HTTP API gateway, routing szyfrowania
- **Endpoints:**
    - `POST /encrypt` - request do węzła
    - `POST /decrypt` - request do węzła
    - `GET /health` - health check
- **Healthcheck:** HTTP 200 OK na `/health` (interval 30s)
- **Dependencies:** redis-py, cryptography, pydantic

### 2. Węzły Szyfrowania (4x)

#### node-py-crypto
- **Library:** cryptography
- **Framework:** FastAPI (Python 3.11-slim)
- **Port:** 8000 (internal)
- **Cipher:** ECIES (Elliptic Curve Integrated Encryption Scheme)
- **Healthcheck:**  HTTP 200 OK

#### node-py-pycryptodome
- **Library:** PyCryptodome
- **Framework:** FastAPI (Python 3.11-slim)
- **Port:** 8000 (internal)
- **Cipher:** ECIES
- **Healthcheck:**  HTTP 200 OK

#### node-cpp-openssl
- **Library:** OpenSSL 3.x
- **Language:** C++17
- **Base:** Alpine + C++17
- **Port:** 8000 (internal)
- **Cipher:** ECIES (evp pkey)
- **Build:** Multi-stage (builder + runtime)
- **Healthcheck:**  File existence test

#### node-cpp-cryptopp
- **Library:** Crypto++ v8.7.0 (built from source)
- **Language:** C++17
- **Base:** Alpine + C++17
- **Port:** 8000 (internal)
- **Cipher:** ECIES
- **Build:** Multi-stage (builder + runtime)
- **Dependencies:** hiredis (from source)
- **Healthcheck:**  File existence test

### 3. Message Broker
- **Type:** Redis (Alpine)
- **Port:** 6379 (exposed + internal)
- **Role:**
    - Rejestracja publicznych kluczy węzłów
    - Task queue dla szyfrowania
    - Przechowywanie wyników operacji
- **Healthcheck:** Not configured (stable, verified via PING)
  
---

### Szczegółowy opis komponentów

#### Benchmark Controller 
Kontroler benchmark'u napisany w FastAPI (architektura asynchroniczna, pełne wsparcie dla async/await) nasłuchuje na porcie 8000. Jest to główny punkt wejścia do całego systemu. Kontroler nie wykonuje żadnych operacji kryptograficznych sam - zamiast tego kieruje żądania HTTP do dostępnych węzłów.

Po otrzymaniu żądania POST do `/encrypt` lub `/decrypt`, kontroler:
1. Parsuje payload (tekst do szyfrowania/deszyfrowania)
2. Wybiera dostępny węzeł (round-robin lub random)
3. Wysyła HTTP POST do wybranego węzła
4. Czeka na odpowiedź
5. Zwraca wynik klientowi

Health check na kontrolerze działa poprzez prosty test HTTPlib - Docker co 30 sekund wysyła GET /health, jeśli odpowiedź to 200 OK, kontener jest oznaczany jako "(healthy)". Jeśli brak odpowiedzi lub inny kod (500, 404 itp.), kontener przechodzi w stan "(unhealthy)". W moim systemie kontroler konsystentnie odpowiada 200 OK, co potwierdza jego stabilność.

#### Węzły szyfrowania - wspólna logika
Wszystkie cztery węzły (2 Python, 2 C++) implementują ten sam interfejs API REST. Po uruchomieniu każdy węzeł:
1. Inicjalizuje bibliotekę kryptograficzną (OpenSSL, Crypto++, cryptography, PyCryptodome)
2. Generuje parę kluczy ECIES (klucz prywatny przechowywany lokalnie w pamięci)
3. Rejestruje publiczny klucz w Redis'ie (format hex)
4. Zaczyna nasłuchiwać na porcie 8000
5. Czeka na HTTP POST żądania

Każdy węzeł odpowiada na:
- `POST /encrypt` - pobiera dane do zaszyfrowania, zwraca ciphertext (hex)
- `POST /decrypt` - pobiera ciphertext, zwraca plaintext
- `GET /health` - zwraca JSON status (dla health check'ów)

#### node-py-crypto
Implementacja Python'a używająca biblioteki `cryptography`. Jest to najpopularniejsza i najnowsza biblioteka kryptograficzna dla Pythona, dobrze utrzymywana przez OpenSSF. ECIES jest tam implementowany jako composite cipher (RSA + AES), choć dla ECIES bezpośrednio rekomendowana jest metoda z elliptic curves.

#### node-py-pycryptodome
Implementacja Python'a używająca biblioteki `PyCryptodome` (fork oryginalnego PyCrypto). Ta biblioteka jest starsza ale powszechnie używana w legacy'owych projektach. PyCryptodome ma pełne wsparcie dla ECIES z eliptycznymi krzywymi.

Oba węzły Python'a działają na tym samym podstawowym obrazie (python:3.11-slim) z pojedynczą fazą budowania (single-stage Dockerfile) ponieważ Python nie wymaga kompilacji - kod jest interpretowany w runtime'ie.

#### node-cpp-openssl
Implementacja C++17 używająca OpenSSL 3.x (najnowsza wersja producenta). OpenSSL jest de facto standardem w industry do operacji kryptograficznych niskopoziomowych. ECIES w OpenSSL jest dostępny poprzez EVP API (Envelope encryption).

Budowa tego kontenera jest multi-stage:
- **Faza 1 (builder):** Alpine + C++17 + g++, build-essential, OpenSSL dev headers, wget, git
    - Ściąga hiredis (C client do Redis) z GitHub'a
    - Ściąga httplib (header-only C++ library do HTTP)
    - Kompiluje main.cpp z optymalizacją (-O2)
    - Linkuje z libssl, libcrypto, libhiredis, libpthread
- **Faza 2 (runtime):** Alpine (minimal install)
    - Kopiuje tylko skompilowany binarny plik `/app/server`
    - Kopiuje dynaiczne biblioteki kryptograficzne (libssl.so.3, libcrypto.so.3)
    - Usuwa wszystkie dev tools aby zmniejszyć rozmiar obrazu



#### node-cpp-cryptopp
Implementacja C++17 używająca biblioteki Crypto++ (Wei Dai's cryptographic library). Crypto++ jest jedną z najpopularniejszych pure-C++ bibliotek kryptograficznych (bez zależności C).

Proces budowania kontenerów C++ jest bardziej złożony niż Python ponieważ wymaga:
1. Pobrania source code Crypto++ (nie dostępny bezpośrednio w Alpine repo)
2. Rozpakowania i kompilacji z źródła
3. Instalacji bibliotek w `/usr/local/lib`
4. Konfiguracji LD_LIBRARY_PATH / ldconfig aby runtime mógł znaleźć biblioteki

Hiredis jest również budowany z źródła ponieważ wersja dostępna w Alpine repo jest stara. Health check dla C++ węzłów to prosty test istnienia pliku (`test -f /app/server`) zamiast HTTP curl ponieważ:
- curl nie jest dostępny w minimalnym runtime obrazie
- Test istnienia pliku jest szybszy i nie wymaga sieciowego callout'a
- File-based health check jest wystarczającym dla weryfikacji że binarny został poprawnie skopiowany

---

### Message Broker - Redis 

Redis pełni funkcję centralnego magazynu danych i systemu komunikacyjnego między węzłami. Uruchamiany ze standardowego obrazu redis:alpine (bardzo lekki, ~10MB), Redis nasłuchuje na porcie 6379 zarówno wewnątrz sieci Docker'a (dostęp z poziomu innych kontenerów) jak i na interface hosta (0.0.0.0:6379, dla dostępu z CLI oraz testów).

**Technicznych dane przechowywane w Redis'ie:**
- **Klucze publiczne węzłów:** Format `nodes:<service_name>:<public_key_hex>` - każdy węzeł przy starcie zapisuje tutaj swój publiczny klucz ECIES
- **Wyniki operacji:** Przechowywane pod kluczami `result:<operation_id>` z czasowym TTL (Time-To-Live) aby nie zaśmecać pamięci
- **Logi zdarzeń:** Opcjonalne logowanie timestamp'ów oraz czasu spędzanego na szyfrowaniu dla benchmark'owania

Komunikacja z Redis'em odbywa się poprzez:
- **redis-py** dla węzłów Python'a - popularna biblioteka Python'a do komunikacji z Redis'em, obsługuje pipelining i connection pooling
- **hiredis** (C binding) dla węzłów C++ - wydajna biblioteka C do Redis'a (parsuje protokol Redis szybciej niż czysta implementacja)

**Dlaczego Redis nie ma health check'a?**
Redis nie ma konfigurowanego health check w docker-compose.yml ponieważ jest niezwykle stabilnym serwisem. Jego dostępność i poprawna konfiguracja zostały potwierdzone testem `redis-cli PING → PONG` w procesie weryfikacji. Redis pracuje z domyślną konfiguracją alpine (in-memory storage, brak persistence na disk, brak uwierzytelniania). W systemie testowym (single-host) ta konfiguracja jest wystarczająca.

Status kontenereru Redis w `docker-compose ps` pokazuje "Up" (bez health status) ponieważ Docker'owi nie powiedzieliśmy aby go testował. Ale operacyjnie wiemy że Redis działa prawidłowo bo testowaliśmy: `docker exec ecies-redis redis-cli PING` → `PONG`.



## Komunikacja i przepływ danych

Wszystkie sześć kontenerów (5 aplikacyjnych + 1 Redis) są połączone w pojedynczej sieci bridge Docker'a o nazwie `crypto-analysis_crypto-net` z CIDR `172.23.0.0/16`. W sieci tej Docker utrzymuje wbudowany DNS server, co oznacza że kontenery mogą się odwoływać do siebie po nazwie serwisu (np. `redis://message-broker:6379` automatycznie resolv'uje się do IP kontenera message-brokera).

Ta izolacja sieciowa ma kilka konsekwencji:
1. **Kontenery nie widzą się nawzajem poza siecią** - węzły nie mogą bezpośrednio komunikować z węzłami, wszystkie komunikacja musi przechodzić przez kontroler
2. **Kontroler jest routerem** - ponieważ tylko kontroler jest exposed na porcie hosta (8000:8000), zewnętrzni klienci mogą się łączyć tylko z nim
3. **Bezpieczeństwo przez izolację** - jeśli jeden węzeł zostanie zkompromitowany, nie ma bezpośredniego dostępu do innych węzłów

### Protocol Stack
```
Layer 4 (Application):  HTTP/1.1 (FastAPI, httplib)
Layer 4 (Application):  Redis Protocol (RESP)
Layer 3 (Transport):    TCP/IP
Layer 2 (Data Link):    Docker virtual bridge
```

FastAPI węzły Python'a obsługują HTTP poprzez uvicorn ASGI server (asynchroniczny, wielowątkowy). Węzły C++ obsługują HTTP poprzez httplib (header-only C++ library, synchroniczny event loop). Redis komunikacja dla Pythona idzie przez redis-py (synchroniczny, connection pooling), dla C++ przez hiredis (synchroniczny C parser).

---
