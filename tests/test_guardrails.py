"""Unit tests for the deterministic grounding guardrail."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp_server"))

from guardrails import check_grounded  # noqa: E402

DEAL = {
    "id": "D-1003",
    "amount": 32000,
    "contact_email": "samir.patel@initech.example.com",
    "notes": "Samir is waiting on updated pricing for 50 seats - blocking signature.",
    "close_date": "2026-06-15",
    "last_activity_date": "2026-06-05",
}


def test_grounded_email_passes():
    email = ("Hi Samir, sending over the updated 50-seat pricing so we can move to "
             "signature. Best, Priya")
    result = check_grounded(email, DEAL)
    assert result["grounded"] is True
    assert result["violations"] == []


def test_invented_price_is_flagged():
    email = "Hi Samir, I can lock in a $250,000 deal today."
    result = check_grounded(email, DEAL)
    assert result["grounded"] is False
    assert any("250,000" in v or "250000" in v for v in result["violations"])


def test_invented_discount_is_flagged():
    email = "Hi Samir, I can offer a 20% discount if you sign this week."
    result = check_grounded(email, DEAL)
    assert result["grounded"] is False
    assert any("commitment" in v.lower() for v in result["violations"])


def test_wrong_contact_email_is_flagged():
    email = "Looping in finance@initech-internal.com on this thread."
    result = check_grounded(email, DEAL)
    assert result["grounded"] is False
    assert any("not the deal contact" in v for v in result["violations"])


def test_real_contact_email_is_ok():
    email = "Reach me and I'll cc samir.patel@initech.example.com on the quote."
    result = check_grounded(email, DEAL)
    # The real contact address must NOT be flagged.
    assert all("not the deal contact" not in v for v in result["violations"])
