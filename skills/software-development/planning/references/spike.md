# Spike Mode

Throwaway experiments to validate ideas before committing to a build.

## Core Loop
```
decompose → research → build → verdict
```

## Steps

### 1. Decompose
Break the idea into 2-5 feasibility questions. Order by risk — the one most likely to kill the idea runs first.

### 2. Research
Per spike: brief it, surface competing approaches, pick one, state why.

### 3. Build
One directory per spike: `spikes/NNN-descriptive-name/README.md` + code.

**Bias toward something the user can interact with:** CLI, HTML page, web server.

### 4. Verdict
```markdown
## Verdict: VALIDATED | PARTIAL | INVALIDATED
### What worked / What didn't / Surprises / Recommendation
```

## Comparison Spikes
Build back-to-back, then head-to-head table:

```markdown
## Head-to-head: approach A vs approach B
| Dimension | A | B |
|-----------|---|---|
| Quality | ... | ... |
| Perf | ... | ... |
| Complexity | ... | ... |
**Winner:** A for our use case.
```

## Key Rules
- Spikes are disposable — throw them away once they've paid their debt
- Hardcode everything — no package managers, Docker, env files
- Don't declare "it works" after one happy-path run — test edge cases
- VALIDATED/INVALIDATED are both successful spikes
