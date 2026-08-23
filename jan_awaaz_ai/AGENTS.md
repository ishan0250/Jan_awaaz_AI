# Agent Instructions — Jan-Awaaz AI

These instructions apply to any AI agent (Antigravity, Gemini, or otherwise)
working in this repository. Read this file fully before making changes.

## Non-negotiable architecture rules

1. **`data_store/db.py` is the ONLY file allowed to read or write ticket
   data.** No page, no module, no "helper" may open the SQLite DB directly
   or store ticket data in `st.session_state`. `session_state` is reserved
   for transient UI state only (form drafts, active tab, simulator clock).
   This rule exists because breaking it previously caused the citizen
   portal and officer dashboard to go out of sync. Do not "simplify" this
   by moving ticket storage back into session_state, even temporarily.

2. **`core/` must never import `streamlit`.** It's the business-logic layer
   and stays unit-testable without a running app. If a change to `core/`
   seems to require a Streamlit import, that logic belongs in `pages/`
   instead.

3. **Do not change the RPI formula, SLA tiers, or department taxonomy
   without being asked explicitly.** These live in `config.py` and
   `core/scoring_engine.py` and were deliberately calibrated — see
   `README.md` → "Scoring methodology" and
   `pages/4_Compliance_Reference_Drawer.py` for the reasoning. If asked to
   tune them, edit `config.py` only; don't hardcode new numbers elsewhere.

4. **Never delete or rewrite a whole file to make a small change.** Use
   targeted edits. If a file genuinely needs a full rewrite, say so and
   explain why before doing it, don't do it silently as a side effect of
   an unrelated task.

## Required workflow for every task

1. **State the plan before editing.** List which files you intend to
   touch and why. Wait for confirmation on anything that touches more
   than 2 files or any file in `core/` or `data_store/`.
2. **Run `pytest tests/` before AND after every change.** If a test that
   passed before your change now fails, that's a regression — fix it or
   revert, don't proceed to the next task with a broken test suite.
3. **Never claim something works without running it.** If you can't run
   it (e.g. no API key available), say so explicitly instead of assuming
   success.
4. **Keep changes scoped to what was asked.** Don't refactor unrelated
   files "while you're in there." If you notice something else that looks
   wrong, mention it and ask, don't fix it unprompted.
5. **Commit after every working increment**, with a message describing
   what changed and that tests pass. Small, reversible commits are the
   actual safety net here — if something breaks two tasks from now, we
   can find exactly which commit did it.

## Known scope decisions — don't "fix" these, they're intentional

- WhatsApp has TWO real tiers: a zero-backend click-to-chat link
  (`core/whatsapp_gateway.build_click_to_chat_link`) and a live webhook
  (`webhook_server.py`) using Meta's free test number. Neither is a
  simulation — both are real. IVR (phone calls) is genuinely out of scope,
  don't try to add it.
- `webhook_server.py` is a SEPARATE process from `app.py` (FastAPI, not
  Streamlit — Streamlit can't receive external webhooks). Don't try to
  merge them into one process.
- Meta sends text/image/audio/location messages to the SAME `/webhook`
  route with different `type` fields — don't split this into separate
  routes per message type, that's not how Meta's API works.
- Department routing uses keyword matching (`core/routing_engine.py`), not
  a classifier. This is a deliberate hackathon-speed tradeoff.
- The demo DB (`data/jan_awaaz.db`) is gitignored and regenerates with
  seed data on first run. Don't commit it.

## If you (the agent) think a rule above is wrong

Say so and explain why, then wait for a human decision. Don't override it
unilaterally.
