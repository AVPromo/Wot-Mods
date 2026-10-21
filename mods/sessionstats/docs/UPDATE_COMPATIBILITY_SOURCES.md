# Odporność na aktualizacje WoT — audyt źródeł

Data odczytu: **20 października 2026 r.** Punktem odniesienia jest działająca u użytkownika wersja moda **0.2.4**. Audyt dotyczy ograniczania zależności od klienta i skutków ich zmiany; nie jest deklaracją zgodności z niewydanymi wersjami WoT.

## Wniosek

Można zwiększyć odporność na brak pojedynczej funkcji, usunięcie pomocnika grafiki, zmianę opcjonalnego kontrolera oraz błędy podczas otwierania lub zamykania okna. Najmniej utrzymania wymaga zachowanie oddzielnego rdzenia obliczeń i zapisu oraz kilku małych adapterów klienta. Działający panel nie wymaga przepisania na inny silnik ani zastępowania go kopią natywnego panelu.

Nie da się na podstawie obecnych źródeł zagwarantować działania po zmianie formatu wyników bitew, protokołu Wulf/Gameface albo środowiska wykonującego bajtkod. Takie zmiany mogą wymagać dostosowania odpowiedniego adaptera lub ponownej kompilacji. Wykrycie dostępności metody ogranicza awarie strukturalne, lecz samo nie dowodzi zachowania jej znaczenia.

## Źródła

Pliki klienta odczytano z publicznego odwzorowania `izeberg/wot-src`, commit **`5e721e36891c80d8d51a431164960c863641ee63`**, gałąź klienta wskazana w wcześniejszej dokumentacji projektu jako **2.4.1.5493**. Jest to materiał do weryfikacji faktycznych kontraktów, a nie oficjalny stabilny SDK Wargaming.

| Źródło | Potwierdzone zachowanie | Znaczenie dla moda |
| --- | --- | --- |
| [Loader gui/mods](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/mods/__init__.py) | Rozpoznaje moduły `mod_*.pyc` w wydaniu produkcyjnym i wywołuje `init`/`fini`. `_callModMethod` przechwytuje `AttributeError`, a import modułu w `_findValidMODs` — `ImportError`. | Własna kontrola błędów na wejściu i wyjściu jest uzasadniona. Nie należy zakładać, że wywołujący otoczy każdy błąd moda pełną izolacją. |
| [Event.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/Event.py) | Zwykły `Event` ponownie zgłasza wyjątek słuchacza, a `SafeEvent` ma odmienną obsługę. | Kod moda powinien sam izolować swoje granice wywołań; nie należy zakładać, że każde zdarzenie klienta jest `SafeEvent`. |
| [PlayerEvents.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/PlayerEvents.py) | Zawiera zdarzenia konta, wejścia do bitwy i `onBattleResultsReceived`, z których korzysta adapter. | Subskrypcje są mniejszą powierzchnią zmian niż podmienianie dużych metod klienta. Uszkodzona opcjonalna subskrypcja nie powinna blokować pozostałych. |
| [LobbyFooter](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/lobby/page/lobby_footer.py) | Stopka jest `ViewComponent`; rejestruje własne dzieci, w tym natywne statystyki sesji. | Mały własny komponent jest rozsądny, ale ścieżka klasy i jej cykl życia pozostają zależnościami klienta. Skrót do oddzielnego okna ogranicza skutki zmiany stopki. |
| [Oficjalny support: problemy związane z modyfikacjami](https://wargaming.net/support/en/products/wot/article/15252/) | Opisuje problemy wywoływane przez mody i uruchomienie czystego klienta w trybie bez modów, bez resetowania ustawień. | Źródło nie daje obietnicy niezmienności wykorzystanych wewnętrznych interfejsów. Kontrola w przeglądarce nie zastępuje uruchomienia moda w nowym kliencie. |

Identyfikatory odczytanych plików: loader `736f2c29ff76644d6cf705b9011389b6136e391d`; `Event.py` `085542140af9e7821f9bd0058242f72e58ab8c80`; `PlayerEvents.py` `9f856791d624bdb147004c5ca0591df43b7049a1`; `LobbyFooter` `c3673d182cfda5711151fdc5b8543051ef3be570`.

## Priorytety poprawy

1. **Odbiór i zapis wyników niezależny od opcjonalnego UI.** Brak przycisku, importu okna, pomocnika miniatur lub sygnału klawiatury nie powinien sam zatrzymywać usług statystyk, jeśli ich właściwe źródło nadal działa.
2. **Kontrola każdej granicy klienta osobno.** Podłączanie, wywoływanie i odłączanie słuchaczy oraz operacje okna powinny mieć odrębne ścieżki błędów. Błąd jednego elementu nie powinien przerywać sprzątania pozostałych ani wypływać do natywnego dispatchera.
3. **Zasoby przez nazwy i identyfikatory klienta.** Obecne używanie własnego rejestru zasobów i rozwiązywanie miniatur w adapterze jest korzystniejsze niż utrwalanie numerycznych identyfikatorów zasobów. Awaria jednej rodziny grafik nie powinna wyłączać pozostałych.
4. **Zachowanie znaczenia danych.** Nieznana lub niepełna dana pozostaje nieznana. Mechanizm zgodności nie może zastępować brakujących kosztów zerem, dowolnie interpretować nowej krotki lub wpisywać domyślnego wyniku bitwy.
5. **Sprawdzanie dostępnych możliwości zamiast listy numerów wersji.** Zmieniony numer klienta nie oznacza automatycznie niezgodności wszystkich elementów. Z drugiej strony sama obecność starej nazwy metody nie dowodzi, że jej argumenty i wynik mają niezmienione znaczenie.

## Kolejność walut: pozostaje jawny kontrakt wyniku

Ponownie sprawdzono [gui/shared/money.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/money.py), blob `751c6da56b3560f3f0198c860efdd6bc4d95cafb`. `Currency.ALL` wymienia waluty modelu `Money`, lecz **nie deklaruje pozycji w polach wyniku bitwy `autoLoadCost`, `autoEquipCost` ani `autoEquipBoostersCost`**. Nie ma podstaw, aby traktować to wyliczenie jako metadane tych trzech pól.

Aktualny [natywny czytnik ekonomii wyników](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/battle_results/reusable/economics_records.py), blob `da97053f85b1faa329971e775c9daf6154469c7e`, wprost używa indeksów:

| Pole | Indeks 0 | Indeks 1 | Indeks 2 |
| --- | --- | --- | --- |
| `autoLoadCost` | kredyty | złoto | nie jest odczytywany |
| `autoEquipCost` | kredyty | złoto | obligacje (`crystal`) |

Odczyt znajduje się w liniach 61–71 i 95–98 przypiętego pliku. [Deklaracja wyniku po stronie wspólnego kodu](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/battle_results/battle_results_common.py), blob `a8476aed85f0cfce21e6a3c9fb267e6cc533ae21`, definiuje `autoLoadCost` jako krotkę z domyślnym `(0, 0)`, a `autoEquipCost` i `autoEquipBoostersCost` jako krotki z `(0, 0, 0)`; nie dostarcza nazwanych pozycji dla zewnętrznego adaptera.

Dlatego zachowujemy znany kontrakt natywnego czytnika. Powiązanie go z `Currency.ALL` stworzyłoby dodatkowe założenie zamiast faktycznie usuwać zależność. Zmiana semantyki pól finansowych lub ich serializacji pozostaje realną granicą zgodności, wymagającą sprawdzenia nowego kodu klienta i rozliczenia konkretnego wyniku. Obecne nazwy pól, formuły i kolejność walut nie są automatycznie zgadywane.

## Ładowanie po zmianie numeru klienta

Zestaw instalacyjny umieszcza pliki `.wotmod` w `mods/<wersja klienta>/`; zapis statystyk leży osobno w AppData. Zmiana aktywnego katalogu wersji i zgodność kodu to dwie różne kwestie. Przeniesienie paczki może rozwiązać wyłącznie pierwszą z nich.

Oficjalna [instrukcja modyfikacji z 17 grudnia 2018 r.](https://worldoftanks.eu/pl/news/general-news/dress-up-santa-vs-krampus/) pokazuje instalację w wersjonowanym podkatalogu `Mods`. Oficjalny [opis techniczny 9.15.1](https://worldoftanks.eu/en/news/general-news/update-9151-technical-aspect/) dokumentuje historyczny przykład zmiany interfejsu, po której przenoszenie starych modów mogło powodować niestabilność. To **dowody historyczne**, nie instrukcja określająca numer bieżącego klienta w październiku 2026 r.

Nie wprowadzamy obchodzenia mechanizmu ładowania przez modyfikowanie podstawowych ścieżek gry ani automatycznego aktywowania paczki w każdym przyszłym kliencie. Pozostaje instalacja dla faktycznie używanej wersji i krótka weryfikacja po większej aktualizacji.

## OpenWG i granice sprawdzenia

Dołączony OpenWG Gameface **1.2.2** zachowuje przypiętą wersję i źródła zapisane w `third_party/openwg/`. Wykorzystuje się go do przycisku garażu; oddzielne okno nie powinno wymagać tego modułu. Utrzymywana wspólna biblioteka zmniejsza ilość własnego kodu integracyjnego, ale nie stanowi gwarancji zgodności z przyszłymi zmianami WoT. Audyt nie wymaga zmiany tej działającej zależności.

Testy nieobecnych metod, odrzuconych subskrypcji i błędów opcjonalnych elementów mogą sprawdzić zaprojektowane ścieżki awaryjne. Nie są emulatorem wszystkich przyszłych aktualizacji. Nie uruchamiano tutaj nowej wersji klienta WoT, nie wykonywano bitew ani nie weryfikowano niewydanego formatu wyników.
