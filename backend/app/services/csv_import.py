import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any

from charset_normalizer import from_bytes

from app.services.amounts import normalize_amount


PREVIEW_LIMIT = 30


@dataclass(frozen=True)
class ParsedRow:
    row_index: int
    booking_date: date
    amount: Decimal
    description: str | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class RowError:
    row_index: int
    message: str


def detect_encoding(content: bytes) -> str:
    best = from_bytes(content).best()
    if best is None or not best.encoding:
        return 'utf-8-sig'
    encoding = best.encoding
    if encoding.lower() in {'utf_8', 'utf-8'} and content.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    return encoding


def detect_delimiter(sample: str) -> str:
    lines = [line for line in sample.splitlines() if line.strip()][:10]
    if not lines:
        return ';'
    joined = '\n'.join(lines)
    semicolon_count = joined.count(';')
    comma_count = joined.count(',')
    tab_count = joined.count('\t')
    if tab_count > semicolon_count and tab_count > comma_count:
        return '\t'
    # Polish exports typically use ';' when the decimal mark is ','.
    if semicolon_count >= comma_count and semicolon_count > 0:
        return ';'
    try:
        dialect = csv.Sniffer().sniff(joined, delimiters=';,\t')
        return dialect.delimiter
    except csv.Error:
        return ',' if comma_count > 0 else ';'


def decode_text(content: bytes, encoding: str) -> str:
    return content.decode(encoding, errors='replace')


def _cell(row: list[str], mapping_value: str | int | None) -> str:
    if mapping_value is None:
        return ''
    if isinstance(mapping_value, int):
        if mapping_value < 0 or mapping_value >= len(row):
            raise ValueError(f'column index {mapping_value} is out of range')
        return row[mapping_value].strip()
    # header name — caller resolves to index first
    raise ValueError('column mapping must be resolved to an index before parsing')


def resolve_mapping(
    column_mapping: dict[str, Any],
    headers: list[str],
    has_header: bool,
) -> dict[str, int]:
    resolved: dict[str, int] = {}
    header_lookup = {name.strip(): index for index, name in enumerate(headers)}
    for field, raw in column_mapping.items():
        if raw is None or raw == '':
            continue
        if isinstance(raw, int):
            resolved[field] = raw
            continue
        if not has_header:
            raise ValueError(f'column "{field}" must be an index when the file has no header')
        if raw not in header_lookup:
            raise ValueError(f'column "{raw}" not found in header')
        resolved[field] = header_lookup[raw]
    if 'booking_date' not in resolved:
        raise ValueError('column_mapping.booking_date is required')
    if 'amount' not in resolved and not (
        'amount_debit' in resolved or 'amount_credit' in resolved
    ):
        raise ValueError('column_mapping.amount or debit/credit columns are required')
    return resolved


def iter_data_rows(
    text: str,
    *,
    delimiter: str,
    has_header: bool,
    skip_rows: int,
) -> tuple[list[str], list[tuple[int, list[str]]]]:
    stream = StringIO(text)
    reader = csv.reader(stream, delimiter=delimiter)
    all_rows = list(reader)
    if skip_rows:
        all_rows = all_rows[skip_rows:]

    headers: list[str] = []
    data: list[tuple[int, list[str]]] = []
    if has_header:
        if not all_rows:
            return [], []
        headers = [cell.strip() for cell in all_rows[0]]
        for offset, row in enumerate(all_rows[1:]):
            data.append((offset, row))
    else:
        max_len = max((len(row) for row in all_rows), default=0)
        headers = [str(index) for index in range(max_len)]
        for offset, row in enumerate(all_rows):
            data.append((offset, row))
    return headers, data


def preview_csv(
    content: bytes,
    *,
    encoding: str | None = None,
    delimiter: str | None = None,
    has_header: bool = True,
    skip_rows: int = 0,
) -> dict[str, Any]:
    detected_encoding = detect_encoding(content)
    used_encoding = encoding or detected_encoding
    text = decode_text(content, used_encoding)
    detected_delimiter = detect_delimiter(text)
    used_delimiter = delimiter or detected_delimiter
    headers, data_rows = iter_data_rows(
        text,
        delimiter=used_delimiter,
        has_header=has_header,
        skip_rows=skip_rows,
    )
    preview_rows = [row for _index, row in data_rows[:PREVIEW_LIMIT]]
    return {
        'encoding': used_encoding,
        'delimiter': used_delimiter,
        'has_header': has_header,
        'skip_rows': skip_rows,
        'headers': headers,
        'rows': preview_rows,
        'row_count': len(data_rows),
        'detected_encoding': detected_encoding,
        'detected_delimiter': detected_delimiter,
    }


def _parse_date(value: str, date_format: str) -> date:
    try:
        return datetime.strptime(value.strip(), date_format).date()
    except ValueError as exc:
        raise ValueError(f'invalid date "{value}" for format {date_format}') from exc


def _row_amount(
    row: list[str],
    resolved: dict[str, int],
    *,
    decimal_separator: str,
    thousand_separator: str,
    amount_mode: str,
) -> Decimal:
    if 'amount' in resolved:
        amount = normalize_amount(
            row[resolved['amount']],
            decimal_separator=decimal_separator,
            thousand_separator=thousand_separator,
        )
    else:
        debit_raw = row[resolved['amount_debit']] if 'amount_debit' in resolved else '0'
        credit_raw = row[resolved['amount_credit']] if 'amount_credit' in resolved else '0'
        debit = (
            normalize_amount(
                debit_raw,
                decimal_separator=decimal_separator,
                thousand_separator=thousand_separator,
            )
            if debit_raw.strip()
            else Decimal('0.00')
        )
        credit = (
            normalize_amount(
                credit_raw,
                decimal_separator=decimal_separator,
                thousand_separator=thousand_separator,
            )
            if credit_raw.strip()
            else Decimal('0.00')
        )
        amount = credit - debit

    if amount_mode == 'absolute':
        amount = abs(amount)
    return amount


def parse_transactions(
    content: bytes,
    *,
    encoding: str,
    delimiter: str,
    has_header: bool,
    skip_rows: int,
    decimal_separator: str,
    thousand_separator: str,
    date_format: str,
    amount_mode: str,
    column_mapping: dict[str, Any],
) -> tuple[list[ParsedRow], list[RowError]]:
    text = decode_text(content, encoding)
    headers, data_rows = iter_data_rows(
        text,
        delimiter=delimiter,
        has_header=has_header,
        skip_rows=skip_rows,
    )
    resolved = resolve_mapping(column_mapping, headers, has_header)
    parsed: list[ParsedRow] = []
    errors: list[RowError] = []

    for row_index, row in data_rows:
        if not any(cell.strip() for cell in row):
            continue
        try:
            booking_date = _parse_date(row[resolved['booking_date']], date_format)
            amount = _row_amount(
                row,
                resolved,
                decimal_separator=decimal_separator,
                thousand_separator=thousand_separator,
                amount_mode=amount_mode,
            )
            description = None
            if 'description' in resolved and resolved['description'] < len(row):
                description = row[resolved['description']].strip() or None
            raw_payload = {
                (headers[index] if index < len(headers) else str(index)): (
                    row[index] if index < len(row) else ''
                )
                for index in range(max(len(headers), len(row)))
            }
            parsed.append(
                ParsedRow(
                    row_index=row_index,
                    booking_date=booking_date,
                    amount=amount,
                    description=description,
                    raw_payload=raw_payload,
                )
            )
        except (ValueError, IndexError) as exc:
            errors.append(RowError(row_index=row_index, message=str(exc)))

    return parsed, errors


def read_file_bytes(path: Path) -> bytes:
    return path.read_bytes()
