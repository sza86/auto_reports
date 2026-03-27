# Automatyzacja raportów

Custom integration do Home Assistant do automatycznego generowania raportów dziennych, tygodniowych, miesięcznych i rocznych na podstawie **encji narastających**: liczników energii, wody, gazu i innych źródeł zużycia/produkcji.

## Najważniejsze funkcje

- raporty: dzień, tydzień, miesiąc, rok,
- archiwizacja raportów do CSV,
- koszt informacyjny na podstawie ceny jednostkowej,
- powiadomienia przez `notify.*`,
- dynamiczne encje diagnostyczne dla każdego źródła,
- wykrywanie problemów danych (`unknown`, `unavailable`, reset/cofnięcie licznika, anomalia),
- edycja źródeł z poziomu opcji integracji,
- reset historii pojedynczego źródła z poziomu UI i usługi.

## Dla jakich encji to działa

Integracja zakłada, że źródłowa encja zwraca **wartość narastającą od początku licznika**.

Przykłady poprawnych źródeł:

- całkowita energia pobrana w kWh,
- całkowite zużycie wody,
- całkowity licznik gazu,
- rosnące subliczniki.

Nie należy używać encji chwilowych ani encji, które same się okresowo zerują.

## Tworzone encje

### Główne

- `Status raportów`
- `Podgląd bazy danych`
- `Raport dzienny`
- `Raport tygodniowy`
- `Raport miesięczny`
- `Raport roczny`

### Dynamiczne dla każdego źródła

- `<nazwa źródła> obecny odczyt`
- `<nazwa źródła> ostatni odczyt z bazy`
- `<nazwa źródła> status źródła`

## Usługi

### `auto_reports.generate_report`
Ręczne wygenerowanie raportu dla wybranego okresu.

### `auto_reports.reset_snapshots`
Ustawienie bieżących wartości liczników jako nowego punktu startowego dla raportów.

### `auto_reports.reset_source_history`
Reset historii jednego źródła: usuwa zapamiętany ostatni poprawny odczyt i snapshoty tylko dla wskazanej encji.

## Konfiguracja w UI

Po dodaniu integracji dostępne są opcje:

- dodanie źródła,
- edycja źródła,
- usunięcie źródła,
- reset historii źródła,
- dodanie/usunięcie odbiorców `notify.*`,
- ustawienia harmonogramów i archiwizacji.

## Instalacja przez HACS

1. Dodaj repozytorium jako **Custom repository** typu **Integration**.
2. Zainstaluj integrację z HACS.
3. Zrestartuj Home Assistant.
4. Dodaj integrację z poziomu **Ustawienia → Urządzenia i usługi**.

## Instalacja ręczna

Skopiuj katalog:

```text
custom_components/auto_reports
```

Do:

```text
/config/custom_components/auto_reports
```

Następnie zrestartuj Home Assistant i dodaj integrację w UI.

## Przykład dashboardu

Przykładowy plik znajdziesz tutaj:

```text
examples/dashboard_example.yaml
```

## Struktura repo

```text
.
├── custom_components/
│   └── auto_reports/
│       ├── __init__.py
│       ├── config_flow.py
│       ├── const.py
│       ├── manifest.json
│       ├── report_manager.py
│       ├── sensor.py
│       ├── services.yaml
│       ├── strings.json
│       ├── translations/
│       └── brand/
├── examples/
├── .github/workflows/
├── CHANGELOG.md
├── LICENSE
├── README.md
└── hacs.json
```

## Publikacja na GitHub

Po wrzuceniu repozytorium na GitHub ustaw jeszcze ręcznie:

- opis repozytorium,
- tematy repozytorium (np. `home-assistant`, `hacs`, `integration`),
- włączone Issues,
- opcjonalnie Releases.

## Autor

**sza86**
