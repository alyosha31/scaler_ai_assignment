# AI Tutor Class Script Authoring Pipeline

Outline-first application for generating, evaluating, reviewing, partially regenerating, and signing off instructor-ready live class scripts.

The system accepts a structured instructor brief, generates a class outline, drafts one script segment per agenda item, runs deterministic and LLM-based evals, supports instructor edits/regeneration, and locks the script after final sign-off.

## Prerequisites

- Python 3.11+
- `uv`
- Node.js 20+
- npm
- Anthropic API key

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Repository Setup

From the repository root:

```bash
uv sync
cp .env.example .env
```

Set the Anthropic key in `.env`:

```bash
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-opus-4-8
DATABASE_URL=sqlite:///./data/script_pipeline.db
MODEL_JUDGE_ENABLED=true
TRACE_ENABLED=true
TRACE_DIR=./data/traces
```

Frontend setup:

```bash
cd frontend
npm install
```

## Run The App

Terminal 1, backend:

```bash
cd /path/to/ai_tutor
uv run uvicorn ai_tutor.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend API docs:

```text
http://127.0.0.1:8000/docs
```

Terminal 2, frontend:

```bash
cd /path/to/ai_tutor/frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173
```

The frontend defaults to `http://127.0.0.1:8000`. To override:

```bash
VITE_API_BASE=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173
```

## First Request Schema

`POST /projects` accepts:

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

Required fields:

- `topic`
- `agenda`
- `beginner_percentage`
- `advanced_percentage`
- `duration_minutes`
- `content_percentage`
- `code_percentage`

Optional field:

- `topics_already_covered`, default `[]`

Validation behavior:

- Audience percentages must sum to 100.
- Content/code percentages must sum to 100.
- Duration supports 5 to 240 minutes.
- Dense agendas and short code-heavy lessons are warnings, not hard failures.
- Missing prior topics is allowed and becomes a warning so the generator does not invent callbacks.

## Application Flow

`POST /projects` runs the complete synchronous generation pipeline:

```text
validate brief
-> generate class outline
-> generate segment drafts
-> repair obvious segment-local failures once
-> run evaluation
-> if eval fails, plan targeted segment repairs and regenerate affected segments once
-> rerun evaluation
-> return READY_FOR_REVIEW or NEEDS_REVISION
```

The frontend displays the project only after generation and evaluation complete, so instructors do not review raw unevaluated model output.

Saved state is persisted to SQLite after major checkpoints:

- project creation
- validation
- outline generation
- each generated segment
- evaluation
- repair attempts
- final status
- instructor edits/regeneration/sign-off

If generation fails midway, the failed project remains inspectable with any outline/segments already saved.

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
GET    /traces
GET    /traces/{trace_id}
```

After sign-off, the backend rejects edit/regenerate calls with `409 Conflict`. The frontend also disables edit/regenerate controls for signed-off projects.

## Frontend Features

- Empty instructor brief form with example placeholders.
- Project browser for previously generated projects.
- Segment sidebar.
- Inline teachable script rendering.
- Inline live-code/checkpoint/activity placement using `[CODE_STEP]`, `[CHECKPOINT]`, and `[ACTIVITY]` markers.
- Worked examples, transitions, recap, and next steps.
- Previous/next segment navigation.
- Segment edit flow.
- Segment-level regeneration flow.
- Evaluation panel.
- Review history.
- Final sign-off and markdown export.

## Module Guide

Backend:

```text
src/ai_tutor/main.py
  FastAPI app creation, CORS, request logging.

src/ai_tutor/api/routes.py
  HTTP routes for projects, segment edits/regeneration, evaluation, sign-off, export.

src/ai_tutor/api/dependencies.py
  Wires settings, repository, Claude client, validator, evaluator, and pipeline.

src/ai_tutor/core/config.py
  Environment-backed settings from .env.

src/ai_tutor/core/models.py
  Pydantic domain models: InstructorBrief, ClassOutline, SegmentDraft, EvaluationReport, ReviewEvent, SignOff.

src/ai_tutor/storage/repository.py
  SQLite persistence using SQLAlchemy. Stores project JSON blobs.

src/ai_tutor/services/validator.py
  Hard validation errors and soft pedagogical warnings for instructor briefs.

src/ai_tutor/services/prompts.py
  Prompt builders for outline generation, segment generation, regeneration, judging, and repair planning.

src/ai_tutor/services/claude.py
  Anthropic API wrapper with structured JSON parsing and request logging.

src/ai_tutor/services/evaluator.py
  Runtime deterministic checks and optional model judge gate.

src/ai_tutor/services/pipeline.py
  Main orchestration: generate, repair, evaluate, edit, regenerate, sign off, export.
```

Eval harness:

```text
scripts/run_evals.py
  CLI entrypoint for eval runs.

src/ai_tutor/evals/types.py
  Eval scenario, guardrail, judge result, pairwise adaptivity result models.

src/ai_tutor/evals/structural.py
  Deterministic guardrails.

src/ai_tutor/evals/judge.py
  LLM-as-judge prompts for script quality and level adaptivity.

src/ai_tutor/evals/runner.py
  Loads scenarios, generates or loads projects, runs guardrails/judges, writes artifacts.

src/ai_tutor/evals/reporter.py
  Markdown and JSON eval report generation.

eval/scenarios/script-generation-cases.json
  Script-generation eval scenarios.

eval/scenarios/level-adaptivity-pairs.json
  Beginner-vs-advanced pairwise adaptivity eval definitions.
```

Frontend:

```text
frontend/src/App.tsx
  Main React app, brief form, project browser, review workspace, segment panel, sign-off UI.

frontend/src/App.css
  Application styling.

frontend/src/api.ts
  Backend API client.

frontend/src/types.ts
  TypeScript representations of backend response models.

frontend/src/main.tsx
  React entrypoint.
```

Docs and artifacts:

```text
DESIGN.md
  Backend architecture and class hierarchy.

FRONTEND_DESIGN.md
  Frontend interaction model and screen flow.

sample_outputs/projects/
  Committed generated project JSON for three scenarios.

sample_outputs/scripts/
  Committed generated markdown scripts for three scenarios.

sample_outputs/final_eval/
  Committed full eval report and JSON results.
```

## Run Checks

Backend syntax/import check:

```bash
uv run python -m compileall src scripts
```

Frontend production build:

```bash
cd frontend
npm run build
```

Optional frontend lint:

```bash
cd frontend
npm run lint
```

## Run Evals

The eval harness writes timestamped artifacts to:

```text
eval/results/<model>/<timestamp>/
  report.md
  results.json
  projects/
  scripts/
```

These generated eval results are ignored by git. Stable submission artifacts are committed under `sample_outputs/`.

### Fast Deterministic Eval

Runs local guardrails only. No Claude judge calls.

```bash
uv run python scripts/run_evals.py \
  --structural-only \
  --from-projects sample_outputs/projects
```

Run one deterministic eval case:

```bash
uv run python scripts/run_evals.py \
  --structural-only \
  --case postgres_beginner \
  --from-projects sample_outputs/projects
```

### Full Judge Eval From Saved Outputs

Runs deterministic guardrails plus LLM judges, but does not regenerate projects.

```bash
uv run python scripts/run_evals.py \
  --from-projects sample_outputs/projects
```

Run one full judge case:

```bash
uv run python scripts/run_evals.py \
  --case postgres_beginner \
  --from-projects sample_outputs/projects
```

### Fresh Generation Eval

Regenerates outputs from scenarios. This is slow because it calls Claude for outline and segment generation.

```bash
uv run python scripts/run_evals.py --structural-only
```

Fresh generation plus LLM judges:

```bash
uv run python scripts/run_evals.py
```

Run one fresh scenario:

```bash
uv run python scripts/run_evals.py \
  --structural-only \
  --case react_short_code_heavy
```

Available case IDs:

```text
postgres_beginner
postgres_advanced
react_short_code_heavy
```

The deterministic guardrails check:

- agenda coverage
- timing sum
- content/code ratio
- stable segment IDs
- required term coverage
- prior-topic re-teaching
- checkpoint/activity presence
- live-code presence when code is required
- reviewer rationale coverage
- content density, using narration words/content-minute, live-code steps/code-minute, and concepts/minute

The LLM judge checks:

- coverage
- faithfulness
- level fit
- pedagogy
- teachability
- pacing
- tone
- code quality
- reviewability
- beginner-vs-advanced adaptivity

## Committed Eval Evidence

Final committed eval report:

```text
sample_outputs/final_eval/report.md
```

Latest committed result summary:

```text
Cases passed: 3/3
Pairs passed: 1/1
Gate: PASS
```

## Logs

The backend logs to the terminal running Uvicorn. Logs include:

- HTTP request start/end with request ID and elapsed time
- project generation start/end/failure
- validation warning/error counts
- outline generation
- segment generation progress
- Claude request start/end/error
- structural eval results
- model judge scores
- repair planning and repair attempts
- edits/regeneration/sign-off

## Traces And Observability

The app writes local LangSmith-style trace artifacts for every Claude call when `TRACE_ENABLED=true`.

Trace files are stored as JSON under:

```text
data/traces/
```

Each trace contains:

- trace id
- span name, such as `outline_generation`, `segment_generation`, `runtime_model_judge`
- kind, currently `llm`
- status
- started/ended timestamps
- elapsed milliseconds
- project id and segment id metadata when available
- model and response schema
- full system prompt
- full user prompt
- schema requested from the model
- raw model output
- parsed Pydantic output
- error details if parsing/API failed

List recent traces:

```bash
curl -s "http://127.0.0.1:8000/traces?limit=20" | python -m json.tool
```

Filter traces for one project:

```bash
curl -s "http://127.0.0.1:8000/traces?project_id=project_123&limit=50" | python -m json.tool
```

Inspect one trace:

```bash
curl -s "http://127.0.0.1:8000/traces/trace_123" | python -m json.tool
```

Watch traces live as they complete:

```bash
curl -N "http://127.0.0.1:8000/traces/stream"
```

Watch traces live for one project:

```bash
curl -N "http://127.0.0.1:8000/traces/stream?project_id=project_123"
```

This gives traceability across the generation pipeline: brief input, outline prompt/output, per-segment prompt/output, repair prompts, runtime judge calls, and offline eval judges.

Logs and traces serve different purposes:

- Logs are operational breadcrumbs: request started, segment generated, eval failed, elapsed time.
- Traces are model-call evidence: exact prompt input, requested schema, raw model output, parsed model object, metadata, timing, and error if any.

In practice, logs answer "what happened?" while traces answer "why did this model call produce that artifact?"

## Data And Secrets

Ignored local files:

```text
.env
data/
eval/results/
data/traces/
frontend/node_modules/
frontend/dist/
```

SQLite database defaults to:

```text
data/script_pipeline.db
```

Never commit `.env`; use `.env.example` as the public template.

## Design Documents

- `DESIGN.md`
- `FRONTEND_DESIGN.md`
