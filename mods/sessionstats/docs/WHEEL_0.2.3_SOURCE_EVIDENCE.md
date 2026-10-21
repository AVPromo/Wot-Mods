# Przewijanie rolką w 0.2.3 — źródła i zakres weryfikacji

Stan przeglądu: 20 października 2026 r. Zmiana dotyczy wyłącznie przewijania panelu `ui/session_stats.js`. Zgłoszenie użytkownika dotyczyło odwróconego kierunku w prawdziwym kliencie WoT; wcześniejszy panel polegał wyłącznie na `overflow-y: auto`.

## 1. Kierunek w aktualnym interfejsie WoT

Odczytany materiał: pliki klienta **2.4.1.0 #977**, utrwalone w repozytorium `Kurzdor/wot.assets`, commit **`3605bd36c53d10c16be5d93f5414aa5fd129e84e`** z 16 października 2026 r. To publiczne odwzorowanie plików klienta; nie jest to oficjalny kontrakt kompatybilności modów Wargaming.

Źródło: [InfoView.js — stały commit](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/InfoView/InfoView.js).

Łańcuch operacji w tym pliku:

| Miejsce | Operacja | Znaczenie |
| --- | --- | --- |
| Linie 2615–2618 | `Next = -1`, `Prev = 1` | Kierunek ma wartość liczbową. |
| Linie 2763–2769 | Aktualna pozycja + kierunek × krok | Ujemny kierunek zmniejsza pozycję przewijania. |
| Linie 2787–2808 | `deltaY` wybiera kierunek i wywołuje przewinięcie | To aktywna ścieżka obsługi rolki. |
| Linie 3150–3157 | `getDirection: e => e.deltaY > 1 ? p.Next : p.Prev` i przypisanie `scrollTop` | Dodatnia delta większa od 1 przesuwa ku górze, ujemna ku dołowi. |
| Linie 3305–3309 | Przycisk górny również używa `Next` | Niezależne potwierdzenie znaczenia ujemnego kierunku. |

Wniosek: natywny komponent WoT interpretuje znak przeciwnie do standardowego przewijania przepełnionej zawartości w przeglądarce. To zgadza się z obserwacją użytkownika. W modzie odwrócenie działa tylko po udanym podłączeniu modelu Gameface (`state.bound`); sam podgląd HTML zachowuje zwykłą obsługę przeglądarki.

Nie skopiowano progu `> 1`, który nie określa spójnego kierunku małych dodatnich delt. Kierunek w modzie wynika ze znaku. Nie skopiowano też szybkości animowanego komponentu WoT: zachowujemy wielkość delty urządzenia.

## 2. Surowy DOM a React

Sam `onWheel` komponentu React nie wystarczyłby do stwierdzenia, że można używać identycznego znaku w bezpośrednim `addEventListener`.

W [InfoView.html z tego samego commitu](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/InfoView/InfoView.html), linie 6120–6133, dołączony React **przepisuje istniejące `deltaY` bez zmiany znaku**. Dopiero gdy tego pola brak, korzysta z zanegowanego `wheelDeltaY` albo `wheelDelta`.

Gameface dokumentuje `wheel` jako obsługiwane zdarzenie DOM L3 z interfejsem `WheelEvent`: [tabela zdarzeń JS](https://docs.coherent-labs.com/cpp-gameface/content_development/supported_features_tables/jsevents/). Oficjalny poradnik [SVG UI Tricks — `mouse-map-controls.js`](https://guide.coherent-labs.com/layout-assets-and-styling/graphics--shapes/svg-ui-tricks/), aktualizacja 2 lipca 2026 r., używa bezpośrednio `map.addEventListener("wheel", ...)`, `event.deltaY` i `event.preventDefault()`, bez React. To uzasadnia użycie surowego DOM `deltaY` przez mod. Nie dodajemy niesprawdzonej ścieżki starszych zdarzeń `mousewheel`.

## 3. Anulowanie domyślnego ruchu — dowody i ograniczenie

[Dokumentacja wejścia Gameface C++](https://docs.coherent-labs.com/cpp-gameface/integration/optional_features/inputhandlingcpp_native/) opisuje kolejność: obsługa skryptowa i propagacja zdarzenia, potem domyślne operacje, w tym przewijanie. [API Event](https://docs.coherent-labs.com/cpp-gameface/api_reference/classes/interface_event/) udostępnia `preventDefault`, `stopPropagation`, `cancelable` i `defaultPrevented`. Wspomniany wyżej oficjalny przykład używa `preventDefault()` w zwykłym listenerze rolki.

Adapter instaluje jeden listener na własnym panelu, anuluje zdarzenie przed zmianą `scrollTop` i zatrzymuje propagację. Nie instaluje globalnej obsługi na `document`. Zamykanie adaptera usuwa ten sam listener. Obsłużone zdarzenie pozostaje anulowane również przy górnej i dolnej granicy listy; dzięki temu nie przewija równocześnie innego elementu.

**Nie potwierdzono pomiarem rzeczywistego `event.cancelable` w uruchomionym WoT.** Publiczna dokumentacja opisuje obsługiwany interfejs i użycie anulowania, lecz nie ustala flagi każdego wejścia natywnego w konkretnym buildzie klienta. `InfoView.js` nie stanowi takiego dowodu: używa własnego komponentu przewijania i nie wywołuje `preventDefault()` w analizowanym handlerze. Jego [InfoView.css](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/InfoView/InfoView.css), linie 190–193, ustawia `overflow-y: hidden`; natywny komponent korzysta z osobnego paska i ręcznej zmiany pozycji.

Jeżeli host poda jawnie `cancelable === false`, adapter pozostawia zdarzenie bez dodatkowej zmiany pozycji. To celowo unika nakładania ręcznego ruchu na domyślny ruch, którego nie można anulować. W takim nietypowym kontrakcie poprawka kierunku nie zadziała; wymagałoby to obserwacji klienta i osobnego dostosowania. Nie udajemy, że test w Chromium rozstrzyga zachowanie silnika C++ Gameface.

## 4. Zachowanie wybrane dla tego panelu

- Tryb pikselowy zachowuje wartość bezwzględną delty, także drobne ruchy trackpada; zmienia się tylko znak w podłączonym Gameface.
- Tryb liniowy mnoży deltę przez 24 jednostki logiczne, z uwzględnieniem skali klienta. Tryb stronowy używa bieżącej wysokości przewijanej części. To decyzja moda o tempie, nie obietnica identycznego tempa jak w `InfoView`.
- Pozycja jest ograniczona do zakresu od zera do końca zawartości. Ręczne przesunięcie uruchamia istniejące doładowanie historii w partiach; nie czeka na kolejną rolkę ani na implementację zdarzenia `scroll` w silniku.
- Gest z dominującą składową poziomą oraz Shift + rolka nie zamienia się w ruch pionowy. Rolka nad tytułem nie steruje listą.
- Otwarty dialog resetu przechwytuje rolkę nad panelem i nie przesuwa statystyk w tle. Zdarzenia już anulowane przez innego odbiorcę są pozostawiane bez dodatkowego ruchu.

## 5. Weryfikacja regresji

Test: `tests/ui-wheel.cjs`. Wynik podczas przygotowania poprawki: **19/19**, bez błędów JavaScript.

Główne przypadki używają **rzeczywistego wejścia Chromium przez CDP** (`page.mouse.wheel`), z `isTrusted === true`. Podłączony model testowy odtwarza kontrakt znaku z pliku WoT. Dzięki temu przeglądarka wykonuje własną domyślną obsługę, jeśli mod jej skutecznie nie anuluje. Sama emisja syntetycznego `WheelEvent` nie wykazałaby tego ryzyka.

Sprawdzone są oba kierunki i dokładnie jedno przesunięcie, małe delty, seria ruchów, poziome gesty, Shift, tytuł okna, dialog resetu, granice oraz doładowanie 95 pozycji w partiach. Oddzielna strona bez modelu Gameface potwierdza niezmienione przewijanie przeglądarkowe. Po `destroy()` test odtwarza pierwotny błędny kierunek dla znaku WoT: stanowi to kontrolę negatywną, a zarazem sprawdzenie usunięcia listenera. Syntetyczne zdarzenia służą wyłącznie dwóm dodatkowym przypadkom jednostek liniowych i stronowych.

Zakres: dostarczony JS/HTML/CSS w Chromium z atrapą mostka modelu. Nie uruchomiono klienta WoT ani silnika Gameface, nie wykonano bitwy i nie zmieniono statystyk konta.
