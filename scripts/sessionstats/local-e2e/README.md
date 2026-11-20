# Session Stats — lokalne testy E2E

Uruchamiaj testy po zmianie interfejsu albo przed zbudowaniem paczki. Narzędzie ładuje rzeczywisty HTML, CSS i JavaScript moda. Bieżący kod Pythona liczy statystyki, filtruje zakresy i odpowiada na polecenia panelu. Symulowane są usługi okna WoT, a historie, obrazy i identyfikatory pochodzą z deterministycznych danych testowych. Przebieg działa bez klienta, logowania i dostępu do danych konta. Zdarzenia trafiają do widoku przez protokół sterowania rendererem.

## Instalacja na Windows x64

1. Zainstaluj Node.js 22 lub nowszy. Możesz wybrać linię 24 LTS i instalator x64. [Pobierz Node.js](https://nodejs.org/en/download)
2. Zainstaluj Python 3 x64 i dodaj go do `PATH`. Przebieg sprawdzono na Pythonie 3.12.14. [Pobierz Pythona dla Windows](https://www.python.org/downloads/windows/)
3. W PowerShellu przejdź do katalogu zawierającego ten plik i wykonaj poniższe polecenia. Pakiet `tzdata` dostarcza strefę `Europe/Warsaw` także na Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SESSIONSTATS_PYTHON = (Resolve-Path .\.venv\Scripts\python.exe).Path
npm.cmd install
```

Do natywnych zrzutów potrzebny jest samodzielny **Gameface Player**. W kliencie EU ustaliliśmy Cohtml **2.2.8.1**. Jeśli uzyskujesz SDK od Coherent Labs, poproś o Player **2.2.8.1** lub najbliższą wersję **2.2.8.x** dostępną do ewaluacji. Dostęp do tego wydania i uruchomienie z wyłączonym oknem pozostają do sprawdzenia na dostarczonym `Player.exe`. [Kontakt i wersja próbna](https://coherent-labs.com/frequently-asked-questions/) · [Dokumentacja Playera](https://docs.coherent-labs.com/cpp-gameface/quick_start/player/player/)

Do prób w Chromium wystarczy albo zainstalować przeglądarkę Playwright, albo wskazać własnego Edge przez `--chrome`. [Instalacja przeglądarek Playwright](https://playwright.dev/docs/browsers)

```powershell
npx.cmd playwright install chromium
```

## Uruchamianie na żądanie

Sprawdź rozmiar i zakres konfiguracji bez uruchamiania renderera.

```powershell
node run.cjs --suite full --plan
```

Sprawdź uruchomienie Playera w krótkiej próbie, a potem wykonaj pełny przebieg. Podaj ścieżkę do posiadanego `Player.exe` lub ustaw `GAMEFACE_PATH`.

```powershell
node run.cjs --suite smoke --player 'C:/Narzędzia/Gameface/Player/Player.exe'
node run.cjs --suite full --player 'C:/Narzędzia/Gameface/Player/Player.exe'
```

Wersja przeglądarkowa jest dostępna jawnie przez `--engine chromium`. Użyj jej podczas pracy nad logiką i układem z danymi testowymi.

```powershell
node run.cjs --engine chromium --suite smoke
node run.cjs --engine chromium --suite full --chrome 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
```

`full` testuje wszystkie warianty sortowania dla pełnej historii i zakresu od niedzieli. Dla pozostałych zakresów sprawdza warianty chronologii. `--all-ranges` rozszerza pełne sortowanie na wszystkie przygotowane zakresy. Podstawowe widoki mają wysokość 730 lub 900 px i maksymalnie trzy ruchy kółkiem. Osobne scenariusze obejmują menu, kalendarz, rozwinięte szczegóły i powrót z wybranej bitwy.

```powershell
node run.cjs --suite full --all-ranges --player 'C:/Narzędzia/Gameface/Player/Player.exe'
node run.cjs --engine chromium --suite full --widths 365,780 --heights 730,900 --ranges history,since-sunday --languages en,pl --limit 40
node run.cjs --engine chromium --suite smoke --source '../WotMods-pr17-next/mods/sessionstats' --python 'C:/Python312/python.exe'
```

`--source` wskazuje katalog `mods/sessionstats` z wybranego checkoutu. W repozytorium przebieg znajduje go automatycznie. W osobnym katalogu szuka też sąsiedniego `WotMods-pr17-next`. `--python` zastępuje ścieżkę z `SESSIONSTATS_PYTHON` lub polecenie `python`. W nowej sesji PowerShell ustaw `$env:SESSIONSTATS_PYTHON` ponownie, jeśli korzystasz z `.venv`. Pełną listę opcji wyświetla `node run.cjs --help`.

## Raporty i porównania

Polecenie wypisuje ścieżkę do nowego katalogu w `runs/`. Otwórz `index.html`, żeby przejrzeć przypadki i zrzuty. `run.json` zapisuje wersję i podsumowanie. `results.ndjson` zawiera wyniki pojedynczych przypadków i pomiary. `--out` pozwala nadać nowemu katalogowi własną nazwę.

Po obejrzeniu pierwszego przebiegu możesz użyć go jako wzorca. Następny przebieg uruchom z tym samym rendererem, wersją, wymiarami i zakresem. `--threshold 0.002` dopuszcza domyślnie do 0,2% różniących się pikseli. Porównanie pomija wnętrze pola z bieżącym czasem w nagłówku. Dla różnic ponad próg raport zapisuje zrzut, wzorzec i obraz różnic.

```powershell
node run.cjs --engine chromium --suite smoke --out 'runs/wzorzec'
node run.cjs --engine chromium --suite smoke --baseline 'runs/wzorzec' --out 'runs/porownanie'
```

Test w Gameface Playerze sprawdza rysowanie panelu i obsługę poleceń w symulowanym oknie. Dokładny czas i zachowanie podczas przeciągania okna wewnątrz WoT zależą też od integracji gry.

## Budowa paczki moda

Do kompilacji wersji instalacyjnej istniejący `tools/build.py` potrzebuje dodatkowo **CPython 2.7.18**. Uruchom polecenie z tego samego katalogu i wskaż właściwą ścieżkę do interpretera. Wynik pojawi się w `dist/` katalogu moda. [Pobierz CPython 2.7.18](https://www.python.org/downloads/release/python-2718/)

```powershell
python ../WotMods-pr17-next/mods/sessionstats/tools/build.py --python27 'C:/Python27/python.exe' --client-version 2.4.1.1
```
