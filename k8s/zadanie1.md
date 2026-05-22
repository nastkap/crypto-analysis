# Zadanie 1.b - Manifesty wdrożenia w Kubernetes

Poniżej zebrano krótki, ale kompletny opis manifestów wdrożeniowych dla systemu `crypto-perf`.

## Namespace
System jest wdrożony w dedykowanej przestrzeni nazw `crypto-perf`.
Izoluje to zasoby aplikacji od innych wdrożeń w klastrze i ułatwia zarządzanie politykami, uprawnieniami oraz storage.

## Deployments / StatefulSets / DaemonSets
W systemie zastosowano:

- `Deployment` dla wszystkich komponentów: `benchmark-controller`, `frontend`, `postgres`, `message-broker`, `node-py-crypto`, `node-py-pycryptodome`, `node-cpp-openssl`, `node-cpp-cryptopp`.
- `DaemonSet` nie jest użyty, ponieważ system nie wymaga uruchamiania kopii na każdym węźle klastra.

**Uzasadnienie:**
- `Deployment` jest właściwy dla mikroserwisów bez potrzeby stałej tożsamości podów.
- `postgres` i `message-broker` są uruchamiane jako `Deployment` z osobnymi `PVC`, ponieważ w tym wariancie projektu nie wymagają stabilnych nazw podów ani sekwencyjnego startu.
- Liczba replik wynosi zwykle `1` dla `postgres`, `message-broker` i `benchmark-controller`, a `2` dla `frontend` w celu prostego zwiększenia dostępności interfejsu WWW.
- Dla węzłów kryptograficznych przyjęto po `1` replikę na komponent, ponieważ każdy z nich reprezentuje osobny wariant implementacji i jest uruchamiany niezależnie.

## Services
Każdy mikroserwis ma własny `Service`, głównie typu `ClusterIP`:

- `postgres` - `ClusterIP`, tylko ruch wewnątrz klastra.
- `message-broker` - `ClusterIP`, komunikacja tylko między podami systemu.
- `benchmark-controller` - `ClusterIP`, dostęp przez `Ingress`.
- `frontend` - `ClusterIP`, dostęp przez `Ingress`.
- `node-py-crypto`, `node-py-pycryptodome`, `node-cpp-openssl`, `node-cpp-cryptopp` - `ClusterIP`, wyłącznie komunikacja wewnętrzna.

**Uzasadnienie:**
`ClusterIP` jest wystarczający, ponieważ mikroserwisy mają być dostępne wewnątrz klastra, a wejście z zewnątrz realizuje warstwa `Ingress`.

## Ingress / LoadBalancer / Gateway
Do dostępu z zewnątrz klastra użyto `Ingress`.
Obsługuje on routing po ścieżkach, np. dla frontendu i API kontrolera.

**Dlaczego Ingress:**
- jedna brama wejściowa dla całego systemu,
- łatwe mapowanie różnych ścieżek URL do różnych usług,
- mniejsza liczba zasobów niż przy osobnych `LoadBalancer` dla każdego komponentu,
- wygodna konfiguracja dla środowiska testowego i lokalnego.

W tym projekcie `Ingress` pełni rolę głównego punktu dostępu do systemu z zewnątrz klastra.

## PV / PVC / StorageClass
Dane trwałe są przechowywane przez `StorageClass` `crypto-storage` oraz osobne `PVC` podłączane do `Deployment` dla baz i brokera.

- `StorageClass` definiuje sposób dynamicznego przydzielania storage.
- `PVC` dla `postgres` i `message-broker` są deklarowane w `storage.yaml`.
- `PostgreSQL` przechowuje dane bazy w trwałym wolumenie.
- `Redis` wykorzystuje trwały wolumen dla zapisu danych AOF/RDB, aby zachować stan po restarcie.

**Uzasadnienie:**
W systemie stanowym dane nie mogą znikać po restarcie poda, dlatego zastosowano trwały storage zamiast pustego wolumenu.

## ConfigMap / Secrets
Konfiguracja jest wstrzykiwana do podów przez:

- `ConfigMap` `crypto-config` - dla ustawień niepoufnych, takich jak hosty, porty, poziom logowania i parametry aplikacji.
- `Secret` `crypto-secrets` - dla danych wrażliwych, np. haseł i connection stringów.

**Mechanizm wstrzykiwania:**
- `envFrom.configMapRef` dla konfiguracji publicznej,
- `envFrom.secretRef` dla danych poufnych.

**Uzasadnienie:**
Takie podejście rozdziela konfigurację od obrazu kontenera, ułatwia zmianę ustawień bez przebudowy obrazów i pozwala bezpiecznie przekazywać sekrety do aplikacji.

## Podsumowanie
Wszystkie wymagane elementy zostały uwzględnione:
- dedykowany `Namespace`,
- `Deployment` dla mikroserwisów aplikacyjnych,
- `Deployment` także dla `postgres` i `message-broker`, z osobnymi `PVC`,
- `Service` typu `ClusterIP`,
- `Ingress` jako punkt wejścia z zewnątrz,
- `StorageClass` + trwałe wolumeny,
- `ConfigMap` i `Secret` do konfiguracji.

Pliki manifestów znajdują się w katalogu `k8s/` i tworzą pełny zestaw wdrożeniowy systemu w Kubernetes.
