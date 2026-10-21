# Interfejs 0.2.4 — zmiany i podstawa weryfikacji

Stan: 20 października 2026 r. Aktualizacja odpowiada na dwa zrzuty działającej wersji 0.2.3 oraz zgłoszenie wolnego przewijania, powtarzania średniej w pojedynczej bitwie i zbyt ostrej siatki zestawień.

## Osobny wynik bitwy

`ui/session_stats.js` rozróżnia agregaty i pojedyncze bitwy przy renderowaniu grup. Nagłówek bitwy zawiera nazwę pojazdu, datę, mapę oraz zwycięstwo, porażkę lub remis. Nie powtarza liczby jednej bitwy ani jej win rate.

`details(..., battle)` tworzy dwie pojedyncze miary w `.ss-battle-performance`: wybrany rodzaj PD i pełną liczbę WN8. PD pochodzą z sumy serii obejmującej dokładnie jeden znany wynik. WN8 pochodzi z `stats.wn8` z pokryciem jednego wyniku. Nie wykorzystuje się średniej do prezentowania pojedynczej bitwy; brak pokrycia daje kreskę, również gdy brakująca seria miałaby sumę równą zero. Potwierdzone zero pozostaje zerem.

Podsumowania sesji, czołgów i map zachowują min/średnią/max. Wspólny kod rozliczeń pokazuje przychód, koszty i netto, w tym obligacje. Nie zmieniono obliczeń, normalizacji wyników ani formatu zapisu historii.

## Łagodniejszy układ

`ui/session_stats.css` zachowuje domyślny panel 700×620, Warhelios i dotychczasową oliwkowo-złotą paletę. Sekcje mają niewielkie zaokrąglenia, a nagłówki spokojne tło. Pionowa siatka komórek została usunięta; wiersze rozdzielają dyskretne poziome linie i niewielka różnica tła.

Cyfry PD/WN8 w agregatach mają nadal 16 jednostek logicznych, finanse 14, a pojedyncze miary bitwy 18. Wiersze otrzymały po 5 jednostek odstępu od góry i dołu. Kwoty są wyrównane do prawej z końcowym odstępem 4 jednostek. W kolumnach liczb miejsce z lewej pozostaje dostępne dla pełnych wartości, ponieważ nie ma tam już pionowej linii. Nazwy i pozostałe komórki zachowują boczne wcięcia. Nie zmniejszano fontu w celu zmieszczenia dużych kwot.

[Oficjalna tabela właściwości CSS Gameface](https://docs.coherent-labs.com/cpp-gameface/content_development/supported_features_tables/cssproperties/) wymienia obsługę `border-radius`, narożników i `box-shadow`; ograniczenie `box-shadow` dotyczy `inherit`, którego tu nie użyto. Dokumentację sprawdzono ponownie 20.10.2026. Nie wprowadzono CSS grid, `object-fit`, `currentColor` jako tła ani nowych zależności.

## Weryfikacja i jej granice

`tests/ui_contract.cjs` sprawdza rzeczywiste dostarczane pliki HTML/CSS/JS. Testy obejmują pojedyncze miary w obu trybach PD, brak min/średniej/max w bitwie, zachowanie agregatów, wyniki i brak danych, finanse z obligacjami, miniatury, kontrolki oraz kontrakt okna. Pomiar tekstu przez DOM Range wykrywa wejście cyfr w odstępy komórek; sprawdzane są zwykłe wyniki oraz pełne kwoty ±12 345 678, PD 123 456 i WN8 10420 przy szerokościach 320, 360, 420, 560, 620 i 744 piksele.

Aktualny raport: `tests/ui-report.json`. Końcowe podglądy sesji i listy bitew obejrzano wewnętrznie; obrazy QA nie są częścią paczki. Testy działają w Chromium z symulacją modelu klienta, bez natywnego renderera uruchomionego WoT. Zrzuty użytkownika potwierdzają działanie poprzedniego wydania, a nie stan nowej paczki 0.2.4 w jego kliencie.

Zmiana tempa rolki i jej niezależne testy są opisane w `WHEEL_0.2.4_SOURCE_EVIDENCE.md`.
