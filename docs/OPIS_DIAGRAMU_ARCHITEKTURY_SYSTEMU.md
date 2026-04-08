# Opis architektury systemu 

> **W celu lepszego zrozumienia mechanizmu systemu wykorzystano analogię – w tym przypadku opowieść o fabryce sejfów** 

---

## Główna Idea: Laboratorium testujące sejfy

Proszę sobie wyobrazić, że jesteś właścicielem fabryki, która produkuje sejfy. Chcesz poznać odpowiedzi na trzy pytania:

1. **Który sejf otwiera się najszybciej?**
2. **Który sejf jest najtrudniejszy do złamania?**
3. **Który sejf jest najbardziej niezawodny?**

Dlatego zbudowałeś eksperymentalne **laboratorium**, gdzie testujesz **cztery różne projekty sejfów**. Każdy projekt wykonuje inny zespół specjalistów. System na diagramie to właśnie to laboratorium.

---

## Jak To Działa?


## Pierwszy poziom: Brama do fabryki (Warsztat HTTP)

Na wejściu do Twojego laboratorium znajduje się recepcja. To jest punkt wejścia dla wszystkich klientów.

Gdy ktoś przybywa do Twojej fabryki, robi to poprzez specjalny system komunikacji zwany HTTP. To jak specjalnie sformatowany list.

Klient (pracownik, tester) przychodzi tutaj i mówi:
- "Proszę, zaszyfruj moją wiadomość" - wysyła polecenie /encrypt
- "Proszę, odszyfruj tę wiadomość" - wysyła polecenie /decrypt

Ten list zostaje dostarczony do Twojego biura (portu 8000), gdzie czekasz jako dyrektor. To jedyna droga, którą klient może się z Tobą komunikować. Transport tego listu odbywa się poprzez HTTP - specjalny protokół internetowy, który gwarantuje, że wiadomość dotrze bezpiecznie.

Recepcja jest otwarta 24/7 i zawsze czeka na klientów z nowymi zadaniami.

---

## Drugi poziom: Dyrektor laboratorium (Kontroler)

Ty jesteś dyrektorem laboratorium. Gdy otrzymujesz zlecenie od klienta, robisz:

1. Zapisujesz zlecenie: "Zaszyfruj: TAJNE DANE 12345"
2. Sprawdzasz zegarek (początek pomiaru)
3. Wołasz do czterech zespołów: "Panowie, macie nowe zadanie!"
4. Czekasz, aż wszyscy skończą
5. Porównujesz wyniki: kto był szybszy, kto był dokładniejszy
6. Robisz notatki dla siebie

To Ty, jako dyrektor, koordynujesz całą pracę. Portu 8000 to Twoje biuro, gdzie przyjmujesz klientów.

---

## Trzeci poziom: Cztery zespoły specjalistów (Węzły)

Za ścianą od Twojego biura pracują cztery niezależne zespoły. Każdy zespół ma inną specjalizację szyfrowania.

### Zespół 1: Modzirna szkoła szyfrowania (Python Cryptography)

Jest to młoda, nowoczesna ekipa. Wszyscy mają dyplomy z najnowszych uniwersytetów.

Co robią: Szyfrują wiadomości najnowoczesnymi metodami
Jak pracują: Spokojnie, metodycznie
Czas pracy: Trwa im 2.8 milisekundy (2.8ms) - średnio
Narzędzia: Python 3.11, biblioteka cryptography
Gdzie pracują: Biuro 1

### Zespół 2: Klasyczna szkoła kryptografii (Python PyCryptodome)

To zespół ze starszymi, bardziej doświadczonymi fachowcami. Mają całą wiedzę kryptograficzną.

Co robią: Szyfrują wiadomości klasycznymi, sprawdzonymi metodami
Jak pracują: Niezawodnie, solidnie
Czas pracy: Trwa im 3.2 ms - nieco wolniej niż zespół 1
Narzędzia: Python 3.11, biblioteka PyCryptodome
Gdzie pracują: Biuro 2

### Zespół 3: Inżynierowie-geniusze (C++ OpenSSL)

To nie są zwykli pracownicy. To są inżynierowie wysokiego poziomu. Pracują na Very Niskim Poziomie Technologii.

Co robią: Szyfrują wiadomości na poziomie Hardware
Jak pracują: Błyskawicznie, optymalno
Czas pracy: Trwa im 1.9 ms - najszybsi ze wszystkich!
Narzędzia: C++, biblioteka OpenSSL, Alpine + C++17
Gdzie pracują: Biuro 3

### Zespół 4: Naukowcy zaawansowanej kryptografii (C++ Crypto++)

To są naukowcy rozwijający przyszłość bezpieczeństwa. Pracują nad najzaawansowanszymi algorytmami.

Co robią: Szyfrują wiadomości zaawansowanymi metodami matematycznymi
Jak pracują: Precyzyjnie, naukowo
Czas pracy: Trwa im 2.1 ms - szybko i dokładnie
Narzędzia: C++, biblioteka Crypto++, Alpine + C++17
Gdzie pracują: Biuro 4

---

## Czwarty poziom: Centralna poczta (Redis)

W samym srodku budynku znajduje się centralna poczty. To Redis.

Gdy ty, dyrektor, wydasz polecenie "Zaszyfuj to!", Redis:

1. Odbiera list z poleceniem
2. Wysyła kopie do wszystkich czterech zespołów
3. Czeka, aż wszyscy skończą
4. Zbiera wyniki z każdego biura
5. Dostarczą ci wszystkie cztery wyniki naraz

Redis jest jak centralny pośrednika informacji. Gdyby nie Redis, zespoły by sobie nawzajem przeszkadzały.

---



