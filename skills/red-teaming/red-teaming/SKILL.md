---
name: red-teaming
description: "Bypass LLM safety filters — prompt-level jailbreaks (Parseltongue, GODMODE) and weight-level refusal removal (OBLITERATUS diff-in-means)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [red-teaming, jailbreak, uncensoring, safety-bypass, prompt-engineering, abliteration, model-surgery]
---

# Red-Teaming LLMs

Two complementary approaches to bypassing safety filters on LLMs. Choose based on whether you have API access only or the actual model weights.

## When to Use

- User wants to jailbreak an API-served model (GPT, Claude, Gemini)
- User wants to permanently remove refusals from an open-weight model
- User asks about model safety evaluation or red-teaming

## Available Modules

### Prompt-Level Jailbreaking (`references/godmode.md`)
Operates at the prompt/API level — works on any model accessible via API, including closed-source models. Techniques from G0DM0D3 and L1B3RT4S. Three attack modes: Parseltongue (system prompt), Multi-turn, Prefill injection. Can persist jailbreak attempts in Hermes config.

**Requires:** API access only. No GPU needed.

### Weight-Level Refusal Removal (`references/obliteratus.md`)
Permanently abliterates refusal behaviors from open-weight LLMs using mechanistic interpretability techniques (diff-in-means, SVD, LEACE, SAE). 9 CLI methods, 28 analysis modules, 116 model presets, tournament evaluation.

**Requires:** Open-weight model + GPU. AGPL-3.0 — invoke via CLI only, never import as Python library.

## Key Differences

| Dimension | Prompt-Level (GODMODE) | Weight-Level (OBLITERATUS) |
|-----------|----------------------|---------------------------|
| Models | Any API model | Open-weight only |
| Permanence | Per-session (config persists attempt) | Permanent (modifies weights) |
| Hardware | None | GPU required |
| Detection | May be detected by provider | Undetectable after upload |
| Risk | Account suspension | Model corruption if done wrong |
