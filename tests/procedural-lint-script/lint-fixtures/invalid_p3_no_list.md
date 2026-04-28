# Worked example with no observation list

```procedural-instruction
- Cover architecture and trade-offs.
```

```worked-example
Architecture is a single FastAPI service. Two tables: urls and users.
Rate limiter is a Redis sliding window keyed by owner_id. Admin
dashboard is a separate sub-app mounted under /admin, sharing the
same DB pool. Data flow is request, validate, persist, respond.
Error handling uses structured exceptions. Testing covers happy path
and edge cases for authentication, rate limits, and slug collisions.
This body has plenty of words but no numbered observation list at
all. Filler filler filler filler filler filler filler filler filler
filler filler filler filler filler filler filler.
```
