"""Tests for create_jira_ticket.py — Jira ticket creation for AI Pipelines."""

from __future__ import annotations

import base64
import json
import subprocess
import urllib.error
import urllib.request
from email.message import Message

import pytest

import create_jira_ticket as cjt

from create_jira_ticket import (
    _BOARD_ID,
    _COMPONENT,
    _JIRA_BASE_URL,
    _PROJECT,
    _SPRINT_FIELD,
    _TEAM_FIELD,
    _TEAM_VALUE,
    _VALID_PRIORITIES,
    _VALID_TYPES,
    _build_parser,
    _build_update_payload,
    _create_ticket,
    _get_api_token,
    _get_email,
    _resolve_sprint,
    _update_issue,
    _update_issue_fields,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_run_factory(
    responses: dict[str, str] | None = None,
) -> tuple[list[list[str]], object]:
    """Return (calls_list, fake_run_fn) for monkeypatching _run.

    *responses* maps a command name (e.g. ``"acli"``, ``"security"``) to the
    stdout string the fake should return when that command is invoked.
    Unrecognised commands return empty stdout.
    """
    calls: list[list[str]] = []
    responses = responses or {}

    def fake_run(
        args: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        stdout = responses.get(args[0], "")
        return subprocess.CompletedProcess(args, 0, stdout, "")

    return calls, fake_run


def _auth_status_output(email: str) -> str:
    return (
        f"✓ Authenticated\n"
        f"  Site: redhat.atlassian.net\n"
        f"  Email: {email}\n"
        f"  Authentication Type: api_token\n"
    )


def _keychain_output(token: str) -> str:
    encoded = base64.b64encode(token.encode()).decode()
    return f"go-keyring-base64:{encoded}\n"


def _sprint_api_body(sprints: list[dict[str, str | int]]) -> bytes:
    return json.dumps({"values": sprints}).encode()


def _acli_create_output(key: str) -> str:
    return f"✓ Work item {key} created: https://redhat.atlassian.net/browse/{key}\n"


class _FakeHTTPResponse:
    """Minimal fake for urllib.request.urlopen return value."""

    def __init__(self, status: int = 204, body: bytes = b"") -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, *args: object) -> None:
        pass


# ---------------------------------------------------------------------------
# TestGetEmail
# ---------------------------------------------------------------------------


class TestGetEmail:
    def test_parses_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _, fake = _fake_run_factory(
            {"acli": _auth_status_output("user@redhat.com")},
        )
        monkeypatch.setattr(cjt, "_run", fake)
        assert _get_email() == "user@redhat.com"

    def test_invokes_correct_acli_command(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls, fake = _fake_run_factory(
            {"acli": _auth_status_output("u@r.com")},
        )
        monkeypatch.setattr(cjt, "_run", fake)
        _get_email()
        assert calls[0] == ["acli", "jira", "auth", "status"]

    def test_exits_when_no_email_line(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _, fake = _fake_run_factory({"acli": "no email here\n"})
        monkeypatch.setattr(cjt, "_run", fake)
        with pytest.raises(SystemExit):
            _get_email()

    def test_exits_when_email_empty(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _, fake = _fake_run_factory({"acli": "  Email: \n"})
        monkeypatch.setattr(cjt, "_run", fake)
        with pytest.raises(SystemExit):
            _get_email()


# ---------------------------------------------------------------------------
# TestGetApiToken
# ---------------------------------------------------------------------------


class TestGetApiToken:
    def test_decodes_base64_token(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _, fake = _fake_run_factory(
            {"security": _keychain_output("my-secret-token")},
        )
        monkeypatch.setattr(cjt, "_run", fake)
        assert _get_api_token() == "my-secret-token"

    def test_invokes_correct_security_command(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls, fake = _fake_run_factory(
            {"security": _keychain_output("tok")},
        )
        monkeypatch.setattr(cjt, "_run", fake)
        _get_api_token()
        assert calls[0] == ["security", "find-generic-password", "-s", "acli", "-w"]

    def test_exits_when_no_prefix(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _, fake = _fake_run_factory({"security": "raw-token-no-prefix\n"})
        monkeypatch.setattr(cjt, "_run", fake)
        with pytest.raises(SystemExit):
            _get_api_token()

    def test_exits_on_bad_base64(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _, fake = _fake_run_factory(
            {"security": "go-keyring-base64:!!!invalid!!!\n"},
        )
        monkeypatch.setattr(cjt, "_run", fake)
        with pytest.raises(SystemExit):
            _get_api_token()


# ---------------------------------------------------------------------------
# TestCreateTicket
# ---------------------------------------------------------------------------


class TestCreateTicket:
    def test_parses_issue_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _, fake = _fake_run_factory(
            {"acli": _acli_create_output("RHOAIENG-12345")},
        )
        monkeypatch.setattr(cjt, "_run", fake)
        assert _create_ticket("Task", "summary", "desc") == "RHOAIENG-12345"

    def test_passes_correct_args_to_acli(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls, fake = _fake_run_factory(
            {"acli": _acli_create_output("RHOAIENG-1")},
        )
        monkeypatch.setattr(cjt, "_run", fake)
        _create_ticket("Bug", "my summary", "my desc")
        argv = calls[0]
        assert argv[0] == "acli"
        assert "workitem" in argv
        assert "create" in argv
        assert "-p" in argv
        assert _PROJECT in argv
        assert "-t" in argv
        assert "Bug" in argv
        assert "-s" in argv
        assert "my summary" in argv
        assert "-d" in argv
        assert "my desc" in argv

    def test_exits_when_key_not_found(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _, fake = _fake_run_factory({"acli": "unexpected output\n"})
        monkeypatch.setattr(cjt, "_run", fake)
        with pytest.raises(SystemExit):
            _create_ticket("Task", "s", "d")


# ---------------------------------------------------------------------------
# TestResolveSprint
# ---------------------------------------------------------------------------


class TestResolveSprint:
    def test_autodetect_returns_first_active(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sprints = [{"id": 68645, "name": "Sprint 42", "state": "active"}]
        requests: list[urllib.request.Request] = []

        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            requests.append(req)
            return _FakeHTTPResponse(200, _sprint_api_body(sprints))

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        assert _resolve_sprint("autodetect", "u@r.com", "tok") == 68645
        assert "state=active" in requests[0].full_url
        assert "state=active%2Cfuture" not in requests[0].full_url
        assert "state=active,future" not in requests[0].full_url

    def test_autodetect_picks_first_when_multiple(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sprints = [
            {"id": 100, "name": "Sprint 10", "state": "active"},
            {"id": 200, "name": "Sprint 11", "state": "active"},
        ]

        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            return _FakeHTTPResponse(200, _sprint_api_body(sprints))

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        assert _resolve_sprint("autodetect", "u@r.com", "tok") == 100

    def test_autodetect_exits_when_no_active(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            return _FakeHTTPResponse(200, _sprint_api_body([]))

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(SystemExit):
            _resolve_sprint("autodetect", "u@r.com", "tok")

    def test_named_sprint_returns_matching_id(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sprints = [
            {"id": 100, "name": "Sprint 1", "state": "active"},
            {"id": 200, "name": "Sprint 2", "state": "future"},
        ]

        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            return _FakeHTTPResponse(200, _sprint_api_body(sprints))

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        assert _resolve_sprint("Sprint 2", "u@r.com", "tok") == 200

    def test_named_sprint_queries_active_and_future(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sprints = [{"id": 1, "name": "X", "state": "future"}]
        requests: list[urllib.request.Request] = []

        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            requests.append(req)
            return _FakeHTTPResponse(200, _sprint_api_body(sprints))

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        _resolve_sprint("X", "u@r.com", "tok")
        url = requests[0].full_url
        assert "state=active%2Cfuture" in url or "state=active,future" in url

    def test_named_sprint_exits_when_not_found(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sprints = [{"id": 1, "name": "Sprint A", "state": "active"}]

        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            return _FakeHTTPResponse(200, _sprint_api_body(sprints))

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(SystemExit):
            _resolve_sprint("Nonexistent", "u@r.com", "tok")
        err = capsys.readouterr().err
        assert "Sprint A" in err

    def test_constructs_correct_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sprints = [{"id": 1, "name": "S", "state": "active"}]
        requests: list[urllib.request.Request] = []

        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            requests.append(req)
            return _FakeHTTPResponse(200, _sprint_api_body(sprints))

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        _resolve_sprint("autodetect", "u@r.com", "tok")
        url = requests[0].full_url
        expected = f"{_JIRA_BASE_URL}/rest/agile/1.0/board/{_BOARD_ID}/sprint"
        assert url.startswith(expected)

    def test_sends_basic_auth(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sprints = [{"id": 1, "name": "S", "state": "active"}]
        requests: list[urllib.request.Request] = []

        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            requests.append(req)
            return _FakeHTTPResponse(200, _sprint_api_body(sprints))

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        _resolve_sprint("autodetect", "me@x.com", "secret")
        auth = requests[0].get_header("Authorization")
        expected = base64.b64encode(b"me@x.com:secret").decode()
        assert auth == f"Basic {expected}"

    def test_exits_on_http_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            raise urllib.error.HTTPError(
                req.full_url,
                403,
                "Forbidden",
                Message(),
                None,
            )

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(SystemExit):
            _resolve_sprint("autodetect", "u@r.com", "tok")
        err = capsys.readouterr().err
        assert "403" in err


# ---------------------------------------------------------------------------
# TestBuildUpdatePayload
# ---------------------------------------------------------------------------


class TestBuildUpdatePayload:
    def test_payload_without_sprint(self) -> None:
        fields = _build_update_payload("Major")
        assert fields["priority"] == {"name": "Major"}
        assert fields["components"] == [{"name": _COMPONENT}]
        assert fields[_TEAM_FIELD] == _TEAM_VALUE
        assert _SPRINT_FIELD not in fields

    def test_payload_with_sprint(self) -> None:
        fields = _build_update_payload("Blocker", sprint_id=68645)
        assert fields[_SPRINT_FIELD] == 68645
        assert fields["priority"] == {"name": "Blocker"}

    def test_payload_without_priority(self) -> None:
        fields = _build_update_payload()
        assert "priority" not in fields
        assert fields["components"] == [{"name": _COMPONENT}]
        assert fields[_TEAM_FIELD] == _TEAM_VALUE

    def test_payload_with_sprint_without_priority(self) -> None:
        fields = _build_update_payload(sprint_id=68645)
        assert "priority" not in fields
        assert fields[_SPRINT_FIELD] == 68645
        assert fields["components"] == [{"name": _COMPONENT}]
        assert fields[_TEAM_FIELD] == _TEAM_VALUE


# ---------------------------------------------------------------------------
# TestUpdateIssueFields
# ---------------------------------------------------------------------------


class TestUpdateIssueFields:
    def test_success_on_204(self, monkeypatch: pytest.MonkeyPatch) -> None:
        requests: list[urllib.request.Request] = []

        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            requests.append(req)
            return _FakeHTTPResponse(204)

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        _update_issue_fields(
            "RHOAIENG-1", {"priority": {"name": "Major"}}, "u@r.com", "tok"
        )

    def test_constructs_correct_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        requests: list[urllib.request.Request] = []

        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            requests.append(req)
            return _FakeHTTPResponse(204)

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        _update_issue_fields("RHOAIENG-999", {}, "u@r.com", "tok")
        assert requests[0].full_url == f"{_JIRA_BASE_URL}/rest/api/3/issue/RHOAIENG-999"

    def test_sends_put_with_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        requests: list[urllib.request.Request] = []

        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            requests.append(req)
            return _FakeHTTPResponse(204)

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        fields: dict[str, object] = {"priority": {"name": "Minor"}}
        _update_issue_fields("RHOAIENG-1", fields, "u@r.com", "tok")
        req = requests[0]
        assert req.get_method() == "PUT"
        assert req.get_header("Content-type") == "application/json"
        assert isinstance(req.data, bytes)
        body = json.loads(req.data)
        assert body == {"fields": fields}

    def test_sends_basic_auth(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        requests: list[urllib.request.Request] = []

        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            requests.append(req)
            return _FakeHTTPResponse(204)

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        _update_issue_fields("RHOAIENG-1", {}, "me@x.com", "secret")
        auth = requests[0].get_header("Authorization")
        expected = base64.b64encode(b"me@x.com:secret").decode()
        assert auth == f"Basic {expected}"

    def test_raises_on_http_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fake_urlopen(req: urllib.request.Request) -> _FakeHTTPResponse:
            raise urllib.error.HTTPError(
                req.full_url,
                400,
                "Bad Request",
                Message(),
                None,
            )

        monkeypatch.setattr(cjt.urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(urllib.error.HTTPError):
            _update_issue_fields("RHOAIENG-1", {}, "u@r.com", "tok")


# ---------------------------------------------------------------------------
# TestUpdateIssue
# ---------------------------------------------------------------------------


class TestUpdateIssue:
    def test_single_call_success(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        call_count = 0

        def fake_update(
            issue_key: str,
            fields: dict[str, object],
            email: str,
            token: str,
        ) -> None:
            nonlocal call_count
            call_count += 1

        monkeypatch.setattr(cjt, "_update_issue_fields", fake_update)
        payload = _build_update_payload("Major", sprint_id=100)
        _update_issue("RHOAIENG-1", payload, "u@r.com", "tok")
        assert call_count == 1

    def test_retries_on_500(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: list[dict[str, object]] = []
        first_call = True

        def fake_update(
            issue_key: str,
            fields: dict[str, object],
            email: str,
            token: str,
        ) -> None:
            nonlocal first_call
            calls.append(fields)
            if first_call:
                first_call = False
                raise urllib.error.HTTPError(
                    "url",
                    500,
                    "Server Error",
                    Message(),
                    None,
                )

        monkeypatch.setattr(cjt, "_update_issue_fields", fake_update)
        payload = _build_update_payload("Major", sprint_id=100)
        _update_issue("RHOAIENG-1", payload, "u@r.com", "tok")
        assert len(calls) == 3

    def test_split_separates_standard_from_custom_fields(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: list[dict[str, object]] = []
        first_call = True

        def fake_update(
            issue_key: str,
            fields: dict[str, object],
            email: str,
            token: str,
        ) -> None:
            nonlocal first_call
            calls.append(dict(fields))
            if first_call:
                first_call = False
                raise urllib.error.HTTPError(
                    "url",
                    500,
                    "Server Error",
                    Message(),
                    None,
                )

        monkeypatch.setattr(cjt, "_update_issue_fields", fake_update)
        fields = _build_update_payload("Major", sprint_id=100)
        _update_issue("RHOAIENG-1", fields, "u@r.com", "tok")
        standard_call = calls[1]
        custom_call = calls[2]
        assert "priority" in standard_call
        assert "components" in standard_call
        assert not any(k.startswith("customfield_") for k in standard_call)
        assert all(k.startswith("customfield_") for k in custom_call)
        assert _TEAM_FIELD in custom_call
        assert _SPRINT_FIELD in custom_call

    def test_exits_when_second_split_call_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        call_count = 0

        def fake_update(
            issue_key: str,
            fields: dict[str, object],
            email: str,
            token: str,
        ) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise urllib.error.HTTPError(
                    "url",
                    500,
                    "Server Error",
                    Message(),
                    None,
                )
            if call_count == 3:
                raise urllib.error.HTTPError(
                    "url",
                    500,
                    "Server Error",
                    Message(),
                    None,
                )

        monkeypatch.setattr(cjt, "_update_issue_fields", fake_update)
        fields = _build_update_payload("Major", sprint_id=100)
        with pytest.raises(SystemExit):
            _update_issue("RHOAIENG-1", fields, "u@r.com", "tok")

    def test_exits_on_non_500(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fake_update(
            issue_key: str,
            fields: dict[str, object],
            email: str,
            token: str,
        ) -> None:
            raise urllib.error.HTTPError(
                "url",
                403,
                "Forbidden",
                Message(),
                None,
            )

        monkeypatch.setattr(cjt, "_update_issue_fields", fake_update)
        payload = _build_update_payload("Major")
        with pytest.raises(SystemExit):
            _update_issue("RHOAIENG-1", payload, "u@r.com", "tok")

    def test_exits_when_split_calls_also_fail(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fake_update(
            issue_key: str,
            fields: dict[str, object],
            email: str,
            token: str,
        ) -> None:
            raise urllib.error.HTTPError(
                "url",
                500,
                "Server Error",
                Message(),
                None,
            )

        monkeypatch.setattr(cjt, "_update_issue_fields", fake_update)
        payload = _build_update_payload("Major", sprint_id=100)
        with pytest.raises(SystemExit):
            _update_issue("RHOAIENG-1", payload, "u@r.com", "tok")


# ---------------------------------------------------------------------------
# TestBuildParser
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_requires_summary(self) -> None:
        with pytest.raises(SystemExit):
            _build_parser().parse_args(
                ["--description", "d", "--priority", "Major", "--type", "Task"],
            )

    def test_requires_description(self) -> None:
        with pytest.raises(SystemExit):
            _build_parser().parse_args(
                ["--summary", "s", "--priority", "Major", "--type", "Task"],
            )

    def test_priority_is_optional(self) -> None:
        args = _build_parser().parse_args(
            ["--summary", "s", "--description", "d", "--type", "Task"],
        )
        assert args.priority is None

    def test_requires_type(self) -> None:
        with pytest.raises(SystemExit):
            _build_parser().parse_args(
                ["--summary", "s", "--description", "d", "--priority", "Major"],
            )

    def test_sprint_is_optional(self) -> None:
        args = _build_parser().parse_args(
            [
                "--summary",
                "s",
                "--description",
                "d",
                "--priority",
                "Major",
                "--type",
                "Task",
            ],
        )
        assert args.sprint is None

    @pytest.mark.parametrize("priority", _VALID_PRIORITIES)
    def test_accepts_valid_priorities(self, priority: str) -> None:
        args = _build_parser().parse_args(
            [
                "--summary",
                "s",
                "--description",
                "d",
                "--priority",
                priority,
                "--type",
                "Task",
            ],
        )
        assert args.priority == priority

    @pytest.mark.parametrize("ticket_type", _VALID_TYPES)
    def test_accepts_valid_types(self, ticket_type: str) -> None:
        args = _build_parser().parse_args(
            [
                "--summary",
                "s",
                "--description",
                "d",
                "--priority",
                "Major",
                "--type",
                ticket_type,
            ],
        )
        assert args.ticket_type == ticket_type

    @pytest.mark.parametrize("bad", ["Low", "High", "None", ""])
    def test_rejects_invalid_priority(self, bad: str) -> None:
        with pytest.raises(SystemExit):
            _build_parser().parse_args(
                [
                    "--summary",
                    "s",
                    "--description",
                    "d",
                    "--priority",
                    bad,
                    "--type",
                    "Task",
                ],
            )

    @pytest.mark.parametrize("bad", ["Epic", "Subtask", "Feature", ""])
    def test_rejects_invalid_type(self, bad: str) -> None:
        with pytest.raises(SystemExit):
            _build_parser().parse_args(
                [
                    "--summary",
                    "s",
                    "--description",
                    "d",
                    "--priority",
                    "Major",
                    "--type",
                    bad,
                ],
            )

    def test_sprint_value_preserved(self) -> None:
        args = _build_parser().parse_args(
            [
                "--summary",
                "s",
                "--description",
                "d",
                "--priority",
                "Major",
                "--type",
                "Task",
                "--sprint",
                "autodetect",
            ],
        )
        assert args.sprint == "autodetect"


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------


class TestMain:
    def _patch_all(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        priority: str | None = "Major",
        sprint: str | None = None,
    ) -> dict[str, list[object]]:
        log: dict[str, list[object]] = {
            "email": [],
            "token": [],
            "sprint": [],
            "create": [],
            "update": [],
        }

        monkeypatch.setattr(
            cjt, "_get_email", lambda: (log["email"].append(1), "u@r.com")[1]
        )
        monkeypatch.setattr(
            cjt, "_get_api_token", lambda: (log["token"].append(1), "tok")[1]
        )
        monkeypatch.setattr(
            cjt,
            "_resolve_sprint",
            lambda s, e, t: (log["sprint"].append(s), 999)[1],
        )
        monkeypatch.setattr(
            cjt,
            "_create_ticket",
            lambda t, s, d: (log["create"].append((t, s, d)), "RHOAIENG-1")[1],
        )
        monkeypatch.setattr(
            cjt,
            "_update_issue",
            lambda k, p, e, t: log["update"].append((k, p, e, t)),
        )

        argv = ["--summary", "sum", "--description", "desc", "--type", "Task"]
        if priority:
            argv.extend(["--priority", priority])
        if sprint:
            argv.extend(["--sprint", sprint])
        monkeypatch.setattr("sys.argv", ["create_jira_ticket.py", *argv])
        return log

    def test_full_flow_without_sprint(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        log = self._patch_all(monkeypatch)
        from create_jira_ticket import main

        main()
        assert log["email"]
        assert log["token"]
        assert not log["sprint"]
        assert log["create"] == [("Task", "sum", "desc")]
        assert log["update"]
        update_args = log["update"][0]
        assert isinstance(update_args, tuple)
        assert update_args[0] == "RHOAIENG-1"
        assert update_args[2] == "u@r.com"
        assert update_args[3] == "tok"
        out = capsys.readouterr().out
        assert "RHOAIENG-1" in out

    def test_full_flow_with_sprint(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log = self._patch_all(monkeypatch, sprint="autodetect")
        from create_jira_ticket import main

        main()
        assert log["sprint"] == ["autodetect"]

    def test_full_flow_without_priority(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        log = self._patch_all(monkeypatch, priority=None)
        from create_jira_ticket import main

        main()
        assert log["create"] == [("Task", "sum", "desc")]
        update_args = log["update"][0]
        assert isinstance(update_args, tuple)
        assert update_args[0] == "RHOAIENG-1"
        fields = update_args[1]
        assert isinstance(fields, dict)
        assert "priority" not in fields
        out = capsys.readouterr().out
        assert "RHOAIENG-1" in out

    def test_email_failure_exits_early(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fail_email() -> str:
            raise SystemExit(1)

        monkeypatch.setattr(cjt, "_get_email", fail_email)
        monkeypatch.setattr(
            "sys.argv",
            [
                "create_jira_ticket.py",
                "--summary",
                "s",
                "--description",
                "d",
                "--priority",
                "Major",
                "--type",
                "Task",
            ],
        )
        with pytest.raises(SystemExit):
            from create_jira_ticket import main

            main()
