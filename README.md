# Pipeline Co-Pilot

**A multi-agent sales assistant that reads your CRM, flags at-risk deals with reasons and dollar value, ranks them, and drafts grounded follow-up emails.**

Built for the **Kaggle AI Agents Intensive — Vibe Coding capstone (Agents for Business track)** with Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/) and a custom [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server.

---

## The problem

Sales reps lose winnable deals not because they make bad calls, but because deals go quiet and slip through the cracks. A rep with 30+ open opportunities can't manually notice that the $120k Globex deal has had no activity in three weeks, or that the Initech deal is already past its close date. The signal is buried in the CRM; nobody is watching it.

## The solution

Pipeline Co-Pilot is a small team of AI agents that does the watching:

1. **Reads the pipeline** through a custom CRM tool layer (MCP server).
2. **Assesses risk** with explicit, auditable rules (stale > 14 days, or past close date).
3. **Ranks** at-risk deals by dollar **value at risk** so the rep works the biggest fire first.
4. **Recommends** one concrete next-best action per deal, grounded in the deal's own notes.
5. **Drafts** a short, grounded follow-up email on request — and logs the outreach back to the CRM, but only after the rep approves and only through an authenticated write.

## Why agents (not a script or a single prompt)

The task is **multi-step and adaptive**, which is exactly where agents earn their keep:

> read pipeline → assess risk → decide the next action → *optionally* write and log outreach

The path branches on what the data says and what the rep asks for. A **coordinator** routes each request; a **Pipeline Analyst** does the triage reasoning; an **Outreach Writer** does the grounded copywriting and the gated write. Splitting these keeps each agent's instructions focused and its tool use predictable, instead of one mega-prompt trying to do everything.

---

## Architecture

```
                         ┌───────────────────────────┐
   "What's at risk?"     │   root_agent              │
   "Draft a follow-up" ─▶│   pipeline_copilot        │   (coordinator / router)
                         │   LLM-driven delegation   │   no tools of its own
                         └───────────┬───────────────┘
                            ┌────────┴─────────┐
                            ▼                  ▼
              ┌───────────────────────┐  ┌──────────────────────────┐
              │ analyst_agent         │  │ writer_agent             │
              │ pipeline_analyst      │  │ outreach_writer          │
              │ ranks risk, advises   │  │ drafts email, logs send  │
              └───────────┬───────────┘  └───────────┬──────────────┘
                          │   each holds its own MCP toolset
                          ▼                          ▼
                   ┌──────────────────────────────────────────┐
                   │  CRM MCP server (mcp_server/crm_server.py)│
                   │  stdio transport · FastMCP                │
                   │  ┌──────────────┬──────────────┬────────┐ │
                   │  │ get_deals    │get_deal_     │ log_   │ │
                   │  │ (read)       │details(read) │activity│ │
                   │  │              │              │(WRITE) │ │
                   │  └──────────────┴──────────────┴────────┘ │
                   │  risk_assessment()  ·  auth gate · redact()│
                   └───────────────────┬──────────────────────┘
                                       ▼
                               data/crm.json (mock CRM)
```

The agents never touch `crm.json` directly — they only see the MCP tool surface. Swap the JSON for a real Salesforce/HubSpot API behind the same three tools and nothing in the agent layer changes.

---

## The four key concepts → where they live

| # | Key concept | Where it's implemented |
|---|---|---|
| 1 | **Multi-agent system (ADK)** | [`pipeline_copilot/agent.py`](pipeline_copilot/agent.py) — coordinator `root_agent` with `sub_agents=[analyst_agent, writer_agent]`; instructions in [`prompts.py`](pipeline_copilot/prompts.py) |
| 2 | **Custom MCP server** | [`mcp_server/crm_server.py`](mcp_server/crm_server.py) — `FastMCP` exposing `get_deals`, `get_deal_details`, `log_activity` over stdio |
| 3 | **Deployability** | [`Dockerfile`](Dockerfile) — `python:3.12-slim`, Cloud Run-ready `adk api_server` entrypoint |
| 4 | **Security feature** | [`crm_server.py`](mcp_server/crm_server.py) — `auth_token` gate on the `log_activity` write + `redact()` PII masking on every log line |

---

## Setup & run (local)

Prerequisites: **Python 3.10+** and a free [Google AI Studio](https://aistudio.google.com/apikey) Gemini API key.

```bash
# 1. Create a virtual environment
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS/Linux:    source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your key (NEVER commit .env — it is git-ignored)
cp .env.example .env
#   then edit .env and paste your key into GOOGLE_API_KEY

# 4a. Run the dev web UI (best for the demo — shows tool calls live)
adk web .

# 4b. ...or the terminal REPL
adk run pipeline_copilot
```

In the web UI, select **`pipeline_copilot`** and try:

- **"What deals are at risk?"** → the Analyst lists D-1002 ($120k) and D-1003 ($32k), ranked, with reasons.
- **"What should I do first?"** → ranked priorities with one next-best action each.
- **"Draft a follow-up for D-1003."** → the Writer pulls the real notes/contact and drafts a < 120-word email, then asks you to confirm before logging it.

### Run the tests

```bash
pytest            # unit tests for the pure risk logic
```

---

## Deploy (Google Cloud Run)

No live endpoint is required for judging — the Dockerfile plus these steps are reproducible.

```bash
# Build locally to verify
docker build -t pipeline-copilot .

# Deploy from source (Cloud Run builds the image for you)
gcloud run deploy pipeline-copilot \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=YOUR_KEY,GOOGLE_GENAI_USE_VERTEXAI=FALSE,CRM_API_TOKEN=your-prod-token"
```

The container runs `adk api_server . --host 0.0.0.0 --port $PORT`; Cloud Run injects `$PORT`. Secrets are passed as environment variables at deploy time and are **never** baked into the image (`.env` is excluded by `.dockerignore`).

---

## Security notes

- **Least privilege.** Reads (`get_deals`, `get_deal_details`) are open; the only **write** (`log_activity`) is gated behind a shared secret `CRM_API_TOKEN`. A wrong/missing token returns a clear `unauthorized` error and touches no data.
- **PII redaction.** Every log line passes through `redact()`, which masks email addresses (`tom@globex.com` → `[redacted-email]`), so contact PII never lands in plaintext logs.
- **No secrets in git.** `.env` is git-ignored; only `.env.example` (with placeholders) is committed. The activity log that writes produce is git-ignored too.
- **Human-in-the-loop.** The Writer never sends or logs outreach until the rep explicitly confirms.

---

## Repo layout

```
pipeline-copilot/
├── README.md                 # you are here
├── requirements.txt          # pinned deps (ADK 2.x, MCP 1.x)
├── .env.example              # template — copy to .env, add your key
├── .gitignore                # ignores .env, venv, caches, activity log
├── .dockerignore
├── Dockerfile                # Cloud Run-ready image
├── data/
│   └── crm.json              # mock CRM (5 deals; 2 at-risk by design)
├── mcp_server/
│   └── crm_server.py         # MCP server: tools + risk logic + security
├── pipeline_copilot/
│   ├── __init__.py           # exposes root_agent (ADK discovery contract)
│   ├── agent.py              # coordinator + Analyst + Writer + MCP toolset
│   └── prompts.py            # all agent instructions
├── tests/
│   └── test_risk.py          # unit tests for the pure risk function
└── docs/
    ├── WRITEUP.md            # Kaggle writeup draft
    └── VIDEO_SCRIPT.md       # 5-minute demo video script + shot list
```

---

## Notes & assumptions

- **Dates are relative to the build date (2026-06-26).** Risk is computed at runtime against the real `today`, so D-1002 and D-1003 are the clearly at-risk deals. If you run this much later, more deals may read as "stale" — that's the rule working, not a bug.
- **Model:** `gemini-2.5-flash` (fallback `gemini-flash-latest`).
- **The MCP server is launched with the current Python interpreter** (`sys.executable`) rather than a hard-coded `python3`, so it works on Windows as well as macOS/Linux.
