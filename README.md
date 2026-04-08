# System bezpiecznej wymiany wiadomości ECIES 

System do porównania wydajności implementacji szyfrowania ECIES w czterech bibliotekach kryptograficznych (cryptography, PyCryptodome, OpenSSL, Crypto++) zbudowany w architekturze mikrousług Docker Compose

**Zrealizowane warunki:** Opracowana architektura 6 usług (kontroler FastAPI + 4 węzły crypto + Redis) oraz Dockerfiles dla każdego mikroserwisu zgodnie z best practices. Obrazy zbudowane i pushowane na DockerHub jako multi-architecture (amd64/arm64) z wbudowanym SBOM. Wszystkie obrazy przeskanowane Trivy

**Docker-Compose & Diagram:** Plik docker-compose.dev.yml zawiera 7 best practices (wersjonowanie, moduły, wolumeny, zmienne środowiskowe, sieci, limity zasobów, health checks). System został testowany - wszystkie 6 kontenerów startuje, API odpowiada, Redis działa. Diagram architektury wygenerowany compose-viz pokazuje wszystkie serwisy, wolumeny, sieć i dependencje
