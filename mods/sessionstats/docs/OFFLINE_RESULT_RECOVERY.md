# Wynik bitwy po wyłączeniu klienta

## Co jest liczone

Początek bitwy jest zapisywany trwale razem z identyfikatorem bitwy, kontem,
regionem i przynależnością do obu okresów. Sam początek nie jest zwycięstwem,
porażką ani wynikiem liczbowym. Dopiero odebrane dane pozwalają go rozliczyć.
Wynik z rozpoznanym rozstrzygnięciem może wnosić potwierdzone statystyki,
nawet jeśli inne pola są jeszcze niepełne. Brakujące pola nie stają się zerami.

Już przy wejściu do bitwy zapisujemy dostępne dane rozpoznawcze: czas,
identyfikator i nazwę mapy oraz identyfikator, nazwę, poziom i klasę własnego
czołgu. Nazwy pochodzą z deskryptora pojazdu i typu areny klienta. Zapis nie
czeka na koniec bitwy ani wyjście z gry. Jeśli arena nie jest jeszcze gotowa,
następne zdarzenia awatara i odczyty co 5 sekund uzupełniają brakujące pola
tego samego wpisu; identyczny odczyt nie powoduje kolejnego zapisu na dysk.
Błąd opcjonalnej nazwy pojazdu nie blokuje zapisania początku bitwy.

Po restarcie wpis zachowuje znaną mapę i czołg oraz nieznany wynik i kreski
przy brakujących statystykach. Nie zapisujemy listy graczy, nicków ani surowego
kontekstu areny. To rozszerzenie nie odtworzy nazw, których starsza wersja
nie zdążyła zachować; mogą je uzupełnić późniejsze dane klienta lub wynik.

Podsumowanie i grupy pokazują liczbę wyników względem wszystkich zarejestrowanych
bitew, np. `20 / 21`. Brakująca bitwa pozostaje także na liście bitew z nieznanym
wynikiem. Pokrycie WN8, PD i finansów uwzględnia pełną liczbę zapisanych bitew.
Procent wygranych i średnie dotyczą potwierdzonych danych; panel jawnie oznacza
niepełny zakres. Wynik odebrany następnego dnia uzupełnia pierwotną bitwę i okres,
zamiast tworzyć drugą bitwę albo trafiać do nowego uruchomienia.

## Odczyt klienta i serwera

Zweryfikowana ścieżka klienta 2.4.1.5493, commit
`5e721e36891c80d8d51a431164960c863641ee63`:

- [BattleResultsCache.get](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client_common/shared_utils/account_helpers/BattleResultsCache.py)
  najpierw sprawdza lokalny plik, a gdy go nie ma, używa natywnego polecenia
  `CMD_REQ_BATTLE_RESULTS`. Jest to ścieżka klienta, bez własnego HTTP/API,
  tokenów, zewnętrznej usługi ani procesu działającego po zamknięciu gry.
- Ten sam kod czyści standardowy katalog wyników w konstruktorze cache.
  Sam plik klienta nie stanowi trwałego archiwum moda.
- Po odebraniu strumienia klient zapisuje swój cache, wywołuje callback,
  a następnie wysyła `CMD_BATTLE_RESULTS_RECEIVED`. Dodatkowy obserwator
  zapisuje znormalizowane dane moda przed oryginalnym callbackiem i tym
  potwierdzeniem. Obejmuje też odczyt zlecony przez interfejs gry lub inny mod,
  gdy zwykłe zdarzenie wyniku nie zostanie dostarczone do naszego adaptera.
- [BattleResultsGetter](https://github.com/izeberg/wot-src/blob/5e721e36891c80d8d51a431164960c863641ee63/sources/res/scripts/client/gui/shared/gui_items/processors/common.py)
  używa tej samej metody `battleResultsCache.get` dla interfejsu WoT.

Obserwator zachowuje argumenty, wynik wywołania i oryginalnego odbiorcę.
Błąd obserwatora nie blokuje odbiorcy. Własne zapytania nie są przetwarzane
podwójnie. Odpowiedź jest związana z kontem i cyklem życia w chwili zlecenia;
callback starego uruchomienia nie modyfikuje nowego. Usuwanie obserwatora
nie nadpisuje opakowania zainstalowanego później przez inny mod.

## Kolejka odzyskiwania

Po zalogowaniu odczytywane są wszystkie zachowane niepełne wpisy. Zapytania
pozostają szeregowe, z pierwszeństwem bieżących bitew i najwcześniej należnych
prób. Stary błąd nie powinien stale wyprzedzać jeszcze niesprawdzonych wyników.
Cooldown współdzielonego cache, niegotowe konto i rozłączenie nie zwiększają
wykładniczego opóźnienia konkretnej bitwy; limit żądań dostaje dłuższą przerwę.
Zwykły błąd odczytu pozostawia wpis i ponowienia z ograniczonym backoffem.

Poprawny strumień przychodzący po wygaśnięciu naszego żądania nadal może
uzupełnić nieznane dane, ale nie zmienia nowszych potwierdzonych wartości
ani nie usuwa tokenu nowszego zapytania. To uzupełnienie ma `reconcile=False`.
Diagnostyka raportuje stany i znane kody klienta, bez numerów kont i bitew,
surowych odpowiedzi ani dowolnych nieznanych wartości liczbowych.

## Granice i weryfikacja

Mod nie działa po zamknięciu klienta. Nierozliczona bitwa czeka na następne
logowanie, a następnie korzysta z powyższego odczytu serwerowego. Kod klienta
nie stanowi gwarancji czasu przechowywania wyniku po stronie serwera.
Jeśli WoT nie udostępnia już danych, nie da się obiecać ich pełnego odtworzenia.
Taki wpis pozostaje jawną luką. Nie zastępujemy go zgadywaną porażką ani
różnicą salda kredytów, na które wpływają także inne operacje.

Testy na syntetycznym transporcie obejmują zamknięcie przed końcem bitwy,
odebranie wyniku po zalogowaniu do nowego uruchomienia, przynależność do
oryginalnego okresu, deduplikację, odczyt natywny bez zdarzeń, zapis przed
odbiorcą, błędy i opakowania innych modów, zmianę konta, cooldown, kolejność
prób oraz poprawne spóźnione strumienie. Testy nie emulują retencji serwera
i nie zastępują próby w rzeczywistym kliencie WoT.
Osobne testy początku bitwy sprawdzają zapis przed zamknięciem klienta,
rozpoznawalny wpis po restarcie bez wyniku, późniejsze ładowanie metadanych,
brak powtórnych zapisów i wykluczenie prywatnych pól kontekstu.
