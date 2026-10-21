# Stay Sharp Medkit Reminder 1.6.0 — code review / hardening

## Punkt wyjścia

Wersja 1.5.0 została potwierdzona przez użytkownika jako działająca w grze, w tym w widokach celowania. Nowe wydanie zmienia tylko mechanizm przyłączania do cyklu życia panelu oraz sprawdzanie zgodności. Algorytm pulsowania i zasoby DDS pozostają bez zmian.

## 1. Subskrypcja zdarzeń zamiast monkeypatchingu

**Wersja 1.5:** podmiana `ConsumablesPanel._populate` i `ConsumablesPanel._dispose` w klasie WoT.

**Wersja 1.6:** dwa odczytowe listenery globalnego `g_eventBus`:

- `ComponentEvent.COMPONENT_REGISTERED` (`event.alias == BATTLE_VIEW_ALIASES.CONSUMABLES_PANEL`) → `_activate`.
- `ComponentEvent.COMPONENT_UNREGISTERED` (`event.componentPy is _panel`) → `_deactivate`.

To nie jest własny, nieudokumentowany event: klient WoT sam używa takiego wzorca, np. w `markers_gui_provider.py`. Klient rejestruje komponent po `componentPy.create()` i emituje zdarzenie przed `viewPy.destroy()`.

Źródła pomocnicze (społecznościowy zrzut kodu klienta WoT, nie oficjalnie stabilne publiczne API):

- https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/gui/Scaleform/framework/entities/BaseDAAPIComponent.py
- https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/gui/Scaleform/framework/entities/DisposableEntity.py
- https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/gui/Scaleform/daapi/view/battle/shared/component_marker/markers_gui_provider.py
- https://github.com/izeberg/wot-src/blob/EU/sources/res/scripts/client/gui/Scaleform/genConsts/BATTLE_VIEW_ALIASES.py

**Zaleta:** brak przepisywania implementacji metod WoT, brak kolizji z modami patchującymi te same metody, mniejsze ryzyko błędnej kolejności wywołań.

**Ryzyko:** przyszła wersja WoT może zmienić/wycofać te zdarzenia. Wtedy mod wyłączy się, a nie automatycznie przełączy na monkeypatching.

## 2. Adapter zgodności

`_panel_contract(panel)` sprawdza przed uruchomieniem:

- identyfikatory i zakresy panelu, 12 slotów;
- obecność `_getPanelSettings()` i standardowy layout (`0`);
- dostępność `as_isVisibleS()`;
- obecność oraz typ `_cds`, poprawny 12-bitowy `_mask`;
- słownik `_equipmentsGlowCallbacks`, zapewniający pierwszeństwo natywnych ostrzeżeń WoT.

`_slot_contract(panel, slot, compact)` sprawdza, czy gotowa apteczka znajduje się rzeczywiście w jednym ze slotów 3..5, czy slot jest w masce i czy kompaktowy identyfikator wyposażenia zgadza się z HUD-em. Jest powtarzany podczas bitwy, więc obejmuje zmianę panelu lub konfiguracji w locie.

`_graphics_contract()` sprawdza istnienie `GUI.Simple`, wymaganych enumów, `ResMgr.isFile`, obsługi callbacków i funkcji BigWorld przed dotknięciem natywnego renderera. Wszystkie zasoby DDS weryfikuje ponadto istniejący `_preflight_frames`.

**Zasada fail-closed:** nieznany układ → brak nakładki i konkretna przyczyna w logu. Nie ma próby zgadywania nieznanego układu interfejsu ani przestawiania slotów.

## 3. Zachowane bez zmian

- 21 bitmap 128x128, DDS ARGB8888: porównanie wszystkich 21 plików z paczką 1.5.0 wykazało zgodność bajt w bajt.
- `TEXTURE_TEMPLATE`, `FRAME_LEVELS=20`, `HALF_PULSE=2.0`, `PULSE_TICK=0.1`.
- Logika `GUI.Simple` i `hud.addChild` z wersji 1.5.0.
- Kontrola `playerVehicleID`, `perkEffects['equipment']`, `item.canActivate(avatar=player)` i priorytetu wbudowanych ostrzeżeń.
- Brak dźwięków, shaderów, DLL, podmiany `battle.swf` i dodatkowych folderów wymaganych do instalacji.

## 4. Walidacja

- 137/137 testów offline (82 regresyjne logiki, 35 nowych testów kompatybilności/eventów, 20 opakowania).
- Całe `.wotmod` jest ZIP_STORED, zawiera 23 wpisy i ma poprawne metadane.
- Bytecode loader jest ten sam co sprawdzony w 1.5.0 format CPython 2.7 (wbudowany w `.pyc` skrypt ASCII).
- Testy symulują niezgodne/nieobecne API, w tym odrzucenie nieznanego layoutu, maski, słownika glow, brak enumów i problemy rejestracji listenera.
- **Nie przeprowadzono testu w działającym kliencie WoT**. Stwierdzenie `137/137` dotyczy testów offline, nie gwarancji stabilności silnika.

## 5. Ograniczenia

- Wciąż korzystamy z niepublicznych `_cds`, `_mask`, `perkEffects`, `as_isVisibleS` i mostka Flash. Nie można zagwarantować działania po przebudowie HUD-u.
- Gdy przyszła wersja zmieni układ, poprawną reakcją jest brak pulsowania, nie błędna ramka nad innym wyposażeniem.
- W razie zmiany interpretera Pythona przez WoT obecny `.pyc` przestanie być zgodny i trzeba zbudować nowe wydanie.
- Nie istnieje bezpieczna, uniwersalna technika zapewniająca 100% kompatybilność z nieznanymi przyszłymi aktualizacjami gry.
