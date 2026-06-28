# Pipeline Co-Pilot — Demo Video Script (≤ 5 minutes)

**Format:** screen recording + voiceover. **Must be uploaded to YouTube** (public or unlisted) and linked in the Kaggle submission.

**Pre-roll checklist (do this before you hit record):**
- `.env` filled with a working `GOOGLE_API_KEY`.
- `adk web .` already running; browser open at the dev UI with `pipeline_copilot` selected.
- A second terminal visible showing the MCP server **stderr logs** (so the security/redaction beat is visible).
- `data/crm.json` open in the editor for the "grounded in real data" moment.

**Total budget: ~4:55.** Beat timings below.

---

## Beat 1 — The problem (~40s) · 0:00–0:40

**Shot:** Slide or talking head, then cut to `crm.json` scrolling.

**Voiceover:**
> "Sales reps don't lose deals by making bad calls — they lose them because deals go quiet and slip through the cracks. Picture a rep with thirty open opportunities. Can they really notice that a $120,000 deal has gone three weeks without a touch, or that another is already past its close date? That signal is buried in the CRM, and nobody's watching it. That's the job I gave to a team of agents."

---

## Beat 2 — Why agents (~30s) · 0:40–1:10

**Shot:** Simple architecture slide (the ASCII diagram from the README, cleaned up).

**Voiceover:**
> "This is a multi-step, adaptive task: read the pipeline, assess risk, decide the next action, and sometimes write and log outreach. That's exactly where agents shine. So I built three: a coordinator that routes requests, a Pipeline Analyst that triages risk, and an Outreach Writer that drafts grounded emails. Each talks to the CRM through a custom MCP server."

---

## Beat 3 — Architecture (~45s) · 1:10–1:55

**Shot:** Keep the architecture diagram up; use a cursor/highlight to trace the flow.

**Voiceover:**
> "Here's the shape. The coordinator owns no tools — it just delegates. The Analyst and Writer each carry their own connection to the MCP server, which exposes three tools: get_deals, get_deal_details, and log_activity. Risk isn't guessed by the model — it's a pure, unit-tested function: a deal is at risk if it's been stale more than fourteen days or it's past its close date. And critically, the agents never read the raw data — only the tool surface. Swap in a real Salesforce API behind these tools and nothing upstream changes."

`[Highlight: get_deals / get_deal_details / log_activity, then risk_assessment()]`

---

## Beat 4 — Live demo (~2.5 min) · 1:55–4:25

**This is the heart of the video. Show the tool calls expanding in the `adk web` trace view each time.**

**4a — Triage (~50s).** Type: **"What deals are at risk?"**
> "I'll ask the co-pilot what's at risk. Watch the trace — the coordinator hands off to the Analyst, which calls get_deals, then pulls details on each flagged deal."

Point out in the answer:
> "Two deals, ranked by dollars at risk: Globex at $120k — no activity in over three weeks — then Initech at $32k, past its close date. And for each one, a single recommended next step, taken straight from the deal's notes."

**4b — Prioritize (~30s).** Type: **"What should I do first?"**
> "Same data, framed as a to-do list. It leads with the highest-value risk and tells me the one action that moves it."

**4c — Grounded drafting (~50s).** Type: **"Draft a follow-up for D-1003."**
> "Now a different kind of request — and the coordinator routes it to the Writer instead. It calls get_deal_details first, so the email uses the real contact, Samir, and the real open item: the 50-seat pricing sheet. Under 120 words, no invented promises."

`[Cut to crm.json to show the notes/contact match the email — proof of grounding]`

**4d — Security (~20s).** Confirm the send when the Writer asks.
> "When I approve, the Writer logs the outreach — but that write is authenticated. Watch the server log: the activity is recorded, and notice the contact's email is masked as 'redacted-email'. Reads are open; writes need a token; PII never hits the logs."

`[Cut to the stderr terminal: show the OK log line with [redacted-email]. Optionally show a denied write with a bad token.]`

---

## Beat 5 — The build & tech (~30s) · 4:25–4:55

**Shot:** Quick montage — repo tree, Dockerfile, `pytest` passing.

**Voiceover:**
> "Under the hood: Google's Agent Development Kit for the multi-agent system, a custom MCP server built with FastMCP, Gemini 2.5 Flash for reasoning, and a Docker image that deploys straight to Cloud Run. The risk logic is unit-tested, secrets stay out of git, and every file is commented. That's Pipeline Co-Pilot — four key concepts, one focused product. Thanks for watching."

---

## Shot list (quick reference)

| # | Visual | Purpose |
|---|---|---|
| 1 | `crm.json` scrolling | establish the buried-signal problem |
| 2 | Architecture diagram | coordinator → Analyst/Writer → MCP → data |
| 3 | `adk web` trace: "What deals are at risk?" | multi-agent delegation + read tools |
| 4 | `adk web`: "What should I do first?" | ranking by value at risk |
| 5 | `adk web`: "Draft a follow-up for D-1003" | routing to Writer + grounded drafting |
| 6 | `crm.json` vs. the drafted email | prove grounding (no hallucination) |
| 7 | Server stderr log | auth-gated write + `[redacted-email]` |
| 8 | Repo tree + Dockerfile + green `pytest` | the build / deployability |
