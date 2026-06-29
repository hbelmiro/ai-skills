# Generic Review Checklist

Apply every check explicitly. If diff acquisition is skipped (e.g. PR diff already fetched via `gh pr diff`), still perform all other sections.

## Diff acquisition (git-based reviews)

Read and apply [`../../prompts/diff-acquisition/diff-acquisition.md`](../../prompts/diff-acquisition/diff-acquisition.md).

## Mandatory diff review

- Review the **full** diff before reporting findings.
- Build hypotheses only **after** the full-diff pass.
- Avoid selective confirmation from isolated snippets.
- Do not limit review to selected files or snippets when assessing correctness and risk.
- Inspect impacted call paths and cross-file effects, not only edited lines.
- For high-impact claims, look for disconfirming evidence in nearby
  call paths or tests.

## Discussion resolution check

- If there are prior review comments, issues, or design threads relevant to this change, verify whether concerns were addressed in code (per [`general-review-requirements.md`](../../prompts/review-shared/general-review-requirements.md)).
- If there are **no** such threads (typical for local-only review), state that explicitly in the output template **Discussion Resolution Check** section (e.g. no PR/issue discussion to validate).

## Risk and test sufficiency

- Prioritize security, data integrity, reliability, and compatibility risks first.
- Verify tests cover changed behavior, edge cases, and failure paths.
- Challenge happy-path assumptions by checking at least one adversarial
  scenario ("what breaks if this assumption is wrong?").
- Explicitly answer: "Do tests cover enough scenarios?"
- After investigating the codebase and tests, state assumptions and list only
  open questions for which intent is still unclear.
