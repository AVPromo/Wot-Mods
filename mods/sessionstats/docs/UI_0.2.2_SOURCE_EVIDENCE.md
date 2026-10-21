# Okno 0.2.2: przeciąganie, geometria i potwierdzone źródła

Sprawdzono 20 października 2026 r. Cel: WoT PC Wargaming EU 2.4.1.0.
Kod źródłowy odczytano z publicznych kopii zasobów klienta oraz repozytorium
autora moda. Nie są one deklaracją stabilnego, oficjalnego API modów Wargaming.

## Obserwacja i zakres poprawki

Nowy pełny obraz użytkownika pokazuje panel około 700×620 px przy lewym górnym
rogu, z poprawnie wyświetlanymi wynikami bitew. W 0.2.1 nie było obsługi natywnego
przeciągania nagłówka. Bez `game.log` nie można rozstrzygnąć, czy pozostawanie
przy (0,0) wynikało z początkowego rozmiaru powierzchni, obszaru okna czy kolejności
wykonania operacji. Nie przedstawiamy żadnego z tych wariantów jako ustalonej
przyczyny testu użytkownika.

0.2.2 dodaje potwierdzone zdarzenie przesuwania klienta, jawne pozycjonowanie
przez `WindowImpl.move(x,y)` oraz rozróżnienie między żądaniem położenia a
zaobserwowanym `Window.position`. Po przesunięciu okna przez gracza odświeżanie
danych nie przywraca środka ekranu. Jeśli zmniejszenie obszaru gry wypchnie panel
poza ekran, pozycja jest jedynie ograniczana do dostępnych granic.

## Natywne przeciąganie: kompletna ścieżka JS i Python

Źródła JS: `Kurzdor/wot.assets`, commit
`3605bd36c53d10c16be5d93f5414aa5fd129e84e` z 16 października 2026 r.; opis
commitu: **2.4.1.0 #977**.

| Sprawdzony element | Dokładne źródło |
| --- | --- |
| Klientowy helper `sendEvent.move(on)` wysyła zdarzenie typu 16 z `isMouseEvent: true` i wartością `on`. Proxy ma typ `GFViewEventProxy`. | [tutorial.js, linie 197–244](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/js/tutorial.js#L197-L244) |
| Natywne okno plutonu rozpoczyna przesuwanie tylko dla lewego przycisku myszy; kończy je w nasłuchu `mouseup` na dokumencie i usuwa ten nasłuch. | [MembersWindow.js, linie 1257–1268](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/lobby/platoon/MembersWindow/MembersWindow.js#L1257-L1268) |
| Pythonowy `MembersWindow` używa `WindowFlags.WINDOW`, bez dodatkowej flagi przesuwalności. Jego content ma `ViewSettings` z domyślnym `ViewFlags.VIEW`, tak jak okno moda. | [platoon_members_view.py, linie 87–92](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/lobby/platoon/view/platoon_members_view.py#L87-L92) oraz [linie 724–739](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/lobby/platoon/view/platoon_members_view.py#L724-L739) |
| Pośrednia klasa `PreloadableWindow` tylko przekazuje flagi i zawartość do `WindowImpl`; jej dodatkowe zachowanie dotyczy ukrywania widoku wczytanego wcześniej. Nie dodaje mechanizmu ani flagi drag. | [platoon_helpers.py, linie 19–36](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/lobby/platoon/platoon_helpers.py#L19-L36) |

Zdarzenie używane przez nasz nagłówek:

```javascript
viewEnv.handleViewEvent({__Type:'GFViewEventProxy', type:16, isMouseEvent:true, on:true});
```

Zakończenie używa tego samego zdarzenia z `on:false`. Polecenie modelu
`{action:'drag', active:true/false}` wyłącznie informuje właściciela okna, by
zachował wybraną pozycję. Nie przesyła współrzędnych kolejnych ruchów myszy.
Nie używamy niepotwierdzonego `startWindowDrag`, przesuwania samego DOM ani
symulacji kursora. Przycisk zamknięcia i otwarty dialog resetowania nie rozpoczynają
drag; JS kończy operację także przy utracie fokusu i zwalnianiu dokumentu.

## Rozmiar i pozycjonowanie

- [tutorial.js, linie 262–282](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/js/tutorial.js#L262-L282)
  potwierdza wywołania `getViewSizePx()`, `resizeViewPx(width,height)`, `getScale()`
  i `remToPx(value)`. To kod korzystający z bindingu; nie zawiera implementacji
  C++ tych metod. Ogólny `engine.call` nie jest podstawą do wymyślania nazw
  dodatkowych poleceń zmiany rozmiaru.
- [WindowImpl.move, linie 42–48](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/pub/window_impl.py#L42-L48)
  deleguje pozycjonowanie do natywnego obszaru. [Window.position i Window.size](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L207-L230)
  odczytują odpowiednio `windowPosition` i `windowSize` proxy. [Zdarzenia](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/frameworks/wulf/windows_system/window.py#L381-L386)
  mają podpisy `onSizeChanged(uniqueID,width,height)` i
  `onPositionChanged(uniqueID,x,y)`.
- [Autorowy card_window.py, linie 417–438](https://github.com/przemyslaw-zan/zanju-wot-mods/blob/809ad2740a33154de22c828a5dd3007e7167a282/mods/campaign-tracker/src/zanju_ct/gameface/card_window.py#L417-L438)
  wyznacza położenie z wymiarów zgłoszonych przez dokument i wymiarów rodzica,
  następnie używa `WindowImpl.move`. To wzorzec przyjęty w 0.2.2.
- [Autorowy card.css](https://github.com/przemyslaw-zan/zanju-wot-mods/blob/809ad2740a33154de22c828a5dd3007e7167a282/mods/campaign-tracker/res/gui/gameface/mods/zanju_campaigns/card.css#L14-L21)
  nie narzuca `html` i `body` szerokości/wysokości 100%; panel pozostaje w normalnym
  przepływie z jawną szerokością. Natywny dokument moda również odłącza wysokość
  `html/body` od początkowej powierzchni. Podgląd przeglądarkowy ma osobny kontekst.

Pomiar DOM nie udaje potwierdzenia wymiarów tekstury. Jednorazowy timer po pięciu
sekundach może oddzielnie wskazać brak etapu renderera, rozbieżność żądanej i
zaobserwowanej pozycji lub rozbieżność dokumentu i natywnej powierzchni. Znika
wcześniej dopiero po zgodnych pomiarach i etapach. Logowanie jest ograniczone,
bez danych konta i treści statystyk; zamknięcie odłącza wszystkie nasłuchy i timer.

## Weryfikacja lokalna

`tests/test_runtime.py`: **34/34 na Pythonie 3 oraz 34/34 na Pythonie 2.7.18**.
Istotne regresje obejmują przyjęte, lecz ograniczone do (0,0) żądanie ruchu
początkowej powierzchni pełnoekranowej; poprawne ustawienie dopiero po jej
natywnym resize; zachowanie pozycji przy aktualizacjach danych/rozmiaru/skali;
nieprzerywanie aktywnego drag; ograniczenie położenia do mniejszego ekranu;
usuwanie nasłuchów i ignorowanie komend poprzedniej instancji okna.

Testy używają podwójnych obiektów Wulf i sprawdzają kod wobec odczytanych
kontraktów. Nie uruchamiają C++ klienta. Nie oznaczają, że wersja 0.2.2 została
już ponownie sprawdzona w działającym WoT.
