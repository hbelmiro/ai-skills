# General Review Requirements

Apply to every review, regardless of language or component.

## Mandatory Review Behavior

- Do not skip checklist items because files look unrelated.
- Escalate security, data integrity, compatibility, reliability risks first.
- Read code and tests. Flag assumptions. List **only** open questions when behavior unclear.
- Actionable fixes over generic advice.
- Assertive when fact verifiable from code. State as fact. No hedge with "if"/"consider" when can confirm by reading diff/codebase.
- Interfaces no `Interface` suffix. Name after behavior. Keep concrete implementation unexported where language supports.
- `switch`/`match`/`when` with one case + default = verbose `if`/`else`. Flag for simplification unless author documents plan for more cases soon.

## Mandatory Discussion Resolution Check

- Prior review comments/design discussions exist = verify addressed in code.
- "Resolved" status = signal, not proof. Confirm concern actually fixed.
- Call out unresolved/weakly-resolved discussions explicit.

## Mandatory Test Sufficiency Check

- Answer explicit: "Tests cover enough scenarios?"
- Note missing boundary cases, failure modes, retries/timeouts, integration gaps when relevant.
- Probe adversarial: identify one "what breaks if assumptions wrong?" scenario. Test covers?
- Never delete test cases covering nil/default behavior in same PR that changes validation logic. Cases genuinely wrong = update to reflect new expected behavior, not remove.

## Mandatory Structural Quality Check

Look beyond correctness for structural regressions, missed simplification opportunities.

Every structural finding **must** include concrete alternative — state what code would look like after simplification. "This complex" not finding. Flag complexity = artifact of **implementation choice**, not domain inherent. Prefer "delete" over "refactor."

- **Structural simplification search**: each materially changed file = ask whether restructuring preserves behavior but eliminates branches, helpers, modes, conditionals, layers entirely. Look for re-organizations using existing architecture more effective.
- **Abstraction justification**: every new abstraction in diff (class, helper, wrapper, adapter) = does it earn existence? Flag thin wrappers adding no logic, pass-through helpers, identity abstractions. Criterion: removing + inlining body makes call site shorter without losing clarity = unjustified. Exceptions: test seams, API stability layers, framework-required interfaces.
- **Conditional sprawl**: flag ad-hoc conditionals scattered across general-purpose flows for same concern. Remedy = restructure so special case lives at boundary (dedicated abstraction, policy object, separate module) instead of threaded through core.
- **Layer correctness**: flag business logic in transport layers, I/O in pure-logic functions, bespoke reimplementations of existing codebase utilities, feature-specific logic leaking into shared paths. Search existing helpers before accepting new one.
- **File size check**: diff pushes file past 1,000 lines = flag with current line count + split suggestion.
- **State model clarity**: flag new mode flags or enum-driven dispatch that multiply `if mode == X` checks across codebase instead of consolidating behavior behind state type.
- **Unnecessary sequential orchestration**: flag step-by-step coordination where operations independent and could run parallel, or multiple updates could be single atomic operation.

## Mandatory Broken Link Check

- Every added/modified file in diff = verify **internal cross-references** resolve to existing target:
  - Markdown/doc links (`[text](path)`, `[text]: path`) — confirm target file or heading anchor exists relative to linking file. Anchor links = use GitHub-style slugification (lowercase, spaces to hyphens, strip punctuation).
  - Import/include paths — confirm referenced module, package, file exists in tree (already covered by language checklists for compile/runtime imports; this targets supplementary references like comments, docs, build configs).
- **Renamed, moved, deleted** files = search diff + surrounding codebase for references pointing to stale path.
- External URLs (`https://…`) in added/changed lines: flag clearly malformed or point to known-dead domains. Full reachability testing not required, but obviously broken URLs call out.
