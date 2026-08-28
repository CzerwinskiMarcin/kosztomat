from datetime import date
from decimal import Decimal

from app.services.matching import MatchInput, match_transactions


def _item(item_id: int, day: int, amount: str, month: int = 1, row_index: int | None = None) -> MatchInput:
    return MatchInput(
        id=item_id,
        row_index=item_id if row_index is None else row_index,
        booking_date=date(2026, month, day),
        amount_abs=Decimal(amount),
    )


def _kinds(outcomes) -> list[tuple[str, int | None, int | None, int]]:
    return [
        (item.kind, item.transaction_a_id, item.transaction_b_id, item.confidence)
        for item in outcomes
    ]


def test_spec_example_exact_probable_and_unmatched() -> None:
    side_a = [
        _item(1, 15, '45.00'),
        _item(2, 16, '120.00'),
        _item(3, 20, '45.00'),
        _item(4, 1, '15.00', month=2),
    ]
    side_b = [
        _item(11, 15, '45.00'),
        _item(12, 16, '120.00'),
        _item(13, 22, '45.00'),
        _item(14, 10, '89.00', month=2),
    ]

    outcomes = match_transactions(side_a, side_b, date_tolerance_days=7)
    exact = [item for item in outcomes if item.kind == 'exact']
    probable = [item for item in outcomes if item.kind == 'probable']
    unmatched_a = [item for item in outcomes if item.kind == 'unmatched_a']
    unmatched_b = [item for item in outcomes if item.kind == 'unmatched_b']

    assert len(exact) == 2
    assert {(item.transaction_a_id, item.transaction_b_id) for item in exact} == {(1, 11), (2, 12)}
    assert len(probable) == 1
    assert probable[0].transaction_a_id == 3
    assert probable[0].transaction_b_id == 13
    assert probable[0].date_delta_days == 2
    assert probable[0].confidence == 80
    assert len(unmatched_a) == 1
    assert unmatched_a[0].amount == Decimal('15.00')
    assert len(unmatched_b) == 1
    assert unmatched_b[0].amount == Decimal('89.00')


def test_same_day_duplicates_then_probable() -> None:
    side_a = [_item(1, 15, '50.00', row_index=0), _item(2, 15, '50.00', row_index=1)]
    side_b = [_item(11, 15, '50.00', row_index=0), _item(12, 16, '50.00', row_index=1)]

    outcomes = match_transactions(side_a, side_b, date_tolerance_days=7)
    exact = [item for item in outcomes if item.kind == 'exact']
    probable = [item for item in outcomes if item.kind == 'probable']

    assert len(exact) == 1
    assert exact[0].transaction_a_id == 1
    assert exact[0].transaction_b_id == 11
    assert len(probable) == 1
    assert probable[0].transaction_a_id == 2
    assert probable[0].transaction_b_id == 12
    assert probable[0].date_delta_days == 1


def test_empty_sets() -> None:
    assert match_transactions([], []) == []
    outcomes = match_transactions([_item(1, 15, '10.00')], [])
    assert len(outcomes) == 1
    assert outcomes[0].kind == 'unmatched_a'


def test_all_exact() -> None:
    side_a = [_item(1, 15, '10.00'), _item(2, 16, '20.00')]
    side_b = [_item(11, 15, '10.00'), _item(12, 16, '20.00')]
    outcomes = match_transactions(side_a, side_b)
    assert all(item.kind == 'exact' for item in outcomes)
    assert len(outcomes) == 2


def test_delta_outside_tolerance_stays_unmatched() -> None:
    side_a = [_item(1, 1, '45.00')]
    side_b = [_item(11, 20, '45.00')]
    outcomes = match_transactions(side_a, side_b, date_tolerance_days=7)
    kinds = {item.kind for item in outcomes}
    assert kinds == {'unmatched_a', 'unmatched_b'}


def test_deterministic_order() -> None:
    side_a = [_item(1, 15, '45.00'), _item(2, 16, '120.00')]
    side_b = [_item(11, 16, '120.00'), _item(12, 15, '45.00')]
    first = _kinds(match_transactions(side_a, side_b))
    second = _kinds(match_transactions(side_a, side_b))
    assert first == second
