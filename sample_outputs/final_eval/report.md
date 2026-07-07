# Class Script Pipeline Eval Report

- **Model**: claude-opus-4-8
- **Judge enabled**: True
- **Prompt hash**: `d1ee2d199da4`
- **Scenario count**: 3
- **Cases passed**: 3/3
- **Adaptivity pairs passed**: 1/1
- **Overall gate**: PASS

## Summary

| # | Case | Category | Structural | Judge | Red lines | Result |
|---|---|---|---|---|---|---|
| 1 | postgres_beginner | level_adaptivity | PASS | 5.00 | - | PASS |
| 2 | postgres_advanced | level_adaptivity | PASS | 5.00 | - | PASS |
| 3 | react_short_code_heavy | constraint_tension | PASS | 5.00 | - | PASS |

## Case Details

### PASS postgres_beginner

- **Project ID**: `project_83f71a5c0379`
- **Generation status**: READY_FOR_REVIEW
- **Project JSON**: `eval/results/claude-opus-4-8/2026-07-07T15-55-40/projects/postgres_beginner.project.json`
- **Script Markdown**: `eval/results/claude-opus-4-8/2026-07-07T15-55-40/scripts/postgres_beginner.script.md`

#### Guardrails

- **PASS** `agenda_coverage`: All agenda items are represented.
- **PASS** `timing_sum`: Outline totals 45 minutes; brief requested 45.
- **PASS** `content_code_ratio`: Actual code ratio 40%; target 40%.
- **PASS** `stable_segment_ids`: Every draft maps to a stable outline segment.
- **PASS** `must_cover_terms`: Expected terms appear in the script.
- **PASS** `prior_topic_not_retaught`: Prior topics are not obviously re-taught.
- **PASS** `checkpoint_presence`: Found 8 checks/activities; expected at least 1.
- **PASS** `live_code_when_required`: Found 10 live-code steps.
- **PASS** `reviewability_rationales`: Every segment includes reviewer rationale.

#### Model Judge

- **Overall**: 5.00
- **Average score**: 5.00
- **Red lines**: -
- **Rationale**: Both agenda items ('Why indexes exist' and 'B-tree index mechanics') are taught with genuine substance, not just named. Durations sum to 45 min (20+25) and content/code minutes (27/18) match the requested 60/40 split precisely. The beginner-heavy calibration is handled well: intuitive analogies (book index, phone book) scaffold vocabulary before any SQL, comprehension checks and prediction polls are front-loaded, and advanced content (write/storage tradeoff, composite leftmost-prefix rule, planner Seq-Scan under low selectivity) is layered as clearly-tagged optional depth for the 30% without derailing the core narrative. Prior topics (basic SQL, primary keys) are used only as callbacks — e.g., the auto-indexed primary key motivates the driving question — and are never re-taught. Pedagogical sequence is motivation-first then mechanics, which suits the audience. The narration is specific, voiced, and teachable, with concrete EXPLAIN ANALYZE steps, expected outputs, worked examples, checks, and facilitation notes an instructor could deliver directly. Live-code is realistic and progressive (equality, range, ORDER BY, composite, low-selectivity), with expected plan outputs. Reviewer rationales are detailed and defensible. No red lines triggered. This reads like a strong human instructor's script.

### PASS postgres_advanced

- **Project ID**: `project_05dd9345554b`
- **Generation status**: READY_FOR_REVIEW
- **Project JSON**: `eval/results/claude-opus-4-8/2026-07-07T15-55-40/projects/postgres_advanced.project.json`
- **Script Markdown**: `eval/results/claude-opus-4-8/2026-07-07T15-55-40/scripts/postgres_advanced.script.md`

#### Guardrails

- **PASS** `agenda_coverage`: All agenda items are represented.
- **PASS** `timing_sum`: Outline totals 90 minutes; brief requested 90.
- **PASS** `content_code_ratio`: Actual code ratio 40%; target 40%.
- **PASS** `stable_segment_ids`: Every draft maps to a stable outline segment.
- **PASS** `must_cover_terms`: Expected terms appear in the script.
- **PASS** `prior_topic_not_retaught`: Prior topics are not obviously re-taught.
- **PASS** `checkpoint_presence`: Found 10 checks/activities; expected at least 3.
- **PASS** `live_code_when_required`: Found 15 live-code steps.
- **PASS** `reviewability_rationales`: Every segment includes reviewer rationale.

#### Model Judge

- **Overall**: 5.00
- **Average score**: 5.00
- **Red lines**: -
- **Rationale**: All four agenda items are taught with real substance: motivation via a slow-query story, B-tree internals with a traced lookup and leftmost-prefix rule, EXPLAIN/EXPLAIN ANALYZE node-by-node reading, and index selection iterated across five index states. Timing sums to 90 minutes (15+27+26+22) and content/code split (54/36) matches the 60/40 brief closely per segment. Audience calibration is genuinely advanced-heavy: beginner scaffolding is a single quick vocabulary check on 'sequential scan,' after which the script pushes into write amplification, bitmap scans, estimated-vs-actual divergence, covering/partial indexes, and over-indexing tradeoffs. Sequence is coherent, with each segment building on the prior and prior topics (basic SQL, primary keys) only referenced, never re-taught. Live code is realistic and concrete—actual SQL, plausible EXPLAIN output, timing figures, INCLUDE and partial index syntax—each step proving a narrated claim rather than dumping syntax. Checkpoints and activities are meaningful (predict-the-traversal, spot-the-misestimate, design-and-verify, over-indexing debate). Instructor narration is specific, conversational, and teachable with clear facilitation notes and instructor guidance; reviewer rationales explain design decisions per segment. No red lines triggered.

### PASS react_short_code_heavy

- **Project ID**: `project_75ab84bd5df5`
- **Generation status**: READY_FOR_REVIEW
- **Project JSON**: `eval/results/claude-opus-4-8/2026-07-07T15-55-40/projects/react_short_code_heavy.project.json`
- **Script Markdown**: `eval/results/claude-opus-4-8/2026-07-07T15-55-40/scripts/react_short_code_heavy.script.md`

#### Guardrails

- **PASS** `agenda_coverage`: All agenda items are represented.
- **PASS** `timing_sum`: Outline totals 45 minutes; brief requested 45.
- **PASS** `content_code_ratio`: Actual code ratio 60%; target 60%.
- **PASS** `stable_segment_ids`: Every draft maps to a stable outline segment.
- **PASS** `must_cover_terms`: Expected terms appear in the script.
- **PASS** `prior_topic_not_retaught`: Prior topics are not obviously re-taught.
- **PASS** `checkpoint_presence`: Found 12 checks/activities; expected at least 1.
- **PASS** `live_code_when_required`: Found 19 live-code steps.
- **PASS** `reviewability_rationales`: Every segment includes reviewer rationale.

#### Model Judge

- **Overall**: 5.00
- **Average score**: 5.00
- **Red lines**: -
- **Rationale**: All five agenda items (local state, derived state, prop drilling, Context API, reducer pattern) are covered with real teaching substance, not just named. Durations sum exactly to 45 minutes (9+7+8+11+10), and each segment's content/code split honors the 60% code target (code minutes exceed content in every segment; ~18 content / ~27 code overall). Audience calibration is explicit and consistently executed: vocabulary scaffolding, 'prop or state?' checks, and radio-broadcast analogies serve the 65% beginners, while distinct advanced callouts (useMemo tradeoffs, Context re-render scope, useState-vs-useReducer, dispatch identity stability) genuinely differentiate the 35% advanced cohort — no R8 violation. Prior topics (components, props, event handlers) are reused as callbacks and never re-taught, so no R6. The pedagogical sequence is excellent: a cumulative refactoring ladder (like button → cart → user tree → Context → reducer) where each segment motivates the next, with the diagnose-before-fix pattern (spot-the-bug in derived state, feel-the-pain in prop drilling before Context). Checkpoints and discussions are meaningful and level-targeted throughout, so no R7. The narration reads like a genuine, teachable instructor script with anticipated misconceptions (double-setCount stale closure, 'reducer deletes from array' framing) and concrete facilitation notes — not generic AI prose, so no R9/R10. Live code is incremental, correct, and each step has explanation and expected output. Reviewer rationales are specific and tie decisions back to the brief. This is essentially what a strong human instructor would produce.

## Level Adaptivity

### PASS postgres_level_pair

- **Beginner case**: postgres_beginner
- **Advanced case**: postgres_advanced
- **Meaningfully different**: True
- **Too similar risk**: Low. Shared analogies (book index, phone book) and the same base narrative overlap slightly, but agenda scope (2 vs 4 items), duration (45 vs 90 min), depth, and code complexity diverge strongly enough to distinguish the two levels clearly.
- **Vocabulary**: The beginner-heavy script leans on extended plain-language analogies (900-page book with no index, phone contacts) and defines every term in bold before use ('sequential scan', 'query cost', 'selectivity', 'lookup structure'). The advanced-heavy script uses terminology tersely and introduces jargon like 'write amplification', 'TID', 'heap fetches', 'Bitmap Heap Scan', 'INCLUDE covering index', 'partial index', 'cardinality', and 'index-only scan' with minimal scaffolding, assuming the reader already parses these.
- **Pacing**: Beginner script spans 45 minutes over 2 segments with a slow motivation-first arc, frequent pauses, and repeated re-anchoring. Advanced script covers 90 minutes over 4 segments, compresses motivation into a single 15-min segment ('move quickly through motivation'), and spends the bulk of time on internals, EXPLAIN literacy, and index selection — a noticeably faster ramp with denser concept-per-minute loading.
- **Assumed knowledge**: Beginner version re-confirms comfort with SELECT/WHERE, treats EXPLAIN as brand-new, and explicitly notes learners have never seen index internals. Advanced version assumes fluency with EXPLAIN vocabulary as a starting point, layers estimated-vs-actual row divergence, bitmap scans, and planner cost math, and treats leftmost-prefix and read/write tradeoffs as callbacks rather than fresh teaching.
- **Examples**: Beginner examples stop at seq-scan vs index-scan on a users table and a single selectivity caveat. Advanced examples iterate a single query across five index states (none → single → composite → covering INCLUDE → partial), plus bitmap heap scans, functional-index distractors, index-only scans, and over-indexing tradeoff debates — substantially deeper and more branched.
- **Code complexity**: Beginner live code is 4 simple steps (EXPLAIN ANALYZE before/after a CREATE INDEX). Advanced code includes composite indexes with DESC ordering, INCLUDE covering indexes, partial indexes with WHERE clauses, \di+ size inspection, bitmap scan plans, and estimated-vs-actual analysis — clearly higher SQL and plan-reading complexity.
- **Checkpoints**: Beginner checkpoints are prediction polls and simple 'is this Seq Scan or Index Scan?' identification with generous, intuitive expected answers. Advanced checkpoints demand reasoning: why a function-wrapped column defeats an index, why a valid index is skipped due to selectivity, spotting estimated-vs-actual divergence, and designing an optimal composite+covering index — evaluative rather than recognition-level.
