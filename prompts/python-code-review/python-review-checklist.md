# Python Review Checklist

Apply every check. Even unrelated change.

## Core Python Standards

- Catch exceptions at right level. No bare `except:` or `except Exception` without re-raise or reason.
- No silent error swallow. Flag `pass` in `except` blocks unless intentional.
- Public functions have type annotations on params and returns.
- No mutable default args (`def f(x=[]):`). Use `None` with guard.
- Resources needing cleanup use context managers (`with` statements).
- Organize imports (stdlib, third-party, local). Remove unused imports.

## Correctness and Reliability

- `None`, empty collections, boundary values handled explicit.
- String formatting use f-strings or `.format()`. No `%`-style in new code without reason.
- Logging include operational context. No secret leak or large payload.
- Functions fail explicit. No sentinel return values callers ignore.

## Concurrency and Async Safety

- Shared mutable state protected by locks or single thread.
- `async`/`await` patterns used correct. No blocking calls inside async functions.
- Thread and process pool lifecycles bounded and shut down proper.

## Security

- No `eval()`, `exec()`, or `pickle.loads()` on untrusted input.
- No secrets, tokens, credentials hardcoded or logged.
- User input in file paths, shell commands, SQL validated or parameterized.

## Testing

- Tests use pytest idioms (`assert`, fixtures, `parametrize`).
- Boundary conditions, failure modes, `None`/empty inputs covered.
- Mocks scoped narrow. No mask behavior under test.
- Test names describe scenario and expected outcome clear.