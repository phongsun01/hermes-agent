---
name: quality-assurance
description: "Pre-commit verification pipeline with independent subagent review, security scanning, and TDD discipline enforcement. Ensures code quality before every commit."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [quality, testing, tdd, code-review, verification, security, pre-commit, testing-methodology]
    related_skills: [github-code-review, debugging, plan]
---

# Quality Assurance

Two complementary quality disciplines that catch bugs at different stages:

## Test-Driven Development (`references/test-driven-development.md`)
Write tests BEFORE code. Watch them fail. Write minimal code. Watch them pass. Refactor. Repeat.

**Core rule:** If you didn't watch the test fail, you don't know if it tests the right thing.

## Pre-Commit Verification Pipeline (`references/requesting-code-review.md`)
Automated quality gate that runs before every commit:

1. Get the diff
2. Static security scan (secrets, injection, dangerous patterns)
3. Baseline-aware test + lint check (only NEW failures block)
4. Self-review checklist
5. **Independent reviewer subagent** — fresh context, no shared assumptions
6. Evaluate results (security + logic errors block the commit)
7. Auto-fix loop (max 2 cycles)
8. Commit with `[verified]` prefix

**Key principle:** No agent should verify its own work. Fresh context finds what you miss.

## Decision Flow

| Scenario | Use |
|----------|-----|
| Writing new code | TDD — test first, then implement |
| Before committing | Pre-commit pipeline — security scan + reviewer |
| After bug fix | TDD regression test + pre-commit pipeline |
| Delegating work | Enforce TDD in subagent goals + pipeline at end |
