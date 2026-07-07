# Scaler Class Script Authoring Pipeline

Outline-first backend for generating, evaluating, reviewing, regenerating, and signing off instructor class scripts.

## Setup

```bash
uv sync
cp .env.example .env
```

Set `ANTHROPIC_API_KEY` in `.env`.

## Run Backend

```bash
uv run uvicorn scaler_script_pipeline.main:app --reload
```

Open API docs at `http://127.0.0.1:8000/docs`.

## Run Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

The frontend defaults to `http://127.0.0.1:8000` for the API. Override with:

```bash
VITE_API_BASE=http://127.0.0.1:8000 npm run dev
```

## Main Endpoints

```text
GET    /health
POST   /projects
GET    /projects
GET    /projects/{project_id}
POST   /projects/{project_id}/segments/{segment_id}/edit
POST   /projects/{project_id}/segments/{segment_id}/regenerate
POST   /projects/{project_id}/evaluate
POST   /projects/{project_id}/sign-off
GET    /projects/{project_id}/export/markdown
```

`POST /projects` runs the full generation pipeline before returning:

```text
validate brief
-> generate outline
-> generate segment drafts
-> repair obvious segment-local failures once
-> run evaluation
-> if eval fails, plan targeted segment repairs and regenerate affected segments once
-> rerun evaluation
-> return READY_FOR_REVIEW or NEEDS_REVISION
```

The frontend displays the project only after it has been generated and evaluated, so instructors do not review raw model output.

## Run Evals

The eval harness is designed for repeatable regression testing: scenario files, timestamped result directories, raw generated artifacts, a Markdown report, and a process exit code gate.

Structural-only evals skip judge calls:

```bash
uv run python scripts/run_evals.py --structural-only
```

Run one case:

```bash
uv run python scripts/run_evals.py --structural-only --case postgres_beginner
```

Re-evaluate saved project JSON without regenerating:

```bash
uv run python scripts/run_evals.py \
  --structural-only \
  --case postgres_beginner \
  --from-projects eval/fixtures/projects
```

Full evals include the LLM judge and level-adaptivity pair judge:

```bash
uv run python scripts/run_evals.py
```

Outputs are written to:

```text
eval/results/<model>/<timestamp>/
  report.md
  results.json
  projects/
  scripts/
```

The deterministic guardrails check agenda coverage, timing, content/code ratio, stable segment IDs, required topic coverage, prior-topic re-teaching, checkpoint presence, live-code presence, and reviewer rationale coverage.

## Example Brief

```json
{
  "topic": "Indexing in PostgreSQL",
  "agenda": [
    "Why indexes exist",
    "B-tree index mechanics",
    "Reading EXPLAIN plans",
    "Choosing indexes for common queries"
  ],
  "beginner_percentage": 70,
  "advanced_percentage": 30,
  "duration_minutes": 90,
  "content_percentage": 60,
  "code_percentage": 40,
  "topics_already_covered": ["basic SQL", "primary keys"]
}
```

## Design Docs

- `DESIGN.md`
- `FRONTEND_DESIGN.md`
