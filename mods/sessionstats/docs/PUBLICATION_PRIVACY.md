# Audyt publikacji źródeł 0.2.7

Import obejmuje kod, zasoby UI, publiczną tabelę oczekiwanych wartości WN8,
testy, syntetyczny podgląd, dokumentację oraz niezmienioną zależność OpenWG.
Nie importowano prywatnej instalacji gry, stanu konta, historii bitew, logów,
zrzutów ekranu, dumpów, plików autoryzacji ani konfiguracji użytkownika.
Dołączony JSON to wbudowane ustawienia domyślne.

Identyfikatory w fixture'ach są syntetyczne: np. `DEMO:100`, małe numery kont
w testach i sekwencyjne numery bitew z generatora. Publiczne deskryptory typów
czołgów w tabeli WN8 nie identyfikują kont graczy.
Nazwy autorów i odnośniki w materiałach zewnętrznych są wymaganymi informacjami
o pochodzeniu/licencji, nie danymi właściciela tego repozytorium.

Kontrola obejmuje źródła i dokumentację, rozwinięte archiwa, teksty w bajtkodzie
Pythona 2.7 oraz wirtualne ścieżki kompilacji. Testy diagnostyki sprawdzają
pomijanie nicków, numerów kont i surowych raportów w komunikatach healthchecku.
Automatyczny skan wzorców jest dodatkową kontrolą; nie dowodzi anonimizacji
dowolnego nieznanego formatu danych.

Mod zapisuje lokalne statystyki rozdzielone według konta. Takiej historii nie wolno
dołączać do PR ani Releases. Lokalny log ma rotację i nie jest wysyłany przez mod.

Repozytorium jest publiczne. Jego właściciel, publiczna tożsamość GitHub,
autorzy commitów i historia PR/Actions pozostają widoczne na zasadach GitHub.
Publikacja kodu nie ukrywa tych metadanych konta.
