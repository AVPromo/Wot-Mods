# Statystyki sesji dla World of Tanks

Źródła wersji 0.2.7: dwie niezależne sesje, WN8, PD, finanse z obligacjami,
podział na czołgi/mapy/bitwy, healthcheck wyników, lokalny log i konfigurowalny wygląd.
Szczegółowa instrukcja: [README_PL.txt](README_PL.txt), historia: [ZMIANY.txt](ZMIANY.txt).
Obie domyślne sesje i ręczny reset są osobne dla konta i regionu.
Opcjonalną trzecią zakładkę dla całego procesu gry włącza
`"sessions": {"instance_tab": true}` w JSON obok moda. Ma niezależny reset;
domyślnie jest wyłączona. Zasady: [ACCOUNT_SESSIONS.md](docs/ACCOUNT_SESSIONS.md).
Poprawki po review importu: [REVIEW_FIXES_PR3.md](docs/REVIEW_FIXES_PR3.md).
Pipeline budowania i walidacji jest dostarczany przez nadrzędny PR #2;
PR ze źródłami jest na nim oparty i wymaga jego wcześniejszego merge.

## Instalacja i współpraca z innymi modami

Pobierz ZIP wydania **Session Stats** z [Releases](https://github.com/Szwarceneger16/WotMods/releases).
Umieść `.wotmod` i `grz.sessionstats.json` razem w aktywnym `mods/<wersja gry>/`.
Zachowaj własny JSON przy aktualizacji. OpenWG Gameface 1.2.2 jest dołączony
na licencji MIT; instaluj tylko jedną kopię tej zależności, także gdy używa jej inny mod.
Usuń poprzednią wersję samych statystyk. Nie kasuj historii w AppData.

Statystyki używają własnego `mod_grz_session_stats`, pakietu `grz_session_stats`,
zasobów `grz.sessionstats` i osobnego katalogu danych/logów. Medkit Reminder ma
oddzielny punkt wejścia i nie jest zależnością. Zbudowane paczki mają rozłączne
ścieżki zasobów; rzeczywiste współdziałanie w kliencie nadal wymaga testu w grze.

## Budowanie lokalne

Pakowanie wymaga Python 3.9+ oraz CPython 2.7.18 do bajtkodu gry.
Python 2.7 służy wyłącznie do testów zgodności i kompilacji, bez dostępu do sieci.
Z tego katalogu:

```sh
python3 -m unittest discover -s tests -v
/path/to/python2.7 -m unittest discover -s tests -v
python3 tools/make_preview.py
python3 tools/build.py --python27 /path/to/python2.7
```

Wyniki w `dist/`: `.wotmod`, pełny ZIP instalacyjny ze źródłami, JSON konfiguracji,
OpenWG, raport `BUILD.json` oraz `SHA256SUMS.txt`. Builder nie pobiera zależności
i weryfikuje SHA-256 OpenWG. Wbudowany bajtkod używa ścieżek wirtualnych,
bez ścieżki komputera, na którym wykonano kompilację.

Podgląd i testy przeglądarkowe używają wyłącznie danych syntetycznych z generatora
`tools/make_preview.py`. Zależność testowa to Playwright; `GRZ_CHROME` opcjonalnie
wskazuje plik wykonywalny Chromium. Testy nie uruchamiają prawdziwego WoT.

## Prywatność i zgodność

Patrz [PUBLICATION_PRIVACY.md](docs/PUBLICATION_PRIVACY.md).
Nie publikuj lokalnych logów, historii gracza, konfiguracji użytkownika ani screenów.
Runtime przechowuje identyfikatory potrzebne do rozdzielania kont wyłącznie lokalnie;
nie są to dane dołączone do tego repozytorium ani telemetria.
Licencja tego moda: [GPL-3.0](LICENSE.txt); zależności: [THIRD_PARTY.txt](THIRD_PARTY.txt).
Ta licencja nie zmienia warunków pozostałych modów w repozytorium.

Interfejsy WoT mogą zmienić się po aktualizacji. Healthcheck nie gwarantuje wykrycia
zmiany znaczenia pola przy zachowaniu jego typu i struktury.
Wersja 0.2.4 została sprawdzona przez użytkownika w grze; 0.2.7 była sprawdzana
w testach automatycznych i wymaga testu w aktualnym kliencie.
