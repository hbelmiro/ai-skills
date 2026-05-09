# PR Review to File — checklist

Execute in order unless a step is not applicable (state N/A with reason).

## 0. Git (hard rule)

- [ ] **Never** `git commit`, `git push`, `git commit --amend`, `git rebase`,
      `git merge`, `git cherry-pick`, `git pull` when it would merge/rebase, or
      anything that creates commits or updates remotes. Read-only git is fine.

## 1. Review

- [ ] Run `../pr-review/SKILL.md` with the provided PR URL.
- [ ] Let `pr-review` handle all phases: PR context collection, full diff via
      `gh`, comment-thread validation, delegation to `generic-review`, and
      Phase 2 duplicate suppression.
- [ ] Capture the final review output produced by `pr-review`.

## 2. Save review to file

- [ ] Parse the PR number from the URL.
- [ ] Create `<project>/.hbelmiro/reviews/` directory if it does not exist.
- [ ] Add `.hbelmiro/` to `<project>/.git/info/exclude` if not already present.
- [ ] Write the final review output to
      `<project>/.hbelmiro/reviews/<YYYY-MM-DD-HHmmss>-pr-<PR_NUMBER>-review.md`.
