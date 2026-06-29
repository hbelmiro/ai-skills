# Thorough Generic Review

Skill for thorough change-set reviews with parallel fan-out and adversarial
verification. Acquires the diff automatically via
[`diff-acquisition`](../../prompts/diff-acquisition/), then delegates to the
[`thorough-review`](../../workflows/thorough-review/) workflow for parallel
Go, Python, and generic reviewers with skeptic verification of each finding.

For fast single-pass reviews, use
[`generic-review`](../generic-review/) instead.

## Files

- `SKILL.md` — entrypoint and workflow rules
- `artifact.json` — Striatum manifest and dependencies

## Install

See the [root README](../../README.md#installing-skills). Installing this skill
pulls **`diff-acquisition`** and **`thorough-review`** (and their transitive
dependencies: `review-shared`, `go-code-review`, `python-code-review`).
