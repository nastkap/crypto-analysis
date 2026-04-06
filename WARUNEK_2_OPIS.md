# Warunek 2



## Polecenia weryfikacji

---

### 1. Walidacja docker-compose.yml
```powershell
docker-compose config
```
**Wynik: cała konfigurację bez błędów**

![Wynik](docs/foto/plik1.png)
![Wynik](docs/foto/plik2.png)
![Wynik](docs/foto/plik3.png)
![Wynik](docs/foto/plik4.png)
---
### 2. Status serwisów

```powershell
docker-compose ps
```
**Wynik: wszystkie 6 serwisów mają status `Up`**

![Wynik](docs/foto/plik5.png)

---

### 3. Sprawdzenie sieci Docker

```powershell
docker network ls
```

**Wynik: sieć `crypto-analysis_crypto-net` (ID: 0ffbfddfa127) prawidłowo utworzona**

![Wynik](docs/foto/plik6.png)

---

### 4. Sprawdzenie szczegółów sieci

```powershell
docker network inspect crypto-analysis_crypto-net
```

**Wynik: wszystkich 6 kontenerów podłączonych do sieci `crypto-analysis_crypto-net` (172.23.0.0/16)**

![Wynik](docs/foto/plik7.png)
![Wynik](docs/foto/plik8.png)
![Wynik](docs/foto/plik9.png)

---
### 5. Test Health Check - Benchmark Controller

```powershell
curl http://localhost:8000/health
```

**Wynik:**
```json
{"status": "healthy", "service": "ECIES Benchmark Controller"}
```
![Wynik](docs/foto/plik10.png)

---
### 6. Test Health Check - Root Endpoint

```powershell
curl http://localhost:8000/
```
**Wynik: JSON z dostępnymi endpointami**

![Wynik](docs/foto/plik11.png)

---

### 7. Sprawdzenie Redis

```powershell
docker exec ecies-redis redis-cli ping
```

**Wynik: `PONG`**

![Wynik](docs/foto/plik12.png)

---

### 8. Sprawdzenie logów - Controller

```powershell
docker-compose logs benchmark-controller | Select-Object -Last 10
```


**Wynik: serwis działa prawidłowo**

![Wynik](docs/foto/plik13.png)

---

### 9. Sprawdzenie logów - Python Crypto Node

```powershell
docker-compose logs node-py-crypto | Select-Object -Last 5
```

**Oczekiwany wynik:** Potwierdzenie rejestracji w Redis

**Wynik: węzeł szyfrowania działa prawidłowo**

![Wynik](docs/foto/plik14.png)


---

### 10. Logi z terminala

![Wynik](docs/foto/plik15.png)

---


### 11. Build bez błędów

```powershell
docker-compose up --build
```

**Wynik: wszystkie kontenery zbudowały się i uruchomiły bez błędów** 

![Wynik](docs/foto/plik16.png)

---

### 12. Komunikacja serwisów

```powershell
# Test Redis
docker exec ecies-redis redis-cli SET test:demo "works"
docker exec ecies-redis redis-cli GET test:demo
```

**Wynik: Serwisy mogą się komunikować prawidłowo** 

![Wynik](docs/foto/plik18.png)



**Wyjaśnienie:**

- **OK** - polecenie SET zadziałało, wartość została zapisana w Redis
- **works** - polecenie GET zwróciło dokładnie to co zostało zapisane

**Znaczenie:**
1. Redis jest dostępny z hosta
2. Dane mogą być zapisywane i odczytywane
3. Komunikacja między serwisami działa
4. Sieć Docker prawidłowo łączy kontenery

---

## Podsumowanie

### Co zostało osiągnięte:

1.  **Plik docker-compose.yml** z 6 serwisami - prawidłowo skonfigurowany
2.  **Sieć bridge** (crypto-analysis_crypto-net) - wszyscy serwisy połączeni
3.  **Zarządzanie portami** - controller na 8000, Redis na 6379, wnętrze na 8000
4.  **Health checks** - 5 serwisów healthy, Redis Up (Redis nie wymaga konfiguracji health check, gdyż jego dostępność i stabilność zostały potwierdzone pozytywnym testem PING.)
5.  **Zmienne środowiskowe** - prawidłowo ustawione dla komunikacji
6.  **Dependency management** - wszystkie serwisy zależą od message-brokera
7.  **Build bez błędów** - wszystkie 6 kontenerów zbudowało się
8.  **Komunikacja serwisów** - Redis SET/GET działa
9.  **Logowanie** - prawidłowe logi z health checks
10.  **Storage** - volumes dostępne dla trwałości danych



### Jak uruchomić system:

```powershell
# W głównym katalogu projektu
docker-compose up --build

# Lub aby zatrzymać
docker-compose down
```

---
