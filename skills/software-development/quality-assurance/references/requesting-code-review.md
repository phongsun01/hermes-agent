# Pre-Commit Verification Pipeline

Automated quality gate: security scan, baseline-aware tests, independent reviewer subagent, auto-fix loop.

**Core principle:** No agent should verify its own work. Fresh context finds what you miss.

## Steps

### Step 1: Get the diff
```bash
git diff --cached  # or git diff / git diff HEAD~1 HEAD
```

### Step 2: Static security scan
```bash
git diff --cached | grep "^+" | grep -iE "(api_key|secret|password|token).*=\s*['\"][^'\"]{6,}['\"]"
git diff --cached | grep "^+" | grep -E "os\.system\(|subprocess.*shell=True|eval\(|exec\(|pickle\.load"
```

### Step 3: Baseline tests + linting
- Run tests/lint WITHOUT your changes (stash), capture `baseline_failures`
- Run WITH your changes — only NEW failures block

### Step 4: Self-review checklist
- Secrets, injection, path traversal, error handling, debug code, tests

### Step 5: Independent reviewer subagent
```python
delegate_task(goal="...", context="Review diff, return JSON verdict")
```
Returns `{passed, security_concerns, logic_errors, suggestions, summary}`.

### Step 6-7: Evaluate → Auto-fix (max 2 cycles)

### Step 8: Commit
```bash
git add -A && git commit -m "[verified] <description>"
```

## This skill vs github-code-review

- **This:** Verifies YOUR changes before committing (pre-push quality gate)
- **github-code-review:** Reviews OTHER people's PRs on GitHub with inline comments
