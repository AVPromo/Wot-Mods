# Poprawki po review PR #3

- Źródła są oparte na gałęzi dedykowanego PR #2, który zawiera budowanie,
  testy obu wersji Pythona, testy Chromium i automatyczne Releases statystyk.
  Zmiany workflow pozostają do review w PR #2. PR #3 pokazuje różnicę źródeł.
  Pipeline musi być zaakceptowany na `main` przed ostatecznym merge źródeł.
- Test błędnego JSON-a wymaga liczbowej lokalizacji błędu i braku prywatnej
  wartości w logu, bez uzależniania wyniku od pozycji wybranej przez dekoder.
- Każde zapytanie cache ma własny token. Spóźnione odpowiedzi wygasłego
  zapytania nie usuwają nowszego zapytania ani nie omijają backoffu.
- Wyłącznie `reconcile=True` pozwala zmieniać znane wyniki. `complete=True`
  oznacza kompletność; bez uprawnienia do rewizji może uzupełniać brakujące pola.
- Błąd opcjonalnej rejestracji Gameface nie blokuje pierwszego odczytu modelu
  i wymiarowania. Następne zdarzenie modelu ponawia rejestrację, bez dodawania
  kolejnych nasłuchów silnika; cleanup usuwa tylko uzyskaną rejestrację.
- Builder wpisuje wersję wydania do nazw plików w aktywnych instrukcjach,
  również w kopii źródeł. Historyczny changelog i dowody zgodności pozostają historyczne.
- Manifest wewnątrz ZIP-a używa ścieżek względem korzenia rozpakowanej paczki;
  `sha256sum -c SHA256SUMS.txt` sprawdza wszystkie trzy pliki instalacyjne.
- Historyczne niepełne wpisy pozostają w kolejce odczytu i historii, ale po
  restarcie bez nowej bitwy nie utrzymują spinnera. Panel pokazuje wyjaśnienie.
  Szczegóły i granice działania: [RESTORED_RESULTS_ACTIVITY.md](RESTORED_RESULTS_ACTIVITY.md).

Weryfikacja: 349 testów na Pythonie 3; ten sam zestaw na Pythonie 2.7
z czterema pominiętymi testami narzędzia pakującego wymagającego Pythona 3.
113 kontroli panelu obejmuje trwały i przejściowy błąd rejestracji callbacku,
synchroniczne wywołanie podczas rejestracji oraz spóźnione zdarzenia po zamknięciu.
Sprawdzono wydanie 0.2.8, rzeczywistą weryfikację sum po rozpakowaniu ZIP-a
oraz identyczny ZIP po ponownym zbudowaniu z zawartych w nim źródeł.
Testy z atrapami klienta nie zastępują uruchomienia WoT.

Odzyskiwanie po wyłączeniu klienta ma dodatkową obserwację natywnego cache
przed odbiorcą i potwierdzeniem strumienia, sprawiedliwą kolejkę, osobne opóźnienia
cooldown/logowania i uzupełnianie nieznanych danych ze spóźnionych strumieni.
Niepełne okresy i brakujące bitwy są jawne w panelu. Granice odzyskiwania
i przypięty kod klienta: [OFFLINE_RESULT_RECOVERY.md](OFFLINE_RESULT_RECOVERY.md).
Przy wejściu do bitwy utrwalamy także dostępne nazwy mapy i własnego czołgu,
poziom i klasę. Brakujący wynik pozostaje dzięki temu rozpoznawalny po restarcie.
Osiem testów obejmuje natywny deskryptor, późną gotowość metadanych, trwałość,
deduplikację zapisów, ochronę potwierdzonych wyników i prywatność kontekstu.

Porównanie rastra zachowuje limit 16 zmienionych pikseli; tolerancja kanału 6/255
obejmuje zaobserwowane na Chromium 151 zaokrąglenie 10 pikseli z różnicą 5/255.
Style i geometria nadal są porównywane dokładnie. Dodatkowa kontrola negatywna
potwierdza odrzucenie rzeczywistej zmiany kolorów, promieni i przezroczystości.

Review 5610518614:
- Opóźnione odświeżenie premii zachowuje konto z chwili zaplanowania.
  Po zmianie konta timer zwalnia swój stan i kończy pracę bez odczytu ani
  przetwarzania wyników nowego konta. Ręczne Odśwież działa niezależnie
  i nie przejmuje ani nie kasuje timera poprzedniego konta.
- Cleanup panelu unieważnia lokalny stan powiązania i callbacku przed
  wywołaniem mostka. Każde z trzech engine.off i usunięcie callbacku modelu
  ma osobną osłonę. Błąd jednego wywołania nie blokuje pozostałych i nie
  wydostaje się do beforeunload. Zachowany callback zmiany skali pozostaje
  nieaktywny po zniszczeniu dokumentu.
- Dwa testy Pythona obejmują zmianę konta w czasie oczekiwania na timer,
  brak odczytu i rewizji nowego konta oraz niezależność ręcznego odświeżenia.
  Piętnaście kontroli Chromium obejmuje osobną awarię każdego usunięcia,
  wspólną awarię wszystkich, ponowne sprzątanie i spóźnione callbacki.

Sesje kont i opcjonalny zakres całego procesu:
- Dwie domyślne zakładki i ręczny reset pozostają osobne dla każdego konta
  i regionu. Stare potwierdzenie po zmianie konta nie resetuje nowego konta.
- sessions.instance_tab=true włącza osobną trzecią zakładkę z niezależnym
  resetem w pamięci procesu. Nie zmienia dzienników ani epok ręcznych kont.
- Dwanaście testów Pythona obejmuje izolację kont/regionów, zmiany konta,
  oba kierunki niezależności resetów, późne wyniki i restart procesu.
  Dziesięć kontroli Chromium sprawdza wyłączenie domyślne, polecenia resetu,
  zamykanie starego potwierdzenia, przełączanie kont i wąski panel z trzema
  podpisami. Szczegóły: [ACCOUNT_SESSIONS.md](ACCOUNT_SESSIONS.md).
