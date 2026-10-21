# Szybkość przewijania w 0.2.4 — źródło i weryfikacja

Stan przeglądu: 20 października 2026 r. Użytkownik potwierdził, że po poprawce kierunku z 0.2.3 przewijanie listy w kliencie WoT jest zbyt powolne. Ta aktualizacja zmienia wielkość kroku. Dotychczasowe zasady interpretacji kierunku, ograniczania pozycji i anulowania domyślnego ruchu pozostają opisane w `WHEEL_0.2.3_SOURCE_EVIDENCE.md`.

## Dlaczego poprzednie tempo było niewłaściwe

Wersja 0.2.3 traktowała wartość `deltaY` w trybie pikselowym jako liczbę pikseli. Gdy host wysyła wartość znormalizowaną, np. `-1`, skutkiem było przesunięcie zaledwie o jeden piksel. Zgłoszenie potwierdza problem z tempem, ale nie jest pomiarem rzeczywistych wartości zdarzenia z klienta użytkownika; przykład `-1` wyjaśnia słabość wcześniejszego algorytmu.

## Wzorzec z interfejsu WoT

Ponownie odczytano [InfoView.js ze stałego commitu plików klienta 2.4.1.0 #977](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/InfoView/InfoView.js). Commit: `3605bd36c53d10c16be5d93f5414aa5fd129e84e`; SHA pliku: `af8259ddacaef0cf69b638b1ae88e455b2f2057b`.

| Miejsce w pliku | Zaobserwowana operacja | Zastosowanie w modzie |
| --- | --- | --- |
| Linie 2619–2622 | Domyślne `step: { type: 'proportional', factor: 4 }` | Krok równy jednej czwartej widocznej wysokości. |
| Linie 2787–2808 | Obliczenie `getWrapperSize / factor`; niezerowe `deltaY` wybiera kierunek | Wielkość surowej delty nie ustala odległości zwykłego ruchu rolki. |
| Linie 3150–3157 | Wysokość obszaru z `offsetHeight`, pozycja przez `scrollTop` | Krok dopasowuje się do bieżącej wysokości panelu. |

Jest to publiczne odwzorowanie plików klienta, a nie oficjalna obietnica zgodności modów Wargaming. Mod wykorzystuje tę samą proporcję, lecz nie kopiuje biblioteki animacji używanej przez klienta. Zmiana pozycji w tym panelu jest bezpośrednia.

## Zachowanie 0.2.4

- Zwykłe pionowe zdarzenie rolki w podłączonym Gameface przesuwa listę o **1/4 widocznej wysokości**. Dotyczy to zarówno wartości `1`, `120`, jak i wartości ułamkowych. Cztery takie zdarzenia pokrywają jedną wysokość widocznej listy, o ile nie osiągnięto końca zawartości.
- Dotyczy to także trybu liniowego. Oddzielny tryb stronowy zachowuje jednostki całych stron, czyli widoczną wysokość pomnożoną przez deltę.
- Rozmiar jest pobierany z rzeczywistego obszaru przewijania; nie ma dodatkowego mnożenia przez skalę GUI. Dzięki temu powiększenie interfejsu nie nalicza skali dwukrotnie.
- Kierunek zależy od znaku: dodatnia delta w natywnym kontrakcie przewija ku górze, ujemna ku dołowi. W podglądzie HTML nadal działa zwykła rolka przeglądarki.
- Pozostają ograniczenia u góry i u dołu listy, doładowywanie dalszej historii, blokada przesuwania tła dialogu resetu oraz ignorowanie pionowego ruchu dla gestów poziomych i Shift + rolka.
- Ruch rolki nad tytułem okna nie steruje zawartością. Anulowanie zdarzenia poprzedza ręczne przesunięcie, więc prawidłowo obsłużona rolka nie dodaje równocześnie domyślnego ruchu przeglądarki.

Ta decyzja celowo nie zachowuje pikselowej precyzji małych natywnych delt: w interfejsie klienta są traktowane jako polecenia przesunięcia listy. Różnice liczby zdarzeń wysyłanych przez urządzenia nadal mogą wpływać na odczuwalne tempo; nie wprowadzono niezweryfikowanego rozpoznawania rodzaju myszy ani trackpada.

## Weryfikacja

Test `tests/ui-wheel.cjs` używa dostarczonych plików HTML/CSS/JS. Główne przypadki korzystają z rzeczywistego wejścia Chromium przez CDP (`page.mouse.wheel`, `isTrusted === true`), co pozwala wykryć nieanulowany domyślny ruch przeglądarki. Tylko przypadki jednostek liniowych i stronowych używają syntetycznych zdarzeń.

Regresje obejmują czytelny krok dla `-1`, prawidłowy kierunek dla `+1`, drobną deltę ułamkową, serię ruchów, krótszy panel, oba kierunki, blokady gestów, modalny reset, granice listy i doładowanie 95 pozycji. Oddzielna strona sprawdza zwykłe przewijanie podglądu bez modelu Gameface. Kontrola po `destroy()` potwierdza usunięcie adaptera.

Wynik bieżącego uruchomienia znajduje się w `tests/wheel-report.json`. Zakres weryfikacji to Chromium z atrapą kontraktu modelu; nie uruchomiono klienta WoT ani natywnego silnika Gameface. Nie wykonywano bitew i nie zmieniano statystyk konta.
