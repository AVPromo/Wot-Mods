# Wspólne repozytorium, niezależne wydania

Infrastruktura CI jest osobnym PR od importu źródeł. Kolejność merge:
**pipeline → źródła statystyk → walidacja importu na zaakceptowanym pipeline**.
Przed importem źródeł infrastruktura wykonuje swoje testy, a kroki kompilacji
i wydawania statystyk raportują oczekiwanie. Nie oznacza to przetestowania moda.
Po połączeniu źródeł z `main` uruchomi się pierwsze automatyczne wydanie.
Samo utworzenie obu PR nie publikuje Release i nie łączy ich automatycznie.

| Mod | Źródła | Wersja bazowa | Tagi | Workflow |
|---|---|---|---|---|
| Medkit Reminder | `source/`, `assets/` | `VERSION` | `v1.6.…` | `release.yml` |
| Session Stats | `mods/sessionstats/` | `mods/sessionstats/VERSION` | `sessionstats-v0.2.…` | `sessionstats-release.yml` |

Zmiany w katalogu jednego moda nie wydają drugiego. Wspólna zmiana publikatora,
obliczania wersji albo skanera powoduje wydanie obu, ponieważ może wpływać na oba.
Każdy push na `main` dotyczący statystyk buduje nową wersję i tworzy Release.
PR wykonuje testy i tworzy tylko artefakt Actions, bez prawa publikacji.

Numer patch = bazowy patch + numer uruchomienia danego workflow − 1.
Puste, nieudane lub wstrzymane przebiegi mogą pozostawić luki w numeracji.
Nie zmieniaj bazowego VERSION dla zwykłych poprawek; podnieś major/minor przy
nowej linii wydań. Ponowienie tego samego run zachowuje wersję i sprawdza
istniejący tag, SHA commitu, pełny zestaw plików oraz ich SHA-256. Opublikowane
pliki nie są nadpisywane. Niepełny draft można wznowić; obcy tag blokuje publikację.

ZIP instalacyjny zawiera `.wotmod`, domyślny JSON, jedną kopię OpenWG i źródła.
Osobnymi assetami są również oba `.wotmod`, JSON, `BUILD.json`, `SHA256SUMS.txt`.
Wersja trafia do nazwy pliku, `meta.xml`, skompilowanego `VERSION` i raportu.
Wersje klienta w starszych notatkach oznaczają przebadany punkt odniesienia,
nie gwarancję zgodności z dowolną przyszłą wersją WoT.

Kompilator gry to CPython 2.7.18 pobrany z oficjalnego python.org i zweryfikowany
SHA-256 `da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814`.
Archiwum zgadza się również z opublikowanym przez Python.org historycznym MD5
`38c84292658ed4456157195f1c9bcbe1` (MD5 jest tu informacją o pochodzeniu;
pipeline egzekwuje SHA-256). Źródło: https://www.python.org/downloads/release/python-2718/.
Kompilacja i testy moda nie pobierają kodu przez interpreter 2.7.

Walidacja obejmuje testy Pythona 3 i 2.7, sześć zestawów testów Chromium,
powtórne budowanie z porównaniem SHA-256, prywatność źródeł i archiwów
oraz rekursywną kontrolę stałych/ścieżek bajtkodu. Materiały QA są syntetyczne.
To testy z atrapami klienta; nie zastępują uruchomienia gry.

Build ma `contents: read`; osobny job publikacji dostaje `contents: write`
i tylko jego krok publikujący otrzymuje `GH_TOKEN`. Bez PAT, sekretów użytkownika,
`pull_request_target`, prywatnych runnerów ani publikacji z gałęzi PR.
Akcje checkout/upload/download mają przypięte pełne SHA.
