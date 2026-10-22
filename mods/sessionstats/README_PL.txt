STATYSTYKI SESJI — MOD DO WORLD OF TANKS PC
Wersja 0.2.7 • 21.10.2026 • cel: Wargaming EU 2.4.1.0

STATUS WYDANIA
To instalacyjny mod .wotmod z kodem skompilowanym do Pythona 2.7.18, własnym oknem
Gameface, adapterem wyników oraz trwałym zapisem obu sesji. Wydanie 0.2.7 dodaje
plik grz.sessionstats.json obok .wotmod: kolory, zaokrąglenia, przezroczystość
i szybkość przewijania. Dołączone wartości domyślne zachowują obecny wygląd
panelu i ikony oraz tempo rolki. Każde pole jest sprawdzane przy odczycie,
a błędy trafiają do własnego logu moda. Działają nadal healthcheck wyników,
ostrzeżenia WoT, spinner oczekiwania i zabezpieczenia integracji z 0.2.5/0.2.6.
Logika, paczka i scenariusze awarii API są sprawdzane automatycznie.
Wydania 0.2.7 nie uruchamiano tutaj w działającym WoT; testy symulowanych
interfejsów nie gwarantują zgodności z przyszłym klientem.
Nie jest to oficjalny produkt Wargaming.

AKTUALIZACJA Z 0.2.6 LUB WCZEŚNIEJSZEJ WERSJI
Przy zamkniętej grze usuń poprzedni plik grz.sessionstats_0.2.6.wotmod
(lub starszą wersję tego samego moda) z aktywnego katalogu mods
i wstaw zamiast niego grz.sessionstats_0.2.7.wotmod z tej paczki. Obok niego
umieść dołączony grz.sessionstats.json. W aktywnym katalogu mods powinna
pozostać jedna wersja grz.sessionstats.
Dołączony OpenWG 1.2.2 jest taki sam jak poprzednio — pozostaw jedną kopię.
Format historii nie zmienia się. Aktualizacja nie wymaga resetowania danych.

Nazwa pliku wyglądu nie zawiera numeru wydania. Przy kolejnych aktualizacjach
zachowaj swój grz.sessionstats.json zamiast nadpisywać go domyślnym plikiem
z nowej paczki. Mod tylko go czyta, nie nadpisuje go ani nie dopisuje pól.
Po zmianie katalogu wersji gry przenieś własny JSON razem z paczką moda.

SZYBKA INSTALACJA
1. Zamknij World of Tanks.
2. Rozpakuj ZIP w dowolnym miejscu.
3. Z zestawu skopiuj katalog mods do głównego katalogu World of Tanks, tego
   z plikiem WorldOfTanks.exe. Dla wersji 2.4.1.0 powinny powstać:
   mods/2.4.1.0/grz.sessionstats_0.2.7.wotmod
   mods/2.4.1.0/grz.sessionstats.json
   mods/2.4.1.0/net.openwg/net.openwg.gameface_1.2.2.wotmod
   Jeżeli masz już własny grz.sessionstats.json, zachowaj go przy kopiowaniu.
4. Jeżeli masz już OpenWG Gameface 1.2.2 lub nowszy z paczki modów, zachowaj jedną
   kopię tej biblioteki. Wtedy wystarczy skopiować paczkę grz.sessionstats
   oraz dołączyć JSON, jeżeli nie masz jeszcze własnego pliku.
   Przy starszym OpenWG zastąp tylko jego plik nowszą dołączoną wersją.
5. Uruchom grę i wejdź do garażu. Użyj ikony trzech słupków z małym WN8
   w prawym górnym rogu w stopce garażu lub
   naciśnij Ctrl+F10. Skrót otwiera/zamyka okno; Esc i krzyżyk również je zamykają.
   Okno można przeciągać lewym przyciskiem myszy za pasek tytułu.

Nie instaluj niczego do res_mods. Folder source, PODGLAD.html, README i pliki
licencji nie muszą znajdować się w katalogu gry. Nie musisz instalować Pythona.

Jeżeli nazwa aktywnego katalogu mods jest inna niż 2.4.1.0, pliki .wotmod trafiają
do katalogu wersji Twojego klienta, a grz.sessionstats.json bezpośrednio obok
grz.sessionstats_0.2.7.wotmod. Samo przeniesienie plików nie potwierdza ich
zgodności z nową wersją gry. Ten adapter oparto na interfejsach gałęzi 2.4.1.

JAK DZIAŁA PANEL
• Na górze: liczba zakończonych bitew, win rate i pełna liczba WN8.
• Dwie zakładki okresu: „Od uruchomienia” oraz „Od resetu”.
  Both belong to the active account. The optional installation tab has its
  own persistent manual reset and is hidden by default.
• Domyślnie „Bazowe PD”. „Otrzymane PD” przełącza wszystkie widoczne statystyki
  doświadczenia na wartości z premiami przyznanymi przez grę.
• Podsumowanie i szczegóły są widoczne od razu. Poniżej są Czołgi / Mapy / Bitwy.
  Czołgi są wybrane przy otwarciu. Cały panel przewijasz w dół; nie ma akordeonów.
  Rolka ma standardowy kierunek: w dół przesuwa do dalszych wyników,
  w górę wraca do wcześniejszych. Przy domyślnym mnożniku 1.0 krok zwykłej rolki
  w kliencie odpowiada ćwierci widocznej wysokości listy, również przy małych
  wartościach wejściowych. Szybkość można zmienić w JSON bez zmiany kierunku.
  Zestawienia mają większy tekst, łagodne krawędzie i dyskretne podziały wierszy.
• Przy nazwach pojazdów i map są ich miniatury z lokalnych zasobów gry.
  Nie trzeba pobierać dodatkowej paczki grafik. Jeśli klient nie ma danego
  zasobu, pozostaje poprawna nazwa i wynik, bez podstawiania innej ilustracji.
• Dla całego okresu i każdego czołgu oraz mapy: min/średnia/max PD
  i min/średnia/max WN8 pojedynczych bitew.
• W „Bitwy”: pojedynczy wynik PD i WN8 oraz zwycięstwo, porażka albo remis.
  Nie ma powtarzania jednego wyniku w trzech kolumnach ani win rate jednej bitwy.
• W każdym zestawieniu: wolne PD, przychód/koszty/netto kredytów i obligacji.
  Złoto pojawia się, jeśli wynik potwierdza związany z bitwą przepływ.
• Główne WN8 jest obliczane ze zsumowanych wyników i oczekiwanych wartości
  poszczególnych pojazdów. Średnia WN8 bitew jest osobną miarą w szczegółach.
• Zapis WN8: 1574, nie 1,6k. Wartość 805 pozostaje 805, a 10420 pozostaje 10420.
• Puste wartości są oznaczone kreską. Niepełne dane mają licznik pokrycia,
  np. 15/16. Częściowa suma finansowa obejmuje wyłącznie potwierdzone kwoty.
• Już po wejściu do bitwy zapisujemy dostępny czas, mapę oraz nazwę, poziom
  i klasę własnego czołgu. Wpis pozostaje na liście po restarcie także bez
  wyniku: znane nazwy są widoczne, brakujące statystyki mają kreski.
  Później załadowane informacje uzupełniają ten sam wpis. Starsze wpisy
  mogą nie mieć nazw, których poprzednia wersja nie zapisała.
• W tym wydaniu liczone są standardowe bitwy losowe. Replaye i tryby specjalne
  nie są włączane do WN8 tego zakresu.

WYGLĄD I PRZEWIJANIE — grz.sessionstats.json
Plik leży obok .wotmod w aktywnym katalogu mods, np.:
mods/2.4.1.0/grz.sessionstats.json
Dołączony pełny plik zawiera 140 ustawień kolorów, 12 promieni zaokrąglenia,
3 ustawienia opacity i mnożnik przewijania. Wartości domyślne zachowują obecny
układ, odstępy, wygląd tabel, ikony, spinnera i szybkość rolki.

Sekcje pliku:
• sessions.instance_tab: true displays the durable installation tab;
  false (default) keeps it hidden. Only JSON booleans are accepted.
  The option controls visibility; hiding it does not interrupt collection.
• colors: kolory tekstu, tła, linii, cieni, gradientów i stanów kontrolek.
  Obsługiwane są #RGB, #RRGGBB, #RRGGBBAA, rgb(...), rgba(...) i transparent.
  Kanały RGB mają zakres 0–255, alpha w rgba ma zakres 0–1.
• radii: promienie od 0 do 24, bez jednostek. Podążają za skalą UI gry;
  przy skali bazowej jedna jednostka odpowiada jednemu pikselowi.
• opacity: window, garage_button i disabled_controls, każda wartość od 0 do 1.
  1 oznacza pełną widoczność. opacity.window wpływa także na tekst i kontrolki.
  Aby zmienić tylko tło okna, użyj koloru rgba w colors.window_background.
• scroll.speed_multiplier: liczba od 0.1 do 8; domyślnie 1.0.
  1.5 zwiększa krok rolki o połowę, 2.0 podwaja go, 0.5 zmniejsza o połowę.
  Dotyczy przewijania w grze; podgląd HTML używa natywnej rolki przeglądarki.

Możesz edytować pełny plik lub zostawić tylko zmieniane pola. Przykład własnych
ustawień — pozostałe wartości będą domyślne:
{
  "schema_version": 1,
  "colors": {
    "window_background": "rgba(17,19,9,0.9)",
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
Zapisz plik w UTF-8; BOM jest obsługiwany. JSON wymaga cudzysłowów i kropki
w liczbach dziesiętnych. Nie dodawaj komentarzy ani przecinka po ostatnim polu.
Pełne opisy pól i przykłady: source/docs/APPEARANCE_CONFIG.md.

Konfiguracja jest czytana przy starcie moda, przy otwarciu panelu i po kliknięciu
„Odśwież”. Po zapisaniu JSON wystarczy odświeżyć panel albo otworzyć go ponownie.
Mod nie sprawdza pliku w każdej klatce ani przy każdym tyknięciu swojego zegara.

Brak pliku daje pełne ustawienia domyślne. Błędna składnia JSON, kodowanie,
powtórzona nazwa pola, NaN/Infinity, plik większy niż 128 KiB, zły typ głównego
obiektu lub nieobsługiwana schema_version również przywracają cały wygląd.
Błędne pole przywraca tylko swoją wartość domyślną; reszta poprawnych zmian działa.
Sekcja o złym typie wraca do wartości domyślnych tej sekcji. Nieznane pola są
pomijane i zgłaszane w logu. Pominięte pola oraz pusty obiekt {} są prawidłowe
i korzystają z wartości domyślnych. Wartości logiczne nie zastępują liczb.

Błędy odczytu i walidacji mają prefiks CONFIG w session-stats.log. Błąd składni
zawiera linię i kolumnę, jeżeli parser je podaje; błędne pole ma nazwę i powód.
Surowy JSON i wartości użytkownika nie trafiają do logu. Nieustalona jednoznacznie
lokalizacja paczki daje CONFIG_PATH i ustawienia domyślne. Mod nie wybiera
najwyższego numeru katalogu mods ani JSON obok starej kopii z innej wersji gry.
Zmiana nazwy .wotmod lub kilka jego aktywnych kopii może uniemożliwić ustalenie
pliku; zachowaj nazwę z paczki i jedną kopię moda. Jeżeli sam moduł konfiguracji
jest niedostępny, pozostają statyczne style i domyślna rolka z paczki.

DWA NIEZALEŻNE OKRESY
Oba okresy i ręczny reset są osobne dla każdego konta oraz regionu. Po zmianie
konta panel pokazuje jego własną historię. Po powrocie poprzedni zakres wraca.
Wyzerowanie konta B nie zeruje konta A. Historia nie jest łączona między kontami.
„Od uruchomienia” zaczyna nowy okres w nowym procesie gry. Powrót z bitwy do
garażu i ponowne połączenie z serwerem w tym samym procesie nie zerują go.
„Od resetu” trwa przez kolejne uruchomienia aż do ręcznego wyzerowania.
Przycisk „Wyzeruj zakres” jest dostępny w „Od resetu” i prosi o potwierdzenie.
Nie zeruje okresu „Od uruchomienia”; północ również niczego nie resetuje.

OPTIONAL INSTALLATION SESSION
To display the third tab, add this section to grz.sessionstats.json:
{"sessions": {"instance_tab": true}}
Keep other existing sections. Refresh or reopen the panel after saving.
The tab is hidden by default; the existing account scopes remain separate.

Installation history combines accounts observed in this installation and
survives game restarts, along with its own manual reset boundary. Only its
explicit reset starts a new period. Neither reset changes the other histories.
Late results retain their original installation period after restarting.
The shared ledger uses atomic, checksummed local storage and a hashed game-root
identity independent of the client version directory. Separate installations
remain separate. Hiding the tab neither clears nor stops the saved period.
The footer spinner still follows only the active account.
No account-history migration or reset is required. Older account archives
without installation provenance are not automatically imported.
Details: source/docs/ACCOUNT_SESSIONS.md.

Przynależność bitwy do obu okresów jest utrwalana przy wejściu do bitwy.
Wynik otrzymany później uzupełnia właściwy okres. Powtórzony wynik aktualizuje
rekord, zamiast dopisywać drugą bitwę. Późniejszy bonus PD nie zwiększa licznika.
Gdy brakuje wyniku, mod próbuje odczytać go z dostępnej pamięci wyników klienta.
Klient może nie udostępnić starego wyniku po restarcie; mod nie dopisze wtedy
domniemanej porażki. Nie importuje historii z Tomonika ani bitew sprzed instalacji.

Odczyt korzysta także z natywnego zapytania WoT do serwera, gdy brak lokalnego
wyniku. Gra może być wyłączona w chwili zakończenia bitwy: zapisany początek
pozostaje w kolejce i jest rozliczany po następnym zalogowaniu, jeśli serwer
udostępni wynik. Mod dodatkowo przechwytuje poprawne wyniki odczytywane przez
sam interfejs klienta, zanim klient potwierdzi ich odbiór. Błędy wspólnego cache
i niegotowe konto mają osobne ponowienia, a stare braki nie blokują nowych bitew.

Niepełny okres pokazuje np. „Bitwy z wynikiem: 20 / 21”. Brakująca bitwa jest
widoczna na liście jako nieznany wynik, a pokrycie WN8, PD i finansów obejmuje
wszystkie zarejestrowane bitwy. Procenty, średnie i sumy dotyczą odebranych danych.
Wynik odzyskany później uzupełnia pierwotną bitwę i okres, bez duplikowania.
Gdy serwer nie udostępnia już danych, nie obiecujemy ich odtworzenia; luka
pozostaje jawna. Szczegóły: source/docs/OFFLINE_RESULT_RECOVERY.md.

Reset rozpoczyna nowy widoczny okres i zachowuje stary dziennik na dysku. Wynik
bitwy rozpoczętej przed resetem nie trafia do świeżego ręcznego okresu.

SPINNER I OCZEKUJĄCE WYNIKI
Mały obracający się wskaźnik pojawia się nad słupkami ikony w garażu, gdy mod
czeka na wynik bitwy zaobserwowanej w bieżącym uruchomieniu albo właśnie
przetwarza wynik lub bonus PD. Dotyczy wyłącznie bieżącego konta.
Przycisk nadal otwiera statystyki i zachowuje małe WN8. Podpowiedź rozróżnia
oczekiwanie od przetwarzania i podaje liczbę oczekujących wyników.

Samo uczestniczenie w bieżącej bitwie nie oznacza oczekującego wyniku.
Jeśli wrócisz do garażu przed jej końcem, znana modowi bitwa pozostaje oczekująca
do czasu udostępnienia wyniku przez WoT. Niepełny wynik może nadal oczekiwać
na uzupełnienie. Spinner gaśnie, gdy kolejka jest pusta i przetwarzanie zakończone;
nie działa według sztucznego czasu. Krótkie przetwarzanie może być ledwo zauważalne.

Wskaźnik dotyczy kolejki konta, niezależnie od wybranej zakładki okresu.
Ręczny reset nie kasuje oczekujących rozliczeń. Zmiana konta przełącza kolejkę;
spóźniony callback poprzedniego konta nie uruchamia wskaźnika nowego konta.
Po ponownym uruchomieniu bez wejścia do nowej lub trwającej bitwy zaległy
niepełny wpis nie podtrzymuje spinnera. Panel zachowuje liczbę brakujących
wyników z wyjaśnieniem, a mod nadal próbuje je odzyskać z pamięci klienta.
Przycisk „Odśwież” ponawia odczyt. Historia nie jest kasowana ani uznawana
za kompletną tylko po to, żeby wyłączyć wskaźnik. Podczas przetwarzania
odzyskanego wyniku spinner może na krótko pokazać rzeczywistą aktywność.
Wyłączenie moda unieważnia jego stare callbacki i usuwa wskaźnik wraz z przyciskiem.

KONTROLA FORMATU WYNIKÓW
Healthcheck porównuje odebrany wynik ze sprawdzonym kontraktem klienta.
Sprawdza nazwy pól, typy i kształt kontenerów, wymagane dane używane przez mod,
zakresy właściwych liczb oraz znany układ kosztów kredytów, obligacji i złota.
Sprawdza także wybrane zgodności identyfikatorów i rozliczenia dyrektyw.
Nowe nazwy pól porównuje ze stałym katalogiem; pierwszy wynik po aktualizacji
nie staje się automatycznie nowym wzorcem.

Przy niezgodności pojawia się ostrzeżenie systemowe WoT z nazwami problematycznych
pól i ścieżką logu. Komunikaty są wysyłane w garażu, bez przerywania bitwy.
Ta sama kombinacja kodu, ścieżki oraz oczekiwanego i otrzymanego typu/kształtu
jest zapisywana i zgłaszana raz na uruchomienie moda. Nowe problemy są grupowane;
próby wysłania ostrzeżenia o wynikach dzieli co najmniej 60 sekund.
Jeśli system powiadomień jest chwilowo niedostępny, komunikat czeka na kolejną
próbę. Panel zachowuje informację o wykrytym problemie w tym uruchomieniu.

Ostrzeżenie nie oznacza, że wszystkie statystyki są błędne. Znane poprawne dane
mogą zostać zapisane mimo nowego nieużywanego pola lub częściowego rozliczenia.
Nieznany układ krotki kosztów nie jest zgadywany na podstawie starych indeksów.
Przy znanym układzie brak jednej kwoty nie usuwa innych potwierdzonych walut.
Zwykłe oczekiwanie na wynik oraz odpowiedź „jeszcze niegotowy” nie wywołują
alarmu o formacie. Zmiana wartości obrażeń czy PD również nie jest takim alarmem.

Zakres kontroli ma granice: zmiany znaczenia przy tych samych nazwach, typach
i dopuszczalnych wartościach nie da się wykryć z samego wyniku. Nieużywane pola
wewnętrznych rozszerzeń nie mają pełnej walidacji, a brak nieużywanego pola
opcjonalnego nie jest alarmem. Po dużej zmianie klienta nadal potrzebne jest
porównanie z natywnym raportem. Szczegóły: source/docs/RESULT_HEALTH_CONTRACT.md.

LOG MODA
Standardowa ścieżka na Windows:
%APPDATA%/grz_wot_session_stats/logs/session-stats.log

Plik jest w UTF-8. Wpisy zawierają czas UTC, poziom, wersję moda oraz diagnostykę,
np. zmianę liczby oczekujących wyników i kod/ścieżkę/typ problemu healthchecka.
Wpisy CONFIG opisują odczyt i walidację wyglądu, a CONFIG_PATH problemy
z ustaleniem ścieżki JSON obok aktywnej paczki moda.
Kontrola zapisuje metadane schematu, bez surowych wyników, nicków, identyfikatorów
kont i wartości statystyk. Własny log zachowuje typ wyjątku i miejsca w kodzie,
bez treści wyjątku, która mogłaby zawierać dane wyniku.

Rotacja: około 1 MiB na plik oraz trzy kopie session-stats.log.1, .2 i .3 —
około 4 MiB dla tej rodziny logu. Równoległe klienty korzystają z krótkiej
nieblokującej blokady pliku; chwilowe zajęcie blokady nie zatrzymuje gry.
Jeżeli środowisko nie udostępnia modułu blokad, używany jest osobny plik
session-stats-<PID>.log, gdzie PID jest numerem procesu gry. Ma taki sam limit
rotacji; limit dotyczy wtedy każdej rodziny PID osobno. Mod nie usuwa logów
innych procesów. Ostrzeżenie o wyniku wskazuje faktycznie używaną ścieżkę.

Błąd zapisu własnego logu nie wyłącza statystyk. Mod zgłasza go w panelu
i powiadomieniach WoT; pozostaje dotychczasowa diagnostyka w game.log.
Log jest lokalny i nie jest automatycznie wysyłany.

FINANSE I PD
Bazowe PD pochodzą z originalXP, a otrzymane PD z wyniku gry. Dodatkowy bonus
zastosowany po bitwie jest uzgadniany z natywnym kontrolerem wyników i zapamiętany.
Nie odtwarzamy bazowych PD przez dzielenie wartości końcowej przez mnożnik.

Kredyty obejmują przyznany wynik z właściwymi potrąceniami oraz koszt napraw,
automatycznego uzupełnienia amunicji, materiałów i dyrektyw. Koszty dyrektyw nie
są odejmowane drugi raz, gdy należą już do kosztu automatycznego uzupełnienia.
Obligacje uwzględniają przychód i wydatki zapisane w rozliczeniu bitwy, także
dyrektywy opłacone obligacjami. Złoto jest oddzielną walutą.

Bilans dotyczy rozliczonych bitew w wybranym okresie. Zakup czołgu, sprzedaż
wyposażenia i inne niezależne operacje w garażu nie są przypisywane ostatniej
mapie. Odroczona rezerwa kredytów nie jest traktowana jak natychmiastowa wypłata.
Nagroda jest doliczana, jeśli została ujęta w wyniku danej bitwy. Brakujące kwoty
pozostają nieznane — nie są zastępowane zerem ani ceną katalogową wyposażenia.

DANE, SKRÓT I PRZYCISK
Standardowa lokalizacja na Windows:
%APPDATA%/grz_wot_session_stats/

Wklej tę ścieżkę do paska Eksploratora. Osobny podkatalog dla każdego konta/regionu
ma nazwę wyliczoną z identyfikatora, a nie nicku. Dane nie leżą w mods/2.4.1.0,
więc przeniesienie moda do nowej wersji gry nie usuwa ręcznego okresu.
Zapis tworzy nową, kompletną generację JSON z sumą kontrolną; przechowuje trzy
najnowsze generacje. Nieznany nowszy schemat blokuje zapis zamiast niszczyć pliki.

Dotychczasowe ustawienia skrótu i włączenia przycisku garażu pozostają osobno
od wyglądu. Opcjonalnie utwórz %APPDATA%/grz_wot_session_stats/config.json:
{
  "hotkey": "CTRL+F10",
  "footer_button": true
}
Możesz ustawić F1–F12 z kombinacją CTRL, SHIFT lub ALT, np. CTRL+SHIFT+F10.
Zmiana skrótu lub footer_button obowiązuje po ponownym uruchomieniu gry.
Nieprawidłowy skrót przywraca domyślne Ctrl+F10.
Kolory i przewijanie edytuj w grz.sessionstats.json obok .wotmod.

WN8 I AKTUALIZACJE GRY
Dołączona jest tabela XVM Wargaming 2026-10-19, 999 pojazdów. Działa bez sieci.
Brak oczekiwanych wartości nowego czołgu nie wyłącza PD, liczników ani finansów;
WN8 pokazuje wówczas brak lub niepełne pokrycie.

Aby uaktualnić wyłącznie dane WN8, pobierz JSON:
https://static.modxvm.com/wn8-data-exp/json/wg/wn8exp.json
i zapisz go jako %APPDATA%/grz_wot_session_stats/wn8exp.json. Uruchom ponownie grę.
Nie używaj pliku z katalogu lesta. Błędny lokalny plik powoduje powrót do tabeli
dołączonej do moda. Aktualizacja tabeli może zmienić WN8 wcześniejszych wyników;
liczniki, PD i rozliczenia walut pozostają oparte na zachowanych wynikach.

Własne zasoby okna są rejestrowane przez gui/gen_resources i nazwę R.mods.grz…,
bez stałych numerów zasobów oraz podmiany podstawowych plików panelu wyników.
Przycisk w garażu korzysta z własnego komponentu stopki i OpenWG Gameface.
Gdy struktura stopki po aktualizacji jest niedostępna, pozostaje niezależny skrót
klawiaturowy, jeżeli interfejs klawiatury i okna nadal działają.
Przy zmianie klienta zwykle wystarczy przejrzeć runtime.py, normalize.py,
views.py, footer.py i mały adapter grafik visuals.py. Rdzeń obliczeń i format
danych są od nich oddzielone. Po potwierdzonej zmianie schematu trzeba również
zaktualizować właściwy kontrakt w health.py; samo ostrzeżenie nie zmienia adaptera.
Odczyt fizycznej lokalizacji konfiguracji jest oddzielony w config_path.py,
a walidacja wyglądu w appearance.py nie zależy od klienta. Źródła lokalizacji
i zasady bezpiecznego odczytu: source/docs/CONFIG_PATH_SOURCES.md.
Żaden mod korzystający z wewnętrznego interfejsu klienta nie ma gwarancji działania
po dowolnej przyszłej aktualizacji; ta architektura ogranicza zakres poprawek.

ZACHOWANE ZABEZPIECZENIA Z 0.2.5
• Brak importu okna, obsługi klawiatury albo opcjonalnej subskrypcji nie blokuje
  sam w sobie odbioru i zapisu wyników z pozostałych dostępnych źródeł.
• Własne callbacki są osłonięte, aby ich błąd nie przerywał natywnego dispatchera.
  Zamykanie i zatrzymanie odłączają elementy niezależnie. Zachowane stare
  callbacki są unieważnione i nie mogą sterować nowym oknem lub uruchomieniem.
• Brak pomocnika miniaturek czołgów nie wyłącza miniaturek map. Brak grafik
  nie blokuje tekstowej części statystyk.
• Ponowny odczyt zapisanego wyniku korzysta ze znanych nazw i identyfikacji mapy,
  gdy bieżący klient nie potrafi ich odtworzyć. Chroni to grupowanie historii.
• Panel ostrzega o niedostępnym źródle wyników lub dodatkowych bonusów PD.
  Powtarzane błędy nie zalewają logu. Brak danych nadal oznacza brak danych;
  nie zgadujemy nowego znaczenia pól finansowych ani wartości bonusu.

To ochrona przed konkretnymi awariami, nie automatyczne dostosowanie do każdego
nowego WoT. Zmiana formatu wyników, mostka Wulf/Gameface lub wersji Pythona może
wymagać aktualizacji adaptera albo ponownej kompilacji. Po zmianie aktywnego
katalogu mods trzeba też zainstalować paczkę dla właściwej wersji klienta.
Szczegóły audytu i przypięte źródła: source/docs/UPDATE_COMPATIBILITY_SOURCES.md.

PIERWSZE SPRAWDZENIE W GRZE
1. W garażu sprawdź małą ikonę, pozycję okna, widoczne podpisy zakładek,
   przeciąganie za tytuł, krzyżyk w prawym rogu, przełączanie PD
   i Czołgi/Mapy/Bitwy, Ctrl+F10 oraz zamknięcie przez Esc.
   Zmień wybrany kolor lub mnożnik rolki w JSON, zapisz i użyj „Odśwież”.
   To sprawdzenie interfejsu nie wymaga rozegrania żadnej bitwy.
2. Odbiór wyników sprawdza się osobno: po nowej zakończonej bitwie losowej
   porównaj bazowe/otrzymane PD oraz netto kredytów i obligacji z natywnym
   raportem tej konkretnej bitwy. Przy wcześniejszym powrocie do garażu
   sprawdź spinner i jego podpowiedź, a po pełnym rozliczeniu — wygaszenie
   wskaźnika, o ile nie oczekują inne wyniki.
3. Zamknij i ponownie uruchom grę: „Od uruchomienia” ma 0 bitew, „Od resetu”
   zachowuje rozegrany wynik. Ręczny reset zeruje tylko drugi okres.
   Jeśli pozostał niepełny wynik z wcześniejszego uruchomienia, sam ten wpis
   nie powinien uruchamiać spinnera; panel pokaże wyjaśnienie braków.
Jeżeli panel się nie otworzy, wynik się nie pojawi lub zobaczysz ostrzeżenie,
zachowaj wskazany log moda wraz z kopiami po rotacji oraz game.log z tego
uruchomienia (i python.log, jeżeli klient go tworzy). Gdy osobny log nie działa,
w game.log wyszukaj grz.sessionstats. Przy rozbieżności potrzebny jest również
natywny ekran szczegółów wyniku. Bez tych danych nie da się potwierdzić przyczyny.

COMMON TEST
Oddzielny klient testowy nie gwarantuje odseparowania lokalnej historii moda.
Dziennik statystyk jest przypisany do konta i regionu. Jeżeli Common Test zwróci
tę samą parę identyfikatorów, a oba klienty użyją tego samego AppData, mogą
korzystać z tej samej lokalnej sesji „Od resetu”. Osobny użytkownik Windows
zapewnia osobne AppData. Zwykła zmiana folderu instalacji gry tego nie zapewnia.
Nie dotyczy to postępu konta głównego na serwerze Wargaming.

ODINSTALOWANIE
Przy zamkniętej grze usuń tylko plik grz.sessionstats_0.2.7.wotmod z aktywnego
katalogu mods. OpenWG może być potrzebny innym modom. Dziennik w AppData pozostaje;
usunięcie katalogu danych usuwa zapamiętane statystyki.
Plik grz.sessionstats.json możesz zachować do kolejnej instalacji.

ŹRÓDŁA I BUDOWA
source/src/ — kod moda; source/ui/ — natywny panel i przycisk.
source/tests/ — testy rdzenia, zapisu, adaptera i interfejsu.
source/tools/build.py — buduje .wotmod metodą ZIP_STORED i zestaw instalacyjny.
source/tools/make_preview.py — podgląd prawdziwego UI na syntetycznych danych.
source/preview/PODGLAD.html oraz PODGLAD.html — podgląd, nie odbiera danych gry.

Budowa wymaga narzędzi deweloperskich Python 3 oraz CPython 2.7:
python3 tools/build.py --python27 /sciezka/do/python2.7 --client-version 2.4.1.0
Testy Pythona uruchamiane z source:
python2.7 -m unittest discover -s tests -p "test_*.py" -v
python3 -m unittest discover -s tests -p "test_*.py" -v
Testy UI wymagają Node i Playwright; ustaw GRZ_CHROME na plik wykonywalny Chrome.
node tests/ui_contract.cjs — kontrolki, układ oraz pojedyncze wyniki bitew.
node tests/ui-wheel.cjs — kierunek i tempo rolki, brak podwójnego ruchu i granice.
node tests/ui-footer.cjs — wygląd, kontrolki i integracja przycisku garażu.
node tests/ui-footer-compat.cjs — awarie API stopki i nieaktywne stare callbacki.
node tests/ui-footer-activity.cjs — spinner, stan kolejki, podpowiedź i cleanup.
node tests/ui-appearance.cjs — style z konfiguracji, fallback i mnożnik rolki.
Testy Pythona obejmują także walidację JSON, zgodność wartości domyślnych ze
stylem, ustalanie ścieżki paczki oraz przekazanie konfiguracji do panelu i stopki.
Source validation after PR #3 corrections: 364 tests on Python 3; the same suite
on CPython 2.7.18 with 4 Python-3-only builder tests skipped.
Testy obejmują zachowanie spinnera po restarcie i odzyskiwanie starych wyników.
Style i geometria domyślnego panelu i ikony są porównywane z bazowym wyglądem;
kontrola rastra dopuszcza ograniczone różnice antyaliasingu między Chromium.
Weryfikacja automatyczna nie jest testem działającego WoT.
Paczka gry zawiera bajtkod Pythona 2.7. Nie należy zastępować go bajtkodem Pythona 3.
Pliki BUILD.json, SHA256SUMS.txt i raporty w tests opisują rzeczywistą weryfikację.

Licencja kodu: GPL-3.0. OpenWG zachowuje MIT. Szczegóły i pierwotne źródła:
LICENSE.txt, THIRD_PARTY.txt, source/third_party/openwg/LICENSE.
