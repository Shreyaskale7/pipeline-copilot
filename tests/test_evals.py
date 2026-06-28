"""Pytest wrapper that runs the eval harness so CI fails if any eval regresses."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))

from run_evals import eval_risk_ranking, eval_groundedness  # noqa: E402


def test_risk_ranking_matches_golden():
    ok, detail = eval_risk_ranking()
    assert ok, detail


def test_groundedness_eval_passes():
    ok, detail = eval_groundedness()
    assert ok, detail
