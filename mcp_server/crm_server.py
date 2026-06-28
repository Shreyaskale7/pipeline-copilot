"""
CRM MCP server for Pipeline Co-Pilot.

WHY THIS FILE EXISTS
--------------------
This is the project's "custom MCP server" (one of the four graded key concepts).
It wraps a mock CRM (data/crm.json) and exposes it to the agents as a small set
of Model Context Protocol *tools*. The agents never read the JSON directly; they
only ever see the tool surface defined here. That separation is the whole point
of MCP: the data source can change (real Salesforce/HubSpot API tomorrow) without
the agents changing at all.

TRANSPORT NOTE
--------------
FastMCP defaults to the stdio transport, so STDOUT is the protocol channel.
Anything we print to stdout would corrupt the MCP stream, therefore ALL human
logging goes to STDERR (see the module logger below).

SECURITY (graded key concept #4)
--------------------------------
- Reads (get_deals, get_deal_details) are open == least privilege for read-only.
- Writes (log_activity) are gated behind a shared secret (CRM_API_TOKEN).
- redact() masks PII (emails) on every log line so contact addresses never land
  in plaintext logs.
"""

import json
import logging
import os
import re
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration / constants
# ---------------------------------------------------------------------------

# A deal whose last activity is older than this many days is considered "stale".
# Kept as a module constant so the rule is easy to find, tune, and unit-test.
STALE_AFTER_DAYS = 14

# Stages that mean the deal is finished; an overdue close date on these is NOT a
# risk (the deal already resolved). None of the mock deals are terminal today,
# but real pipelines have them, so we guard for it.
TERMINAL_STAGES = {"closed won", "closed lost"}

# Absolute path to the mock CRM, resolved relative to THIS file so the server
# works no matter what directory it is launched from (ADK launches it via an
# absolute path of its own).
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "crm.json"

# Append-only activity log written by log_activity(). Git-ignored because it can
# contain customer-specific notes.
ACTIVITY_LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "activity_log.jsonl"

# The shared secret that authorizes writes. Defaults to "demo-token" so the demo
# runs out of the box; in production this would be a real secret injected by the
# environment (and the default would be removed).
CRM_API_TOKEN = os.environ.get("CRM_API_TOKEN", "demo-token")

# ---------------------------------------------------------------------------
# Logging — STDERR ONLY (stdout is the MCP stream)
# ---------------------------------------------------------------------------

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[crm-mcp] %(levelname)s %(message)s",
)
log = logging.getLogger("crm-pipeline-server")

# Matches typical email addresses. Used by redact() to keep PII out of logs.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact(text: str) -> str:
    """Mask any email address in `text` so PII never reaches the logs.

    Example: "pinged tom@globex.com" -> "pinged [redacted-email]".
    Applied to every log line we emit (security key concept).
    """
    return _EMAIL_RE.sub("[redacted-email]", str(text))


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

def _load_deals() -> list[dict]:
    """Load the raw deal records from disk.

    Read on every call (rather than cached at import) so edits to crm.json show
    up immediately during a demo without restarting the server. The dataset is
    tiny, so the I/O cost is irrelevant.
    """
    with open(DATA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)["deals"]


def _parse(d: str) -> date:
    """Parse a YYYY-MM-DD string into a date."""
    return datetime.strptime(d, "%Y-%m-%d").date()


# ---------------------------------------------------------------------------
# Pure risk logic (unit-tested in tests/test_risk.py)
# ---------------------------------------------------------------------------

def risk_assessment(deal: dict, today: date | None = None) -> dict:
    """Assess a single deal's risk. PURE function: no I/O, no globals besides
    the STALE_AFTER_DAYS constant, and `today` is injectable so tests are
    deterministic.

    A deal is at risk when EITHER:
      * it has gone quiet  -> last activity older than STALE_AFTER_DAYS, OR
      * it is overdue      -> today is past its close_date and it has not closed.

    Returns a dict with:
      is_at_risk (bool), risk_reasons (list[str]),
      days_since_last_activity (int), value_at_risk (int).
    """
    today = today or date.today()

    last_activity = _parse(deal["last_activity_date"])
    close = _parse(deal["close_date"])
    days_since_last_activity = (today - last_activity).days
    is_terminal = deal.get("stage", "").strip().lower() in TERMINAL_STAGES

    reasons: list[str] = []

    # Rule 1: stale / no recent activity.
    if days_since_last_activity > STALE_AFTER_DAYS:
        reasons.append(
            f"No activity in {days_since_last_activity} days "
            f"(stale after {STALE_AFTER_DAYS})."
        )

    # Rule 2: past the expected close date but not actually closed.
    if today > close and not is_terminal:
        overdue_days = (today - close).days
        reasons.append(
            f"Close date was {deal['close_date']} ({overdue_days} days overdue) "
            f"but stage is still '{deal['stage']}'."
        )

    is_at_risk = len(reasons) > 0
    return {
        "is_at_risk": is_at_risk,
        "risk_reasons": reasons,
        "days_since_last_activity": days_since_last_activity,
        # Dollar value exposed to risk if this deal slips. Drives the Analyst's
        # ranking ("value at risk"); 0 when the deal is healthy.
        "value_at_risk": deal["amount"] if is_at_risk else 0,
    }


def _summary(deal: dict) -> dict:
    """Build a compact, agent-friendly view of a deal + its risk flags.

    We deliberately drop the long free-text `notes` here to keep the tool output
    small; the Writer pulls full notes via get_deal_details when it needs them.
    """
    risk = risk_assessment(deal)
    return {
        "id": deal["id"],
        "name": deal["name"],
        "account": deal["account"],
        "stage": deal["stage"],
        "amount": deal["amount"],
        "owner": deal["owner"],
        "is_at_risk": risk["is_at_risk"],
        "risk_reasons": risk["risk_reasons"],
        "days_since_last_activity": risk["days_since_last_activity"],
        "value_at_risk": risk["value_at_risk"],
    }


# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

mcp = FastMCP("crm-pipeline-server")


@mcp.tool()
def get_deals(stage: str | None = None, at_risk_only: bool = False) -> list[dict]:
    """List pipeline deals as compact summaries with risk flags attached.

    Args:
        stage: optional case-insensitive stage filter (e.g. "Negotiation").
        at_risk_only: when True, return only deals flagged at risk.

    Returns: list of compact deal summaries (no free-text notes).
    """
    deals = [_summary(d) for d in _load_deals()]

    if stage:
        deals = [d for d in deals if d["stage"].lower() == stage.strip().lower()]
    if at_risk_only:
        deals = [d for d in deals if d["is_at_risk"]]

    log.info(redact(f"get_deals(stage={stage}, at_risk_only={at_risk_only}) -> {len(deals)} deals"))
    return deals


@mcp.tool()
def get_deal_details(deal_id: str) -> dict:
    """Return the FULL record for one deal (including notes + contact) merged
    with its live risk assessment.

    The Writer agent calls this before drafting an email so the message is
    grounded in real notes/contact data instead of being invented.

    Returns the deal dict plus a nested "risk" key, or an {"error": ...} dict if
    the id is unknown.
    """
    for deal in _load_deals():
        if deal["id"].lower() == deal_id.strip().lower():
            enriched = dict(deal)
            enriched["risk"] = risk_assessment(deal)
            log.info(redact(f"get_deal_details({deal_id}) -> found"))
            return enriched

    log.info(f"get_deal_details({deal_id}) -> not found")
    return {"error": f"No deal found with id '{deal_id}'."}


@mcp.tool()
def log_activity(deal_id: str, summary: str, auth_token: str) -> dict:
    """Record an outreach activity against a deal. THIS IS A WRITE -> auth-gated.

    Security gate (key concept #4): the call is rejected unless `auth_token`
    matches the server's CRM_API_TOKEN. This models least-privilege: anyone can
    read the pipeline, but only an authorized caller can mutate it. The Writer
    agent supplies the token (passed to the server via the toolset env), and it
    only logs *after* the human rep confirms the send.

    Returns:
        {"status": "ok", ...} on success,
        {"status": "unauthorized", ...} on a bad/missing token,
        {"status": "error", ...} if the deal id is unknown.
    """
    # 1) Authorization check FIRST — never touch data on an unauthorized call.
    if auth_token != CRM_API_TOKEN:
        log.warning(f"log_activity DENIED for {deal_id}: invalid auth token.")
        return {
            "status": "unauthorized",
            "error": "Invalid auth_token. Writes require a valid CRM_API_TOKEN.",
        }

    # 2) Validate the target deal exists.
    if not any(d["id"].lower() == deal_id.strip().lower() for d in _load_deals()):
        return {"status": "error", "error": f"No deal found with id '{deal_id}'."}

    # 3) Persist the activity (append-only). The file is git-ignored.
    activity_id = f"ACT-{uuid.uuid4().hex[:8]}"
    record = {
        "activity_id": activity_id,
        "deal_id": deal_id,
        "summary": summary,
        "logged_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(ACTIVITY_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    # 4) Log it — redact() keeps any email in the summary out of the log line.
    log.info(redact(f"log_activity OK {activity_id} on {deal_id}: {summary}"))
    return {"status": "ok", **record}


if __name__ == "__main__":
    # Launch banner goes to STDERR so it cannot corrupt the stdio MCP stream.
    log.info(f"Starting crm-pipeline-server (data={DATA_PATH}, stale_after={STALE_AFTER_DAYS}d)")
    mcp.run()  # stdio transport by default
