# Worked example with too-short observation list

```procedural-instruction
- Cover the design.
```

```worked-example
Architecture is a single FastAPI service. Two tables: urls and users.
Rate limiter is a Redis sliding window keyed by owner_id. Admin
dashboard is a separate sub-app mounted under /admin, sharing the
same DB pool. Data flow is request, validate, persist, respond.
Error handling uses structured exceptions. Testing covers happy path
and edge cases. Filler filler filler filler filler filler filler
filler filler filler filler filler filler filler filler filler.

1. Item one observation about the example.
2. Item two observation about the example.
```
