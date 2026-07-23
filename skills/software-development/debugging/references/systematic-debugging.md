# Systematic Debugging — 4-Phase Methodology

**Core principle:** Find root cause before fixing. Symptom fixes are failure.

**Iron Law:** NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST

## Phase 1: Root Cause Investigation
- Read error messages carefully (they often contain the exact solution)
- Reproduce consistently — if not reproducible, gather more data
- Check recent changes: `git log --oneline -10`, `git diff`
- Trace data flow upstream to find where bad values originate
- **Multi-component systems:** Add diagnostic instrumentation at component boundaries

## Phase 2: Pattern Analysis
- Find working examples in the same codebase
- Compare against reference implementations
- Identify every difference between working and broken
- Understand all dependencies

## Phase 3: Hypothesis and Testing
- Form single hypothesis: "I think X is the root cause because Y"
- Test minimally — one variable at a time, smallest possible change
- Did it work? → Phase 4. Didn't work? → New hypothesis
- **When unsure:** Say "I don't understand X" — don't pretend

## Phase 4: Implementation
- **Create failing test first** (RED → GREEN pattern)
- Implement single fix addressing root cause
- Verify: run regression test + full suite
- **Rule of Three:** If 3+ fixes failed → STOP and question the architecture

## Red Flags (STOP and Return to Phase 1)
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Multiple changes at once saves time"
- "One more fix attempt" (after 2+ failures)
- Proposing solutions before tracing data flow
