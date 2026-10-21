# Miniatury 0.2.2: identyfikatory i zasoby klienta

Sprawdzono 20 października 2026 r. Implementacja: `visuals.py`, wywoływana
wyłącznie podczas budowania snapshotu dla UI. Nie zmienia schematu zapisu ani
obliczeń. Czyta istniejące identyfikatory pojazdu i geometrii mapy, także ze starych
rekordów. Nazwy wyświetlane służą tylko opisowi grafiki.

## Wersje i potwierdzone API

Publiczna kopia kodu klienta: `izeberg/wot-src`, commit
`5e721e36891c80d8d51a431164960c863641ee63`; odczytane `.version_name`:
`2.4.1.5493`. Nie jest to deklaracja stabilnego API dla modów.

| Element | Potwierdzone zachowanie i źródło |
| --- | --- |
| Zapisane numeryczne `typeCompDescr` | [getVehicleType](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/items/vehicles.py#L3165-L3171) rozpoznaje całkowity deskryptor typu i odczytuje pojazd z cache. [VehicleType](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/items/vehicles.py#L1971-L1974) zachowuje `name` i `compactDescr`. Resolver konwertuje zapis dziesiętny na liczbę i wymaga zgodności zwróconego deskryptora, aby błędne bity ID nie wskazały innego czołgu. |
| Ikona pojazdu | [getIconPath](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/gui_items/Vehicle.py#L2244-L2249) używa `R.images.gui.maps.icons.vehicle.dyn(...)`, `exists()` i `backport.image`. [getIconResourceName](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/gui_items/Vehicle.py#L2280-L2281) dostarcza klucz zasobu z technicznej nazwy pojazdu. Wariant `vehicle.small` jest tylko alternatywną ikoną tego samego czołgu; nie używamy `noImage`. |
| Miniatura mapy | [getArenaImage](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/utils/functions.py#L185-L192) wybiera `R.images.gui.maps.icons.map`, opcjonalne `dyn(subdir)`, a następnie `num(geometryName)`. [Natywna lista treningów](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/Scaleform/daapi/view/lobby/trainings/trainings_list_base.py) używa wariantu `small`. Resolver robi to samo; domyślna ikona tej samej geometrii jest alternatywą przy braku miniatury. |
| Rejestr i ścieżka | [R](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/gen/resources/__init__.py) pochodzi z menedżera zasobów `GuiApplication`. [backport.image](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/impl/backport/backport_r.py#L52-L53) deleguje do `wulf.getImagePath`; [getAbsoluteUrl](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/utils/functions.py#L232-L233) zamienia względny prefiks `../` na `img://gui/`. |
| Sprawdzenie lokalnego pliku | [Natywny ekran wczytywania](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/game_loading/state_machine/states/slide.py#L36-L37) używa `ResMgr.isFile`. Resolver sprawdza ścieżkę zwróconą przez rejestr i, jeśli logiczny PNG nie istnieje, plik DDS o tej samej nazwie. Emituje URL tylko po pozytywnym odczycie istnienia pliku. |

## Rzeczywiste grafiki i loader

Katalog zasobów: `Kurzdor/wot.assets`, commit
`3605bd36c53d10c16be5d93f5414aa5fd129e84e`; odczytane
[.metadata_version](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/.metadata_version):
`2.4.1.0 #977`.

- [map/small/01_karelia.png](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/map/small/01_karelia.png): nagłówek PNG potwierdza 100×60; domyślne [map/01_karelia.png](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/map/01_karelia.png) ma 300×300. W pierwszej kolejności wybieramy mały wariant.
- Istnieją dokładne ścieżki [vehicle/uk-GB31_Conqueror_Gun.png](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/vehicle/uk-GB31_Conqueror_Gun.png) oraz [vehicle/small/uk-GB31_Conqueror_Gun.png](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/maps/icons/vehicle/small/uk-GB31_Conqueror_Gun.png). Nazw ścieżek nie tworzymy ręcznie; pobieramy wynik `R` i backport.
- [Natywny Gameface maps_training_result/bundle.js](https://github.com/Kurzdor/wot.assets/blob/3605bd36c53d10c16be5d93f5414aa5fd129e84e/gui/gameface/_dist/production/mono/maps_training/maps_training_result/bundle.js) ustawia `backgroundImage` z `img://gui/maps/icons/map/screen/…dds`. Potwierdza to natywny schemat i obsługę DDS. Nie zastępujemy go loaderem `coui://`.

Grafiki sprawdzono jako materiał referencyjny. Żaden obraz klienta nie został
dołączony do paczki moda. Kod gry nie wykonuje żądań sieciowych po obrazy.

## Kontrakt i odporność

`row.visual` zawiera `kind`, `src` i `alt`. Dozwolone rodziny to wyłącznie
`img://gui/maps/icons/vehicle/` i `img://gui/maps/icons/map/`; brak lub błąd
zasobu oznacza brak pola `visual`, z zachowaniem nazwy i statystyk. Dla bitwy
preferowany jest zapisany pojazd, a następnie jej własna mapa. Nie dopasowujemy
grafiki według nazwy i nie korzystamy z grafiki innego rekordu. Błędy jednego
obrazu nie przerywają przetwarzania sąsiednich wierszy. Nieudane odczyty mogą
zostać ponowione w kolejnym snapshotcie po gotowości zasobów.

## Weryfikacja

`tests/test_visuals.py`: 21 testów na Pythonie 3 i Pythonie 2.7.18. Obejmują
numeryczne deskryptory, nieprawidłowe aliasowanie ID, wariant small mapy,
brak węzła lub pliku, PNG/DDS, odrzucone URL, późniejszą dostępność zasobów,
starsze rekordy oraz snapshot Runtime bez zmiany historii i statystyk.

To testy kodu z zastępczymi obiektami zasobów zgodnymi z odczytanym API.
Nie uruchamiają natywnego loadera C++ ani aktualnego klienta WoT. Wyświetlenie
każdej miniatury i faktyczne mapowanie zasobów w instalacji gracza wymagają
jeszcze sprawdzenia wersji 0.2.2 w grze.
