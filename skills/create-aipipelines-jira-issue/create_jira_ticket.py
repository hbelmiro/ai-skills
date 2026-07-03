"""Create Jira tickets for the AI Pipelines team via acli + Jira REST API."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

_PROJECT = "RHOAIENG"
_COMPONENT = "AI Pipelines"
_TEAM_FIELD = "customfield_10001"
_TEAM_VALUE = "ec74d716-af36-4b3c-950f-f79213d08f71-1530"
_SPRINT_FIELD = "customfield_10020"
_BOARD_ID = "1146"
_JIRA_BASE_URL = "https://redhat.atlassian.net"
_VALID_PRIORITIES = ("Blocker", "Critical", "Major", "Minor", "Trivial")
_VALID_TYPES = ("Task", "Story", "Bug")
_ISSUE_KEY_RE = re.compile(r"(RHOAIENG-\d+)")
_EMAIL_RE = re.compile(r"^\s*Email:\s*(\S+)", re.MULTILINE)
_KEYCHAIN_PREFIX = "go-keyring-base64:"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        msg = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"exit code {result.returncode}"
        )
        print(f"error: {args[0]}: {msg}", file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def _get_email() -> str:
    result = _run(["acli", "jira", "auth", "status"])
    match = _EMAIL_RE.search(result.stdout)
    if not match or not match.group(1):
        print("error: could not parse email from acli auth status", file=sys.stderr)
        raise SystemExit(1)
    return match.group(1)


def _get_api_token() -> str:
    result = _run(["security", "find-generic-password", "-s", "acli", "-w"])
    raw = result.stdout.strip()
    if not raw.startswith(_KEYCHAIN_PREFIX):
        print("error: unexpected token format from keychain", file=sys.stderr)
        raise SystemExit(1)
    encoded = raw[len(_KEYCHAIN_PREFIX) :]
    try:
        return base64.b64decode(encoded).decode()
    except binascii.Error, UnicodeDecodeError:
        print("error: could not decode API token", file=sys.stderr)
        raise SystemExit(1)


def _create_ticket(ticket_type: str, summary: str, description: str) -> str:
    result = _run(
        [
            "acli",
            "jira",
            "workitem",
            "create",
            "-p",
            _PROJECT,
            "-t",
            ticket_type,
            "-s",
            summary,
            "-d",
            description,
        ]
    )
    match = _ISSUE_KEY_RE.search(result.stdout)
    if not match:
        print(
            f"error: could not parse issue key from acli output: {result.stdout}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return match.group(1)


def _resolve_sprint(sprint_arg: str) -> int:
    if sprint_arg == "autodetect":
        state = "active"
    else:
        state = "active,future"
    result = _run(
        [
            "acli",
            "jira",
            "board",
            "list-sprints",
            "--id",
            _BOARD_ID,
            "--state",
            state,
            "--json",
        ]
    )
    sprints: list[dict[str, str | int]] = json.loads(result.stdout)
    if sprint_arg == "autodetect":
        if not sprints:
            print(
                f"error: no active sprints found for board {_BOARD_ID}", file=sys.stderr
            )
            raise SystemExit(1)
        return int(sprints[0]["id"])
    for sprint in sprints:
        if sprint["name"] == sprint_arg:
            return int(sprint["id"])
    names = [str(s["name"]) for s in sprints]
    print(
        f"error: sprint {sprint_arg!r} not found; available: {', '.join(names)}",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _build_update_payload(
    priority: str | None = None,
    sprint_id: int | None = None,
) -> dict[str, object]:
    fields: dict[str, object] = {
        "components": [{"name": _COMPONENT}],
        _TEAM_FIELD: _TEAM_VALUE,
    }
    if priority is not None:
        fields["priority"] = {"name": priority}
    if sprint_id is not None:
        fields[_SPRINT_FIELD] = sprint_id
    return fields


def _update_issue_fields(
    issue_key: str,
    fields: dict[str, object],
    email: str,
    token: str,
) -> None:
    url = f"{_JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"
    data = json.dumps({"fields": fields}).encode()
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Basic {credentials}")
    with urllib.request.urlopen(req):
        pass


def _update_issue(
    issue_key: str,
    fields: dict[str, object],
    email: str,
    token: str,
) -> None:
    try:
        _update_issue_fields(issue_key, fields, email, token)
        return
    except urllib.error.HTTPError as e:
        if e.code != 500:
            print(
                f"error: Jira API returned HTTP {e.code}: {e.reason}", file=sys.stderr
            )
            raise SystemExit(1)

    standard = {k: v for k, v in fields.items() if not k.startswith("customfield_")}
    custom = {k: v for k, v in fields.items() if k.startswith("customfield_")}
    try:
        if standard:
            _update_issue_fields(issue_key, standard, email, token)
        if custom:
            _update_issue_fields(issue_key, custom, email, token)
    except urllib.error.HTTPError as e:
        print(f"error: Jira API returned HTTP {e.code}: {e.reason}", file=sys.stderr)
        raise SystemExit(1)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a Jira ticket for the AI Pipelines team.",
    )
    parser.add_argument("--summary", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--priority", default=None, choices=_VALID_PRIORITIES)
    parser.add_argument(
        "--type", required=True, choices=_VALID_TYPES, dest="ticket_type"
    )
    parser.add_argument("--sprint", default=None)
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    email = _get_email()
    token = _get_api_token()

    sprint_id = None
    if args.sprint:
        sprint_id = _resolve_sprint(args.sprint)

    issue_key = _create_ticket(args.ticket_type, args.summary, args.description)

    fields = _build_update_payload(args.priority, sprint_id)
    _update_issue(issue_key, fields, email, token)

    print(f"✓ {issue_key}: {_JIRA_BASE_URL}/browse/{issue_key}")


if __name__ == "__main__":
    main()
