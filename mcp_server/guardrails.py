"""
Grounding guardrail for the Outreach Writer.

WHY THIS EXISTS
---------------
The #1 failure mode of an LLM that writes customer emails is *hallucination*:
inventing a price, a discount, a date, or a commitment that was never in the CRM.
That can embarrass a rep or create a fake promise to a customer.

This module is a small, DETERMINISTIC safety net (no LLM, so it can't hallucinate
about hallucinations). Given a drafted email and the deal it's about, it flags
factual claims that are NOT supported by the deal's own data:

  * dollar amounts not equal to the deal amount or mentioned in the notes,
  * email addresses other than the real contact's,
  * percentages / discounts / "free" / "refund" promises not in the notes.

It is exposed to the Writer as an MCP tool (`check_email_grounding`) so the agent
can self-check and revise BEFORE showing the rep a draft, and it is also scored by
the eval harness. Heuristic by design: it favours catching the obvious, dangerous
fabrications over perfect linguistic understanding.
"""

import re

# Currency-style amounts: "$120,000", "$120k", "120000", "120k".
_MONEY_RE = re.compile(r"\$?\b(\d{1,3}(?:,\d{3})+|\d{3,})\b(k)?|\$\d+(k)?", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Risky commitment language that is easy to invent and expensive if wrong.
_PROMISE_RE = re.compile(r"\b(\d{1,3})\s?%|\bdiscount\b|\brefund\b|\bfree\b|\bguarantee\b", re.IGNORECASE)


def _numbers_in(text: str) -> set[str]:
    """Return the set of bare digit-strings appearing in `text` (commas stripped).

    Used to build the 'allowed' set of numbers from the deal data, so a figure in
    the email only counts as grounded if those exact digits appear in the source.
    """
    return {m.replace(",", "") for m in re.findall(r"\d[\d,]*", text)}


def check_grounded(email_text: str, deal: dict) -> dict:
    """Check whether `email_text` is grounded in `deal`.

    Returns:
        {
          "grounded": bool,            # True == no violations found
          "violations": list[str],     # human-readable problems
        }
    """
    violations: list[str] = []

    # Build the set of facts we consider "supported" by this deal.
    allowed_numbers = _numbers_in(str(deal.get("amount", "")))
    allowed_numbers |= _numbers_in(deal.get("notes", ""))
    # Dates in the record are legitimately referenceable.
    allowed_numbers |= _numbers_in(deal.get("close_date", ""))
    allowed_numbers |= _numbers_in(deal.get("last_activity_date", ""))
    allowed_email = deal.get("contact_email", "").lower()

    # 1) Dollar amounts that don't trace back to the deal.
    for match in _MONEY_RE.finditer(email_text):
        raw = match.group(0)
        digits = re.sub(r"[^\d]", "", raw)
        if not digits:
            continue
        # "120k" -> 120000 so it can match a written-out amount.
        if raw.lower().endswith("k"):
            digits_full = str(int(digits) * 1000)
            if digits in allowed_numbers or digits_full in allowed_numbers:
                continue
        elif digits in allowed_numbers:
            continue
        violations.append(f"Mentions an amount '{raw}' not found in the deal data.")

    # 2) Email addresses other than the real contact.
    for addr in _EMAIL_RE.findall(email_text):
        if addr.lower() != allowed_email:
            violations.append(f"Mentions email '{addr}' that is not the deal contact.")

    # 3) Invented commitments (discounts/percentages/guarantees) not in the notes.
    notes_lower = deal.get("notes", "").lower()
    for match in _PROMISE_RE.finditer(email_text):
        phrase = match.group(0)
        if phrase.lower() not in notes_lower:
            violations.append(
                f"Mentions a commitment '{phrase}' not supported by the deal notes."
            )

    # De-duplicate while preserving order.
    seen, unique = set(), []
    for v in violations:
        if v not in seen:
            seen.add(v)
            unique.append(v)

    return {"grounded": len(unique) == 0, "violations": unique}
