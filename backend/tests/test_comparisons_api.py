from pathlib import Path

from fastapi.testclient import TestClient

FIXTURES = Path(__file__).resolve().parents[2] / 'fixtures'


def _upload(client: TestClient, path: Path) -> dict:
    with path.open('rb') as handle:
        response = client.post(
            '/api/files',
            files={'file': (path.name, handle, 'text/csv')},
        )
    assert response.status_code == 201, response.text
    return response.json()


def test_import_and_compare_fixtures(client: TestClient) -> None:
    budget = _upload(client, FIXTURES / 'budget-january.csv')
    bank = _upload(client, FIXTURES / 'bank-january.csv')

    profiles = client.get('/api/profiles').json()
    budget_profile = next(item for item in profiles if item['name'] == 'Budżet domowy')

    imported_budget = client.post(
        f'/api/files/{budget["id"]}/import',
        json={'profile_id': budget_profile['id']},
    )
    assert imported_budget.status_code == 200, imported_budget.text
    assert imported_budget.json()['file']['status'] == 'imported'
    assert imported_budget.json()['file']['row_count'] == 4

    imported_bank = client.post(
        f'/api/files/{bank["id"]}/import',
        json={
            'config': {
                'delimiter': ',',
                'encoding': 'utf-8',
                'has_header': True,
                'skip_rows': 0,
                'decimal_separator': '.',
                'thousand_separator': '',
                'date_format': '%Y-%m-%d',
                'amount_mode': 'signed',
                'column_mapping': {
                    'booking_date': 'Data operacji',
                    'amount': 'Kwota',
                    'description': 'Tytuł',
                },
            }
        },
    )
    assert imported_bank.status_code == 200, imported_bank.text
    assert imported_bank.json()['file']['row_count'] == 4

    compared = client.post(
        '/api/comparisons',
        json={'file_a_id': budget['id'], 'file_b_id': bank['id'], 'date_tolerance_days': 7},
    )
    assert compared.status_code == 201, compared.text
    summary = compared.json()['summary']
    assert summary == {
        'exact': 2,
        'probable': 1,
        'unmatched_a': 1,
        'unmatched_b': 1,
        'total_a': 4,
        'total_b': 4,
    }

    matches = client.get(f'/api/comparisons/{compared.json()["id"]}/matches').json()
    probable = next(item for item in matches if item['kind'] == 'probable')
    assert probable['date_delta_days'] == 2
    assert probable['amount'] == '45.00'

    unmatched_a = next(item for item in matches if item['kind'] == 'unmatched_a')
    unmatched_b = next(item for item in matches if item['kind'] == 'unmatched_b')
    assert unmatched_a['amount'] == '15.00'
    assert unmatched_b['amount'] == '89.00'

    deleted = client.delete(f'/api/files/{budget["id"]}')
    assert deleted.status_code == 204
    assert client.get(f'/api/files/{budget["id"]}').status_code == 404
    assert client.get(f'/api/comparisons/{compared.json()["id"]}').status_code == 404
