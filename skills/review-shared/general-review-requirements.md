# General Review Requirements

Apply these requirements to every review, regardless of language or component.

## Mandatory Review Behavior

- Do not skip checklist items because files look unrelated.
- Escalate security, data integrity, compatibility, and reliability risks first.
- Flag assumptions and open questions when intended behavior is unclear.
- Prefer actionable fixes over generic advice.

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
