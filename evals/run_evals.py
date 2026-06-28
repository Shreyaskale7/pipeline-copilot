"""
Eval harness for Pipeline Co-Pilot.

WHY THIS EXISTS
---------------
"It runs" is not the same as "it's correct." This harness turns the two judgement
calls the product makes into *measurable* checks against a golden answer, so we can
prove the agent behaves and catch regressions automatically (it runs in CI):

  EVAL 1 — Risk ranking: does the deterministic risk logic flag exactly the right
           at-risk deals, in the right value-at-risk order, vs evals/expected.json?
  EVAL 2 — Groundedness: does the guardrail correctly PASS grounded emails and
           CATCH emails that invent prices / contacts / discounts?

These evals are deterministic (no LLM, no API key, no quota) so they're fast and
reproducible. A separate, optional live check (tests/_verify_mcp_roundtrip.py)
exercises the real agents.

Run:  python evals/run_evals.py     (exit code 0 == all evals passed)
"""

import json
import sys
from pathlib import Path

# Make the MCP server package importable (risk logic + guardrail live there).
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcp_server"))

from crm_server import risk_assessment, _load_deals  # noqa: E402
from guardrails import check_grounded  # noqa: E402

EXPECTED = json.loads((ROOT / "evals" / "expected.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# EVAL 1 — risk ranking matches the golden answer
# ---------------------------------------------------------------------------
def ranked_at_risk_ids() -> list[str]:
    """The at-risk deals, ranked by value at risk (highest $ first; id as tiebreak)
    — exactly what the Analyst is supposed to produce."""
    flagged = []
    for deal in _load_deals():
        risk = risk_assessment(deal)
        if risk["is_at_risk"]:
            flagged.append((deal["id"], risk["value_at_risk"]))
    flagged.sort(key=lambda x: (-x[1], x[0]))
    return [deal_id for deal_id, _ in flagged]


def eval_risk_ranking() -> tuple[bool, str]:
    got = ranked_at_risk_ids()
    want = EXPECTED["ranked_at_risk_ids"]
    ok = got == want
    return ok, f"ranking got={got} want={want}"


# ---------------------------------------------------------------------------
# EVAL 2 — groundedness guardrail behaves
# ---------------------------------------------------------------------------
# Each case: an email about a deal, and whether it SHOULD be considered grounded.
GROUNDING_CASES = [
    {
        "name": "clean grounded email (D-1003)",
        "deal_id": "D-1003",
        "email": ("Hi Samir, following up on the Initech onboarding add-on. I know "
                  "you're waiting on the updated 50-seat pricing - I'll get that over "
                  "so we can move to signature. Best, Priya"),
        "expect_grounded": True,
    },
    {
        "name": "invented discount + wrong price (D-1003)",
        "deal_id": "D-1003",
        "email": ("Hi Samir, great news - I can offer a 20% discount and lock in a "
                  "$250,000 deal today. Best, Priya"),
        "expect_grounded": False,
    },
    {
        "name": "wrong contact email leaked (D-1002)",
        "deal_id": "D-1002",
        "email": "Hi Tom, looping in finance@globex-internal.com to discuss the ROI model.",
        "expect_grounded": False,
    },
]


def eval_groundedness() -> tuple[bool, str]:
    deals = {d["id"]: d for d in _load_deals()}
    failures = []
    for case in GROUNDING_CASES:
        result = check_grounded(case["email"], deals[case["deal_id"]])
        if result["grounded"] != case["expect_grounded"]:
            failures.append(
                f"'{case['name']}': expected grounded={case['expect_grounded']}, "
                f"got {result['grounded']} ({result['violations']})"
            )
    ok = not failures
    detail = "all grounding cases correct" if ok else "; ".join(failures)
    return ok, detail


# ---------------------------------------------------------------------------
# Scorecard
# ---------------------------------------------------------------------------
def main() -> int:
    evals = [
        ("Risk ranking vs golden answer", eval_risk_ranking),
        ("Groundedness guardrail", eval_groundedness),
    ]
    print("=" * 64)
    print("Pipeline Co-Pilot — eval scorecard")
    print("=" * 64)
    passed = 0
    for name, fn in evals:
        ok, detail = fn()
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}\n        {detail}")
    print("-" * 64)
    print(f"{passed}/{len(evals)} evals passed")
    return 0 if passed == len(evals) else 1


if __name__ == "__main__":
    sys.exit(main())
