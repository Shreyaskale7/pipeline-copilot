"""
Unit tests for the pure risk logic.

We test `risk_assessment` directly (no MCP, no LLM, no network) because the whole
point of pulling the rule into a pure function was to make it cheaply and
deterministically testable. `today` is injected so the tests never depend on the
real calendar.
"""

import sys
from datetime import date
from pathlib import Path

# Make the mcp_server package importable when running `pytest` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp_server"))

from crm_server import STALE_AFTER_DAYS, risk_assessment  # noqa: E402

# A fixed "today" so every assertion below is deterministic.
TODAY = date(2026, 6, 26)


def _deal(**overrides):
    """A healthy baseline deal; override individual fields per test."""
    base = {
        "id": "D-TEST",
        "name": "Test Deal",
        "account": "Test Co",
        "stage": "Negotiation",
        "amount": 50000,
        "last_activity_date": "2026-06-24",  # 2 days ago -> fresh
        "close_date": "2026-07-30",          # comfortably in the future
    }
    base.update(overrides)
    return base


def test_healthy_deal_is_not_at_risk():
    result = risk_assessment(_deal(), today=TODAY)
    assert result["is_at_risk"] is False
    assert result["risk_reasons"] == []
    assert result["value_at_risk"] == 0


def test_stale_deal_is_flagged():
    # Last activity 25 days ago (> STALE_AFTER_DAYS) -> at risk.
    result = risk_assessment(_deal(last_activity_date="2026-06-01"), today=TODAY)
    assert result["is_at_risk"] is True
    assert result["days_since_last_activity"] == 25
    assert any("stale" in r.lower() or "no activity" in r.lower() for r in result["risk_reasons"])
    # value_at_risk surfaces the dollar amount for ranking.
    assert result["value_at_risk"] == 50000


def test_overdue_close_date_is_flagged():
    # Fresh activity but the close date already passed -> at risk (overdue).
    result = risk_assessment(
        _deal(last_activity_date="2026-06-25", close_date="2026-06-15"),
        today=TODAY,
    )
    assert result["is_at_risk"] is True
    assert any("overdue" in r.lower() for r in result["risk_reasons"])


def test_boundary_exactly_stale_threshold_is_not_at_risk():
    # Exactly STALE_AFTER_DAYS days is NOT yet stale (rule is strictly greater).
    last = date(2026, 6, 26 - STALE_AFTER_DAYS).isoformat()  # 14 days ago
    result = risk_assessment(_deal(last_activity_date=last), today=TODAY)
    assert result["days_since_last_activity"] == STALE_AFTER_DAYS
    assert result["is_at_risk"] is False


def test_terminal_stage_overdue_is_not_at_risk():
    # A won deal that is "overdue" should not be flagged — it already resolved.
    result = risk_assessment(
        _deal(stage="Closed Won", close_date="2026-06-01", last_activity_date="2026-06-25"),
        today=TODAY,
    )
    assert result["is_at_risk"] is False
