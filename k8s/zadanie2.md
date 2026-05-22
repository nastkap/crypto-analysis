# Zadanie 2 - Ograniczenie zasobów, polityki sieciowe i planowanie w Kubernetes

Poniżej opisano krótko, ale konkretnie dodatkowe mechanizmy użyte w projekcie `crypto-perf`.

## a) Ograniczenie wykorzystywanych zasobów
W projekcie zastosowano `resources.requests` i `resources.limits` w manifestach wszystkich głównych podów.
Dodatkowo w `resource-quota.yaml` zdefiniowano `ResourceQuota` oraz `LimitRange` dla całego namespace `crypto-perf`.

**Uzasadnienie:**
- `requests` określają minimalną ilość CPU i pamięci potrzebną do poprawnego działania poda.
- `limits` chronią klaster przed nadmiernym zużyciem zasobów przez pojedynczy komponent.
- `ResourceQuota` ogranicza łączny pobór zasobów w całym namespace.
- `LimitRange` wymusza sensowne domyślne limity także dla nowych podów.

Takie podejście zapobiega sytuacji, w której jeden mikroserwis zużyje zbyt dużo CPU lub RAM i pogorszy działanie całego systemu.

## b) Zdefiniowanie polityki sieciowej
W projekcie skonfigurowano `NetworkPolicy` w pliku `network-policy.yaml`.
Domyślna polityka blokuje ruch przychodzący, a następnie jawnie dopuszczane są tylko potrzebne połączenia między komponentami.

**Uzasadnienie:**
- ruch do `postgres` jest dozwolony tylko z komponentów aplikacyjnych,
- ruch do `message-broker` jest dozwolony tylko z kontrolera i węzłów kryptograficznych,
- `frontend` może przyjmować ruch z zewnątrz przez `Ingress` i łączyć się z kontrolerem,
- komunikacja DNS jest dopuszczona tylko tam, gdzie jest potrzebna.

Dzięki temu system ma zasadę najmniejszych uprawnień w warstwie sieciowej i ogranicza ryzyko nieautoryzowanej komunikacji między podami.

## c) Mechanizmy sterujące planowaniem rozmieszczenia obiektów
W projekcie użyto mechanizmów wpływających na to, gdzie pody są uruchamiane:

- `nodeAffinity` w pliku `node-affinity.yaml`,
- `podAntiAffinity` w `frontend.yaml`,
- dodatkowo gotowe są reguły rozproszenia i przykłady planowania dla komponentów testowych.

**Uzasadnienie:**
- `nodeAffinity` pozwala preferować lub wymuszać uruchamianie wybranych podów na określonych węzłach, np. dla zadań obliczeniowo ciężkich.
- `podAntiAffinity` rozkłada repliki frontendu na różne węzły, co poprawia dostępność.
- W środowisku testowym Minikube nie jest to krytyczne dla działania, ale pokazuje poprawne wykorzystanie mechanizmów planowania w Kubernetes.

## Podsumowanie
Projekt uwzględnia wszystkie dodatkowe elementy wymagane w p. 2:
- kontrolę zużycia zasobów,
- polityki sieciowe,
- sterowanie rozmieszczeniem podów na węzłach klastra.

Mechanizmy te zwiększają bezpieczeństwo, przewidywalność i stabilność wdrożenia.
