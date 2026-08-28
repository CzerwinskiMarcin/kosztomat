from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

TWOPLACES = Decimal('0.01')


def normalize_amount(
    raw: str,
    *,
    decimal_separator: str = ',',
    thousand_separator: str = ' ',
) -> Decimal:
    value = raw.strip()
    if not value:
        raise ValueError('empty amount')

    if thousand_separator:
        value = value.replace(thousand_separator, '')
    # Some exports use a non-breaking space as a thousand separator.
    value = value.replace('\u00a0', '')
    value = value.replace(' ', '')

    if decimal_separator and decimal_separator != '.':
        value = value.replace(decimal_separator, '.')

    # Residual thousands dots when decimal is already a dot, e.g. 1.234.56
    if value.count('.') > 1:
        parts = value.split('.')
        value = ''.join(parts[:-1]) + '.' + parts[-1]

    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f'invalid amount: {raw}') from exc

    return amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
