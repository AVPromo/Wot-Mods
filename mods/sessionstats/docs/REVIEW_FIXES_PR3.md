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

Validation: 364 Python 3 tests; the same Python 2.7 suite with 4 Python-3-only
builder tests skipped. The 114 panel checks cover rejected callback registration,
synchronous delivery during registration and retained callbacks after teardown.
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

Account scopes and the optional durable installation scope:
- Default scopes and manual resets remain isolated per account and region.
  A confirmation from a previous account cannot reset the current account.
- sessions.instance_tab=true displays the installation tab. Its history and
  manual reset persist across game restarts using a separate transactional
  StatsService ledger; account ledgers and reset epochs are never modified.
- Installation identity uses the verified physical game root, independent of
  client-version directories. Unknown roots do not select a global fallback.
- Fifteen additional Python tests cover persistent history and reset boundaries,
  restart recovery, late discovery, separate installations, failed writes,
  corrupted generations and identity discovery. An additional browser check
  verifies that confirmation explains restart persistence.
- Details and migration rules: [ACCOUNT_SESSIONS.md](ACCOUNT_SESSIONS.md).

## English defaults and editable language catalogs

- All mod interface text now uses an English default and a configurable local
  JSON catalog with complete English, Russian, French, Polish, German, Spanish
  and Ukrainian dictionaries (178 message keys per language).
- Root `language` in `grz.sessionstats.json` selects the language. The neighboring
  `grz.sessionstats.languages.json` can override individual messages or add
  languages. The installation ZIP includes the editable file and verifies its
  checksum; the `.wotmod` includes all bundled translations as an offline fallback.
- Translation validation rejects unsafe placeholders and malformed catalogs;
  valid partial overrides retain per-message fallbacks. Native notifications
  escape markup and panel/footer labels use text nodes. Catalog values and
  private paths are omitted from diagnostics.
- Canonical English and legacy Polish warning templates are translated at
  presentation time. Account histories, session/reset boundaries and game-supplied
  map/vehicle names remain intact. Language reloads require opening the panel or
  Refresh, with no per-tick file reads.
- Local validation: 375 Python tests on both runtime interpreters (four builder
  cases skipped on Python 2.7), 183 infrastructure/Medkit tests, 165 panel checks,
  29 footer activity checks, 22 wheel checks, 12 footer compatibility checks and
  31 appearance checks. Raster checks use grayscale text to avoid RGB subpixel
  repaint artifacts while retaining the original exact style/layout comparison
  and pixel thresholds. All six assets reproduce; recursive privacy and
  cross-mod integration checks pass. Native Gameface still needs in-game review.
