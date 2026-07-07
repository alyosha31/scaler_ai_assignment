# Indexing in PostgreSQL

## Brief

- Duration: 90 minutes
- Audience: 20% beginner / 80% advanced
- Ratio: 60% content / 40% code

## Opening Frame

Audience is 80% advanced, 20% beginner. Move quickly through motivation, spend most time on B-tree internals, EXPLAIN plan reading, and index selection tradeoffs. Use minimal vocabulary scaffolding (one quick check early), then favor deeper examples, cost tradeoffs, and real EXPLAIN ANALYZE output. Assume comfort with basic SQL and primary keys.

## 1. The Cost of Full Scans: Why Indexes Exist

Timing: 15 min (11 content / 4 code)

**Transition in:** Open with a relatable pain point: a query that used to be fast is now crawling as data grew.

### Instructor Script

Let's start with a story that probably feels familiar. You ship a feature, everything is snappy in development, and the orders table has a few thousand rows. Six months later that same table has five million rows, and a query that used to return in milliseconds now takes several seconds. Nothing in your code changed. So what happened?

Here's the core issue: when you filter on a column that has no index, PostgreSQL has no shortcut. It has to look at every single row to decide which ones match your WHERE clause. That's a sequential scan—reading the table top to bottom. When you had a few thousand rows, scanning all of them was cheap. At five million rows, you're paying for every one of them on every query.

**Checkpoint:** Quick poll: I'm about to run the same query twice—once before adding an index and once after. Which will be faster, and by roughly how much: a little, or a lot?

- Expected: The indexed run will be faster, and for a selective filter on a 5M-row table it should be dramatically faster—orders of magnitude, not a small percentage.
- Facilitation: Take a quick show of hands or chat responses. Most will guess 'a lot'—use that to build anticipation for the demo. If anyone hedges toward 'a little,' note that the magnitude is exactly what surprises people and is why indexes matter. Keep under 90 seconds.

Quick vocabulary alignment before we go further, since we've got a range of backgrounds here.

**Checkpoint:** In one sentence, what does a 'sequential scan' mean in PostgreSQL?

- Expected: Postgres reads through every row in the table to find the ones matching the query, rather than using a shortcut.
- Guidance: Keep this to 20-30 seconds. Accept any answer that captures 'reads the whole table.' If someone says 'it's slow,' redirect: slow is the consequence, not the definition. This is the single beginner scaffold for the segment—don't dwell.

Good. So a sequential scan is Postgres reading the whole table. The alternative we want is an index scan, where Postgres uses a secondary data structure to jump more or less straight to the rows it needs. And that's the key mental model I want you to leave with: an index is an auxiliary data structure. It is a separate on-disk structure that Postgres maintains alongside your table, storing your column values in an organized, searchable order along with pointers back to the actual rows. It is not part of the table's own storage—it's an extra copy of specific columns kept in a shape that's fast to search.

Let me make this concrete instead of hand-wavy. I've got an orders table here with five million rows. Let's watch the difference.

**Live code 1: Run a filtered query against the unindexed created_at column and capture the timing.**

```text
\timing on
SELECT * FROM orders WHERE customer_id = 48213;
```
With no index on customer_id, Postgres must sequentially scan all 5M rows to find matches. Point out the wall-clock time in the output.

Notice that wall-clock time. Now let's give Postgres a shortcut.

**Live code 2: Create a B-tree index on the filtered column.**

```text
CREATE INDEX idx_orders_customer_id ON orders (customer_id);
```
This builds the auxiliary data structure. Mention it takes a moment because Postgres is reading the whole table once to construct the index, and this structure now lives on disk separately from the table.

And rerun the exact same query.

**Live code 3: Rerun the identical query and compare timing.**

```text
SELECT * FROM orders WHERE customer_id = 48213;
```
Same query, dramatically faster because Postgres can now use the index to locate matching rows directly instead of scanning all 5M. Contrast the new time against step 1.

That's the whole pitch for indexes in one demo—orders of magnitude faster on reads. But here's where I want the advanced folks especially to resist the temptation to index everything. An index is not free. Think about what has to happen on every INSERT, UPDATE, or DELETE: Postgres doesn't just modify the table row, it also has to keep every relevant index up to date. That's write amplification—one logical write becomes multiple physical writes because each index touching that column needs maintenance. On top of that, the index consumes real disk space; a large composite or covering index can rival the size of the table itself.

So the real framing for the rest of this session is a tradeoff, not a win. Indexes buy you read speed and pay for it with write cost and storage. Every index you add makes writes a little slower and your database a little bigger. The engineering skill is deciding which reads are worth that price. We'll spend the back half of today learning to make exactly that call with data instead of guesses.

**Worked example:** A 5M-row orders table with no index on customer_id, and a common lookup query filtering by a single customer.

First run the query as-is and note the multi-second sequential scan cost. Then create a B-tree index on customer_id and rerun the exact same query, observing the drop from seconds to milliseconds. Finally, discuss what Postgres now had to build and must maintain going forward.

- Takeaway: An index converts a full-table scan into a targeted lookup for reads, but it introduces an ongoing maintenance and storage cost that must be justified per query pattern.

**Transition out:** We saw indexes help dramatically—now let's open the hood on the most common index type to understand why.

## 2. Inside the B-tree: How Lookups Actually Work

Timing: 27 min (18 content / 9 code)

**Transition in:** Indexes helped—here's the data structure making that possible.

### Instructor Script

In the last segment we saw that an index scan crushed a sequential scan on a selective lookup. Good—but I don't want you treating the index as a magic box. Today we open the box. Because once you understand the *shape* of the data structure, you can predict, without running anything, which queries an index will accelerate and which it will quietly ignore.

Let me draw the structure. I'm sketching a tree here—three levels. At the very top, one node: the root. Below it, a handful of internal nodes. And at the bottom, a wide row of leaf nodes. This is a B-tree. Note it's a B-tree, not a binary tree—each node holds many keys, not just one, and it stays balanced: every leaf is at the same depth. That balance is the whole point.

Walk with me through what's actually stored. Each internal node holds sorted key values and pointers that say 'values less than 50 go left, values between 50 and 100 go here, values 100 and up go right.' The leaf nodes hold the indexed key values in sorted order, and alongside each key, a pointer—in Postgres terms, a TID—back to the actual row in the heap. So the index is a sorted, navigable map from key to row location.

Now let's do a lookup. Suppose I ask for the row where id = 73. I start at the root. I compare 73 against the separator keys, pick the child pointer whose range contains 73, drop down one level, compare again, drop to the leaf, and there's my key with its heap pointer. Notice how many comparisons that took: one per level. Three levels, three hops. And here's the beautiful part—because each node fans out to hundreds of children, a three-to-four level B-tree can index *hundreds of millions* of rows. Doubling your table doesn't double your lookup work; it maybe adds one level. That's logarithmic lookup. Sequential scan is linear—work grows with row count. Index lookup is logarithmic—work barely grows at all. That gap is why indexes matter at scale.

Now the part most people miss. Because the leaves are stored *in sorted order* and linked to their neighbors, a B-tree isn't just good at 'find one value.' It's good at anything that benefits from sorted order.

Equality—id = 73—one path down, done. Range—id BETWEEN 50 AND 200—find the start of the range, then just walk the linked leaves in order until you pass 200. No re-descending the tree. ORDER BY on the indexed column—the leaves are *already* in that order, so Postgres can read them in sequence and skip a sort entirely. That last one surprises people: an index can eliminate a sort step, not just a filter step.

Let me show you all of this live rather than just assert it.

**Live code 1: On a table 'accounts' with an indexed integer column 'id', run an equality lookup and a range query under EXPLAIN to show the index scan and range traversal.**

```text
EXPLAIN SELECT * FROM accounts WHERE id = 73;

EXPLAIN SELECT * FROM accounts WHERE id BETWEEN 50 AND 200;
```
The equality query descends the tree once. The range query finds the low bound then walks sorted leaves—point out that both show an Index Scan, and the range doesn't re-descend for each value.

So equality, range, and ordered traversal all fall out of the same sorted structure.

**Live code 2: Show the index serving an ORDER BY without a separate sort step.**

```text
EXPLAIN SELECT id FROM accounts ORDER BY id LIMIT 10;
```
Highlight the absence of a 'Sort' node. Because leaves are pre-sorted, Postgres reads them in order and stops after 10 rows—no sort, no full scan.

There's one more capability worth naming: the index-only scan. Normally after finding a key in the leaf, Postgres follows the pointer to the heap to fetch the rest of the row's columns. But if *every column your query needs* is already in the index, there's no reason to visit the heap at all—it can answer straight from the index. That's an index-only scan, and it's dramatically faster because it skips the heap fetch. Hold that thought; we'll exploit it deliberately with covering indexes in the final segment.

**Checkpoint:** You have a B-tree index on the column 'created_at'. Which of these can the index accelerate: (a) created_at = '2024-01-01', (b) created_at > '2024-01-01', (c) ORDER BY created_at, (d) DATE_PART('year', created_at) = 2024?

- Expected: a, b, and c can all use it; d cannot, because wrapping the column in a function destroys the sorted ordering the index relies on.
- Guidance: Push on (d) specifically—advanced learners should articulate that the index stores raw column values, not the function's output, so the sorted structure no longer maps to the query. Tease functional indexes as the fix without teaching them here.

Now the deeper topic, and this is where composite indexes bite people. Suppose I build an index on (last_name, first_name)—two columns, in that order. Think of it like a phone book: sorted by last name first, and *within* each last name, sorted by first name.

**Live code 3: Create a composite index and contrast two queries: one that respects the leading column and one that skips it.**

```text
CREATE INDEX idx_name ON people (last_name, first_name);

EXPLAIN SELECT * FROM people WHERE last_name = 'Nguyen' AND first_name = 'Maria';

EXPLAIN SELECT * FROM people WHERE first_name = 'Maria';
```
The first query uses idx_name via the leftmost prefix. The second, filtering only on first_name, cannot use it as an efficient tree descent—expect a Seq Scan. This is the phone-book intuition made concrete.

Here's the rule that governs everything: the leftmost-prefix rule. A B-tree on (a, b, c) can serve queries that filter on a, or on a and b, or on a, b, and c. It can serve a filter on a with a range on b. But it *cannot* efficiently serve a query that filters only on b, skipping a. Why? Go back to the phone book. If I ask 'find everyone whose first name is Maria,' the phone book is useless—Marias are scattered across every last name. The sort order only helps you if you constrain the leading column first. Same with the index: without a value for the leading column, there's no single contiguous range in the leaves to walk. So column order in a composite index is not cosmetic—it decides which queries the index can accelerate.

**Checkpoint:** Given an index on a single integer column, which of these four queries can use it, and why: point equality, a BETWEEN range, ORDER BY on that column, and a query needing only that column in its SELECT list?

- Expected: All four can use it: equality via descent, range via ordered leaf walk, ORDER BY via pre-sorted leaves, and the SELECT-only case via an index-only scan.
- Facilitation: Call on a couple of learners rapid-fire. The goal is to confirm they connect each query shape to the sorted-leaf structure rather than memorizing a list.

And remember the tradeoff we keep circling back to: every one of these indexes is a second sorted structure that must be updated on every insert, update, and delete of the indexed columns. The B-tree buys you logarithmic reads at the cost of extra write work and storage. That's the lever you're always pulling.

You now know what a B-tree *can* do—equality, ranges, ordered scans, index-only scans, and prefix matching on composites. Next we learn to read what Postgres actually *decides* to do, because knowing the capability and confirming the planner uses it are two different skills.

**Worked example:** A 3-level B-tree over an integer id column, drawn on the board: root with separators, internal nodes, sorted linked leaves each pointing to heap rows.

Trace id = 73: root comparison selects a child range, internal node comparison narrows further, leaf holds key 73 plus its heap TID. Count the three hops and connect to logarithmic growth versus linear sequential scan.

- Takeaway: Lookup cost scales with tree depth, not table size; high fan-out means depth grows extremely slowly.

**Discussion:** We have an index on (last_name, first_name). A query filters only on first_name and is slow. Why does the composite index fail to help, and what would you change?

- Expected: The leading column last_name isn't constrained, so there's no contiguous leaf range to walk—the phone-book problem. Fixes: reorder columns to (first_name, last_name) if that query pattern dominates, or add a separate index on first_name, weighed against write cost.
- Facilitation: Let learners debate reorder-vs-add-index. Steer toward 'it depends on which queries are hot' and flag that this is exactly the selectivity/ordering decision we'll formalize in the final segment.

**Transition out:** Now that you know what a B-tree can do, let's learn to read what Postgres actually decides to do.

## 3. Reading EXPLAIN and EXPLAIN ANALYZE

Timing: 26 min (15 content / 11 code)

**Transition in:** The planner is the judge of your indexes—let's learn its language.

### Instructor Script

The planner is the judge of your indexes—let's learn its language. Everything we've discussed so far—sequential versus index scans, how a B-tree lets us do logarithmic lookups—all of that is theory until PostgreSQL actually chooses a plan for your query. And the way it tells you what it decided is EXPLAIN. So in this segment our goal is simple but powerful: you'll be able to look at an EXPLAIN plan and read it like a sentence—what scan type ran, what it cost, and whether the planner's guesses matched reality.

Let's start with the core distinction. EXPLAIN alone shows you the plan the planner *intends* to use, with its cost estimates—it does not run the query. EXPLAIN ANALYZE actually *executes* the query and shows you both the estimates and the real numbers. Think of EXPLAIN as reading the recipe and EXPLAIN ANALYZE as cooking the dish and tasting it. The distinction matters enormously: EXPLAIN is cheap and safe, but its numbers are predictions. ANALYZE gives you ground truth—at the cost of actually running the statement, which you'll want to be careful about on writes or expensive queries in production.

Let's put a plan on screen.

**Live code 1: Run a plain EXPLAIN on an unfiltered query to see a baseline Seq Scan and name every field.**

```text
EXPLAIN
SELECT * FROM orders;
```
This is the simplest possible plan. Use it to introduce the node type (Seq Scan), the cost pair (startup..total), rows, and width. No predicate means nothing to filter, so we get the cleanest possible reading of the field vocabulary.

Now let's read this line by line, because every field earns its place. The node type at the top tells you the operation—here a Seq Scan. The `cost=0.00..431.00` is a pair: startup cost before the first row, and total cost to return all rows. These are arbitrary planner units, not milliseconds—don't confuse them with time. `rows=10000` is the planner's *estimate* of how many rows this node emits. `width=45` is the estimated average row size in bytes. Memorize that trio: cost, rows, width. You'll read it on every node.

Now let's make the plan choose an index instead of scanning everything.

**Live code 2: Add a highly selective equality predicate on an indexed column to trigger an Index Scan.**

```text
EXPLAIN
SELECT * FROM orders WHERE id = 4217;
```
With a unique or near-unique match, the planner expects one row and chooses an Index Scan. Point out the Index Cond line and contrast it with a Filter line so learners can distinguish index-satisfied conditions from post-fetch filtering.

See how the node changed to an Index Scan? That's the planner deciding the index is cheaper for this selective predicate—a direct callback to what we discussed about when an index beats a full scan. Notice the Index Cond line: that's the condition the index itself is satisfying, versus a Filter line which is applied after fetching rows.

Here's where it gets interesting for real workloads. When a predicate is neither highly selective nor totally unselective—say it matches five or ten percent of the table—PostgreSQL often picks something in between: a Bitmap Heap Scan.

**Live code 3: Use a medium-selectivity range predicate to produce a Bitmap Heap Scan.**

```text
EXPLAIN
SELECT * FROM orders WHERE amount BETWEEN 100 AND 250;
```
This predicate matches enough rows that a plain index scan's random I/O gets costly, but few enough that a full scan is wasteful. The planner builds a bitmap of matching heap pages, then reads them in physical order. Name both the Bitmap Index Scan and the Bitmap Heap Scan nodes.

Walk through what's happening: the Bitmap Index Scan builds an in-memory bitmap of which heap pages contain matching rows, then the Bitmap Heap Scan visits those pages in physical order. This is the planner's answer to 'too many rows for a plain index scan, too few to justify reading the whole table.' Medium selectivity is exactly the bitmap sweet spot.

And now the counterintuitive case that trips up even experienced engineers.

**Live code 4: Run EXPLAIN ANALYZE on a low-selectivity predicate where the planner ignores the index and picks a Seq Scan, and compare estimated vs actual rows.**

```text
EXPLAIN ANALYZE
SELECT * FROM orders WHERE amount > 10;
```
The predicate matches most of the table, so a Seq Scan wins despite an index on amount. ANALYZE also runs the query, so learners can see actual rows and actual time next to the estimates. Emphasize the estimated-vs-actual comparison as the key diagnostic.

The index exists—but the planner chose a Seq Scan anyway. Why? Because the predicate matches a large fraction of the table. Random heap fetches through an index become more expensive than just streaming the whole table sequentially. The planner isn't broken; it's doing cost-based math. This is the single most important lesson of the segment: an available index is not a used index.

**Checkpoint:** You have an index on the amount column, yet EXPLAIN shows a Seq Scan for WHERE amount > 10. Is this a bug, and what does it tell you about the predicate?

- Expected: It's not a bug. The predicate matches a large fraction of the table, so random heap fetches through the index would cost more than a sequential scan. Low selectivity means a full scan wins.
- Guidance: Reinforce that this is cost-based, not a failure. Ask the group whether making amount > 10000 (highly selective) would change the plan—it should flip to an Index or Bitmap scan. Tie back to the sequential-vs-index tradeoff from segment one.

Now, the reason EXPLAIN ANALYZE is your real diagnostic tool: it shows estimated rows *and* actual rows side by side. When those two numbers diverge wildly, that's your signal that the planner is working from bad statistics—and a bad estimate is the root cause of most bad plans you'll ever debug.

**Quick Exercise:** Look at this EXPLAIN ANALYZE fragment: 'Index Scan ... (cost=... rows=50 ...) (actual time=... rows=8400 loops=1)'. Where is the problem, and what is the likely root cause?

- Expected: The planner estimated 50 rows but 8400 actually came back—a large estimated-vs-actual divergence. The root cause is stale or insufficient statistics, which will lead the planner toward a poor plan choice for this and dependent nodes.
- Facilitation: Have learners point at the two rows= numbers specifically. Steer them to identify the divergence itself before speculating on causes. Mention ANALYZE (the maintenance command) refreshes statistics as the fix, but keep it brief—deeper tuning belongs to the next segment.

You can now read the plan; next we use it to make deliberate indexing decisions.

**Worked example:** Same orders table used earlier, roughly 10,000 rows, with a primary key index on id and a B-tree index on amount.

We progressively tightened and loosened the predicate: an equality on id produced an Index Scan (one row expected), a mid-range BETWEEN produced a Bitmap Heap Scan (medium selectivity), and a broad amount > 10 produced a Seq Scan even though an index existed. At each step we read the node type, the cost pair, rows, and width, then under ANALYZE compared estimated rows against actual rows.

- Takeaway: The scan type the planner chooses is a direct function of estimated selectivity. An index existing does not mean it will be used; the planner does cost math, and when estimates are wrong, the plan is wrong.

**Transition out:** You can now read the plan; next we use it to make deliberate indexing decisions.

## 4. Choosing the Right Index for Real Queries

Timing: 22 min (10 content / 12 code)

**Transition in:** Now let's turn plan-reading into concrete indexing decisions.

### Instructor Script

Now let's turn plan-reading into concrete indexing decisions. Everything we've done so far — understanding sequential versus index scans, walking the B-tree, reading EXPLAIN — was building toward this moment: given a real query, what index do I actually create, and how do I prove it was the right call?

Let me start with the single most important word in this segment: selectivity. Selectivity is the fraction of rows a condition keeps. If a column has a million rows and your filter matches ten of them, that's highly selective — great index candidate. If your filter matches half the table, that's low selectivity, and the planner may well decide a sequential scan is cheaper than an index scan plus all those heap fetches. Related to that is cardinality — the number of distinct values in a column. High cardinality columns like email or user_id tend to be selective; low cardinality columns like a boolean flag or a status with three values usually aren't, at least not uniformly. Hold onto that word 'uniformly' — it's going to matter when we get to partial indexes.

So the mental model I want you to carry: an index earns its keep when it lets Postgres touch dramatically fewer rows than the table has. That's the read benefit. But remember from our first segment — every index is write amplification. Every INSERT, UPDATE, and DELETE has to maintain that index. So indexing is always a read-versus-write trade, and our job is to make that trade deliberately, not accidentally.

Let's make this real with a query pattern you will see constantly: filter on one column, sort by another. We have an orders table, and we want the recent orders for a given status.

**Live code 1: Run the baseline query with no supporting index and read the plan.**

```text
EXPLAIN ANALYZE
SELECT id, customer_id, total
FROM orders
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;
```
Establishes the pain: without an index Postgres scans the whole table and adds a Sort node. Point at the Seq Scan and the Sort so learners connect plan nodes to cost.

Look at that plan — a Seq Scan, and a Sort node on top. Postgres read the whole table and then sorted it in memory. On a big table that's exactly the cost we're trying to avoid.

First instinct: index the filter column.

**Live code 2: Add a single-column index on the filter column and re-run.**

```text
CREATE INDEX idx_orders_status ON orders (status);

EXPLAIN ANALYZE
SELECT id, customer_id, total
FROM orders
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;
```
Shows partial improvement: an Index Scan (or Bitmap) narrows rows, but the Sort node remains because the index gives no ordering by created_at.

Better — we get an Index Scan on status now, but notice the Sort node is still sitting there. We narrowed the rows but Postgres still has to order them by created_at. We solved half the problem.

This is where composite ordering strategy comes in, and it ties directly back to the leftmost-prefix rule we covered in the B-tree segment. If I build an index on (status, created_at), the index is already sorted by status first, then by created_at within each status. That means Postgres can seek to the status we want AND read the rows back in created_at order — no separate sort.

**Live code 3: Replace with a composite index ordered for equality-then-sort and re-run.**

```text
DROP INDEX idx_orders_status;
CREATE INDEX idx_orders_status_created ON orders (status, created_at DESC);

EXPLAIN ANALYZE
SELECT id, customer_id, total
FROM orders
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;
```
Demonstrates the leftmost-prefix payoff: equality column first, ordering column second. The Sort node disappears because the index already returns rows in order.

There it is — the Sort node is gone. The equality column goes first, the range-or-sort column goes second. That's the rule of thumb: equality columns lead, range and ordering columns follow.

**Checkpoint:** For a query with WHERE region = 'EU' AND price > 100 ORDER BY price, in what order should the composite index columns go, and why?

- Expected: region first (equality), then price (range/ordering). The leftmost-prefix rule lets Postgres seek on the equality column and then read the range in sorted order, avoiding a separate Sort.
- Guidance: Listen for the equality-before-range principle. If someone puts price first, show that region can no longer be used as an efficient seek and the equality benefit is lost. Reinforce the callback to the leftmost-prefix rule from segment 2.

Now, can we do even better? Look at what the query actually returns. If we're selecting a couple of columns, Postgres still has to visit the heap to fetch them, because the index only holds status and created_at. That's where covering indexes come in. Using INCLUDE, we can carry extra columns in the leaf nodes of the index without making them part of the search key.

**Live code 4: Add a covering index with INCLUDE to enable an Index Only Scan.**

```text
DROP INDEX idx_orders_status_created;
CREATE INDEX idx_orders_covering
  ON orders (status, created_at DESC)
  INCLUDE (id, customer_id, total);

EXPLAIN ANALYZE
SELECT id, customer_id, total
FROM orders
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;
```
The returned columns now live in the index leaves, so Postgres answers from the index alone. Highlight the 'Index Only Scan' node and the disappearance of heap fetches (Heap Fetches: 0 after vacuum).

Now watch — the plan says Index Only Scan. Postgres answered the entire query from the index and never touched the table heap. That's the fastest read path we have. The caveat: INCLUDE columns add width to every leaf page, so don't stuff your whole row in there — include only what that hot query needs.

Let me address the skew case, because it's incredibly common. Suppose 95% of your orders are status 'completed' and you almost always query for 'pending'. Indexing all statuses wastes space and write cost on the 95% you never filter for. A partial index solves this — you index only the rows matching a WHERE clause.

**Live code 5: Create a partial index for a skewed, rarely-matched status value.**

```text
CREATE INDEX idx_orders_pending_partial
  ON orders (created_at DESC)
  WHERE status = 'pending';

EXPLAIN ANALYZE
SELECT id, customer_id, total
FROM orders
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;
```
Shows a tiny, write-cheap index that only covers the rows we query. Note the planner uses it when the query predicate matches the partial WHERE clause, and compare its size with \di+ to make the storage savings concrete.

That index is tiny, it's cheap to maintain, and the planner uses it whenever your query's predicate matches the partial index's condition. Small, targeted, and it barely taxes writes.

Which brings us to the discipline half of this segment: over-indexing. Every index you add speeds some reads and slows every write. On a write-heavy table, a fifth or sixth index can quietly become your bottleneck — INSERT latency climbs, autovacuum works harder, and disk usage balloons. So before adding an index, ask three questions: Is there a real query that needs it? Is the filter selective enough to help? And can the write path afford it? If you can't answer all three, don't add it.

**Discussion:** You maintain an events table that ingests thousands of rows per second and already has four indexes. A reporting team asks for a fifth index to speed up a dashboard query they run twice a day. Do you add it? Argue both sides.

- Expected: A thoughtful answer weighs the twice-daily read benefit against per-write maintenance cost on a high-ingest table. Alternatives include a partial or covering index scoped tightly, running the report on a replica, or a materialized view — rather than a full new index on the hot write path.
- Facilitation: Push students to quantify: how selective is the dashboard filter, and what's the write volume? Steer them toward the three-question test (real query, selective enough, writes can afford it). Reward answers that propose scoping the index or moving reads off the primary.

Let's consolidate the decision framework and where to go next.

**Worked example:** A query filtering on status and sorting by created_at DESC with a LIMIT, run against a large orders table.

Iterate through four index states — none, single-column, composite (status, created_at DESC), and covering with INCLUDE — reading the EXPLAIN plan at each step to observe the Sort node vanishing and the scan progressing from Seq Scan to Index Only Scan.

- Takeaway: The best index mirrors the query shape: equality columns lead, ordering columns follow, and INCLUDE eliminates heap trips when a specific hot query dominates.

**Quick Exercise:** Given SELECT id, total FROM orders WHERE customer_id = $1 AND status = 'shipped' ORDER BY created_at DESC, design the single best index and predict the plan node, then verify with EXPLAIN ANALYZE.

- Expected: An index on (customer_id, status, created_at DESC) INCLUDE (id, total), producing an Index Only Scan with no Sort node.
- Facilitation: Give 3-4 minutes. Common miss: forgetting INCLUDE and still getting an Index Scan with heap fetches. Have one student share their CREATE INDEX and run it live to confirm the predicted node.

**Transition out:** Let's consolidate the decision framework and where to go next.

## Recap

Summarize the arc: indexes trade write/storage cost for read speed; B-trees enable log-time lookups, ranges, ordered scans, and index-only scans with leftmost-prefix rules; EXPLAIN/ANALYZE reveals what the planner actually does and where estimates go wrong; index choice follows from selectivity, query shape, and verified plans. Reinforce with a one-slide decision checklist.

## Next

Point to next sessions and practice: GIN/GiST/BRIN index types, index maintenance (bloat, REINDEX), ANALYZE/statistics and planner tuning, and a hands-on assignment to profile and index a provided slow-query workload using EXPLAIN ANALYZE.
