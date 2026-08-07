# Go Review Checklist

Apply every check explicit, even when change seem unrelated.

## Static Analysis (golangci-lint)

Run `golangci-lint` when target project Go module and tool available.
Best-effort step; if tool missing, note gap and continue manual checks.

- Confirm `go.mod` exist at project root. If not, skip section.
- Check availability: `which golangci-lint`. If unavailable, record "golangci-lint: not available — skipped" in review output Coverage Check and proceed.
- Run: `golangci-lint run ./...` from module root. If config file exist (`.golangci.yml`, `.golangci.yaml`, or `.golangci.toml`), `golangci-lint` pick up automatic.
- **Diff-scope filter:** Only report finding on file and line touched by change under review. Cross-reference linter output against diff. Discard finding on unchanged line.
- **Deduplication:** When linter finding cover same issue as manual checklist item below, report once. Cite linter as supporting evidence rather than list both separate.
- **Coverage Check annotation:** Annotate "Go baseline checklist" line with `golangci-lint` status: ran (with finding count on changed line), not available, or skipped (with reason).

## Core Go Standards

- Returned error handled by caller.
- Error wrapped with context using package-consistent style (prefer `fmt.Errorf("...: %w", err)`).
- No `panic` in production path unless behavior explicit fatal.
- `context.Context` passed through I/O call chain consistent.
- Test use `t.Helper()` for helper and fail fast on helper failure.
- Test prefer `require` for critical assertion and use `assert` selective. Follow rule even when existing code in file use `assert` everywhere.

## Correctness and Reliability

- Error handling cover failure path, including timeout and cancellation case.
- Default or permissive fallback value not used to hide error.
- Logging include enough operational context without leak secret or large payload.
- Boundary condition and failure mode tested.

## Concurrency and Lifecycle Safety

- Goroutine lifecycle bounded; no leak risk on context cancellation or early return.
- Shared state access concurrency-safe (map, channel, and mutable struct).
- Channel ownership and close semantic clear and safe.