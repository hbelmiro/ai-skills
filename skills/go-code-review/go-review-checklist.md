# Go Review Checklist

Apply every check explicitly, even when a change seems unrelated.

## Core Go Standards

- Returned errors are handled by the caller.
- Errors are wrapped with context using package-consistent style (prefer `fmt.Errorf("...: %w", err)`).
- No `panic` in production paths unless behavior is explicitly fatal.
- `context.Context` is passed through I/O call chains consistently.
- Tests use `t.Helper()` for helpers and fail fast on helper failures.
- Tests prefer `require` for critical assertions and use `assert` selectively. Follow this rule even when existing code in the file uses `assert` everywhere.

## Correctness and Reliability

- Error handling covers failure paths, including timeout and cancellation cases.
- Default or permissive fallback values are not used to hide errors.
- Logging includes enough operational context without leaking secrets or large payloads.
- Boundary conditions and failure modes are tested.

## Concurrency and Lifecycle Safety

- Goroutine lifecycle is bounded; no leak risk on context cancellation or early return.
- Shared state access is concurrency-safe (maps, channels, and mutable structs).
- Channel ownership and close semantics are clear and safe.
