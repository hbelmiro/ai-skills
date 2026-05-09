# Kubeflow Pipelines Review Checklist

Apply every check explicitly, even when a file does not obviously match.

## Control Plane and API Surface

- For `backend/src/` and `backend/src/v2/`, verify API changes include corresponding REST/gRPC and swagger/openapi updates where applicable.
- Validate compatibility between v1 and v2 paths when shared code paths exist.

## Persistence and Data Integrity

- For `backend/src/agent/persistence/`, review schema migrations, lineage updates, and idempotency of writes.
- For run/job fields (for example `plugins_input` and `plugins_output`), ensure every create and update write path persists fields consistently with the same nil/NULL handling.
- Flag silent defaulting on persistence or validation errors; prefer propagating errors.

## Scheduling and Execution

- For `backend/src/crd/controller/scheduledworkflow/`, verify CRD versioning and reconcile behavior remain backward compatible.
- If one-off run behavior changes, check whether recurring runs need parity; raise uncertainty explicitly.
- For cache and execution paths, verify cache-key stability, artifact hashing inputs, and observability for cache hits/misses.
- Identify cache opportunities and verify invalidation scope and lifecycle correctness.

## Engine and Layer Boundaries

- In pipeline-agnostic layers, confirm no Argo-specific implementation details are introduced.
- Flag cross-binary internal imports (for example controller importing apiserver internals); require shared/common or API boundaries.

## Frontend, SDK, and Manifests

- For `frontend/`, verify API contract changes are reflected in queries/mutations and feature-flag behavior.
- For `sdk/python/` and `samples/`, verify API usage parity and runnable docs/tests.
- For `manifests/kustomize/`, verify image/pull-policy consistency and overlay validity.

## Test Expectations

- Verify coverage for boundary conditions, failure modes, and cancellation paths.
- Call out missing integration coverage when behavior spans components.
