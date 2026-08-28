# Kosztomator — specyfikacja produktu i architektury

Aplikacja prywatna do porównywania dwóch zestawień CSV (historia bankowa vs budżet domowy) i znajdowania brakujących wpisów.

Język interfejsu: **polski**.
Język kodu, komentarzy i commitów: **angielski**.

---

## 1. Problem i cel

Użytkownik spisuje wydatki w budżecie domowym. Część transakcji kartą wypada z listy. Ręczne porównanie historii bankowej z budżetem jest żmudne.

Kosztomator:

1. Przechowuje wgrane pliki CSV.
2. Normalizuje wiersze z różnych źródeł do wspólnego modelu (`data`, `kwota`, opcjonalny `opis`).
3. Na żądanie porównuje dowolne dwa pliki i pokazuje:
   - **100%** — ta sama kwota i ta sama data,
   - **80%** — ta sama kwota, inna data (w oknie tolerancji),
   - **brak dopasowania** — wpis tylko w jednym pliku.

---

## 2. Decyzje architektoniczne (zablokowane)

| Temat | Decyzja | Uzasadnienie |
|---|---|---|
| Frontend | Angular (standalone, signals, `inject()`) | Wymaganie użytkownika |
| Backend | FastAPI + Pydantic v2 + Uvicorn | REST, typowanie, szybki start |
| ORM / migracje | SQLAlchemy 2.0 + Alembic | Relacyjny model, ewolucja schematu |
| Baza | **SQLite** (`data/kosztomator.db`) | Darmowa, plikowa, zeroops, wystarczy do użytku prywatnego |
| Pliki CSV | Dysk: `data/uploads/{file_id}/{original_name}` + metadane w SQLite | Proste, łatwy backup całego katalogu `data/` |
| Kwoty | `Decimal` (Python) / `NUMERIC` (SQLite) + normalizacja do 2 miejsc | Unikamy błędów `float` |
| Auth | Brak w v1 | Aplikacja lokalna, jeden użytkownik |
| Monorepo | `backend/` + `frontend/` | Jeden repo, dwa procesy deweloperskie |
| UI | Angular Material 3 + własne tokeny CSS (ciemny motyw domyślny) | Nowoczesny, spójny, dostępny |
| HTTP | REST JSON, CORS tylko na localhost | Zgodnie z wymaganiem |

Nie używać: PostgreSQL, Docker (opcjonalnie później), auth, chmury, kolejek, WebSocket.

---

## 3. Słownik

- **Source file** — wgrany CSV + metadane (nazwa, źródło, status importu).
- **Source profile** — wielokrotnego użytku mapa kolumn i reguł parsowania dla danego banku/aplikacji.
- **Transaction** — znormalizowany wiersz: `booking_date`, `amount`, `description`, `raw_payload`.
- **Comparison** — wynik porównania dwóch plików (snapshot, nie live).
- **Match 100** — para 1:1, identyczna data i kwota.
- **Match 80** — para 1:1, identyczna kwota, daty różne, różnica ≤ `date_tolerance_days`.
- **Unmatched** — wiersz bez pary po obu fazach.

Strony porównania nazywamy **A** (lewy plik) i **B** (prawy plik). Semantyka „bank vs budżet” nie jest wymuszana — użytkownik wybiera dowolne dwa pliki.

---

## 4. Model danych (SQLite)

### 4.1 `source_profiles`

Wielokrotnego użytku szablony importu.

| Kolumna | Typ | Uwagi |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT UNIQUE | np. `mBank karta`, `Budżet domowy` |
| `delimiter` | TEXT | `,` / `;` / `\t` |
| `encoding` | TEXT | domyślnie `utf-8-sig` |
| `has_header` | BOOLEAN | |
| `skip_rows` | INTEGER | wiersze przed nagłówkiem, domyślnie 0 |
| `decimal_separator` | TEXT | `,` albo `.` |
| `thousand_separator` | TEXT | ` ` / `.` / `''` |
| `date_format` | TEXT | np. `%d.%m.%Y`, `%Y-%m-%d` |
| `amount_mode` | TEXT | `signed` \| `absolute` — jak zapisać kwotę po imporcie |
| `column_mapping` | JSON | patrz 4.2 |
| `created_at` | DATETIME | |
| `updated_at` | DATETIME | |

### 4.2 `column_mapping` (JSON)

Kanoniczne pola aplikacji → nazwa kolumny w CSV (po nagłówku) albo indeks `0-based` gdy brak nagłówka.

```json
{
  "booking_date": "Data operacji",
  "amount": "Kwota",
  "description": "Tytuł"
}
```

Wymagane: `booking_date`, `amount`.
Opcjonalne: `description`.
Inne kolumny trafiają w całości do `raw_payload` i nie biorą udziału w matchowaniu.

Opcjonalne rozszerzenia mapowania (v1, jeśli kolumna istnieje):

```json
{
  "booking_date": "Data transakcji",
  "amount": "Kwota",
  "description": "Opis",
  "amount_debit": "Obciążenia",
  "amount_credit": "Uznania"
}
```

Jeśli podano `amount_debit` / `amount_credit` zamiast `amount`: `amount = credit - debit` (oba znormalizowane).

### 4.3 `source_files`

| Kolumna | Typ | Uwagi |
|---|---|---|
| `id` | INTEGER PK | |
| `display_name` | TEXT | edytowalna nazwa w UI |
| `original_filename` | TEXT | |
| `stored_path` | TEXT | relatywna do katalogu danych |
| `byte_size` | INTEGER | |
| `checksum_sha256` | TEXT | detekcja duplikatu tego samego pliku |
| `profile_id` | INTEGER FK NULL | ustawiane przy imporcie |
| `status` | TEXT | `uploaded` \| `mapped` \| `imported` \| `failed` |
| `row_count` | INTEGER | po udanym imporcie |
| `error_message` | TEXT NULL | |
| `uploaded_at` | DATETIME | |
| `imported_at` | DATETIME NULL | |

Usunięcie pliku: soft-delete nie jest wymagane. Kasować kaskadowo: plik na dysku + wiersze `transactions` + porównania, w których plik brał udział.

### 4.4 `transactions`

| Kolumna | Typ | Uwagi |
|---|---|---|
| `id` | INTEGER PK | |
| `source_file_id` | INTEGER FK | ON DELETE CASCADE |
| `row_index` | INTEGER | 0-based w pliku źródłowym (po skip_rows) |
| `booking_date` | DATE | |
| `amount` | NUMERIC(14,2) | zawsze 2 miejsca; znak zgodny z `amount_mode` profilu |
| `amount_abs` | NUMERIC(14,2) | `abs(amount)` — kolumna używana do matchowania |
| `description` | TEXT NULL | |
| `raw_payload` | JSON | oryginalny wiersz jako obiekt |

Indeksy: `(source_file_id)`, `(source_file_id, amount_abs, booking_date)`.

### 4.5 `comparisons`

| Kolumna | Typ | Uwagi |
|---|---|---|
| `id` | INTEGER PK | |
| `file_a_id` | INTEGER FK | |
| `file_b_id` | INTEGER FK | |
| `date_tolerance_days` | INTEGER | domyślnie 7 |
| `created_at` | DATETIME | |

Wynik jest snapshotem: ponowne porównanie tych samych plików tworzy nowy rekord (stary można nadpisać tylko jeśli użytkownik uruchomi porównanie ponownie z tego samego ekranu — wtedy usunąć poprzedni wynik tej pary i zapisać nowy). **Reguła v1:** jedna aktywna para `(file_a_id, file_b_id)` — upsert.

### 4.6 `comparison_matches`

| Kolumna | Typ | Uwagi |
|---|---|---|
| `id` | INTEGER PK | |
| `comparison_id` | INTEGER FK | ON DELETE CASCADE |
| `kind` | TEXT | `exact` \| `probable` \| `unmatched_a` \| `unmatched_b` |
| `confidence` | INTEGER | `100` / `80` / `0` |
| `transaction_a_id` | INTEGER FK NULL | |
| `transaction_b_id` | INTEGER FK NULL | |
| `date_delta_days` | INTEGER NULL | `abs(date_a - date_b)` dla par |
| `amount` | NUMERIC(14,2) | `amount_abs` pary albo pojedynczego wpisu |

Dla `unmatched_*` jedna ze stron jest NULL.

---

## 5. Algorytm porównania (normatywny)

Wejście: zbiór transakcji pliku A, zbiór transakcji pliku B, `date_tolerance_days` (domyślnie 7).

Matchowanie jest **1:1**. Jeden wiersz może wejść do co najwyżej jednej pary.

Kwota do porównania: **`amount_abs`** (wartość bezwzględna). Dzięki temu `-45,00` z banku zgadza się z `45,00` z budżetu.

Data do porównania: sama data (`DATE`), bez czasu.

### Faza 1 — 100% (kwota + data)

1. Zbuduj multimapę A: klucz `(amount_abs, booking_date)` → kolejka id (stabilna: sortuj po `row_index`).
2. Iteruj B w kolejności `row_index`.
3. Jeśli w A jest wolny wiersz o tym samym kluczu — zdejmij go i zapisz `kind=exact`, `confidence=100`, `date_delta_days=0`.
4. Wiersze bez pary zostają w puli.

### Faza 2 — 80% (ta sama kwota, inna data)

Na pozostałych wierszach:

1. Zbuduj grupy po `amount_abs`.
2. Dla każdej kwoty, której są niesparowane wiersze w A **i** w B:
   - policz wszystkie pary `(a, b)` gdzie `abs(date_a - date_b) <= date_tolerance_days` **oraz** daty są różne (pary z tą samą datą już nie istnieją po fazie 1, ale warunek zostaw jako strażnik),
   - posortuj kandydatów: `date_delta_days ASC`, potem `row_index_a`, potem `row_index_b`,
   - zachłannie bierz pierwszą parę, której obie strony są jeszcze wolne → `kind=probable`, `confidence=80`.
3. Pary poza oknem tolerancji **nie** są 80%. Trafiają do unmatched.

### Faza 3 — unmatched

Każdy pozostały wiersz A → `unmatched_a` (`confidence=0`).
Każdy pozostały wiersz B → `unmatched_b` (`confidence=0`).

### Przykład

```
A: 15.01 45.00 | 16.01 120.00 | 20.01 45.00 | 01.02 15.00
B: 15.01 45.00 | 16.01 120.00 | 22.01 45.00 | 10.02 89.00
tolerance = 7

Faza 1: (15.01, 45) i (16.01, 120)
Faza 2: (20.01, 45) ↔ (22.01, 45)  delta=2  → 80%
Unmatched A: 15.00
Unmatched B: 89.00
```

### Duplikaty tego samego dnia

```
A: 15.01 50 | 15.01 50
B: 15.01 50 | 16.01 50

Faza 1: jedna para 15.01/50
Faza 2: druga 50 z A (15.01) ↔ 50 z B (16.01) → 80%
```

Algorytm musi być **deterministyczny** (te same pliki + ta sama tolerancja = ten sam wynik). Pokryć testami jednostkowymi powyższe przypadki oraz: puste pliki, wszystkie unmatched, wszystkie exact, brak kandydatów 80% bo delta > tolerance.

---

## 6. Import CSV

### 6.1 Upload

`POST /api/files` (multipart). Zapis na dysk, status `uploaded`. Jeśli `checksum_sha256` już istnieje — **nie blokować** (użytkownik może wgrać ten sam eksport dwa razy pod inną nazwą), ale pokazać ostrzeżenie w odpowiedzi (`duplicate_of_file_id`).

### 6.2 Podgląd

`GET /api/files/{id}/preview?encoding=&delimiter=&skip_rows=&has_header=`

Backend:

1. Wykrywa encoding (`charset-normalizer`), delimiter (`csv.Sniffer` + heurystyka `;` vs `,` — w PL częstszy `;`).
2. Zwraca max 30 wierszy, listę nagłówków, wykryte wartości i liczbę wierszy.

Użytkownik może nadpisać encoding/delimiter/skip w UI; preview liczy się ponownie.

### 6.3 Mapowanie i import

`POST /api/files/{id}/import`

Body: `profile_id` **albo** inline config (te same pola co profil) + opcjonalnie `save_as_profile: { name }`.

Walidacja każdego wiersza:

- data musi dać się sparsować `date_format`,
- kwota po usunięciu separatora tysięcy i zamianie separatora dziesiętnego musi być liczbą,
- puste wiersze pomijane,
- wiersz z błędem: zbierany do listy; jeśli błędów > 0 — status `failed`, nic nie commituj (transakcja DB). Lepsze UX: zwrócić pierwsze 20 błędów z numerem wiersza.

Po sukcesie: status `imported`, `row_count`, `imported_at`. Ponowny import tego samego pliku **kasuje stare transakcje** i wstawia nowe.

### 6.4 Profile wbudowane (seed)

Nie zgadywać konkretnych banków na ślepo. Dodać 2–3 przykładowe profile jako seed, łatwe do edycji:

1. `Uniwersalny (nagłówek: date, amount, description)` — CSV z kolumnami angielskimi.
2. `Polski bank (średnik, przecinek dziesiętny)` — typowe `Data;Kwota;Opis`.
3. `Budżet domowy` — ten sam kształt, inna nazwa, żeby UI pokazał ideę wielu źródeł.

Użytkownik tworzy własne profile przy pierwszym imporcie z realnego banku.

---

## 7. Kontrakt REST

Prefix: `/api`. JSON, błędy w kształcie:

```json
{ "detail": "Human readable message", "code": "FILE_NOT_IMPORTED" }
```

Kody HTTP: 400 walidacja, 404 brak zasobu, 409 konflikt (porównanie pliku niezaimportowanego), 413 plik > 10 MB, 500 nieoczekiwany.

### Pliki

| Metoda | Ścieżka | Opis |
|---|---|---|
| `GET` | `/api/files` | Lista: id, nazwa, status, row_count, uploaded_at, profile |
| `POST` | `/api/files` | Upload multipart pole `file` |
| `GET` | `/api/files/{id}` | Szczegóły + statystyki |
| `PATCH` | `/api/files/{id}` | `{ display_name }` |
| `DELETE` | `/api/files/{id}` | Plik + transakcje + porównania tej pary |
| `GET` | `/api/files/{id}/preview` | Podgląd / detekcja |
| `POST` | `/api/files/{id}/import` | Mapowanie + import |
| `GET` | `/api/files/{id}/transactions` | Paginacja (`offset`, `limit`, `q` po opisie) |

### Profile

| Metoda | Ścieżka | Opis |
|---|---|---|
| `GET` | `/api/profiles` | Lista |
| `POST` | `/api/profiles` | Utwórz |
| `GET` | `/api/profiles/{id}` | |
| `PUT` | `/api/profiles/{id}` | |
| `DELETE` | `/api/profiles/{id}` | 409 jeśli plik go używa — wtedy tylko odpinamy FK, profil można skasować |

### Porównania

| Metoda | Ścieżka | Opis |
|---|---|---|
| `POST` | `/api/comparisons` | `{ file_a_id, file_b_id, date_tolerance_days? }` → liczy i zapisuje |
| `GET` | `/api/comparisons` | Historia |
| `GET` | `/api/comparisons/{id}` | Podsumowanie + grupy (lub osobne endpointy poniżej) |
| `GET` | `/api/comparisons/{id}/matches?kind=` | Filtrowane wiersze wyniku |
| `DELETE` | `/api/comparisons/{id}` | |

Odpowiedź `POST /api/comparisons` i `GET /api/comparisons/{id}`:

```json
{
  "id": 1,
  "file_a": { "id": 1, "display_name": "mbank-styczen.csv" },
  "file_b": { "id": 2, "display_name": "budzet-styczen.csv" },
  "date_tolerance_days": 7,
  "created_at": "2026-08-28T07:00:00Z",
  "summary": {
    "exact": 12,
    "probable": 3,
    "unmatched_a": 4,
    "unmatched_b": 2,
    "total_a": 19,
    "total_b": 17
  }
}
```

Wiersz matcha (lista):

```json
{
  "id": 10,
  "kind": "probable",
  "confidence": 80,
  "date_delta_days": 2,
  "amount": "45.00",
  "a": { "id": 101, "booking_date": "2026-01-20", "amount": "45.00", "description": "Biedronka" },
  "b": { "id": 204, "booking_date": "2026-01-22", "amount": "-45.00", "description": "SKLEP" }
}
```

Oba pliki muszą mieć `status=imported`. Nie można porównać pliku z samym sobą.

---

## 8. Frontend — IA i ekrany

Routing (standalone):

| Ścieżka | Ekran |
|---|---|
| `/` | Dashboard: ostatnie pliki, ostatnie porównania, CTA „Wgraj plik” / „Porównaj” |
| `/files` | Lista plików (karty lub tabela) + upload dropzone |
| `/files/:id` | Szczegóły pliku: status, mapowanie jeśli nie imported, tabela transakcji |
| `/profiles` | Lista / edycja profili źródeł |
| `/compare` | Wybór dwóch plików + tolerancja daty + uruchomienie |
| `/compare/:id` | Wynik porównania |

### 8.1 Upload i mapowanie (kluczowy flow)

1. Dropzone na `/files` (drag & drop + przycisk). Akceptuj `.csv` i `.txt`.
2. Po uploadzie przekieruj na `/files/:id`.
3. Jeśli `uploaded`: wizard 3 kroki
   - **Źródło** — wybierz istniejący profil albo „nowy”.
   - **Podgląd** — encoding, separator, skip rows; tabela 30 wierszy; selecty mapujące kolumny na `Data`, `Kwota`, `Opis`.
   - **Import** — podsumowanie, liczba wierszy, błędy.
4. Jeśli `imported`: tabela transakcji + przycisk „Importuj ponownie” (wraca do wizarda) oraz „Usuń”.

### 8.2 Wynik porównania

Nowoczesny, czytelny layout:

- Pasek podsumowania: 4 metryki (100%, 80%, tylko A, tylko B) jako karty z kolorem.
- Tabulator / segmented control: `Dopasowane 100%` | `Prawdopodobne 80%` | `Tylko plik A` | `Tylko plik B`.
- Wiersz 100%/80%: dwie kolumny (A | B), kwota wyeksponowana, daty, opisy, dla 80% badge z `Δ N dni`.
- Unmatched: jedna kolumna + komunikat „Brak odpowiednika w drugim pliku”.
- Filtr kwoty i wyszukiwarka opisu.
- Przycisk „Porównaj ponownie” (ta sama para, aktualna tolerancja).

Nie implementować w v1: ręcznego potwierdzania 80%, eksportu PDF, edycji pojedynczych transakcji.

### 8.3 UX / UI (wiążące)

- Domyślny motyw ciemny, akcent teal/emerald (finanse, spokój, nie bankowy granat).
- Typografia: czytelna sans (np. DM Sans / Inter przez Google Fonts).
- Kwoty: `pl-PL` (`45,00 zł` w UI; w API zawsze `"45.00"`).
- Daty w UI: `dd.MM.yyyy`.
- Puste stany z krótką instrukcją, nie suche „brak danych”.
- Potwierdzenie przed usunięciem pliku.
- Skeleton / spinner przy imporcie i porównaniu.
- Responsywność: desktop first, używalne od ~768px (to narzędzie biurkowe).
- A11y: focus visible, labele, `role="status"` na wynikach, nie polegaj tylko na kolorze (badge z procentem + tekstem).

Komponenty: standalone, OnPush, signals, `trackBy` na listach.

---

## 9. Struktura repozytorium

```
kosztomator/
  AGENTS.md
  SPEC.md
  README.md
  .gitignore
  backend/
    pyproject.toml          # lub requirements.txt + requirements-dev.txt
    alembic.ini
    alembic/
    app/
      main.py               # FastAPI, CORS, routery
      config.py             # ścieżka data/, max upload
      db.py
      models/
      schemas/
      routers/
        files.py
        profiles.py
        comparisons.py
      services/
        csv_import.py
        matching.py
        storage.py
      seed.py
    tests/
      test_matching.py
      test_csv_import.py
      test_comparisons_api.py
    data/                   # gitignored; db + uploads
  frontend/
    (Angular CLI, standalone, SCSS)
    src/app/
      core/                 # api services, models
      features/
        dashboard/
        files/
        profiles/
        compare/
      shared/               # dropzone, money pipe, empty state
```

Skrypty deweloperskie opisać w `README.md`:

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend && npm install && ng serve --port 4200
```

Proxy Angular: `/api` → `http://127.0.0.1:8000`.

---

## 10. Stos wersji (orientacyjnie, bieżące stabilne)

- Python 3.12+
- FastAPI 0.115+
- SQLAlchemy 2.0
- Alembic
- Pydantic v2
- pytest + httpx
- Angular 19+ (standalone default)
- Angular Material 3
- TypeScript strict

---

## 11. Zakres v1 / poza zakresem

**v1 (zrobić):**

- CRUD plików i profili
- Upload + preview + mapowanie + import
- Porównanie 100 / 80 / unmatched
- Dashboard, lista, wynik
- Testy algorytmu matchowania i importu CSV
- README po polsku: jak uruchomić lokalnie

**Poza v1:**

- Logowanie, multi-user
- Automatyczne rozpoznawanie banku z zawartości
- Fuzzy match po opisie
- Ręczna korekta par w UI
- Eksport wyniku
- Parsowanie XLS/PDF
- Docker / deploy

---

## 12. Kryteria akceptacji

1. Można wgrać dwa różne CSV, zmapować kolumny (różne nagłówki) i zaimportować.
2. Można usunąć plik — znika z listy, z dysku i z porównań.
3. Porównanie tych samych danych zawsze daje ten sam podział na 100 / 80 / unmatched.
4. Identyczna kwota i data → 100%, wiersze znikają z puli.
5. Identyczna kwota, data w oknie tolerancji → 80%, poza oknem → unmatched.
6. Wpis tylko w jednym pliku jest widoczny jako brakujący.
7. UI po polsku, ciemny, zrozumiały bez dokumentacji.
8. API nie wymaga auth; wszystko działa na localhost.

---

## 13. Zasady implementacji

- Backend: type hints wszędzie, żadnego `float` dla pieniędzy, `Decimal`.
- Brak `SELECT *` logiki w serwisach — jawne schematy Pydantic.
- Matching w czystej funkcji (`match_transactions(...)`) niezależnej od FastAPI — łatwe testy.
- Frontend: zero `any`, signals zamiast ręcznego subscribe w szablonach, `async` pipe gdy Observable jest konieczny.
- Nie dodawać bibliotek „na zapas”.
- Nie commitować `data/`, `.venv`, `node_modules`, sekretów.
- Komentarze tylko tam, gdzie algorytm nie jest oczywisty (głównie matching i normalizacja kwoty).
