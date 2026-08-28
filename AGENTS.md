# Instrukcje dla agenta implementującego Kosztomator

Ten plik jest kontraktem wykonawczym. Specyfikacja normatywna: [`SPEC.md`](SPEC.md). W razie konfliktu wygrywa `SPEC.md`, a ten plik mówi **w jakiej kolejności** i **jak** budować.

## Cel sesji implementacyjnej

Dostarczyć działającą aplikację lokalną (Angular + FastAPI + SQLite), która:

- wgrywa i usuwa pliki CSV,
- mapuje różne układy kolumn przez profile źródeł,
- porównuje dwa zaimportowane pliki algorytmem 100% / 80% / unmatched.

Nie wychodzić poza v1 z `SPEC.md` §11.

## Zasady

1. Czytaj `SPEC.md` zanim dodasz endpoint, tabelę albo ekran.
2. Najpierw backend (model → serwis matchowania z testami → API), potem frontend.
3. Nie zgaduj layoutu CSV banków. Detekcja + ręczna mapa kolumn + seed 3 profili.
4. Kwoty wyłącznie jako `Decimal` / string dziesiętny. Żadnego `float`.
5. Język UI: polski. Identyfikatory w kodzie: angielski.
6. Nie commituj, dopóki użytkownik o to nie poprosi.
7. Po zmianach UI zweryfikuj flow w przeglądarce (upload → mapowanie → import → porównanie → wynik → usunięcie).
8. Nie dodawaj auth, Dockera, fuzzy-match po opisie, eksportu PDF.

## Kolejność implementacji (obowiązkowa)

### Faza 0 — szkielet

- `backend/`: FastAPI, SQLAlchemy 2, Alembic, CORS, `data/` gitignored.
- `frontend/`: `ng new` standalone + routing + SCSS + Angular Material, proxy `/api`.
- `README.md` z komendami uruchomienia.
- `.gitignore` (`.venv`, `node_modules`, `data/`, `dist/`, `__pycache__/`).

### Faza 1 — persistencja

- Tabele i modele zgodnie z `SPEC.md` §4.
- Migracja początkowa Alembic.
- Seed 3 profili (`SPEC.md` §6.4).

### Faza 2 — matching (zanim API porównania)

- Czysta funkcja `match_transactions` + testy z `SPEC.md` §5 (przykład główny, duplikaty, puste zbiory, delta > tolerance).
- Dopiero potem router porównań.

### Faza 3 — import CSV

- Upload na dysk, checksum, preview z detekcją encoding/delimiter.
- Import transakcyjny (rollback przy błędach wierszy).
- Testy normalizacji kwoty: `1 234,56`, `-45.00`, kolumny debit/credit.

### Faza 4 — REST

- Endpointy z `SPEC.md` §7. Kontrakt JSON 1:1.
- Testy API: import + porównanie na `fixtures/budget-january.csv` i `fixtures/bank-january.csv` (oczekiwany wynik: 2×100%, 1×80% Δ2 dni, 1 unmatched A `15.00`, 1 unmatched B `89.00`).

### Faza 5 — UI

- Shell: nawigacja, ciemny motyw, tokeny z `SPEC.md` §8.3.
- `/files` dropzone, wizard mapowania, tabela transakcji, usuwanie.
- `/compare` wybór dwóch plików + wynik z 4 grupami.
- Dashboard jako skrót do tych dwóch flow.

### Faza 6 — twarde kryteria

Odznacz dopiero po ręcznym sprawdzeniu `SPEC.md` §12.

## Wzorce kodu

**Backend**

- Serwisy bez zależności od Request/Response.
- Pydantic v2 schemas w `app/schemas`.
- Błędy: `HTTPException` + `code` w `detail` obiektowym zgodnie ze spec.
- Limit uploadu 10 MB.

**Frontend**

- Standalone, signals, `inject()`, OnPush.
- Jedna klasa API na zasób (`FilesApi`, `ProfilesApi`, `ComparisonsApi`).
- Pipe `pln` / formatter `pl-PL` do kwot.
- `trackBy` na listach matchy i transakcji.

## Definition of done

- `pytest` przechodzi (matching + import + przynajmniej jeden test porównania E2E API).
- `ng build` przechodzi.
- README pozwala uruchomić oba procesy od zera.
- Da się na świeżej bazie: wgrać 2 CSV, zmapować, porównać, zobaczyć 100/80/unmatched, usunąć plik.
