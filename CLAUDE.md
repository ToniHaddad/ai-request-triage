# ai-request-triage

Intake form, transparent scoring model, routing rules and a ranked 90-day roadmap for AI help
requests at a fictional NGO (Northbridge Relief). FastAPI + SQLite + one self-contained page.
No API key, no LLM, no network needed.

## Run and test
- `pip install -e ".[dev]"`
- `python -m triage serve` (port 8107, seed data loaded into `triage.db` in the current folder)
- `python -m triage report` prints the ranked roadmap as text
- `pytest -q`

## Layout
- `triage/config.toml`: every weight, scale and threshold. The page reads it live.
- `triage/model.py`: scoring, the five written routing rules (`RULES`), `plan()` (ranking and
  capacity), `stability()` (seeded Monte Carlo), `what_would_change()` (sensitivity search).
- `triage/memo.py`: builds the memo and roadmap JSON. `triage/app.py`: API. `triage/store.py`: SQLite.
- `triage/seed.py`: the eight fictional requests. `triage/static/index.html`: the whole UI.
- `tests/`: one file per concern (scoring, routing, capacity, sensitivity, stability, seed, api).

## Rules for changes
- No request-specific code in `model.py`: seed outcomes must come from the general rules
  (a test checks the file for seed titles).
- Changing config or seed changes the pinned stability figures in `tests/test_stability.py`.
- Capacity counts build items (pilots and automations). Existing-capability training uses no slot.

## Quirks
- After editing a file within the same second, stale `.pyc` can survive; delete `__pycache__`.
- Sensitivity search tries one answer at a time. Items needing several changes say so.
