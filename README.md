# Analiza wydajnościowa bibliotek kryptograficznych realizowana w rozproszonej architekturze Kubernetes

System do porównania wydajności implementacji szyfrowania ECIES w czterech bibliotekach kryptograficznych (cryptography, PyCryptodome, OpenSSL, Crypto++) oparty na architekturze mikrousług i wdrożony w środowisku Kubernetes

Opracowana architektura chmurowa oparta na 8 głównych komponentach (Frontend React, kontroler FastAPI, 4 węzły kryptograficzne, broker Redis oraz baza PostgreSQL) zarządzanych przez Nginx Ingress Controller. Dla autorskich mikroserwisów przygotowano pliki Dockerfile zgodnie z najlepszymi praktykami (m.in. multi-stage build). Obrazy zostały zbudowane, przeskanowane pod kątem podatności narzędziem Trivy i udostępnione w rejestrze kontenerów.

Kubernetes & Diagram Architektury: System jest wdrażany deklaratywnie w środowisku Kubernetes za pomocą narzędzia Kustomize. Konfiguracja wykorzystuje zaawansowane mechanizmy i najlepsze praktyki K8s: izolację zasobów (dedykowany Namespace), separację konfiguracji (ConfigMap/Secrets), zarządzanie pamięcią masową (PV/PVC), bezpieczeństwo sieciowe Zero-Trust (NetworkPolicies) oraz kontrolę zużycia sprzętu (ResourceQuota i LimitRange). System został w pełni przetestowany – wszystkie pody przechodzą sondy Liveness/Readiness, a testy E2E potwierdzają poprawny przepływ danych od interfejsu graficznego aż do trwałego zapisu w bazie danych. Zaktualizowany diagram architektury ilustruje pełny układ usług, reguły routingu oraz zależności sieciowe wewnątrz klastra.



