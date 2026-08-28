# Kosztomator

Prywatna aplikacja do porównywania dwóch zestawień CSV (historia bankowa i budżet domowy) i znajdowania brakujących wpisów.

## Stack

- Frontend: Angular (standalone, signals, Material 3)
- Backend: FastAPI
- Baza: SQLite (`backend/data/kosztomator.db`)

Porównanie: **100%** (kwota + data) → **80%** (ta sama kwota, data w oknie tolerancji) → **unmatched**.

## Uruchomienie lokalne

Wymagane: Python 3.12+ i Node.js 20+.

Jeśli `python3 -m venv` zgłasza brak `ensurepip`, utwórz środowisko bez pip i doinstaluj go:

```bash
python3 -m venv --without-pip .venv
.venv/bin/python /path/to/get-pip.py   # https://bootstrap.pypa.io/get-pip.py
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Tabele SQLite i 3 profile startowe powstają przy pierwszym starcie API (`backend/data/kosztomator.db`). Migracje Alembic są w `backend/alembic/` na późniejsze zmiany schematu.

API: `http://127.0.0.1:8000/api`

### Frontend

```bash
cd frontend
npm install
ng serve --port 4200
```

Aplikacja: `http://localhost:4200` (proxy `/api` → backend).

### Testy

```bash
cd backend
source .venv/bin/activate
pytest
```

## Dokumentacja

| Plik | Rola |
|---|---|
| [SPEC.md](SPEC.md) | Specyfikacja produktu, model danych, API, algorytm |
| [AGENTS.md](AGENTS.md) | Kolejność implementacji |
