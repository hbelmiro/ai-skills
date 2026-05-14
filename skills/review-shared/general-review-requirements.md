# General Review Requirements

Apply these requirements to every review, regardless of language or component.

## Mandatory Review Behavior

- Do not skip checklist items because files look unrelated.
- Escalate security, data integrity, compatibility, and reliability risks first.
- After reading relevant code and tests, flag assumptions and list **only**
  remaining open questions when intended behavior is still unclear.
- Prefer actionable fixes over generic advice.
- Be assertive: when a fact is verifiable from the code, state it as a fact. Do not hedge with "if" or "consider" when you can confirm the condition by reading the diff or codebase.
- Interfaces should not use an `Interface` suffix. Name the interface after the behavior and keep the concrete implementation unexported where the language supports it.

## Independent Reviewer Mode (Mandatory)

- Review as if you did **not** author the change and have no prior design context.
- Treat author intent as unproven until supported by code, tests,
  or explicit spec text.
- For each major conclusion, cite concrete evidence from diff behavior,
  call paths, and tests.
- Attempt to disprove your first impression by checking at least one
  plausible failure path.
- If evidence is incomplete, state uncertainty explicitly instead of inferring correctness.

## Mandatory Discussion Resolution Check

- If prior review comments or design discussions exist, verify whether they were addressed in code.
- Treat "resolved" status as a signal, not proof; confirm the concern is actually fixed.
- Call out unresolved or weakly-resolved discussions explicitly.

## Mandatory Test Sufficiency Check

- Explicitly answer: "Do tests cover enough scenarios?"
- Include notes for missing boundary cases, failure modes, retries/timeouts, and integration gaps when relevant.
- Probe adversarially: identify at least one
  "what breaks if assumptions are wrong?" scenario and whether a test
  covers it.
- Never delete test cases covering nil/default behavior in the same PR
  that changes validation logic. If those cases are genuinely wrong,
  they should be updated to reflect the new expected behavior, not
  removed.

## Mandatory Broken Link Check

- For every added or modified file in the diff, verify that **internal
  cross-references** resolve to an existing target:
  - Markdown/doc links (`[text](path)`, `[text]: path`) — confirm the
    target file or heading anchor exists relative to the linking file.
    For anchor links, use GitHub-style slugification (lowercase, spaces
    to hyphens, strip punctuation).
  - Import/include paths — confirm the referenced module, package,
    or file exists in the tree (already covered by language checklists
    for compile/runtime imports; this item targets supplementary
    references such as comments, docs, and build configs).
- For **renamed, moved, or deleted** files, search the diff and
  surrounding codebase for references that now point to a stale path.
- External URLs (https://…) in added or changed lines: flag any that
  are clearly malformed or point to known-dead domains. Full
  reachability testing is not required, but obviously broken URLs
  should be called out.
- Classify broken-link findings using the severity rubric (typically
  Medium for documentation links, High when a broken reference would
  cause a build or runtime failure).
