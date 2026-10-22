# Spinner po ponownym uruchomieniu gry

Przyczyną stałego oczekiwania bez rozegrania nowej bitwy było utożsamienie
nierozliczonych wpisów dziennika z bieżącą aktywnością klienta. Wpis rozpoczętej
bitwy może pozostać niepełny po zamknięciu gry. Jeśli klient nie udostępnia jej
wyniku w cache, taki wpis sam nie znika przy następnym uruchomieniu.

Przycisk w garażu sygnalizuje teraz oczekiwanie na wyniki bitew zaobserwowanych
w bieżącym uruchomieniu oraz faktyczne przetwarzanie wyniku lub premii PD.
Wcześniejsze niepełne wpisy pozostają w historii i w kolejce odczytu cache.
Panel pokazuje ich liczbę z wyjaśnieniem; przycisk Odśwież ponawia odczyt.
Udane odzyskanie rozlicza wynik zwykłą ścieżką, z zachowaniem deduplikacji.
Nie ma migracji schematu, usuwania historii ani uznawania braków za zera.

Odzyskiwanie i jawne pokrycie statystyk opisuje
[OFFLINE_RESULT_RECOVERY.md](OFFLINE_RESULT_RECOVERY.md). Wskaźnik aktywności
nie jest miarą kompletności danych. Ta jest pokazywana osobno jako liczba
odebranych wyników względem wszystkich zarejestrowanych bitew.

Testy obejmują restart bez nowej bitwy, niegotowy cache, odzyskanie starego
wyniku, nową bitwę obok zaległości, ręczne odświeżenie i reset zakresu,
ponowny start tej samej instancji, reconnect do trwającej bitwy oraz stary
lub bieżący wynik dostarczony bez zdarzenia avatar-ready.

Zgłoszenie odtworzono na syntetycznych danych testowych. Logów, zrzutów
ekranu, identyfikatorów konta i prywatnej historii gracza nie dodano do repo.
