# Konfiguracja obok pakietu — lokalizacja i źródła 0.2.7

## Kontrakt

`config_path.find_config_path(package_name=None, resmgr=None, cwd=None)` zwraca
bezwzględną ścieżkę `grz.sessionstats.json` obok rozpoznanego fizycznego pakietu
albo `None`. Domyślna nazwa pakietu to `grz.sessionstats_<VERSION>.wotmod`.
Funkcja nie tworzy pliku, nie zmienia instalacji ani historii statystyk.
Brak samego JSON nie przeszkadza w ustaleniu ścieżki; jego odczyt, walidacja
i wartości domyślne należą do loadera konfiguracji.

## Wybór aktywnej instalacji

1. Spróbuj rozwiązać `../paths.xml` przez `ResMgr.resolveToAbsolutePath`.
   Wynik musi wskazywać absolutną ścieżkę istniejącego fizycznego `paths.xml`.
2. Jeśli plik został w ten sposób potwierdzony, jest autorytatywny. Jego błąd,
   nieobsługiwana struktura, brak naszej paczki lub wiele pasujących kopii
   powoduje użycie ustawień domyślnych. Nie przechodź wtedy do innej instalacji.
3. Jeśli resolver nie udostępnia fizycznego pliku, sprawdź tylko `appDirectory()`,
   jego rodzica, katalog roboczy i jego rodzica. Istniejące pliki `paths.xml`
   muszą łącznie prowadzić do jednej jednoznacznej ścieżki naszej paczki.
   Błąd któregokolwiek sprawdzanego XML również kończy szukanie ustawieniami
   domyślnymi, zamiast pomijania nieczytelnego kandydata.
4. Z XML wybierz deklaracje `Paths/Path` z `mask="*.wotmod"`. Ścieżki względne
   odnieś do katalogu samego `paths.xml`. Uszanuj `mode="recursive"`; brak trybu
   lub pusty tryb oznacza kontrolę tylko bezpośredniego katalogu.
5. Znajdź dokładną nazwę bieżącej paczki. JSON leży w tym samym katalogu co ona,
   także gdy użytkownik umieścił paczkę w podfolderze aktywnego korzenia.

Nie wybieramy najwyższego numeru katalogu `mods`, nie szukamy konfiguracji
w starszych wersjach i nie wyprowadzamy położenia archiwum z `__file__`.
Zmiana nazwy paczki bez zmiany nazwy oczekiwanej przez locator oznacza użycie
wartości domyślnych; dołączona paczka ma właściwą nazwę.

## Granice odczytu i błędy

- XML: najwyżej 256 KiB i 4096 elementów; najwyżej 32 deklaracje korzeni pakietów.
- Skanowanie: najwyżej 8192 wpisy łącznie i 8 poziomów podkatalogów.
  Osiągnięcie granicy powoduje rezygnację z wyboru, także gdy wcześniej znaleziono
  jedną paczkę. Nie można wtedy wykluczyć drugiej kopii w nieprzejrzanej części.
- Nie przechodzimy do dowiązań symbolicznych napotkanych jako korzeń skanowania,
  podkatalog lub pasujący plik pakietu. Nie jest to wykrywanie wszystkich rodzajów
  punktów ponownej analizy Windows; obowiązuje możliwości `os.path.islink`
  dostępne w osadzonym interpreterze.
- Wspierane kodowanie XML to UTF-8 z opcjonalnym BOM, również deklaracja ASCII.
  Deklaracje DTD i ENTITY są odrzucane przed uruchomieniem parsera.
- Parser `xml.etree.ElementTree` jest importowany dopiero podczas odczytu XML.
  Jego brak pozostaje lokalnym błędem konfiguracji i nie blokuje importu moda.
- Ścieżki Unicode działają pod Pythonem 2.7 i 3. Dla bajtowych ścieżek z natywnego
  API rozważane jest UTF-8 oraz kodowanie systemu plików; wybór wymaga istniejącego
  pliku. Dwie różne pasujące interpretacje oznaczają niejednoznaczność.
- Jedno nieudane wywołanie daje najwyżej jeden wpis `CONFIG_PATH code=...`
  w loggerze `grz.sessionstats`, bez surowego XML, ścieżek użytkownika,
  treści wyjątków lub tracebacku. Zwracana jest wartość `None`.

Względna ścieżka pakietów może wskazywać poza katalog zawierający XML, jeżeli
tak deklaruje rzeczywisty `paths.xml`. Locator respektuje jawne korzenie klienta;
nie dodaje własnego wyszukiwania po innych katalogach lub dyskach.

## Dowody źródłowe odczytane 21.10.2026

Wspólny commit w publicznym odwzorowaniu klienta `izeberg/wot-src`:
`5e721e36891c80d8d51a431164960c863641ee63`.
Są to dowody faktycznej implementacji, a nie gwarancja stabilnego SDK.

### Aktywny korzeń pakietów

[sources/paths.xml](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/paths.xml),
blob `60508b70e99ae41f14d145f4d833001cb60fd06c`, deklaruje oddzielne ścieżki
`res_mods/2.4.1.0` i `mods/2.4.1.0`. Druga ma maskę `*.wotmod`, tryb `recursive`
i korzeń zasobów `res`. Locator korzysta z tej deklaracji, nie z numeru kompilacji.

### Rozwiązywanie fizycznej ścieżki

[BWUtil.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/BWUtil.py),
blob `c23dc364997687941ddf4ee5e9fee537818e7d56`: `bwResRelativePatch` wywołuje
`ResMgr.resolveToAbsolutePath`, konwertuje wynik na Unicode i przekazuje go
do funkcji plikowej. `bwResRelativeIOOpen` wykorzystuje to dla `io.open`.

[helpers/__init__.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/helpers/__init__.py),
blob `a35e8a97f926c54f39c1cbb37c770684197f1b2b`: klient odczytuje swój plik wersji
przez ścieżkę zasobu `../version.xml`.
[sources/version.xml](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/version.xml),
blob `898de2d92c1f15464d17f416446677ea6c949169`, zawiera `v.2.4.1.0 #977`.
Numer `.version_name` repozytorium `2.4.1.5493` nie jest nazwą katalogu modów.

Zastosowanie `resolveToAbsolutePath('../paths.xml')` jest wnioskiem z tych
kontraktów i położenia pliku. Nie znaleziono tego dokładnego wywołania w kodzie
klienta, dlatego wynik jest sprawdzany na fizycznym systemie plików, a brak
rozwiązania ma ograniczony fallback opisany powyżej.

### Katalog aplikacji

[OfflineMode.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/helpers/OfflineMode.py),
blob `368aa61a53e9dfeaac8e300bed23fe88bff17680`, oraz
[VehicleTelemetry.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client_common/shared_utils/avatar_helpers/VehicleTelemetry.py),
blob `71ca2fbed601d75bef1c5d9b477ac3e1f063b917`, używają `ResMgr.appDirectory()`
bez argumentów do lokalnych plików. Nie dowodzą, że zawsze zwraca główny katalog
gry. Fallback sprawdza więc istniejący XML w tym katalogu i bezpośrednim rodzicu.

### Wirtualne ścieżki nie identyfikują archiwum

[gui/mods/__init__.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/mods/__init__.py),
blob `736f2c29ff76644d6cf705b9011389b6136e391d`, przegląda wirtualny folder
skryptów przez `ResMgr.openSection` i importuje moduły. Nie przekazuje do moda
fizycznego położenia pakietu.

[extension_utils.py](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/common/extension_utils.py),
blob `4a17a1fb0b5d7b97968f8356ea7f187ed7abb7d4`: `findFirstPathOccurrence`
zwraca ścieżkę zasobu lub ścieżkę z prefiksem aktywnego rozszerzenia. Nie jest
API zwracającym katalog fizycznego `.wotmod`, więc locator go nie wykorzystuje.
