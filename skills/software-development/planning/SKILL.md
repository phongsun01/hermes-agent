---
name: planning
description: "Write actionable implementation plans for multi-step features, or throwaway spike experiments to validate ideas before committing to a build. Plan mode: no execution, just markdown plan output."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, plan-mode, spike, prototype, feasibility, implementation, design, exploration]
    related_skills: [subagent-driven-development, test-driven-development, quality-assurance]
---

# Planning & Experimentation

Two complementary pre-implementation activities:

## Plan Mode (`references/plan.md`)
When the user wants a plan instead of execution. Write bite-sized, actionable markdown plans. Save to `.hermes/plans/YYYY-MM-DD_HHMMSS-slug.md`.

**Key principles:**
- Each task = 2-5 minutes of focused work
- Exact file paths and complete code in every task
- TDD cycle for every code task
- Frequent commits after each task

## Spike Mode (`references/spike.md`)
Throwaway experiments to validate an idea before committing to a build. Runs in `spikes/` directory.

**Key principles:**
- One directory per spike: `spikes/NNN-descriptive-name/`
- README.md per spike captures: question, approach, results, verdict
- Verdict: VALIDATED / PARTIAL / INVALIDATED
- Bias toward something the user can interact with (CLI, HTML page, web server)

## Decision Flow

| Scenario | Use |
|----------|-----|
| User says "make a plan" | Plan mode → write .hermes/plans/...md |
| User asks "is X even possible?" | Spike → build prototype, get verdict |
| User says "compare A vs B" | Spike → build both, head-to-head |
| User says "implement the plan" | subagent-driven-development |
| You're unsure about an approach | Spike first, then plan, then implement |
