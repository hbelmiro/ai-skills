# General Review Requirements

Apply to every review, regardless of language or component.

## Mandatory Review Behavior

- Do not skip checklist items because files look unrelated.
- Escalate security, data integrity, compatibility, reliability risks first.
- Read code and tests. Flag assumptions. List **only** open questions when behavior unclear.
- Ask, don't assume: when behavior or intent stays unclear after investigating code, tests, and in-scope context, ask the user directly instead of guessing.
- Actionable fixes over generic advice.
- Assertive when fact verifiable from code. State as fact. No hedge with "if"/"consider" when can confirm by reading diff/codebase.
- Interfaces no `Interface` suffix. Name after behavior. Keep concrete implementation unexported where language supports.
- `switch`/`match`/`when` with one case + default = verbose `if`/`else`. Flag for simplification unless author documents plan for more cases soon.

## Mandatory Discussion Resolution Check

- Prior review comments/design discussions exist = verify addressed in code.
- "Resolved" status = signal, not proof. Confirm concern actually fixed.
- Call out unresolved/weakly-resolved discussions explicit.

## Mandatory Test Sufficiency and Quality Check

- Answer explicit: "Tests cover enough scenarios?" When insufficient, state it as a finding or a Coverage Check bullet; the default "no open gaps" line covers adequate coverage.
- Note missing boundary cases, failure modes, retries/timeouts, integration gaps when relevant.
- Probe adversarial: identify one "what breaks if assumptions wrong?" scenario. Test covers?
- Never delete test cases covering nil/default behavior in same PR that changes validation logic. Cases genuinely wrong = update to reflect new expected behavior, not remove.

### Test implementation quality

- Assertions specific: each test asserts expected values/behavior, not just "no error" or "call ran".
- No tautological tests: test asserting a mock returns what it was stubbed to return, with no real behavior exercised, = flag.
- Tests exercise real code paths. Over-mocked tests that stub the unit under test = flag.
- Test name and assertions match claimed behavior. Test would fail if behavior regressed.
- Setup/teardown isolated: no hidden inter-test ordering or shared mutable state.

## Mandatory CWE-74 Injection Validation

- Trace untrusted input (user input, request params, env vars, file contents, external API responses) to every sink that interprets text as code or structure:
  - SQL/NoSQL query construction: string-built queries, format strings.
  - Shell command construction: `exec`, `subprocess` with `shell=True`, backticks, `os.system`.
  - Template engines: Jinja2, Go `text/template`/`html/template` fed untrusted templates.
  - `eval`/`exec`/dynamic code evaluation, deserialization of untrusted data.
  - Format strings, XPath, LDAP, header/CRLF injection, path construction from untrusted input.
- Flag any flow where untrusted input reaches such a sink without parameterization, safe APIs, escaping, or allow-listing.
- Prefer parameterized queries, safe template contexts, argument-array process APIs. Flag string concatenation into interpreters.
- Assertive when verifiable from diff/codebase. Cite file:line for each finding.

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
