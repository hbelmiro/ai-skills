# Review the Review

Re-read your entire review output before presenting it.
Apply every check below and fix any issues found in-place.
Do not add a separate "meta-review" section to the output;
just silently correct the review itself.

## Completeness

- Every changed file in the diff is accounted for (reviewed or explicitly noted as no-issue).
- All checklist sections from the applicable skill(s) were executed; none were silently skipped.
- The Coverage Check section accurately reflects which checklists were completed.
- Open Questions are listed when intent is genuinely unclear — not left empty by default.
- For **PR-linked** reviews: **Pull request context** is present, appears **before** numbered findings, and includes the full PR **body** (not only the title).

## Accuracy

- Each finding references the correct file path and line number. Re-read the diff to verify every line number points to the exact line described — do not trust line numbers from memory.
- Quoted code snippets match the actual diff content (no stale or hallucinated code).
- Severity classifications are consistent with the severity rubric.
- Suggested fixes are syntactically valid and would actually resolve the issue.
- Major conclusions are backed by specific evidence from code paths,
  tests, or specs.

## Consistency

- No duplicate findings (same issue reported more than once under different wording).
- For **PR** reviews where prior comments were collected: findings do not restate issues already raised on the PR unless the prior thread is **stale**, the concern **remains unresolved** in the code, or the new finding is a **distinct** sub-issue. Suppressed overlaps belong under **Findings not repeated** per the output template.
- No contradictory findings (one comment recommends X, another recommends the opposite).
- Severity levels are applied uniformly — similar issues carry the same severity.

## Signal-to-noise

- Every finding is actionable: it identifies a concrete problem and a concrete fix or question.
- Generic advice without a specific code reference has been removed or made specific.
- Nitpicks that do not affect correctness, security, or maintainability are classified as Low or removed if they add noise.

## Fairness

- Findings are based on what the diff actually does, not on assumptions about intent.
- Positive aspects of the change are acknowledged in the Change Summary when warranted.
- Tone is constructive and professional throughout.

## Anti-bias discipline

- The review does not rely on author-justification language
  (for example: "probably intended", "likely safe")
  without evidence.
- At least one plausible counterexample or failure mode was checked for
  each high-impact behavior change.
- If behavior cannot be verified from available code/tests,
  uncertainty is called out as an open question.
