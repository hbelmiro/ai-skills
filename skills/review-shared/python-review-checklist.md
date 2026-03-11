# Python Review Checklist

Apply every check explicitly, even when a change seems unrelated.

## Core Python Standards

- Exceptions are caught at the appropriate level; no bare `except:` or `except Exception` without re-raise or explicit justification.
- Errors are not silently swallowed; `pass` in `except` blocks is flagged unless clearly intentional.
- Public functions and methods have type annotations on parameters and return values.
- No mutable default arguments (`def f(x=[]):`); use `None` with a guard instead.
- Resources that require cleanup use context managers (`with` statements).
- Imports are organized (stdlib, third-party, local) and unused imports are removed.

## Correctness and Reliability

- `None`, empty collections, and boundary values are handled explicitly.
- String formatting uses f-strings or `.format()` consistently; no `%`-style in new code without justification.
- Logging includes operational context without leaking secrets or large payloads.
- Functions fail explicitly rather than returning sentinel values that callers may ignore.

## Concurrency and Async Safety

- Shared mutable state is protected by locks or confined to a single thread.
- `async`/`await` patterns are used correctly; no blocking calls inside async functions.
- Thread and process pool lifecycles are bounded and properly shut down.

## Security

- No `eval()`, `exec()`, or `pickle.loads()` on untrusted input.
- No secrets, tokens, or credentials hardcoded or logged.
- User-supplied input used in file paths, shell commands, or SQL is validated or parameterized.

## Testing

- Tests use pytest idioms (`assert`, fixtures, `parametrize`).
- Boundary conditions, failure modes, and `None`/empty inputs are covered.
- Mocks are scoped narrowly and do not mask the behavior under test.
- Test names clearly describe the scenario and expected outcome.
