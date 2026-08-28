from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SourceProfile

SEED_PROFILES = [
    {
        'name': 'Uniwersalny (nagłówek: date, amount, description)',
        'delimiter': ',',
        'encoding': 'utf-8-sig',
        'has_header': True,
        'skip_rows': 0,
        'decimal_separator': '.',
        'thousand_separator': '',
        'date_format': '%Y-%m-%d',
        'amount_mode': 'signed',
        'column_mapping': {
            'booking_date': 'date',
            'amount': 'amount',
            'description': 'description',
        },
    },
    {
        'name': 'Polski bank (średnik, przecinek dziesiętny)',
        'delimiter': ';',
        'encoding': 'utf-8-sig',
        'has_header': True,
        'skip_rows': 0,
        'decimal_separator': ',',
        'thousand_separator': ' ',
        'date_format': '%d.%m.%Y',
        'amount_mode': 'signed',
        'column_mapping': {
            'booking_date': 'Data',
            'amount': 'Kwota',
            'description': 'Opis',
        },
    },
    {
        'name': 'Budżet domowy',
        'delimiter': ';',
        'encoding': 'utf-8-sig',
        'has_header': True,
        'skip_rows': 0,
        'decimal_separator': ',',
        'thousand_separator': ' ',
        'date_format': '%d.%m.%Y',
        'amount_mode': 'absolute',
        'column_mapping': {
            'booking_date': 'Data',
            'amount': 'Kwota',
            'description': 'Opis',
        },
    },
]


def seed_profiles(session: Session) -> None:
    existing = set(session.scalars(select(SourceProfile.name)).all())
    for payload in SEED_PROFILES:
        if payload['name'] in existing:
            continue
        session.add(SourceProfile(**payload))
    session.commit()
