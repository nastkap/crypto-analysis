# WARUNEK 3: Budowa i Push Obrazów Docker na DockerHub

---

## Podsumowanie

Zostały zbudowane i przesłane na DockerHub **5 obrazów mikroserwisów** w formacie wieloarchitekturowym:


| Serwis | Repozytorium | Architekury |
|--------|-------------|------------|
| Benchmark Controller | `nastap/controller:latest` | arm64, amd64 | 
| Python Cryptography | `nastap/crypto:latest` | arm64, amd64 | 
| Python PyCryptodome | `nastap/pycryptodome:latest` | arm64, amd64 | 
| C++ OpenSSL | `nastap/openssl:latest` | arm64, amd64 | 
| C++ Crypto++ | `nastap/cryptopp:latest` | arm64, amd64 | 

---

### Generowanie pełnego SBOM 

```bash
trivy image --format cyclonedx --output sbom.json nastap/controller:latest

```

**Wynik: sbom.json (pełny raport w CycloneDX)**

---

---

## 🚀 Polecenia Uruchamiające

### **Build i Push Obrazów (wszystkie serwisy)**

```bash
python build_push_docker.py --push --no-cache
```

**Opcje:**
- `--push` — Push obrazów na DockerHub po zbudowaniu
- `--no-cache` — Zbuduj bez cache (gwarantuje świeże warstwy)
- bez opcji — Samo build, bez push

### **Tryb Dry-Run (podgląd bez budowania)**

```bash
python build_push_docker.py --dry-run
```

Wyświetla polecenia buildx bez faktycznego wykonania.

---

## SBOM Files Lokalne

Wszystkie manifesty zależności zapisane w workspace:

```
sbom-controller.txt      
sbom-crypto.txt          
sbom-cryptopp.txt        
sbom-openssl.txt        
sbom-pycryptodome.txt    
```

## Weryfikacji

### **1. Sprawdzenie SBOM Labels w dowolnym obrazie**

```bash
docker inspect nastap/crypto:latest | findstr "org.sbom"
```
**Wynik:**

![Wynik](docs/foto/plik19.png)


---

### **2. Wyświetlanie SBOM na przykładzie `nastap/controller:latest`**

```bash
docker sbom nastap/controller:latest
```

**Wynik** - lista 115+ pakietów z wersjami:


![Wynik](docs/foto/plik20.png)

---

### **3. Sprawdzenie Multi-Architecture Support**

```bash
docker buildx ls
```

**Wynik:**

![Wynik](docs/foto/plik20.png)
---

### **4. Inspekcja Manifest (Proof Multi-Arch)**

```bash
docker manifest inspect nastap/crypto:latest
```

**Wynik** - manifest dla obu architektur:

![Wynik](docs/foto/plik22.png)
---


### **5. Weryfikacja Health Check**

```bash
docker inspect nastap/controller:latest --format='{{.Config.Healthcheck}}'
```
**Wynik:**

![Wynik](docs/foto/plik23.png)

---

## ✅ PODSUMOWANIE SPEŁNIENIA WARUNKU 3

### **Requirement: Budowa wieloarchitekturowych obrazów Docker z SBOM na DockerHub**

### Checklist Spełnienia:

| Element | Status | Dowód |
|---------|--------|-------|
| **5 obrazów zbudowanych** | ✅ | Tabela w sekcji powyżej |
| **Architektura: linux/amd64** | ✅ | `docker manifest inspect nastap/crypto:latest` pokazuje architecture: amd64 |
| **Architektura: linux/arm64** | ✅ | `docker manifest inspect nastap/crypto:latest` pokazuje architecture: arm64 |
| **SBOM wbudowany w obrazy** | ✅ | `docker inspect nastap/crypto:latest \| findstr "org.sbom"` zwraca labels |
| **SBOM format: CycloneDX** | ✅ | `org.sbom.format=cyclonedx` label w każdym obrazie |
| **SBOM treść generowana** | ✅ | `docker sbom nastap/controller:latest` wyświetla 115+ pakietów |
| **Pliki SBOM lokalne** | ✅ | 5 plików .txt w workspace + sbom.json z Trivy |
| **Publikacja na DockerHub** | ✅ | Wszystkie obrazy dostępne jako public repos na nastap/* |
| **Health checks** | ✅ | `docker inspect nastap/controller:latest --format='{{.Config.Healthcheck}}'` |
| **Security: non-root user** | ✅ | User: appuser w każdym Dockerfile |

### Kluczowe Artefakty:

1. **Obrazy na DockerHub** (public):
   - nastap/controller:latest
   - nastap/crypto:latest
   - nastap/pycryptodome:latest
   - nastap/openssl:latest
   - nastap/cryptopp:latest

2. **Dokumentacja SBOM**:
   - sbom-controller.txt (14.9 KB, 115+ packages)
   - sbom-crypto.txt (15.2 KB, 120+ packages)
   - sbom-pycryptodome.txt (15 KB, 118+ packages)
   - sbom-openssl.txt (1.8 KB, 19 packages)
   - sbom-cryptopp.txt (1.8 KB, 19 packages)
   - sbom.json (CycloneDX format z Trivy)

3. **Skrypty Weryfikacji**:
   - verify_warunek_3.ps1 (PowerShell)
   - verify_warunek_3.sh (Bash)

### Wyniki Weryfikacji:

✅ **Multi-Architektura**: Obie architektury (amd64, arm64) są obecne w manifeście Docker
✅ **SBOM Labels**: Potwierdzają format CycloneDX, wersję 1.0, scope application
✅ **Zawartość SBOM**: Zawiera listę wszystkich zależności ze wersjami
✅ **Security**: Wszystkie obrazy działają jako non-root user (appuser)
✅ **Health**: Health checks skonfigurowane dla serwisów Python

---

**Warunek 3 jest w pełni spełniony i gotów do przeglądu.**
