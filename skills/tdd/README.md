# tdd

Test-driven development workflow for agents: tests and scenario coverage first, implementation second, post-implementation scenario pass, refactor, overlap pruning, post-overlap scenario audit (F↔G until settled), then **review/fix loop last** (Phase H) using [`generic-review`](../generic-review).

## Contents

- `SKILL.md` — main workflow (through phases A–H)
- `scenario-coverage.md` — prompts for “enough” scenarios, overlap signals, post-overlap recheck note

## Install

See the [root README](../../README.md#installing-skills) for Striatum-based install, e.g.:

```bash
uv run python src/install.py --target cursor --personal --skill tdd
```

(Requires registry/env setup as documented there.)

Installing `tdd` also installs transitive review skills (for example `review-shared`, `generic-review`, `go-code-review`, `python-code-review`, and `kubeflow-pipelines-code-review`) so Phase H can follow routed checklists. **Uninstall** only removes the skill you name; see the [Installing Skills](../../README.md#installing-skills) section for how to remove leftover dependency skills if needed.
