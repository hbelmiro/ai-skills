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
- A `switch`/`match`/`when` with only one case and a default is a verbose `if`/`else`. Flag it for simplification unless the author documents a concrete plan to add more cases imminently.

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

## Mandatory Structural Quality Check

Look beyond correctness for structural regressions and missed
simplification opportunities.

Every structural finding **must** include a concrete alternative — state
what the code would look like after simplification. "This is complex" is
not a finding. Flag complexity that is an artifact of the
**implementation choice**, not complexity inherent to the domain. Prefer
"delete" over "refactor."

- **Structural simplification search**: for each materially changed file,
  ask whether a restructuring preserves behavior but eliminates branches,
  helpers, modes, conditionals, or layers entirely. Look for
  re-organizations that use the existing architecture more effectively.
- **Abstraction justification**: for every new abstraction introduced by
  the diff (class, helper, wrapper, adapter), does it earn its existence?
  Flag thin wrappers that add no logic, pass-through helpers, and identity
  abstractions. Criterion: if removing it and inlining its body makes the
  call site shorter without losing clarity, it is unjustified. Exceptions:
  test seams, API stability layers, framework-required interfaces.
- **Conditional sprawl**: flag ad-hoc conditionals scattered across
  general-purpose flows for the same concern. The remedy is to restructure
  so the special case lives at the boundary (dedicated abstraction, policy
  object, or separate module) instead of threaded through the core.
- **Layer correctness**: flag business logic in transport layers, I/O in
  pure-logic functions, bespoke reimplementations of existing codebase
  utilities, and feature-specific logic leaking into shared paths. Search
  for existing helpers before accepting a new one.
- **File size check**: if the diff pushes any file past 1,000 lines, flag
  it with the current line count and a split suggestion.
- **State model clarity**: flag new mode flags or enum-driven dispatch
  that multiply `if mode == X` checks across the codebase instead of
  consolidating behavior behind the state type.
- **Unnecessary sequential orchestration**: flag step-by-step coordination
  where operations are independent and could run in parallel, or where
  multiple updates could be a single atomic operation.

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
- External URLs (`https://…`) in added or changed lines: flag any that
  are clearly malformed or point to known-dead domains. Full
  reachability testing is not required, but obviously broken URLs
  should be called out.
