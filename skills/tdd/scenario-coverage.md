# Scenario coverage prompts

Checklist to think with. Not mandatory universal list.
Each row ask: "Need this for *this* change?"
If yes, need test
(or explicit reason why not, e.g. out of scope).

Apply prompts as independent reviewer,
not implementation author.
Falsify assumptions before accepting coverage sufficient.

| Area | Prompt |
| ---- | ------ |
| Happy path | Primary success case with realistic inputs |
| Boundaries | Min/max, empty, single element, "full" collections, off-by-one |
| Invalid input | Malformed types, out-of-range, missing required fields |
| Authorization / tenancy | Wrong user, wrong resource, cross-tenant access if applicable |
| Errors | Domain errors vs unexpected failures; stable error semantics if specified |
| State | Preconditions, idempotency, double-submit, retries |
| Time | Clocks, timeouts, ordering, expiry if applicable |
| Concurrency | Races, locks, parallel safety if applicable |
| I/O | Partial failure, unavailable dependency, timeout, retry behavior |
| Observability | Logging/metrics behavior only if part of contract |
| Assumption challenge | Plausible "this could fail differently" hypothesis has test or explicit out-of-scope note |

**Definition of "enough"**: Reviewer cannot reasonably ask "what happens if …?" for obvious case implied by spec without finding test or explicit out-of-scope note.

## Overlapping scenarios (final pass)

Signals tests may be **overlapping** (same behavior, redundant maintenance):

- Same assertion target and outcome under inputs **cosmetically** different only (e.g. two strings exercise same branch).
- **Unit** test already proves branch, **integration** test repeats **without** covering new seam (wiring, serialization, config, real I/O).
- Duplicate examples in **table-driven** tests where rows collapse to one equivalence class.
- Copy-pasted tests with identical structure and expectations.

**Not overlap**: Different failure modes, different boundaries, different public contracts, or second test exists as **documented** regression guard for fixed bug.

**After overlap removal**: Run coverage prompts again. Merging or deleting tests sometimes removes last test for branch, boundary, or error path—restore coverage before finishing.