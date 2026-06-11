# Go Review Checklist

Apply every check explicitly, even when a change seems unrelated.

## Static Analysis (golangci-lint)

Run golangci-lint when the target project is a Go module and the tool is available.
This step is best-effort; if the tool is missing, note the gap and continue with manual checks.

- Confirm a `go.mod` exists at the project root. If not, skip this section.
- Check availability: `which golangci-lint`. If unavailable, record "golangci-lint: not available — skipped" in the review output's Coverage Check and proceed.
- Run: `golangci-lint run ./...` from the module root. If a config file exists (`.golangci.yml`, `.golangci.yaml`, or `.golangci.toml`), golangci-lint picks it up automatically.
- **Diff-scope filter:** Only report findings on files and lines touched by the change under review. Cross-reference linter output against the diff. Discard findings on unchanged lines.
- **Deduplication:** When a linter finding covers the same issue as a manual checklist item below, report it once. Cite the linter as supporting evidence rather than listing both separately.
- **Coverage Check annotation:** Annotate the "Go baseline checklist" line with golangci-lint status: ran (with finding count on changed lines), not available, or skipped (with reason).

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
