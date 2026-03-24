# Scenario coverage prompts

Use this as a **checklist to think with**, not a mandatory universal list.
For each row, ask: "Do we need this for *this* change?"
If yes, there should be a test
(or an explicit documented reason why not, e.g. out of scope).

Apply these prompts as an independent reviewer,
not as the implementation author.
Try to falsify assumptions before accepting coverage as sufficient.

| Area | Prompt |
| ---- | ------ |
| Happy path | Primary success case with realistic inputs |
| Boundaries | Min/max, empty, single element, “full” collections, off-by-one |
| Invalid input | Malformed types, out-of-range, missing required fields |
| Authorization / tenancy | Wrong user, wrong resource, cross-tenant access if applicable |
| Errors | Domain errors vs unexpected failures; stable error semantics if specified |
| State | Preconditions, idempotency, double-submit, retries |
| Time | Clocks, timeouts, ordering, expiry if applicable |
| Concurrency | Races, locks, parallel safety if applicable |
| I/O | Partial failure, unavailable dependency, timeout, retry behavior |
| Observability | Logging/metrics behavior only if part of the contract |
| Assumption challenge | A plausible "this could fail differently" hypothesis has a test or explicit out-of-scope note |

**Definition of “enough”**: A reviewer could not reasonably ask “what happens if …?” for an obvious case implied by the spec without finding a test or an explicit out-of-scope note.

## Overlapping scenarios (final pass)

Signals that two or more tests may be **overlapping** (same behavior, redundant maintenance):

- Same assertion target and outcome under inputs that are **cosmetically** different only (e.g. two strings that exercise the same branch).
- A **unit** test already proves the branch, and an **integration** test repeats it **without** covering a new seam (wiring, serialization, config, real I/O).
- Duplicate examples in **table-driven** tests where rows collapse to one equivalence class.
- Copy-pasted tests with identical structure and expectations.

**Not overlap**: Different failure modes, different boundaries, different public contracts, or a second test that exists as a **documented** regression guard for a fixed bug.

**After overlap removal**: Run the coverage prompts again. Merging or deleting tests sometimes removes the last test for a branch, boundary, or error path—restore coverage before finishing.
