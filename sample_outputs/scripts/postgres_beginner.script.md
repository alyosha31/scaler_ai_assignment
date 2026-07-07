# Indexing in PostgreSQL

## Outline

70% beginner / 30% advanced. Lead with intuitive, vocabulary-scaffolded explanations and frequent comprehension checks. Layer in tradeoff discussions and internals for advanced learners as optional depth, without slowing the core narrative. Assume comfort with basic SQL and primary keys (do not re-teach them).

## 1. Segment

Welcome back, everyone. Before we dive in, let me confirm where we are: you're all comfortable with basic SQL — writing SELECT statements, filtering with WHERE — and you've seen primary keys. Good. Today we build directly on top of that foundation.

Let me start with a question that sounds almost too simple: when you run `SELECT * FROM users WHERE email = 'alice@example.com'`, what actually happens inside PostgreSQL? How does the database *find* that one row?

Here's an analogy to anchor us. Imagine I hand you a 900-page book with no table of contents and no index at the back, and I ask you to find every mention of the word 'photosynthesis.' What do you have to do? You start at page one and read every single page until you reach the end. You can't stop early, because there might be a match on the last page. That exhaustive, page-by-page reading is what we call a **sequential scan** — the database reads every row in the table to check which ones match.

Now imagine that same book *with* an index at the back. You flip to 'P', find 'photosynthesis — pages 44, 210, 388', and jump straight there. You skipped hundreds of pages. That back-of-the-book index is exactly what a database index is: a **separate lookup structure** that lets you find matching rows without reading the whole table.

So why does this matter? For a table with a hundred rows, a sequential scan is instant — who cares. But for a table with a million rows, reading every single one to answer one query is genuinely slow. That's the core problem indexes solve: the **cost of finding rows**.

Here's a useful piece of intuition I want you to hold onto — we call it **query cost**. Every query has a cost, roughly proportional to how much work the database does. A sequential scan's cost grows with the size of the table: twice the rows, roughly twice the work. An index scan's cost is much flatter — it barely grows as the table gets bigger. That difference is the whole game.

Now, a callback to primary keys, which you already know. When you query `WHERE id = 42` on a primary key, that's already fast. Why? Because a primary key is *automatically indexed* by PostgreSQL. You've been benefiting from an index this whole time without realizing it. The question we're really asking today is: what about all the *other* columns — like email — that aren't the primary key?

Let's make this concrete. I've got a `users` table here with about a million rows. Let's watch the database actually do the work.

[Run the live code steps here — poll first, then EXPLAIN before the index, then create the index, then EXPLAIN again.]

So what did we just see? Before the index: a Seq Scan reading through the whole table. After the index: an Index Scan that jumps almost straight to the row. Same query, dramatically less work.

Now one concept that ties this together: **selectivity**. An index is most valuable when your filter is *selective* — when it matches only a small fraction of rows. Filtering to one user out of a million? Extremely selective, index shines. But if you filter on something that matches half the table — say `WHERE active = true` where most users are active — the database might decide the index isn't worth it and just scan everything anyway. Hold that thought; it comes back later.

And for those of you who want to go deeper — here's the 'no free lunch' theme that runs through this entire topic. That index we created isn't free. It's a separate structure stored on disk, so it costs **storage**. And every time you INSERT, UPDATE, or DELETE a row, PostgreSQL has to update the index too — so it costs **write performance**. Indexes trade slower writes and more storage for faster reads. That tradeoff is a decision you make deliberately, not a switch you flip everywhere.

So to summarize: indexes exist because finding rows in a big table is expensive, and an index is a lookup structure that makes selective reads fast — at the cost of writes and storage.

## 2. Segment

Now that we know indexes speed up lookups, let's see the structure that makes it possible — the B-tree — and trace exactly how PostgreSQL walks it.

In the last segment we treated the index as a black box: a lookup structure that lets us avoid scanning every row. Let's open that box. When you create a plain index in PostgreSQL, by default you get a B-tree. The 'B' stands for 'balanced', and that balance is the whole trick.

Let me draw the shape of it. Picture a small pyramid. At the very top is a single node called the root. The root doesn't hold all your data — it holds a handful of key values and pointers that say, roughly, 'values less than 50 go left, values 50 and up go right.' One level down we have internal nodes, which do the same kind of routing but at finer granularity. At the very bottom we have leaf nodes, and the leaves are where the actual indexed key values live, in sorted order, each pointing to the row's location on disk.

Here's the key mental model: every level you descend narrows your search dramatically. Let's trace a lookup. Say we're searching for the value 73. We start at the root. The root says values 50 and up go right, so we follow that pointer. At the internal node we compare again — maybe it says 70 to 90 go down this branch. We follow that. Now we land in a leaf node, which holds a small sorted run of keys, and we find 73, which points us straight to the row. Three hops, and we're done.

Why does that matter? Because the tree is balanced and each node holds many keys, the height of the tree grows only logarithmically with the number of rows. Doubling your table doesn't double your lookup work — it adds at most one more hop. A table with millions of rows is typically only three or four levels deep. That's the difference between reading a few pages versus scanning the entire table, which is exactly the sequential-scan cost we talked about in Segment 1.

Now, here's the second big idea, and it's why B-trees are so useful beyond simple equality. The leaves are stored in sorted order and linked together. That means once you've found your starting point, you can just walk sideways through the leaves. This is huge for two query patterns: range queries — like 'give me everything between two dates' — and ORDER BY. If the data is already sorted in the index in the order you asked for, PostgreSQL can hand you rows in order without doing a separate sort step. Keep that in mind as we look at EXPLAIN in a moment.

Let's make this concrete with our users table from before. We'll compare an equality lookup, a range query, and an ordered query, and we'll read the plans together.

[After the equality and range demos] Notice how the range query used an 'Index Scan' or 'Index Range Scan' — it found the low end of the range in the tree, then walked the leaves rightward until it passed the high end. That sideways walk is the sorted structure paying off.

[After the ORDER BY demo] And here's the ORDER BY plan — see that there's no separate 'Sort' node? The index already stores things in order, so PostgreSQL just reads them off. That's a free sort, courtesy of the B-tree.

Now for a bit more depth — this next part is especially for those of you who've worked with indexes before, but everyone should follow the shape of the idea. Real queries often filter on multiple columns, so we create composite indexes, like an index on (last_name, first_name). The critical thing to understand is that a composite B-tree is sorted by the first column, then by the second within each value of the first — exactly like a phone book sorted by last name, then first name. This gives us the 'leftmost prefix' rule: the index can help a query that filters on last_name, or on last_name AND first_name, but it generally can't help a query that filters only on first_name. Why? Because first names are scattered all over the book once you ignore last name — there's no single place to start walking. Column order in a composite index is a design decision, not a formality.

One last thing that surprises people: sometimes you have a perfectly good index and PostgreSQL refuses to use it, choosing a Seq Scan instead. That's not a bug. Remember selectivity from Segment 1 — if your predicate matches a large fraction of the table, say 40% of rows, then hopping into the index and back out to fetch each row is actually more expensive than just reading the whole table sequentially. The planner does this cost math for you. So an index isn't a guarantee of an index scan; it's an option the planner weighs. Let's watch that happen live.

[Closing] You can now explain not just that indexes help, but how a B-tree finds rows and when it won't be used. Let's recap and look at where to go next.
