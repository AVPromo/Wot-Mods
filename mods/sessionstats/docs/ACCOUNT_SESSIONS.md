# Sesje kont i całej instancji gry

Domyślnie mod pokazuje wyłącznie statystyki bieżącego konta. Rozdziela również
konta o takim samym numerze w różnych regionach. Nie zapisuje nicku jako klucza.

| Zakładka | Konta | Reset | Nowy proces gry |
| --- | --- | --- | --- |
| Od uruchomienia | Tylko bieżące konto | Nowy proces | Pusty zakres |
| Od resetu | Tylko bieżące konto | Ręczny, osobny dla konta | Zachowuje historię |
| Cała instancja, opcjonalnie | Konta użyte w bieżącym procesie | Własny ręczny | Pusty zakres |

Przełączenie A → B → A przywraca poprzednią historię i ręczny okres A.
Reset B nie zmienia historii A ani jego daty resetu. Zwykły przycisk resetu
działa na wybrany zakres bieżącego konta. Potwierdzenie znika po zmianie konta,
a adapter odrzuca polecenie ze starym kluczem konta lub nieznanym zakresem.

W JSON obok paczki moda opcjonalnie ustaw:

```json
{
  "sessions": {
    "instance_tab": true
  }
}
```

Domyślne `false`, brak pola i błędny typ pozostawiają trzecią zakładkę ukrytą.
Pozostałe sekcje istniejącego pliku można zachować. Zmiana jest odczytywana
przy otwieraniu panelu lub po wybraniu „Odśwież”. Przy trzech zakładkach
„Od uruchomienia” ma krótszy podpis „Od startu”, aby zmieścić się w wąskim oknie.

Wspólny zakres jest projekcją wpisów przypisanych do bieżącego procesu gry.
WN8, średnie i pokrycie są ponownie liczone z poszczególnych bitew. Nie jest to
średnia wyników kont. Identyfikacja wierszy uwzględnia konto, ale wiersz wspólny
nie ujawnia jego identyfikatora. Istniejące miniatury i grupowania pozostają.

Wspólny reset nie zapisuje ani nie zmienia żadnej historii konta. Ręczny reset
konta również nie zmienia wspólnego zakresu. Wyniki zaczętych wcześniej bitew,
także nierozliczonych w chwili resetu, nadal uzupełniają pierwotną historię
konta, ale nie trafiają do świeżego wspólnego zakresu. Zaległości poprzedniego
procesu również nie są dodawane do nowej instancji gry.

Wspólny reset i identyfikacja jego wierszy istnieją wyłącznie w pamięci procesu.
Ukrycie i ponowne włączenie zakładki zachowuje reset; uruchomienie nowego
procesu rozpoczyna nowy wspólny zakres. Mod nie tworzy połączonego archiwum
kont. Zmiana konta nadal przełącza spinner na kolejkę aktywnego konta.

Testy używają syntetycznych kont, wyników i transportu. Weryfikacja w Chromium
i Pythonie nie zastępuje sprawdzenia w działającym kliencie WoT.
