# Review Output Template

Use this output format for reviews.

## GitHub Review Comments (Ready To Paste)

For each finding, output the metadata fields (File, Line, Severity) as plain
text followed by the comment body as regular markdown. Since the output file is
already a markdown document, do NOT wrap the comment body in a fenced code
block. Write it as normal markdown prose so it renders correctly, including any
embedded code blocks for suggested fixes.

Template (repeat for each finding, incrementing the number):

### Comment 1

File: BACKTICK path/to/file BACKTICK
Line: BACKTICK 42 BACKTICK
Severity: BACKTICK High BACKTICK

Description of the issue — what is wrong.

**Why it matters:** impact and risk description. (Include only when the risk is
not obvious from the context. Omit for self-evident issues.)

**Suggested fix:** concrete remediation with code if applicable.

### Comment 2

...

In the template above, replace BACKTICK with a single backtick character.
The placeholder is used here only because real backticks inside this template
would be consumed by the markdown parser instead of being reproduced in output.

## Open Questions

- \<question where intended behavior is unclear\>

## Discussion Resolution Check

- Prior comments/discussions reviewed: yes/no
- Unresolved discussions: list or "none"
- Resolved-but-questionable discussions: list or "none"

## Coverage Check

- Go baseline checklist: complete/incomplete
- Python baseline checklist: complete/incomplete
- KFP checklist (if applicable): complete/incomplete
- Independent reviewer mode applied: yes/no with brief evidence note
- Tests and edge cases reviewed: yes/no with notes
- Do tests cover enough scenarios?: yes/no with notes
- Adversarial scenario gaps still open: list or "none"

## Change Summary

- \<brief summary after findings\>
