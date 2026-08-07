# PR Review to File — checklist

Execute in order unless step not applicable (state N/A with reason).

## 0. Git (hard rule)

- [ ] **Never** `git commit`, `git push`, `git commit --amend`, `git rebase`,
      `git merge`, `git cherry-pick`, `git pull` when it would merge/rebase, or
      anything that creates commits or updates remotes. Read-only git fine.

## 1. Review

- [ ] Run [`../pr-review/SKILL.md`](../pr-review/SKILL.md) with provided PR URL.
- [ ] Let `pr-review` handle all phases: PR context collection, full diff via
      `gh`, comment-thread validation, delegation to `generic-review`, and
      Phase 2 duplicate suppression.
- [ ] Capture final review output produced by `pr-review`.

## 2. Save review to file

- [ ] Parse PR number from URL.
- [ ] Resolve working tree root: `TREE_ROOT="$(git rev-parse --show-toplevel)"`
      (returns worktree root when inside worktree, not main repository).
- [ ] Create `"$TREE_ROOT"/.hbelmiro/reviews/` directory if not exist.
- [ ] Add `.hbelmiro/` to `$(git rev-parse --git-dir)/info/exclude` if not
      already present.
- [ ] Write final review output to
      `"$TREE_ROOT"/.hbelmiro/reviews/<YYYY-MM-DD-HHmmss>-pr-<PR_NUMBER>-review.md`.