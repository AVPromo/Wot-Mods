# Konfiguracja wyglądu i przewijania — 0.2.7

## Plik i stosowanie zmian

Plik **`grz.sessionstats.json`** umieść w tym samym folderze co właściwa paczka
`grz.sessionstats_0.2.7.wotmod`, np.:

```text
mods/2.4.1.0/grz.sessionstats_0.2.7.wotmod
mods/2.4.1.0/grz.sessionstats.json
```

Nazwa JSON nie zawiera numeru wydania, więc można zachować własne ustawienia
przy wymianie paczki. Przy kopiowaniu kolejnej aktualizacji zachowaj swój JSON,
jeżeli chcesz nadal korzystać z wprowadzonych kolorów. Mod tylko go odczytuje;
nie nadpisuje pliku ani nie dopisuje brakujących pól.

Konfiguracja jest czytana przy starcie moda, przy otwieraniu panelu i po wybraniu
**„Odśwież”**. Po zapisaniu pliku można więc zamknąć i otworzyć panel albo użyć
przycisku odświeżania. Nie ma ciągłego sprawdzania pliku w każdej klatce.

Dołączony pełny JSON zawiera **obecny wygląd jako wartości domyślne**:
140 ustawień kolorów, 12 promieni zaokrąglenia, 3 ustawienia opacity oraz
mnożnik przewijania. Brak pliku, pusty obiekt `{}` i pominięte pola korzystają
z wartości wbudowanych w mod.

## Najczęściej przydatne pola

| Pole | Wartość domyślna | Znaczenie |
| --- | --- | --- |
| `colors.window_background` | `"#111309"` | Główne tło okna |
| `colors.window_border` | `"#646044"` | Obramowanie okna |
| `colors.table_header_background_start` | `"#292e1f"` | Początek gradientu nagłówków tabel |
| `colors.table_header_background_end` | `"#222719"` | Koniec gradientu nagłówków tabel |
| `colors.table_row_background` | `"#181d11"` | Tło pierwszego wiersza tabeli |
| `colors.table_row_following_background` | `"#1a1f13"` | Tło kolejnych wierszy tabeli |
| `colors.table_row_following_border_top` | `"#2e3522"` | Delikatna linia między wierszami |
| `colors.table_row_hover_background` | `"#252d1b"` | Tło wiersza po najechaniu |
| `colors.metric_value_text` | `"#ebe7d4"` | Liczby w tabeli skuteczności |
| `colors.positive_text` | `"#c0d889"` | Dodatni bilans |
| `colors.negative_text` | `"#e4ad84"` | Ujemny bilans |
| `colors.garage_bars_background` | `"#969a9d"` | Słupki ikony w garażu |
| `colors.garage_wn8_text` | `"#bdc0c2"` | Mały napis WN8 |
| `colors.garage_spinner_border` | `"rgba(207,190,140,0.25)"` | Półprzezroczysta część spinnera |
| `colors.garage_spinner_border_top_color` | `"#dfd3a4"` | Jasna część spinnera |
| `radii.window` | `4` | Zaokrąglenie okna |
| `radii.table_header` | `3` | Zaokrąglenie nagłówków tabel |
| `radii.table_row` | `2` | Zaokrąglenie wierszy tabel |
| `radii.group_card` | `5` | Zaokrąglenie kart czołgów/map/bitew |
| `radii.garage_spinner` | `5` | Zaokrąglenie spinnera |
| `opacity.window` | `1.0` | Widoczność całego panelu wraz z tekstem |
| `opacity.garage_button` | `1.0` | Widoczność całego przycisku w garażu |
| `opacity.disabled_controls` | `0.45` | Widoczność nieaktywnych kontrolek |
| `scroll.speed_multiplier` | `1.0` | Mnożnik obecnej szybkości rolki w grze |

Pozostałe klucze w pełnym JSON odpowiadają także tłu dokumentu, paskowi tytułu,
zakładkom okresu, przełącznikowi PD, nagłówkom i wartościom statystyk, separatorom,
kartom i wynikom bitew, komunikatom, przyciskom, oknu potwierdzenia resetu,
scrollbarowi, cieniom i stanom po najechaniu. Sufiks `text` oznacza tekst,
`background` tło, `border`/`border_top`/`border_left` linię, `shadow` cień,
`hover` stan po najechaniu, `active` zaznaczenie. Sufiksy `start`, `middle`
i `end` opisują kolejne kolory istniejącego gradientu.

## Formaty i zakresy

### Kolory i przezroczyste tła

Dozwolone zapisy kolorów:

- `"#abc"` — krótki zapis RGB;
- `"#aabbcc"` — pełny zapis RGB;
- `"#aabbcc80"` — RGB z końcowym kanałem alpha w zapisie szesnastkowym;
- `"rgb(170,187,204)"`;
- `"rgba(170,187,204,0.5)"` — alpha od `0` do `1`;
- `"transparent"`.

Kanały RGB są liczbami całkowitymi od `0` do `255`. Alpha `0` oznacza pełną
przezroczystość danego koloru, `1` pełne krycie. Kanał szesnastkowy `80`
oznacza około 50,2% krycia. Zapis ośmiocyfrowy jest zamieniany na `rgba(...)`,
aby nie uzależniać renderowania od obsługi takiego hex przez Gameface.

Aby zmienić **tylko przezroczystość tła**, użyj np.
`"colors": {"window_background": "rgba(17,19,9,0.8)"}`. Pozostałe tła,
gradienty i cienie są osobnymi kolorami i zachowują swoje wartości. Ustawienie
`opacity.window` wpływa na **cały panel, również tekst i kontrolki**.

Każdy składnik gradientu lub cienia można zmienić osobno. JSON nie przyjmuje
całych deklaracji CSS, nazwanych kolorów typu `red`, `url(...)`, `var(...)`,
`currentColor`, nazw selektorów ani dowolnych gradientów. Kierunki gradientów,
ich punkty, położenia cieni i układ pozostają częścią stylu moda.

### Zaokrąglenia

Każde pole `radii` przyjmuje liczbę od **0 do 24**. Jednostki podążają za skalą
interfejsu WoT: przy bazowej skali jedna jednostka odpowiada jednemu pikselowi.
Nie dopisuj `px` ani `rem` w JSON. `0` usuwa istniejące zaokrąglenie danej grupy.
W paskach zaokrąglonych tylko u góry albo u dołu ustawienie nadal dotyczy tych
samych narożników; nie zmienia struktury panelu.

### Opacity

Każde pole `opacity` przyjmuje liczbę od **0 do 1**. `1` oznacza pełną
widoczność, `0.8` — 80% widoczności, `0` — niewidoczność. Nie zapisuj procentów
ani liczb jako tekstu. Na przykład `0.8` jest prawidłowe, a `"80%"` nie.

### Szybkość rolki

`scroll.speed_multiplier` przyjmuje liczbę od **0.1 do 8**:

- `1.0` zachowuje obecną szybkość;
- `1.5` oznacza krok o połowę większy;
- `2.0` oznacza dwukrotnie większy krok;
- `0.5` zmniejsza krok o połowę.

Mnożnik dotyczy adaptera przewijania w grze, w tym wejścia w jednostkach strony.
Dotychczasowy kierunek przewijania i zatrzymywanie na końcach pozostają zachowane.
Podgląd otwierany jako zwykły plik HTML zachowuje natywną obsługę rolki przeglądarki.

## Krótki przykład własnych ustawień

Możesz pozostawić pełny plik z paczki albo zastąpić go częściowym plikiem.
Poniższy przykład zmienia tylko wymienione wartości; reszta zostaje domyślna:

```json
{
  "schema_version": 1,
  "colors": {
    "window_background": "rgba(17,19,9,0.9)",
    "table_row_background": "#202719",
    "table_row_following_background": "#242c1c",
    "table_row_following_border_top": "#465336"
  },
  "radii": {
    "window": 6,
    "group_card": 7
  },
  "opacity": {
    "window": 1.0
  },
  "scroll": {
    "speed_multiplier": 1.5
  }
}
```

To przykład zmian, **nie ustawienia domyślne dołączone do paczki**. Zapisz plik
w UTF-8; BOM jest obsługiwany. JSON wymaga cudzysłowów przy nazwach pól, kropki
w liczbach dziesiętnych i przecinków między polami. Nie obsługuje komentarzy ani
przecinka po ostatnim polu.

## Zachowanie przy błędach i log

| Przypadek | Zachowanie |
| --- | --- |
| Brak pliku lub brak pojedynczego pola | Wbudowane wartości domyślne |
| Niepoprawna składnia JSON, kodowanie, duplikat nazwy pola lub przekroczone 128 KiB | Cały domyślny wygląd |
| Główny obiekt o złym typie lub nieobsługiwane `schema_version` | Cały domyślny wygląd |
| Błędny kolor, typ albo zakres pojedynczego pola | Domyślna wartość tego pola; poprawne pozostałe ustawienia działają |
| Sekcja o złym typie, np. `"colors": []` | Domyślna wartość tej sekcji |
| Nieznana nazwa pola | Pole jest pomijane i zgłaszane w logu |

`true` i `false` nie są liczbami konfiguracyjnymi. Niestandardowe stałe JSON
`NaN` i `Infinity` odrzucają plik. Każda wartość liczbowa jest również sprawdzana
pod kątem skończoności i odpowiedniego zakresu.

Nowy błędny plik przy „Odśwież” przywraca odpowiednie wartości domyślne;
nie zachowuje po cichu poprzednich niestandardowych wartości.

Błędy mają w logu moda prefiks **`CONFIG`**, nazwę pola i powód odrzucenia.
Błąd składni zawiera numer linii i kolumny, jeżeli parser go udostępnia;
obsługiwany jest również tekstowy format błędu Pythona 2.7. Surowe wartości
z pliku oraz pełna treść JSON nie są wpisywane do logu. Pojedynczy odczyt
zapisuje najwyżej 64 diagnostyki pól oraz informację o pominiętej nadwyżce.

Standardowy log:

```text
%APPDATA%\grz_wot_session_stats\logs\session-stats.log
```

## Kontrakt implementacji

`appearance.py` ma wbudowane niezależne kopie wartości domyślnych i szablony
całych obecnych arkuszy. Z JSON podstawiane są wyłącznie sprawdzone skalary.
Kod nie używa zmiennych CSS i nie odczytuje plików stylu z obcej ścieżki.
Statyczne arkusze w paczce pozostają awaryjnym stylem bazowym.

Testy sprawdzają, że rozwinięcie domyślnych szablonów jest tekstowo równe
obecnym plikom CSS, z wyjątkiem dopisanych neutralnych deklaracji `opacity:1`
panelu i przycisku. Osobna kontrola wymaga, aby wszystkie rzeczywiste kolory,
promienie i deklaracje opacity były objęte tokenami oraz aby dołączony JSON
zawierał dokładnie te same wartości domyślne. Przyszła zmiana bazowego stylu
wymaga aktualizacji tego jawnego kontraktu.

Publiczne funkcje: `default_config()`, `load_config(path)`,
`validate_config(object)` i `build_presentation(config)`. Ostatnia zwraca
`panel_css`, `footer_css` oraz `scroll_speed` do przekazania istniejącym modelom UI.
