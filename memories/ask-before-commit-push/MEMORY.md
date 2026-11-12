---
name: ask-before-commit-push
description: >-
  Never commit, push, or open a pull request without asking the user
  first.
metadata:
  type: feedback
---

Never run `git commit` or `git push`, and never open a pull request,
without asking the user first and getting their approval.

**Why:** The user owns their git history and remotes, and wants to
review and control exactly what enters them.

**How to apply:** Make the changes, summarize them (status/diff), and
ask the user before committing, pushing, or opening a PR.
