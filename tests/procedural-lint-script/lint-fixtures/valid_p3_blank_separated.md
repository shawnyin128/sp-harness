# Worked example with blank-line-separated list items

Regression guard: numbered list items separated by blank lines are a
common markdown style that still renders as a single ordered list.
P3 must accept this.

```procedural-instruction
- Cover the design.
```

```worked-example
Architecture is a single FastAPI service running on Python with
two tables: urls (slug, target, owner_id, created_at) and users
(id, email_hash, pw_hash). Rate limiter is a Redis sliding window
keyed by owner_id. Admin dashboard is a separate FastAPI sub-app
mounted under /admin, sharing the same DB pool. Data flow is request,
validate, persist, respond. Error handling uses structured exceptions
surfaced as HTTP problem details. Testing covers both happy path and
edge cases for authentication, rate limits, and slug collisions.
Filler filler filler filler filler filler filler filler filler.

1. First observation about the example with enough text.

2. Second observation about the example with enough text.

3. Third observation about the example with enough text.
```
