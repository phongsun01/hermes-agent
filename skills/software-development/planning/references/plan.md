# Plan Mode

When the user wants a plan instead of execution. No code, no file edits (except the plan file).

## Output

Save to `.hermes/plans/YYYY-MM-DD_HHMMSS-slug.md`:

```markdown
# Feature Name Implementation Plan

**Goal:** One sentence
**Architecture:** 2-3 sentences
**Tech Stack:** Key technologies

### Task 1: Descriptive name
- Create: `path/to/new_file.py`
- Modify: `path/to/existing.py:45-67`
- Test: `tests/path/to/test.py`

**Step 1:** Write failing test [code]
**Step 3:** Run: `pytest ...` (expected: FAIL)
**Step 4:** Write minimal implementation [code]
**Step 5:** Run: `pytest ...` (expected: PASS)
**Step 6:** Commit
```

## Key Rules

- **Bite-sized tasks:** 2-5 minutes each
- **Exact file paths** — not "the config file" but `src/config/settings.py`
- **Complete code** — copy-pasteable
- **Exact commands with expected output**
- **Verification steps**
- DRY, YAGNI, TDD, frequent commits
- **A good plan makes implementation obvious**
