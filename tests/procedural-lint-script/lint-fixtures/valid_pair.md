# Sample skill

## Section using fixtures

```procedural-instruction
- Once you understand what is being built, present the design.
- Cover architecture, components, data flow, error handling, testing.
- Scale each section to its complexity.
```

```worked-example
Suppose the user wants a URL shortener with admin dashboard. After
clarifying questions you understand: PostgreSQL backend, JWT auth,
rate limiting at one hundred requests per minute per user. The
"Presenting the design" output should look like the following.

Architecture. Single FastAPI service. Two tables: urls (slug, target,
owner_id, created_at) and users (id, email_hash, pw_hash). Rate
limiter is a Redis sliding window keyed by owner_id. Admin dashboard
is a separate FastAPI sub-app mounted under /admin, sharing the same
DB pool.

Three things this example does that abstract bullets do not enforce:

1. Each section names concrete files and tables, not abstract roles
   such as "the API layer" or "the storage tier".
2. The rate-limiter section says HOW it is implemented and KEYED BY
   WHAT. Not just "rate limiting".
3. The trade-off lives in the choice (Redis vs in-process), not in
   whether to have rate limiting at all.
```
