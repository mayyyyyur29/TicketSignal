import pandas as pd

from app.core.ingestion import validate


def _ticket(ticket_id: str | None, rating: float | None) -> dict:
    return {
        "ticket_id": ticket_id,
        "category": "Billing",
        "priority": "High",
        "status": "Resolved",
        "created_at": "2024-01-01 00:00:00",
        "customer_rating": rating,
    }


def test_validate_rejects_missing_and_blank_ticket_ids() -> None:
    frame = pd.DataFrame([_ticket(None, 4), _ticket("   ", 5)])

    valid, rejects = validate(frame)

    assert valid.empty
    assert rejects == [(None, "ticket_id is required"), (None, "ticket_id is required")]


def test_validate_rejects_fractional_rating_and_keeps_whole_rating() -> None:
    frame = pd.DataFrame([_ticket("T-1", 3.7), _ticket("T-2", 4.0)])

    valid, rejects = validate(frame)

    assert valid["ticket_id"].tolist() == ["T-2"]
    assert valid["customer_rating"].tolist() == [4]
    assert rejects == [("T-1", "customer_rating must be a whole number")]