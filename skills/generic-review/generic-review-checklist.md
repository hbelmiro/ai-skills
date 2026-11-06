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

## Discussion resolution check and test sufficiency

Apply the mandatory checks in [`general-review-requirements.md`](../../prompts/review-shared/general-review-requirements.md). When no prior discussions exist (typical for local-only review), the **Discussion Resolution Check** section states this in one line (e.g. `- No prior discussions`).