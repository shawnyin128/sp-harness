# Skill without procedural fixtures

This skill has no procedural-instruction fences and no worked-example
fences. The lint should pass trivially because no rule applies.

It may have other fences, like:

<!-- lint:disable=R7 -->
```output-template
This is governed by lint-skill-output, not procedural lint.
```

And regular code blocks:

```python
print("hello")
```

None of these are scanned by the procedural rules.
