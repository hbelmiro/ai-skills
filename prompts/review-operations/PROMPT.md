---
name: review-operations
description: Read-only Git and no-remote-mutation rules for review workflows.
---

# Review Operations

Review workflows may inspect Git and edit the working tree, but must never create commits or update remotes. Do not run `git commit`, `push`, `commit --amend`, `rebase`, `merge`, `cherry-pick`, or a merge/rebase-capable `pull`.
