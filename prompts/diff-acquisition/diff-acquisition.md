# Diff acquisition (git-based reviews)

Skip when diff already got (via `pr-review` and `gh pr diff`).

- **Read-only:** use commands that only **read** working tree and history (e.g. `git diff`, `git show`). Do **not** create or delete branches, switch branches, commit, amend, rebase, cherry-pick, reset, or change git state for review.
- Agree review scope with user or repo convention, then show change as exists: unstaged (`git diff`), staged (`git diff --cached`), or compare existing refs without checking out (e.g. `git diff origin/main...HEAD` or `git diff $(git merge-base origin/main HEAD)...HEAD`).
- Prefer range that matches how change will land (merge base vs tip); use triple-dot `...` when comparing histories unless user names different base ref.
- Obtain **complete** unified diff for that scope; include every changed file in review.