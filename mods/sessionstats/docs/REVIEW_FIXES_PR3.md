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

Weryfikacja: 291 testów na Pythonie 3; ten sam zestaw na Pythonie 2.7
z czterema pominiętymi testami narzędzia pakującego wymagającego Pythona 3.
84 kontrole panelu obejmują trwały i przejściowy błąd rejestracji callbacku.
Sprawdzono wydanie 0.2.8, rzeczywistą weryfikację sum po rozpakowaniu ZIP-a
oraz identyczny ZIP po ponownym zbudowaniu z zawartych w nim źródeł.
Testy z atrapami klienta nie zastępują uruchomienia WoT.

Porównanie rastra zachowuje limit 16 zmienionych pikseli; tolerancja kanału 6/255
obejmuje zaobserwowane na Chromium 151 zaokrąglenie 10 pikseli z różnicą 5/255.
Style i geometria nadal są porównywane dokładnie. Dodatkowa kontrola negatywna
potwierdza odrzucenie rzeczywistej zmiany kolorów, promieni i przezroczystości.
