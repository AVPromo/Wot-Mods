# Import źródeł i kontrola publikacji

Punkt odniesienia: paczka źródłowa Session Stats 0.2.7.
Pierwotny import zachowywał kod runtime i UI z tej paczki. Poprawki po review
opisuje `REVIEW_FIXES_PR3.md`; schemat zapisu i domyślny JSON pozostają bez zmian.
Builder otrzymał numerowanie wydań, pełny manifest assetów i filtrowanie
wygenerowanych raportów testowych. Test obrazu zachowuje dokładne porównanie
stylów/geometrii; raster dopuszcza najwyżej 16 pikseli krawędzi z różnicą
do 4/255 na kanał, aby uniknąć różnic zaokrąglenia renderera Chromium.

Pierwotna weryfikacja lokalna importu (przed poprawkami po review):

- 284 testy statystyk na Pythonie 3 i 284 na CPythonie 2.7.18.
- 175 testów istniejącego moda i wspólnej infrastruktury wydawania.
- 78 kontroli panelu, 22 rolki, 22 aktywności spinnera, 12 zgodności stopki,
  30 konfiguracji wyglądu oraz zestaw bazowej ikony.
- Pierwotny `.wotmod` 0.2.7 był zgodny bajtowo z paczką wejściową:
  SHA-256 `76e5cffa54d79b6cbee37858725d063664082fe8cf0da41eb9406b10bff394bd`.
  To historyczny punkt odniesienia; poprawiony kod ma inną sumę.
- Dwukrotne budowanie daje identyczne wszystkie sześć assetów wydania.
- Próbne wydanie 0.2.8 ma właściwą wersję także wewnątrz bajtkodu.
- Brak kolizji identyfikatorów paczek i ścieżek zasobów z Medkit Reminder.
- Skan źródeł, zagnieżdżonych archiwów i stałych/ścieżek bajtkodu: PASS.

Wyniki te dotyczą lokalnego złożenia obu PR. Nowy workflow musi zostać
zaakceptowany na `main`, zanim wynik jego CI będzie potwierdzał import źródeł.
Wersji repozytoryjnej nie uruchamiano w prawdziwym kliencie WoT.
Informacje o ograniczeniach: `UPDATE_COMPATIBILITY_SOURCES.md`,
`RESULT_HEALTH_CONTRACT.md` oraz `PUBLICATION_PRIVACY.md`.
