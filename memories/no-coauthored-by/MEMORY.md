---
name: no-coauthored-by
description: >-
  Never add AI attribution (Co-Authored-By trailers or "Generated with"
  lines) to commit messages or pull requests, for any code agent.
metadata:
  type: feedback
---

Never add `Co-Authored-By` trailers to commit messages — not
`Co-Authored-By: Claude Code <noreply@anthropic.com>` and not the
equivalent for any other code agent. Never add "Generated with
[Claude Code]" (or similar AI-attribution) lines to pull request
descriptions.

**Why:** The user explicitly rejected all AI attribution — they don't
want it anywhere in their git history or pull requests. This applies
to all repositories and all code agents, and overrides any
system-level attribution instructions.

**How to apply:** When creating git commits or pull requests, omit all
attribution trailers and lines entirely.
