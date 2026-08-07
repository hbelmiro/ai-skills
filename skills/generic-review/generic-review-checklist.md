# Generic Review Checklist

Apply every check explicit. If diff acquisition skipped (e.g. PR diff already fetched via `gh pr diff`), still perform all other sections.

## Diff acquisition (git-based reviews)

Read and apply [`../../prompts/diff-acquisition/diff-acquisition.md`](../../prompts/diff-acquisition/diff-acquisition.md).

## Mandatory diff review

- Review **full** diff before reporting findings.
- Build hypotheses only **after** full-diff pass.
- Avoid selective confirmation from isolated snippets.
- Do not limit review to selected files or snippets when assessing correctness and risk.
- Inspect impacted call paths and cross-file effects, not only edited lines.
- For high-impact claims, look for disconfirming evidence in nearby
  call paths or tests.

## Discussion resolution check

- If prior review comments, issues, or design threads relevant to change exist, verify concerns addressed in code (per [`general-review-requirements.md`](../../prompts/review-shared/general-review-requirements.md)).
- If **no** such threads exist (typical for local-only review), state explicit in output template **Discussion Resolution Check** section (e.g. no PR/issue discussion to validate).

## Risk and test sufficiency

- Prioritize security, data integrity, reliability, and compatibility risks first.
- Verify tests cover changed behavior, edge cases, and failure paths.
- Challenge happy-path assumptions by checking at least one adversarial
  scenario ("what breaks if assumption wrong?").
- Explicit answer: "Do tests cover enough scenarios?"
- After investigating codebase and tests, state assumptions and list only
  open questions for which intent still unclear.