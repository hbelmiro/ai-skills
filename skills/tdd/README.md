# tdd

Test-driven development workflow for agents: tests and scenario coverage first, implementation second, post-implementation scenario pass, refactor, overlap pruning, post-overlap scenario audit (F↔G until settled), then **review/fix loop last** (Phase H).

## Contents

- `SKILL.md` — main workflow (through phases A–H)
- `scenario-coverage.md` — prompts for “enough” scenarios, overlap signals, post-overlap recheck note

## Install

See [skills/README.md](../README.md) for Striatum-based install, e.g.:

```bash
uv run python src/install.py --personal --skill tdd
```

(Requires registry/env setup as documented there.)
