# Review Output Template

Use this output format for reviews.

```markdown
## GitHub Review Comments (Ready To Paste)

- **File:** `<path/to/file>`
  **Line:** `<line number>`
  **Severity:** `Critical|High|Medium|Low`
  **Comment:**
  `<short title>.`
  `[Optional when not obvious] Why it matters: <impact and risk>.`
  `Suggested fix: <concrete remediation>.`

## Open Questions

- <question where intended behavior is unclear>

## Coverage Check

- Go baseline checklist: complete/incomplete
- Python baseline checklist: complete/incomplete
- KFP checklist (if applicable): complete/incomplete
- Tests and edge cases reviewed: yes/no with notes
- Do tests cover enough scenarios?: yes/no with notes

## Change Summary

- <brief summary after findings>
```
