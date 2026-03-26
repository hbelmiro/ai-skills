# Generic Review Checklist

Apply every check explicitly. If diff acquisition is skipped (e.g. PR diff already fetched via `gh pr diff`), still perform all other sections.

## Diff acquisition (git-based reviews)

Skip this section when the full diff was already obtained (including via `pr-review` and `gh pr diff`).

- **Read-only:** use commands that only **read** the working tree and history (e.g. `git diff`, `git show`). Do **not** create or delete branches, switch branches, commit, amend, rebase, cherry-pick, reset, or otherwise change git state for the sake of the review.
- Agree the review scope with the user or repo convention, then show the change as it already exists: unstaged (`git diff`), staged (`git diff --cached`), or compare existing refs without checking them out (e.g. `git diff origin/main...HEAD` or `git diff $(git merge-base origin/main HEAD)...HEAD`).
- Prefer a range that matches how the change will land (merge base vs tip); use triple-dot `...` when comparing histories unless the user names a different base ref.
- Obtain the **complete** unified diff for that scope; include every changed file in the review.

## Mandatory diff review

- Review the **full** diff before reporting findings.
- Build hypotheses only **after** the full-diff pass.
- Avoid selective confirmation from isolated snippets.
- Do not limit review to selected files or snippets when assessing correctness and risk.
- Inspect impacted call paths and cross-file effects, not only edited lines.
- For high-impact claims, look for disconfirming evidence in nearby
  call paths or tests.

## Discussion resolution check

- If there are prior review comments, issues, or design threads relevant to this change, verify whether concerns were addressed in code (per `general-review-requirements.md`).
- If there are **no** such threads (typical for local-only review), state that explicitly in the output template **Discussion Resolution Check** section (e.g. no PR/issue discussion to validate).

## Risk and test sufficiency

- Prioritize security, data integrity, reliability, and compatibility risks first.
- Verify tests cover changed behavior, edge cases, and failure paths.
- Challenge happy-path assumptions by checking at least one adversarial
  scenario ("what breaks if this assumption is wrong?").
- Explicitly answer: "Do tests cover enough scenarios?"
- After investigating the codebase and tests, state assumptions and list only
  open questions for which intent is still unclear.
