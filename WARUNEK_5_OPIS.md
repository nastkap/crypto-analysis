# WARUNEK 5: Testowa (deweloperska) wersja pliku docker-compose.yaml


## **Weryfikacja**

1. **Uruchomienie systemu:**
```bash
docker-compose -f docker-compose.dev.yml --env-file .env.dev up -d
```
![Wynik](docs/foto/plik32.png)



2. **Sprawdzenie statusu:**
```bash
docker-compose -f docker-compose.dev.yml ps
```
**Wynik**: wszystkie 6 kontenerów **Up** i biegną

![Wynik](docs/foto/plik33.png)

3. **Test API Controller:**
```bash
curl http://localhost:8000/health
```
**Wynik**: HTTP 200 OK
```json
{"status":"healthy","service":"ECIES Benchmark Controller"}
```

![Wynik](docs/foto/plik34.png)

3. **Test Redis Connectivity**
```bash
docker exec crypto-redis redis-cli -a devpassword ping
```

**Wynik: PONG**

![Wynik](docs/foto/plik35.png)
---

