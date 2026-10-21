# Źródła poprawki okna 0.2.1

Sprawdzono 20 października 2026 r. Cel pakietu: WoT PC Wargaming EU 2.4.1.0.
To zapis dowodów implementacyjnych i zakresu lokalnej weryfikacji, a nie deklaracja
gwarantowanego przez Wargaming, stabilnego API dla modów.

## Co wykazał test użytkownika

Na przesłanym obrazie z wersji 0.2.0 okno pojawia się przy lewym górnym rogu.
Model dostarcza widoczne dane i teksty stanu, natomiast etykiety elementów `button`
są niewidoczne. Działający przycisk stopki ma jawny układ flex i etykietę w `span`.
Sam obraz nie rozstrzyga, czy poprzedni callback `resize` nie dotarł do Pythona,
czy późniejsza operacja pozycjonowania zakończyła się błędem. Nie otrzymaliśmy
logu pozwalającego rozróżnić te warianty.

W poprzednim `views.py` pozycjonowanie wykonywało się dopiero po komunikacie
`resize` z dokumentu. Brakowało wywołania natywnego centrowania przy `_onReady`
i reakcji na rzeczywisty rozmiar powierzchni `onSizeChanged`. Odczyt wymiarów
rodzica zakładał, że `Window.parent` zawsze ma interfejs wrappera `Window.size`.
Kod nie sprawdzał również wyniku `False` zwracanego przez natywne `move`.

## Przypięte źródła klienta

Repozytorium `izeberg/wot-src`, gałąź EU, sprawdzony commit
`5e721e36891c80d8d51a431164960c863641ee63` z 16 października 2026 r.
To publiczne odwzorowanie skryptów klienta, a nie oficjalnie udokumentowany
kontrakt kompatybilności modów Wargaming.

| Fakt sprawdzony w kodzie | Dokładne źródło |
| --- | --- |
| `WindowImpl.center()` wywołuje `self.area.center(self)`; `move(x,y,...)` korzysta z tego samego obszaru. Obie metody zwracają `False`, gdy okno nie jest przypisane do obszaru. | [window_impl.py, linie 35–57](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/pub/window_impl.py#L35-L57) |
| `WindowsArea.center(window)` deleguje do `centerPyWindow(window.uniqueID)`; `move` do `movePyWindow`. Sam algorytm natywnego wyznaczania pozycji nie jest opisany w tych skryptach. | [windows_area.py, linie 40–44](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/windows_area.py#L40-L44) |
| `Window.parent` zwraca `self.proxy.parent` bez `getObject`, podczas gdy `WindowSettings.parent` jawnie używa `getObject`. Nie należy zakładać identycznego interfejsu obu zwracanych obiektów. | [window.py, linie 83–91](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L83-L91) oraz [linie 153–159](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L153-L159) |
| Wrapper `Window.size` odczytuje `proxy.windowSize`. Stub `PyObjectWindow` udostępnia `windowSize`, nie deklaruje aliasu `.size`. To uzasadnia zachowanie jawnego wrappera głównego okna; nie dowodzi samo w sobie konkretnego wyjątku w teście użytkownika. | [window.py, linie 223–230](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L223-L230) oraz [_wulf.py: PyObjectWindow](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/_stubs/_wulf.py#L1293-L1338) |
| Bazowe `Window._onReady()` wykonuje wyłącznie `self.show()`. `WindowImpl` nie dodaje własnej implementacji `_onReady`. Nasze centrowanie i `show(True)` zachowują tę czynność; nie jest potrzebne drugie `super()._onReady()` wyświetlające okno ponownie. | [window.py, linie 285–287](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L285-L287), [linie 315–316](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L315-L316) oraz [window_impl.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/pub/window_impl.py) |
| `_cWindowStatusChanged(_,newStatus)` emituje publiczne zdarzenie **z jednym argumentem**: `onStatusChanged(newStatus)`. `_cResized(width,height)` emituje **trzy argumenty**: `onSizeChanged(uniqueID,width,height)`. `_cReady` woła `_onReady` przy stanie `LOADED`. | [window.py, linie 359–383](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L359-L383) |
| `IGuiLoader.scale` jest właściwością interfejsu; `GuiApplication.scale` odczytuje rzeczywistą wartość `self.__impl.scale`. To źródło skali publikowanej w `payload.viewport.scale`, bez parsowania ustawienia automatycznej skali i bez używania `devicePixelRatio`. | [skeletons/gui/impl.py, linie 46–48](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/skeletons/gui/impl.py#L46-L48) oraz [gui_application.py, linie 69–71](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/gui_application.py#L69-L71) |

Nie znaleziono w sprawdzonych Pythonowych wrapperach okna ani widoku
udokumentowanego odpowiednika ustawiania rozmiaru tekstury. Mod nie dodaje
domyślnej metody `resize` do C++ ani nie przypisuje do read-only `Window.size`.

## Źródło autora moda: rozmiar Gameface i gotowość okna

`przemyslaw-zan/zanju-wot-mods`, commit
`809ad2740a33154de22c828a5dd3007e7167a282` z 14 października 2026 r., GPL-3.0:

- [card_window.py, linie 163–171](https://github.com/przemyslaw-zan/zanju-wot-mods/blob/809ad2740a33154de22c828a5dd3007e7167a282/mods/campaign-tracker/src/zanju_ct/gameface/card_window.py#L163-L171)
  pokazuje `_onReady` z bezpośrednim `show(False)`. Nasze interaktywne okno używa
  `show(True)`, aby otrzymać fokus.
- [card_panel.js, linie 128–181](https://github.com/przemyslaw-zan/zanju-wot-mods/blob/809ad2740a33154de22c828a5dd3007e7167a282/mods/campaign-tracker/res/gui/gameface/mods/zanju_campaigns/card_panel.js#L128-L181)
  mierzy układ po klatkach renderowania, publikuje fizyczny rozmiar przez
  `viewEnv.resizeViewPx(width,height)` i oddzielnie wysyła komendę do modelu.
  W tym źródle nie ma dowodu na sygnaturę `viewEnv.remToPx(1)`; w naszym UI
  jest to wyłącznie chroniona ścieżka rezerwowa. Preferowana skala pochodzi
  z natywnego `IGuiLoader.scale`.
- [Choosing a UI approach](https://github.com/przemyslaw-zan/zanju-wot-mods/blob/809ad2740a33154de22c828a5dd3007e7167a282/docs/reference/choosing-a-ui-approach.md)
  opisuje potrzebę poprawnego rozmiaru rzeczywistej powierzchni natywnego okna,
  ponieważ wpływa ona na obszar przechwytujący wejście. Test w przeglądarce
  nie zastępuje tej części testu w grze.

## Zmiana integracji w 0.2.1

1. Przy natywnym `_onReady` okno korzysta z `WindowImpl.center()` przed `show(True)`.
   Pierwsza próba ustawienia pozycji nie zależy od komunikatu z JavaScript.
2. Po każdym nowym, potwierdzonym rozmiarze powierzchni `onSizeChanged` następuje
   ponowne centrowanie. Dokument nadal odpowiada za `resizeViewPx`.
3. Zachowany wrapper głównego okna dostarcza wymiarów do modelu i do rezerwowego
   `move`. Ta ścieżka jest używana, gdy obszar nie przyjmie natywnego `center`.
   Wynik `False` jest rozpoznawany i nie trafia do pamięci udanego pozycjonowania.
4. Zmiana rozmiaru głównego okna odświeża granice i skalę dokumentu. Zdarzenie
   skali w UI wysyła komendę `viewport`, która ponownie odczytuje natywną skalę.
5. `close` jest obsługiwane bezpośrednio przez właściciela okna. Zamknięcie
   odłącza subskrypcje i timer; spóźnione komendy oraz gotowość poprzedniego
   okna są ignorowane przy użyciu numeru jego generacji.
6. Diagnostyka zapisuje po jednym komunikacie dla `dom_ready`, `model_bound`
   i `layout_ready`, pierwszym komunikacie każdego typu oraz maksymalnie czterech
   zmian rozmiaru na otwarcie. Pojedynczy timer po pięciu sekundach zgłasza brakujące
   etapy. Nie zapisuje identyfikatora konta, pseudonimu, danych sesji ani całego
   payloadu. `layout_ready` oznacza ukończony pomiar DOM, nie dowód widoczności
   każdego tekstu w natywnym rendererze.

## Lokalna weryfikacja i granice

`tests/test_runtime.py`: **31 testów przechodzi w CPython 3 oraz CPython 2.7.18**.
Testowe odpowiedniki obiektów Wulf sprawdzają kolejność `center` przed `show`, rzeczywiste
sygnatury zdarzeń, ponowne centrowanie bez komendy HTML, brak `.size` na natywnym
obiekcie rodzica, zmianę skali, błędne wymiary, odrzucone pozycjonowanie, zamknięcie,
spóźnione komendy oraz brak pozostawionych subskrypcji i timerów.

Te testy sprawdzają nasz kod wobec odczytanego kontraktu. Nie uruchamiają silnika
WoT ani Coherent Gameface. W chwili zapisu tego dokumentu poprawka 0.2.1 nie została
jeszcze ponownie przetestowana w kliencie gry. Dlatego poprawnego natywnego rysowania
tekstu, hit-testów i działania centrowania wewnątrz C++ nie przedstawiamy jako
potwierdzonych testem gry. Pełne wyniki testów UI i kontroli gotowej paczki są
podawane oddzielnie w raporcie wydania.
