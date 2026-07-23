# Test-Driven Development (TDD)

**Core rule:** If you didn't watch the test fail, you don't know if it tests the right thing.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

## Red-Green-Refactor

### RED — Write Failing Test
- One behavior per test
- Clear descriptive name (contains "and"? Split it)
- Real code, not mocks (unless unavoidable)
- Name describes behavior, not implementation

### Verify RED — Watch It Fail (MANDATORY)
```bash
pytest tests/test_feature.py::test_specific_behavior -v
```
- Test fails (not errors from typos)
- Fails because feature is missing

### GREEN — Minimal Code
Write simplest code to pass. No extras (no logging, no features beyond test).

**Cheating is OK in GREEN:** hardcode, copy-paste, skip edge cases. Fix in REFACTOR.

### Verify GREEN — Watch It Pass
```bash
pytest tests/test_feature.py::test_specific_behavior -v
pytest tests/ -q  # Check regressions
```

### REFACTOR — Clean Up
- Remove duplication, improve names, extract helpers
- Keep tests green throughout
- If tests fail: undo immediately, smaller steps

## Common Rationalizations (All Invalid)

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. |
| "Already manually tested" | No record, can't re-run. |

## In subagent-driven-development

Enforce TDD in the goal:
```
Goal: "Implement [feature] using strict TDD"
Context: "Step 1: Write failing test FIRST. Step 2: Run to verify fail..."
```
