# Automatyzacja raportów

Custom integration do Home Assistant do automatycznego generowania raportów dziennych, tygodniowych, miesięcznych i rocznych na podstawie **encji narastających** (liczniki energii, wody, gazu, subliczniki itp.).

Autor / branding: **sza86**

## Co nowego w tej paczce

Ta wersja rozszerza integrację o diagnostykę i podgląd danych roboczych:

- dodany **interwał odświeżania źródeł w UI**,
- domyślny interwał skanowania ustawiony na **10 minut**,
- dodany sensor **Podgląd bazy danych**,
- dla każdego źródła tworzone są dynamiczne encje:
  - **obecny odczyt**,
  - **poprzedni odczyt**,
  - **status źródła**,
- status źródła pokazuje także:
  - ostatni błąd,
  - opis błędu,
  - skąd błąd się wziął,
  - aktualny i startowy stan dla okresów: dzień, tydzień, miesiąc, rok,
  - wyliczoną deltę dla każdego okresu,
- sensor podglądu bazy pokazuje skrót danych ze storage i listę ostatnich plików CSV.

## Co robi integracja

Integracja:

- pobiera stany z wybranych encji narastających,
- zapisuje snapshoty początków okresów,
- oblicza zużycie za:
  - dzień,
  - tydzień,
  - miesiąc,
  - rok,
- może doliczać **koszt informacyjny** na podstawie ceny jednostkowej,
- wysyła raporty przez `notify.*`,
- zapisuje archiwum do CSV,
- udostępnia sensory do dashboardu,
- wykrywa podstawowe problemy danych:
  - `unknown`,
  - `unavailable`,
  - cofnięcie licznika,
  - opcjonalną anomalię na podstawie progu.

## Ważne założenie

Źródłowe encje powinny przekazywać **wartość narastającą od początku licznika**.

Przykłady poprawnych źródeł:

- licznik energii całkowitej w kWh,
- licznik wody całkowitej w m³,
- licznik gazu całkowitego w m³,
- subliczniki rosnące od początku pracy licznika.

Integracja **nie wymaga**, aby encje same liczyły dzień / tydzień / miesiąc / rok — robi to we własnym silniku na podstawie snapshotów.

## Instalacja ręczna

Skopiuj katalog:

```text
custom_components/auto_reports
```

Do:

```text
/config/custom_components/auto_reports
```

Następnie:

1. zrestartuj Home Assistant,
2. przejdź do **Ustawienia → Urządzenia i usługi → Dodaj integrację**,
3. wyszukaj **Automatyzacja raportów**,
4. skonfiguruj podstawowe ustawienia,
5. wejdź w **Opcje** integracji,
6. dodaj źródła,
7. dodaj odbiorców `notify.*`.

## Konfiguracja początkowa

Podczas pierwszej konfiguracji ustawiasz:

- nazwę integracji,
- katalog CSV,
- retencję plików CSV,
- **interwał odświeżania źródeł**,
- godzinę raportu dziennego,
- godzinę raportu tygodniowego,
- godzinę raportu miesięcznego,
- godzinę raportu rocznego.

Domyślne wartości:

- interwał odświeżania: `10 min`,
- dzienny: `00:05:00`,
- tygodniowy: `00:10:00`,
- miesięczny: `00:15:00`,
- roczny: `00:20:00`.

## Dodawanie źródeł danych

Każde źródło ma pola:

- **Nazwa**
- **Encja źródłowa**
- **Medium**
  - energia
  - woda
  - gaz
  - inne
- **Rola**
  - zużycie
  - produkcja
  - import
  - eksport
  - informacyjne
- **Jednostka** (opcjonalnie)
- **Cena jednostkowa**
- **Uwzględniaj w raporcie zbiorczym**
- **Aktywne**
- **Próg anomalii**

## Archiwum CSV i podgląd bazy

Integracja dalej zapisuje raporty do CSV, np.:

```text
/config/auto_reports/reports_2026.csv
```

Dodatkowo pojawia się nowy sensor:

- **Podgląd bazy danych**

W jego atrybutach są m.in.:

- `store_key`,
- `last_scan`,
- `scan_interval_minutes`,
- `csv_directory`,
- `sources_count`,
- `issues_count`,
- `snapshots_count`,
- `last_reports`,
- `recent_csv_files`.

## Sensory tworzone przez integrację

Integracja tworzy teraz:

### Sensory główne

- **Status raportów**
- **Podgląd bazy danych**
- **Raport dzienny**
- **Raport tygodniowy**
- **Raport miesięczny**
- **Raport roczny**

### Sensory dynamiczne dla każdego źródła

Dla każdego dodanego źródła powstają 3 encje:

- **`<nazwa źródła> obecny odczyt`**
- **`<nazwa źródła> poprzedni odczyt`**
- **`<nazwa źródła> status źródła`**

Sensor statusu źródła zawiera atrybuty:

- `current_value`
- `previous_value`
- `last_valid_value`
- `raw_state`
- `valid`
- `issue`
- `error_origin`
- `error_at`
- `last_scan`
- `day_start`, `day_current`, `day_delta`
- `week_start`, `week_current`, `week_delta`
- `month_start`, `month_current`, `month_delta`
- `year_start`, `year_current`, `year_delta`
- `periods`

## Wykrywanie problemów danych

Integracja oznacza źródło jako problematyczne, gdy:

- encja nie istnieje,
- stan to `unknown`,
- stan to `unavailable`,
- licznik się cofnął,
- przekroczony został próg anomalii.

W takiej sytuacji:

- raport nadal jest generowany,
- w raporcie pojawia się ostrzeżenie,
- szczegóły problemu zapisują się w atrybutach sensora i CSV,
- sensor statusu źródła pokazuje opis problemu i jego pochodzenie.

## Usługi integracji

### `auto_reports.generate_report`

Ręcznie generuje raport.

Przykład:

```yaml
service: auto_reports.generate_report
data:
  period: month
```

Dostępne okresy:

- `day`
- `week`
- `month`
- `year`

### `auto_reports.reset_snapshots`

Ustawia bieżące stany liczników jako nowy punkt startowy dla wszystkich okresów.

Przykład:

```yaml
service: auto_reports.reset_snapshots
```

## Ograniczenia tej wersji

- dynamiczne encje są tworzone na podstawie aktualnej listy źródeł po przeładowaniu integracji,
- brak edycji istniejącego źródła z poziomu UI — w tej wersji usuń i dodaj je ponownie,
- brak osobnego modelu odkupu energii,
- brak eksportu PDF,
- brak osobnych uprawnień per odbiorca.

## Autor

**sza86**


## Nowości 0.3.4

- Dynamiczna encja **ostatni odczyt z bazy** zamiast poprzedniego odczytu.
- Edycja nazwy i parametrów źródła w opcjach integracji.
- Nowa usługa `auto_reports.reset_source_history` do resetu historii pojedynczego źródła.
