# Start Finishing Organiser (SFO)

Neon-themed, single-user organiser inspired by *Start Finishing*. Built on FastAPI, Jinja, and SQLite for quick iteration.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://localhost:8000 to see the prototype UI.

## Stack

- FastAPI + Jinja2
- SQLAlchemy + SQLite (`sfo.db`)
- Vanilla JS/CSS (Simulation Theory neon palette)

## Early feature map

- Projects (work/personal) with a soft 4+3 weekly cap.
- Tasks with Today/Week/Month/Later buckets, frogs, alignment, block types.
- Blocks to reserve Focus/Admin/Social/Recovery time.
- Success Packs and Waiting On slots (models in place; UI/APIs coming next).
- Health check at `/health`; JSON APIs under `/api`.

## Next steps

- Flesh out forms/POST flows on the UI for projects/tasks/blocks.
- Add gentle enforcement prompts for weekly caps and thrashing signals.
- Wire reflection/ritual prompts (morning/evening) into the interface.
- Expand docs (architecture/setup) and add basic tests.
