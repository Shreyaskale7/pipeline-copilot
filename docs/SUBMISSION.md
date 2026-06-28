# Submission guide — Vibe Coding Agents Capstone

Competition: <https://www.kaggle.com/competitions/vibecoding-agents-capstone-project>

> ⚠️ **Deadline is tight** — reported as **June 30** or **July 6, 2026, 11:59 PM PT** (sources conflict).
> Confirm the exact cutoff on the competition's Overview/Rules tab and submit early.

## What the competition requires
- A **Kaggle Writeup** (this is the submission itself).
- A **link to public code** — GitHub repo *or* Kaggle Notebook.
- A **card title + thumbnail image**.
- A short **rationale** + demonstrate **≥3 key concepts** (this project shows **4**).
- A **video** is **optional** → bonus points only. Not required for the certificate.

## Minimum valid submission = writeup + public GitHub link + thumbnail.

---

## Step 1 — Rotate your API key (do this first)
You shared the key in chat, so regenerate it at <https://aistudio.google.com/apikey>.
It lives only in `.env`, which is git-ignored and never pushed.

## Step 2 — Push the code to a PUBLIC GitHub repo
```bash
# create an empty PUBLIC repo named "pipeline-copilot" on github.com, then:
git branch -M main
git remote add origin https://github.com/<your-username>/pipeline-copilot.git
git push -u origin main
```
Then open the repo in a browser and confirm:
- `.env` is **absent**, `.env.example` is present.
- `README.md` renders correctly.

## Step 3 — Create the Kaggle Writeup
1. On the competition page, click **New Writeup**.
2. **Title:** Pipeline Co-Pilot — a multi-agent sales assistant.
3. **Thumbnail / card image:** upload `docs/thumbnail.png`.
4. **Body:** paste from `docs/WRITEUP.md`; replace each `[SCREENSHOT]` marker with a
   real screenshot (from `adk web` — see Step 4). At minimum include the architecture
   image and one "at-risk deals" answer.
5. **Code link:** add your GitHub URL.
6. **Name the 4 key concepts explicitly** so judges can check them off:
   multi-agent (ADK), custom MCP server, deployability (Docker/Cloud Run), security.
7. Click **Submit to competition** (a saved draft does NOT count).

## Step 4 — (Optional, for screenshots + the bonus video)
```bash
adk web .
```
Ask "What deals are at risk?" and "Draft a follow-up for D-1003"; screenshot the
trace showing the tool calls. For the bonus video, follow `docs/VIDEO_SCRIPT.md`,
upload to YouTube (Public or Unlisted), and add the link to the writeup.
Free-tier key = 5 requests/min — pace one prompt per minute.

---

## Final checklist
- [ ] API key rotated; `.env` not in the public repo
- [ ] Repo public; README renders; `.env.example` present
- [ ] Writeup has title + `thumbnail.png` + GitHub link
- [ ] Writeup names the 4 key concepts
- [ ] Writeup **submitted to the competition** (not just saved)
- [ ] Submitted before the deadline (verify exact UTC/PT time)
- [ ] (optional) Docker build verified locally; video on YouTube + linked
