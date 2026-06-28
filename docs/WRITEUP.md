# Pipeline Co-Pilot — Kaggle Writeup

> **Draft for the Kaggle AI Agents Intensive — Vibe Coding capstone (Agents for Business track).**
> Target length ≤ 2500 words. `[SCREENSHOT]` markers indicate where to drop captures from the demo.

---

## Title

**Pipeline Co-Pilot: a multi-agent sales assistant that stops winnable deals from going quiet.**

### Subtitle

A coordinator + two specialist agents (Analyst & Writer) that read a CRM through a custom MCP server, rank at-risk deals by dollar value, and draft grounded follow-ups — with an authenticated write gate and PII-safe logging.

---

## The problem

Sales reps don't lose deals because they make bad decisions. They lose deals because deals go **quiet** and slip out of attention. A rep juggling 30+ open opportunities cannot reliably notice that:

- the **$120k Globex** expansion has had **no activity in three weeks**, or
- the **Initech** add-on is **already past its close date** while the customer waits on a pricing sheet.

The information is sitting in the CRM. The problem is that nobody is continuously watching it and turning it into a prioritized, actionable next step. That's a perfect job for an agent: it's repetitive, judgment-laden, and multi-step.

## The solution

**Pipeline Co-Pilot** is a small team of AI agents that watches the pipeline and acts on it:

1. **Reads** the pipeline through a custom CRM tool layer.
2. **Assesses risk** with explicit, auditable rules: *stale* (no activity in > 14 days) or *overdue* (past the close date and not closed).
3. **Ranks** at-risk deals by **value at risk** (dollar amount) so the rep fixes the biggest leak first.
4. **Recommends** exactly one next-best action per deal, grounded in that deal's own notes.
5. **Drafts** a short (< 120-word) follow-up email on request, grounded in the real contact and notes — and **logs** the outreach back to the CRM, but only after the rep approves and only through an authenticated write.

`[SCREENSHOT: adk web — asking "What deals are at risk?" and the ranked answer]`

## Why agents (and why multi-agent)

The task is **multi-step and adaptive**:

> read pipeline → assess risk → decide the next action → *optionally* write and log outreach

The control flow branches on what the data says and what the rep asks for — a static script can't gracefully handle "what's at risk?" one moment and "draft a follow-up for D-1003, then log it" the next. That adaptivity is the case for agents.

Within that, I chose a **multi-agent** design over one mega-prompt:

- a **coordinator** (`pipeline_copilot`) that routes each request,
- a **Pipeline Analyst** (`pipeline_analyst`) that does the triage reasoning, and
- an **Outreach Writer** (`outreach_writer`) that does grounded copywriting and the gated write.

Separating "decide what's at risk" from "write outreach" keeps each agent's instructions short and its tool use predictable. The coordinator uses ADK's LLM-driven delegation (`sub_agents=`) to pick the specialist — no brittle keyword routing.

## Architecture

```
   request ─▶ root_agent (pipeline_copilot)  ── coordinator / router, no tools
                   │
          ┌────────┴────────┐
          ▼                 ▼
   pipeline_analyst   outreach_writer        ── each holds its own MCP toolset
          │                 │
          └──────┬──────────┘
                 ▼
        CRM MCP server (stdio, FastMCP)
        get_deals · get_deal_details · log_activity
        risk_assessment() · auth gate · redact()
                 │
                 ▼
           data/crm.json (mock CRM)
```

The agents never read `crm.json` directly — they only see the MCP tool surface. That boundary is deliberate: swap the mock JSON for a real Salesforce/HubSpot API behind the same three tools and the entire agent layer is unchanged.

`[SCREENSHOT: the agent graph / trace view in adk web showing the tool calls]`

## The build

### Tools & stack

- **Google Agent Development Kit (ADK) 2.x** — agents, LLM-driven delegation, and the `adk web` / `adk api_server` runtimes.
- **Model Context Protocol (MCP) 1.x** via **`FastMCP`** — the custom CRM server, exposed over the stdio transport.
- **Gemini 2.5 Flash** — the reasoning model (fast and cheap; plenty for tool routing and short drafting).
- **Docker** — a `python:3.12-slim` image with a Cloud Run-ready `adk api_server` entrypoint.
- **pytest** — unit tests for the pure risk function.
- Built iteratively in **Claude Code**, verifying each phase (install → MCP server → single-agent slice → multi-agent → security → container → docs) before moving on.

### The four key concepts

1. **Multi-agent system** — coordinator + Analyst + Writer in `pipeline_copilot/agent.py`, instructions in `prompts.py`.
2. **Custom MCP server** — `mcp_server/crm_server.py` exposes `get_deals`, `get_deal_details`, `log_activity`.
3. **Deployability** — `Dockerfile`, documented `gcloud run deploy --source .`.
4. **Security feature** — `auth_token` gate on the only write + `redact()` PII masking on every log line.

### Design decisions worth calling out

- **The risk rule is a pure function** (`risk_assessment`) with an injectable `today`, so it's unit-tested deterministically and lives independently of the LLM. Agents reason *about* risk; they don't *invent* it.
- **Grounding is enforced by instruction and tool design.** The Writer must call `get_deal_details` before drafting, and the compact `get_deals` output deliberately omits free-text notes so the Analyst fetches them when it needs to justify an action.
- **Human-in-the-loop on writes.** The Writer drafts, asks the rep to confirm, and only then calls `log_activity`. The write itself is auth-gated.

## Security

- **Least privilege:** reads are open; the only write (`log_activity`) requires a valid `CRM_API_TOKEN`. A wrong/missing token returns `unauthorized` and touches no data.
- **PII redaction:** every log line passes through `redact()`, masking emails (`tom@globex.com` → `[redacted-email]`).
- **No secrets in git:** `.env` is git-ignored; only `.env.example` ships. Secrets are injected at deploy time, never baked into the image.

`[SCREENSHOT: server log showing a DENIED write with a bad token, and an OK write with [redacted-email]]`

## Challenges

- **API drift.** ADK and MCP move fast; I pinned the exact 2.x import paths (`McpToolset`, `StdioConnectionParams`, `FastMCP`) and verified them on install rather than trusting older tutorials.
- **stdio is the protocol channel.** Because FastMCP uses stdout for the MCP stream, every human log had to go to **stderr** — a subtle but critical detail, or the stream corrupts.
- **Cross-platform launch.** The common `command="python3"` pattern fails on Windows; launching the server with `sys.executable` made it portable.
- **Grounding vs. helpfulness.** Getting the Writer to stay strictly grounded (no invented prices/dates) while still producing a warm, usable email was mostly a prompt-shaping exercise.

## What's next

- Back the MCP server with a **real CRM API** (Salesforce/HubSpot) behind the same three tools.
- Add a **scheduler** so the Analyst runs a daily morning triage and pushes the top three risks.
- Expand the security model from a shared token to **per-user OAuth scopes**.
- Add an **eval harness** that scores the Analyst's rankings and the Writer's groundedness against a labeled set.

---

*Repo: see `README.md` for setup, run, and deploy instructions. Demo video: see `docs/VIDEO_SCRIPT.md`.*
