from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

MatchKind = Literal['exact', 'probable', 'unmatched_a', 'unmatched_b']


@dataclass(frozen=True)
class MatchInput:
    id: int
    row_index: int
    booking_date: date
    amount_abs: Decimal


@dataclass(frozen=True)
class MatchOutcome:
    kind: MatchKind
    confidence: int
    transaction_a_id: int | None
    transaction_b_id: int | None
    date_delta_days: int | None
    amount: Decimal


def match_transactions(
    side_a: list[MatchInput],
    side_b: list[MatchInput],
    date_tolerance_days: int = 7,
) -> list[MatchOutcome]:
    """Deterministic 1:1 matching: exact (amount+date), then probable (amount + date window)."""
    remaining_a = sorted(side_a, key=lambda item: item.row_index)
    remaining_b = sorted(side_b, key=lambda item: item.row_index)
    outcomes: list[MatchOutcome] = []

    buckets: dict[tuple[Decimal, date], deque[MatchInput]] = defaultdict(deque)
    for item in remaining_a:
        buckets[(item.amount_abs, item.booking_date)].append(item)

    unmatched_b: list[MatchInput] = []
    used_a_ids: set[int] = set()

    for item_b in remaining_b:
        key = (item_b.amount_abs, item_b.booking_date)
        queue = buckets.get(key)
        if queue:
            item_a = queue.popleft()
            used_a_ids.add(item_a.id)
            outcomes.append(
                MatchOutcome(
                    kind='exact',
                    confidence=100,
                    transaction_a_id=item_a.id,
                    transaction_b_id=item_b.id,
                    date_delta_days=0,
                    amount=item_a.amount_abs,
                )
            )
        else:
            unmatched_b.append(item_b)

    unmatched_a = [item for item in remaining_a if item.id not in used_a_ids]
    used_a_ids = set()
    used_b_ids: set[int] = set()

    by_amount_a: dict[Decimal, list[MatchInput]] = defaultdict(list)
    by_amount_b: dict[Decimal, list[MatchInput]] = defaultdict(list)
    for item in unmatched_a:
        by_amount_a[item.amount_abs].append(item)
    for item in unmatched_b:
        by_amount_b[item.amount_abs].append(item)

    for amount, group_a in by_amount_a.items():
        group_b = by_amount_b.get(amount)
        if not group_b:
            continue

        candidates: list[tuple[int, int, int, MatchInput, MatchInput]] = []
        for item_a in group_a:
            for item_b in group_b:
                if item_a.booking_date == item_b.booking_date:
                    continue
                delta = abs((item_a.booking_date - item_b.booking_date).days)
                if delta <= date_tolerance_days:
                    candidates.append(
                        (delta, item_a.row_index, item_b.row_index, item_a, item_b)
                    )

        candidates.sort(key=lambda row: (row[0], row[1], row[2]))
        for delta, _ia, _ib, item_a, item_b in candidates:
            if item_a.id in used_a_ids or item_b.id in used_b_ids:
                continue
            used_a_ids.add(item_a.id)
            used_b_ids.add(item_b.id)
            outcomes.append(
                MatchOutcome(
                    kind='probable',
                    confidence=80,
                    transaction_a_id=item_a.id,
                    transaction_b_id=item_b.id,
                    date_delta_days=delta,
                    amount=amount,
                )
            )

    for item in unmatched_a:
        if item.id in used_a_ids:
            continue
        outcomes.append(
            MatchOutcome(
                kind='unmatched_a',
                confidence=0,
                transaction_a_id=item.id,
                transaction_b_id=None,
                date_delta_days=None,
                amount=item.amount_abs,
            )
        )

    for item in unmatched_b:
        if item.id in used_b_ids:
            continue
        outcomes.append(
            MatchOutcome(
                kind='unmatched_b',
                confidence=0,
                transaction_a_id=None,
                transaction_b_id=item.id,
                date_delta_days=None,
                amount=item.amount_abs,
            )
        )

    return outcomes
