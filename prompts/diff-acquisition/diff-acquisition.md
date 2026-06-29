# Diff acquisition (git-based reviews)

Skip this section when the full diff was already obtained (including via `pr-review` and `gh pr diff`).

- **Read-only:** use commands that only **read** the working tree and history (e.g. `git diff`, `git show`). Do **not** create or delete branches, switch branches, commit, amend, rebase, cherry-pick, reset, or otherwise change git state for the sake of the review.
- Agree the review scope with the user or repo convention, then show the change as it already exists: unstaged (`git diff`), staged (`git diff --cached`), or compare existing refs without checking them out (e.g. `git diff origin/main...HEAD` or `git diff $(git merge-base origin/main HEAD)...HEAD`).
- Prefer a range that matches how the change will land (merge base vs tip); use triple-dot `...` when comparing histories unless the user names a different base ref.
- Obtain the **complete** unified diff for that scope; include every changed file in the review.
