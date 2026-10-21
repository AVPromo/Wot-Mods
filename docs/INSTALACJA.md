# Stay Sharp Medkit Reminder 1.6.0 — instalacja i test

## Co robi

Wyświetla pomarańczową, gradientową ramkę apteczki, pulsującą przez 2 sekundy do pełnej intensywności i przez 2 sekundy do zera. Działa wyłącznie wtedy, gdy własny pojazd ma uprawnienie do wykorzystania apteczki wynikające z aktywnego efektu atutu, apteczka jest gotowa, HUD jest widoczny i trwa bitwa. Nie aktywuje apteczki, nie wydaje żadnego dźwięku i nie zmienia statystyk gry.

## Instalacja

1. Zamknij World of Tanks.
2. Zachowaj kopię potwierdzonej jako działająca wersji 1.5.0 poza katalogiem `mods`.
3. **Usuń stary plik 1.5.0 z aktywnego katalogu `mods/<wersja_gry>/`**. Dwie wersje tego samego moda nie mogą działać równocześnie.
4. Skopiuj `com.staysharp.medkitreminder_1.6.0.wotmod` do katalogu gry, np. `C:\Games\World_of_Tanks_EU\mods\2.4.1.0\` (jeżeli gra zaktualizowała numer katalogu, użyj nowego katalogu wersji).
5. Uruchom grę normalnie.

Nie trzeba kopiować `.py`, `.dds`, `.swf`, shaderów, banków dźwięku ani DLL. Pakiet `.wotmod` zawiera `meta.xml`, plik `.pyc` i komplet 21 DDS, pod ścieżkami zasobów WoT.

## Test w grze

- Przed odliczaniem i podczas wyboru konfiguracji nie powinna pojawić się ramka.
- Po rozpoczęciu bitwy, na pojeździe z właściwym atutem, gotowa apteczka powinna pulsować w cyklu 4 sekund.
- Sprawdź kamerę arcade, sniper, widok artyleryjski z góry i widok trajektorii.
- Po użyciu apteczki oraz podczas cooldownu ramka ma zgasnąć, a po odnowieniu wrócić.
- Przy rannym członku załogi lub natywnym podświetleniu WoT przypomnienie nie powinno zastępować ostrzeżenia gry.
- Po zamknięciu bitwy nie powinny pozostawać ramki ani uruchomione animacje.

## Diagnostyka

Log jest zapisywany pod:

`%LOCALAPPDATA%\StaySharpMedkit\staysharp.log`

Najbardziej przydatne wpisy:

- `v1.6.0 loaded; component events` — subskrypcja zdarzeń gry zainstalowana.
- `battle panel populated` — komponent został wykryty za pomocą zdarzenia rejestracji (nie przez podmianę metod).
- `HUD registration rejected: ...` — niezgodny klient / układ HUD; mod nie włączy grafiki.
- `equipment state=incompatible_hud_...` — niespodziewana zmiana w trakcie bitwy; mod wygasza ramkę.
- `GFX disabled by compatibility preflight: ...` — brak wymaganej części interfejsu renderera.
- `overlay mounted: hud_child` — nakładka została dodana pod komponentem HUD.
- `overlay mounted: gui_root` — stara metoda graficzna, gdy komponent HUD nie jest dostępny.
- `PULSE alive` — animacja dalej aktualizuje klatki.

Jeśli gra się wyłącza, **usuń 1.6.0**, wróć do sprawdzonej wersji 1.5.0 i wyślij końcówkę logu. Żaden test offline nie zastępuje prawdziwego klienta WoT.

## Aktualizacje WoT

Jeżeli aktualizacja nie zmieni API, wystarczy przenieść ten sam `.wotmod` do nowego katalogu `mods/<wersja_gry>`. Przy zmianie struktury HUD lub API moduł ma się wyłączyć bez zgadywania położenia ramki; może to wymagać aktualizacji moda. Plik `.pyc` jest zgodny z bajtkodem CPython 2.7 używanym przez zweryfikowany klient. Migracja gry na inny interpreter będzie wymagała nowej kompilacji.
