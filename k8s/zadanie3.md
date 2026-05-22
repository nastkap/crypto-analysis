# Zadanie 3 - Krótka prezentacja uruchomienia systemu

Najlepiej pokazać to w prosty sposób: **polecenie, krótki wynik i jedno zdanie komentarza**. Taka forma jest czytelna i od razu pokazuje, że system działa poprawnie.

## 1. Wdrożenie manifestów
```bash
kubectl apply -k k8s
```
**Co pokazuje:** uruchomienie całego systemu w namespace `crypto-perf`.

## 2. Sprawdzenie podów
```bash
kubectl get pods -n crypto-perf
```
**Co pokazuje:** wszystkie mikroserwisy zostały uruchomione i mają stan `Running` oraz `READY 1/1`.

Przykładowo powinny być widoczne pody dla:
- `benchmark-controller`
- `frontend`
- `message-broker`
- `postgres`
- `node-py-crypto`
- `node-py-pycryptodome`
- `node-cpp-openssl`
- `node-cpp-cryptopp`

## 3. Sprawdzenie usług
```bash
kubectl get svc -n crypto-perf
```
**Co pokazuje:** usługi `ClusterIP` są utworzone i działają wewnątrz klastra.

## 4. Sprawdzenie ingressu
```bash
kubectl get ingress -n crypto-perf
```
**Co pokazuje:** system ma skonfigurowany punkt wejścia z zewnątrz klastra.

## 5. Test działania aplikacji
```bash
kubectl logs deploy/frontend -n crypto-perf
kubectl logs deploy/benchmark-controller -n crypto-perf
```
**Co pokazuje:** aplikacja startuje bez błędów i komponenty komunikują się ze sobą.

## 6. Test funkcjonalny z przeglądarki lub curl
```bash
curl http://localhost/
```
**Co pokazuje:** frontend jest osiągalny z zewnątrz klastra przez `Ingress`.

Jeżeli dostępne są endpointy API, można też pokazać odpowiedź kontrolera, np.:
```bash
curl http://localhost/api
```

## 7. Co warto pokazać na prezentacji
Najlepiej wystarczy krótka sekwencja:
1. `kubectl apply -k k8s`
2. `kubectl get pods -n crypto-perf`
3. `kubectl get svc -n crypto-perf`
4. `kubectl get ingress -n crypto-perf`
5. test w przeglądarce lub `curl`

## Podsumowanie
Taka prezentacja pokazuje trzy rzeczy:
- system został poprawnie wdrożony,
- obiekty Kubernetes działają zgodnie z konfiguracją,
- aplikacja realizuje założoną funkcjonalność i jest dostępna z zewnątrz.
