# General Review Requirements

Apply these requirements to every review, regardless of language or component.

## Mandatory Review Behavior

- Do not skip checklist items because files look unrelated.
- Escalate security, data integrity, compatibility, and reliability risks first.
- Flag assumptions and open questions when intended behavior is unclear.
- Prefer actionable fixes over generic advice.

## Mandatory Discussion Resolution Check

- If prior review comments or design discussions exist, verify whether they were addressed in code.
- Treat "resolved" status as a signal, not proof; confirm the concern is actually fixed.
- Call out unresolved or weakly-resolved discussions explicitly.

## Mandatory Test Sufficiency Check

- Explicitly answer: "Do tests cover enough scenarios?"
- Include notes for missing boundary cases, failure modes, retries/timeouts, and integration gaps when relevant.
