# Prose between the two fences

```procedural-instruction
- Cover the design.
```

This narrative paragraph sits between the procedural-instruction fence
and the worked-example fence below. It should trip P1 because only
blank lines are allowed between the pair.

```worked-example
Body of the worked example with enough words to satisfy P2 on its
own merits if it were properly paired. Architecture is a single
service with two tables. Data flow is request, validate, persist,
respond. Error handling uses structured exceptions surfaced as HTTP
problem details. Testing covers both happy path and edge cases for
authentication, rate limits, and slug collisions. Filler filler
filler filler filler filler filler filler filler filler filler.

1. Item one observation about the example.
2. Item two observation about the example.
3. Item three observation about the example.
```
