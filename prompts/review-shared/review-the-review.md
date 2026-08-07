# Review the Review

Re-read entire review output before presenting.
Apply every check below and fix issues found in-place.
No separate "meta-review" section to output;
silently correct review itself.

## Completeness

- Every changed file in diff accounted for (reviewed or explicitly noted as no-issue).
- All checklist sections from applicable artifact(s) executed; none silently skipped.
- Coverage Check section accurately reflects which checklists completed.
- **Open Questions** always present, but bullets list **only** uncertainties
  that stay unresolved **after** you searched codebase, tests, and
  in-scope context (PR body, etc.). No use this section for items you could
  have settled by reading code. If nothing remains open, state **None**
  explicitly.
- For **PR-linked** reviews: **Pull request context** present, appears **before** numbered findings, and includes full PR **body** (not only title).

## Accuracy

- Each finding references correct file path and line number. Re-read diff to verify every line number points to exact line described — no trust line numbers from memory.
- For findings about **removed** lines, verify Line field references nearest surviving context line and explicitly notes deletion — not line number that points to unrelated code in current file.
- Quoted code snippets match actual diff content (no stale or hallucinated code).
- Suggested fixes syntactically valid and would actually resolve issue.
- Major conclusions backed by specific evidence from code paths,
  tests, or specs.

## Consistency

- No duplicate findings (same issue reported more than once under different wording).
- For **PR** reviews where prior comments collected: findings no restate issues already raised on PR unless prior thread **stale**, concern **remains unresolved** in code, or new finding is **distinct** sub-issue. Suppressed overlaps belong under **Findings not repeated** per output template.
- No contradictory findings (one comment recommends X, another recommends opposite).

## Signal-to-noise

- Every finding actionable: identifies concrete problem and concrete fix or question.
- Generic advice without specific code reference removed or made specific.
- Nitpicks that no affect correctness, security, or maintainability removed.

## Structural quality

- At least one structural simplification opportunity actively searched for (not only correctness bugs and style nits).
- If no structural issues found, review states this explicitly rather than silently omitting dimension.
- Structural findings include concrete alternative, not generic "this is complex" advice.

## Fairness

- Findings based on what diff actually does, not on assumptions about intent.
- Positive aspects of change acknowledged in Change Summary when warranted.
- Tone constructive and professional throughout.

## Anti-bias discipline

- Review no rely on author-justification language
  (for example: "probably intended", "likely safe")
  without evidence.
- At least one plausible counterexample or failure mode checked for
  each high-impact behavior change.
- If behavior cannot be verified from available code/tests,
  uncertainty called out as open question.