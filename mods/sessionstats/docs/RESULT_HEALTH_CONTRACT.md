# Kontrola formatu wyników — kontrakt 0.2.6

## Co sprawdza kontrola

`health.inspect_result(results, context=None, random_bonus_type=1)` jest funkcją
bez I/O i bez importów klienta WoT. Zwraca listę wpisów
`{code, path, expected, actual}`, nie zmieniając przekazanego wyniku.

Kontrola dotyczy dostarczonej odpowiedzi z wynikiem. Warstwa wywołująca pomija
odpowiedzi „jeszcze niegotowe” i błędy transportu; samo oczekiwanie na wynik
nie jest dowodem zmiany formatu.

Sprawdzane są:

- Typ głównego wyniku oraz kontenerów `common`, `personal`, `avatar`,
  a także obecnych kontenerów `players`, `vehicles` i `avatars`.
- Wymagane przez adapter identyfikatory, pola wyniku, WN8, PD, walut,
  kosztów i potrąceń; rodzaje danych, nieujemność właściwych wartości
  i obsługiwane numery drużyn.
- Nowe nazwy pól w kopercie, common, avatar, pojazdach i rekordach graczy.
  Katalog jest przypięty do odczytanych definicji klienta. Pierwszy wynik
  po aktualizacji nie staje się automatycznie „nową prawdą”.
- Krotki `autoLoadCost` o dwóch elementach i `autoEquipCost` /
  `autoEquipBoostersCost` o trzech elementach, również obligacje na
  potwierdzonej pozycji kosztu wyposażenia.
- Zgodność tożsamości pojazdu oraz znanego podziału kosztów dyrektyw
  zawartych już w automatycznym uzupełnieniu wyposażenia.

Katalog obejmuje 20 nazw w common, 62 w avatar, 249 w połączonych rekordach
pojazdów oraz 7 w danych gracza. Jest to suma odpowiednich kategorii
`BATTLE_RESULTS`, `BATTLE_PASS_RESULTS` i rozszerzenia `random`.
Nie wymaga obecności wszystkich tych pól: większość nie jest używana
przez mod albo występuje warunkowo. Kontrola typów skalarnych dotyczy pól
czytanych przez adapter; katalog pozostałych pól służy wykrywaniu nowych nazw.

Nie generują alarmu sama zmiana obrażeń, PD, wyniku bitwy, liczby graczy,
identyfikatorów w mapach rekordów, brak nieużywanego pola opcjonalnego ani
użycie listy zamiast krotki z tym samym obsługiwanym układem kosztów.
W nieużywanych mapach graczy, avatarów i pojazdów sprawdzany jest typ klucza,
bez zakładania dodatniego znaku: źródłowe `convertToFullForm` nie gwarantuje
dodatnich wartości dla wszystkich takich rekordów. Własne accountDBID,
arenaUniqueID i typeCompDescr nadal muszą być dodatnie.
Brak mnożnika potrącenia jest alarmem tylko przy niezerowym potrąceniu;
wadliwy obecny mnożnik jest nadal widoczną niezgodnością.
Prawidłowo rozpoznany wynik innego konta, replay i obsługiwane przez klienta
inne tryby są wyłączone z kontroli dotyczącej naszego zakresu bitew losowych.

## Zapis częściowego wyniku

Nowe nieużywane pole samo nie blokuje znormalizowania znanych danych.
Nieznany typ liczby pozostaje nieznany. Nie odczytujemy znanych indeksów
z wydłużonej albo skróconej krotki walut: nie da się wówczas potwierdzić,
że pozycje zachowały znaczenie.

Jeżeli długość i pozycje są znane, ale jedna konkretna kwota jest niedostępna,
pozostałe potwierdzone waluty zachowują niezależne wartości. Awaria części
finansowej nie usuwa poprawnie odczytanego wyniku walki ani PD.

## Zakres diagnostyki

Lista zawiera najwyżej 32 wpisy, ze stałymi limitami długości tekstu i
liczby przeglądanych pól/rekordów. Zawiera wyłącznie ścieżkę schematu i
opis typu/kształtu lub niespójności. Nie zawiera wartości statystyk, numeru
konta, numerów graczy/pojazdów, nicków ani całego surowego wyniku.
Dynamiczne klucze rekordów są reprezentowane jako `<record>` lub `vehicle`.
Niepoprawne, bardzo długie i niepasujące do nazw pól klucze są maskowane.

Funkcja nie wysyła komunikatów, nie zapisuje plików i nie ustala liczby
oczekujących wyników. Powiadomienia, ograniczenie ich powtarzania,
własny log moda oraz stan przycisku należą do warstwy runtime.

## Granice

Zmiana znaczenia liczby przy identycznych nazwach, typach i poprawnych
zakresach nie może zostać wykazana z samego payloadu. Kontrola nie dowodzi
też niezmienności wnętrz nieużywanych zagnieżdżonych rozszerzeń ani usunięcia
nieużywanego pola opcjonalnego. Nie zastępuje porównania z natywnym raportem
po dużej zmianie protokołu. Nowe pole może być nieszkodliwym rozszerzeniem;
ostrzeżenie sygnalizuje zmianę względem sprawdzonego kontraktu, nie dowodzi
błędu wszystkich statystyk.

## Źródła odczytane 21.10.2026

Wspólny commit: `5e721e36891c80d8d51a431164960c863641ee63` w publicznym
odwzorowaniu kodu klienta `izeberg/wot-src` (gałąź 2.4.1.5493).
Odczyt służy weryfikacji faktycznej implementacji, nie deklaracji stabilnego SDK.

- [Definicje pól i kosztów](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/battle_results/battle_results_common.py),
  blob `a8476aed85f0cfce21e6a3c9fb267e6cc533ae21`.
- [Składanie schematu według kategorii](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/battle_results/__init__.py).
- [Przypisanie trybu losowego do rozszerzenia random](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/battle_results/battle_results_constants.py).
- [Dodatkowe pole trybu losowego](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/battle_results/random.py),
  blob `60149af5c3da7728bc294a5a75d9f77aacfea9a4`.
- [Budowanie pełnej koperty i dynamicznych map rekordów](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client_common/shared_utils/account_helpers/BattleResultsCache.py),
  blob `f2f88011e792c06d332f73ac3aa237c567d8567f`, funkcja `convertToFullForm`.
- [Nazwy sekcji używane przez UI klienta](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/battle_results/settings.py),
  blob `63e443d35b0f11a7c5fa3caf172b401792949e5f`.

