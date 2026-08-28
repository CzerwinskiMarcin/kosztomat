from decimal import Decimal

from app.services.amounts import normalize_amount
from app.services.csv_import import parse_transactions


def test_normalize_polish_thousands_and_comma() -> None:
    assert normalize_amount('1 234,56', decimal_separator=',', thousand_separator=' ') == Decimal(
        '1234.56'
    )


def test_normalize_signed_dot() -> None:
    assert normalize_amount('-45.00', decimal_separator='.', thousand_separator='') == Decimal(
        '-45.00'
    )


def test_normalize_debit_credit_columns() -> None:
    csv_bytes = (
        'Data;Obciążenia;Uznania;Opis\n'
        '15.01.2026;45,00;;Sklep\n'
        '16.01.2026;;120,00;Zwrot\n'
    ).encode('utf-8')

    parsed, errors = parse_transactions(
        csv_bytes,
        encoding='utf-8',
        delimiter=';',
        has_header=True,
        skip_rows=0,
        decimal_separator=',',
        thousand_separator=' ',
        date_format='%d.%m.%Y',
        amount_mode='signed',
        column_mapping={
            'booking_date': 'Data',
            'amount_debit': 'Obciążenia',
            'amount_credit': 'Uznania',
            'description': 'Opis',
        },
    )

    assert errors == []
    assert len(parsed) == 2
    assert parsed[0].amount == Decimal('-45.00')
    assert parsed[1].amount == Decimal('120.00')


def test_parse_budget_fixture_shape() -> None:
    csv_bytes = (
        'Data;Kwota;Opis\n'
        '15.01.2026;45,00;Żabka\n'
        '16.01.2026;120,00;Lidl\n'
    ).encode('utf-8')
    parsed, errors = parse_transactions(
        csv_bytes,
        encoding='utf-8',
        delimiter=';',
        has_header=True,
        skip_rows=0,
        decimal_separator=',',
        thousand_separator=' ',
        date_format='%d.%m.%Y',
        amount_mode='absolute',
        column_mapping={'booking_date': 'Data', 'amount': 'Kwota', 'description': 'Opis'},
    )
    assert errors == []
    assert [row.amount for row in parsed] == [Decimal('45.00'), Decimal('120.00')]


def test_row_error_is_collected() -> None:
    csv_bytes = b'Data;Kwota;Opis\nnot-a-date;45,00;X\n'
    parsed, errors = parse_transactions(
        csv_bytes,
        encoding='utf-8',
        delimiter=';',
        has_header=True,
        skip_rows=0,
        decimal_separator=',',
        thousand_separator=' ',
        date_format='%d.%m.%Y',
        amount_mode='signed',
        column_mapping={'booking_date': 'Data', 'amount': 'Kwota', 'description': 'Opis'},
    )
    assert parsed == []
    assert len(errors) == 1
    assert errors[0].row_index == 0
