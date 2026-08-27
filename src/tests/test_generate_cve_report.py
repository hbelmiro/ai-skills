"""Tests for generate_cve_report.py — CVE report generation for AI Pipelines."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from email.message import Message
from typing import Self

import generate_cve_report as gcr
import pytest
from generate_cve_report import (
    _build_parser,
    _extract_description,
    _extract_version,
    _extract_vuln_id,
    _fetch_issues,
    _get_api_token,
    _get_email,
    _group_issues,
    _jira_search,
    _render_markdown,
    _run,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _issue(
    key: str = "R-1",
    summary: str = "CVE-2026-100 desc [rhoai-3.4]",
    assignee: str = "",
    status: str = "New",
    duedate: str = "",
) -> dict[str, str]:
    return {
        "key": key,
        "summary": summary,
        "assignee": assignee,
        "status": status,
        "duedate": duedate,
    }


def _rest_response(
    issues: list[dict[str, object]],
    is_last: bool = True,
) -> bytes:
    return json.dumps(
        {
            "issues": issues,
            "isLast": is_last,
        }
    ).encode()


def _rest_issue(
    key: str = "R-1",
    summary: str = "CVE-2026-100 desc [rhoai-3.4]",
    assignee_email: str | None = None,
    status_name: str = "New",
    duedate: str | None = None,
) -> dict[str, object]:
    assignee = {"emailAddress": assignee_email} if assignee_email else None
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "status": {"name": status_name},
            "assignee": assignee,
            "duedate": duedate,
        },
    }


# ---------------------------------------------------------------------------
# TestRun
# ---------------------------------------------------------------------------


class TestRun:
    def test_exits_on_nonzero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_subprocess_run(
            *args: object, **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(["cmd"], 1, "", "something failed")

        monkeypatch.setattr(subprocess, "run", fake_subprocess_run)
        with pytest.raises(SystemExit):
            _run(["cmd"])

    def test_returns_result_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_subprocess_run(
            *args: object, **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(["cmd"], 0, "output", "")

        monkeypatch.setattr(subprocess, "run", fake_subprocess_run)
        result = _run(["cmd"])
        assert result.stdout == "output"


# ---------------------------------------------------------------------------
# TestGetEmail
# ---------------------------------------------------------------------------


class TestGetEmail:
    def test_parses_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(args: list[str]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args,
                0,
                "✓ Authenticated\n  Site: redhat.atlassian.net\n  Email: user@redhat.com\n",
                "",
            )

        monkeypatch.setattr(gcr, "_run", fake_run)
        assert _get_email() == "user@redhat.com"

    def test_exits_on_missing_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(args: list[str]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, "not logged in", "")

        monkeypatch.setattr(gcr, "_run", fake_run)
        with pytest.raises(SystemExit):
            _get_email()


# ---------------------------------------------------------------------------
# TestGetApiToken
# ---------------------------------------------------------------------------


class TestGetApiToken:
    def test_decodes_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import base64

        encoded = base64.b64encode(b"my-secret-token").decode()

        def fake_run(args: list[str]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args, 0, f"go-keyring-base64:{encoded}\n", ""
            )

        monkeypatch.setattr(gcr, "_run", fake_run)
        assert _get_api_token() == "my-secret-token"

    def test_exits_on_bad_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(args: list[str]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, "plain-token\n", "")

        monkeypatch.setattr(gcr, "_run", fake_run)
        with pytest.raises(SystemExit):
            _get_api_token()

    def test_exits_on_invalid_base64(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(args: list[str]) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args, 0, "go-keyring-base64:!!!invalid\n", ""
            )

        monkeypatch.setattr(gcr, "_run", fake_run)
        with pytest.raises(SystemExit):
            _get_api_token()


# ---------------------------------------------------------------------------
# TestJiraSearch
# ---------------------------------------------------------------------------


class TestJiraSearch:
    def test_parses_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        body = _rest_response(
            [
                _rest_issue(
                    "RHOAIENG-1", "CVE-2026-1 desc", "u@r.com", "New", "2026-09-15"
                )
            ]
        )

        def fake_urlopen(req: object, **kwargs: object) -> object:
            class FakeResp:
                def read(self) -> bytes:
                    return body

                def __enter__(self) -> Self:
                    return self

                def __exit__(self, *args: object) -> None:
                    pass

            return FakeResp()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        issues = _jira_search("jql", "e@r.com", "token")
        assert len(issues) == 1
        assert issues[0]["key"] == "RHOAIENG-1"
        assert issues[0]["assignee"] == "u@r.com"
        assert issues[0]["duedate"] == "2026-09-15"

    def test_null_assignee_and_duedate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        body = _rest_response([_rest_issue("R-1", "desc", None, "New", None)])

        def fake_urlopen(req: object, **kwargs: object) -> object:
            class FakeResp:
                def read(self) -> bytes:
                    return body

                def __enter__(self) -> Self:
                    return self

                def __exit__(self, *args: object) -> None:
                    pass

            return FakeResp()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        issues = _jira_search("jql", "e@r.com", "token")
        assert issues[0]["assignee"] == ""
        assert issues[0]["duedate"] == ""

    def test_exits_on_http_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_urlopen(req: object, **kwargs: object) -> object:
            raise urllib.error.HTTPError(
                "url",
                403,
                "Forbidden",
                Message(),
                None,
            )

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        with pytest.raises(SystemExit):
            _jira_search("jql", "e@r.com", "token")

    def test_paginates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        page1 = json.dumps(
            {
                "issues": [_rest_issue("R-1")],
                "isLast": False,
                "nextPageToken": "token123",
            }
        ).encode()
        page2 = json.dumps(
            {
                "issues": [_rest_issue("R-2")],
                "isLast": True,
            }
        ).encode()
        pages = iter([page1, page2])
        captured_urls: list[str] = []

        def fake_urlopen(req: urllib.request.Request, **kwargs: object) -> object:
            captured_urls.append(req.full_url)
            body = next(pages)

            class FakeResp:
                def read(self) -> bytes:
                    return body

                def __enter__(self) -> Self:
                    return self

                def __exit__(self, *args: object) -> None:
                    pass

            return FakeResp()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(gcr, "_MAX_RESULTS", 1)
        issues = _jira_search("jql", "e@r.com", "token")
        assert len(issues) == 2
        assert issues[0]["key"] == "R-1"
        assert issues[1]["key"] == "R-2"
        assert "nextPageToken=token123" in captured_urls[1]


# ---------------------------------------------------------------------------
# TestExtractVulnId
# ---------------------------------------------------------------------------


class TestExtractVulnId:
    def test_cve_id(self) -> None:
        summary = (
            "CVE-2026-11824 rhoai/odh-ml-pipelines-driver-rhel9: "
            "SQLite: buffer overflow [rhoai-3.4]"
        )
        assert _extract_vuln_id(summary) == "CVE-2026-11824"

    def test_multiple_cve_ids(self) -> None:
        summary = (
            "CVE-2026-41142, CVE-2026-42216 odh-autorag-v3-5 "
            "openexr-libs 0:3.1.1-3.el9_6.3 3.5.1 GA RHOAI"
        )
        assert _extract_vuln_id(summary) == "CVE-2026-41142, CVE-2026-42216"

    def test_ghsa_id(self) -> None:
        summary = (
            "GHSA-pc3f-x583-g7j2 odh-data-science-pipelines-argo-"
            "workflowcontroller-v3-5 github.com/moby/spdystream 0.5.1 "
            "3.5.1 GA RHOAI"
        )
        assert _extract_vuln_id(summary) == "GHSA-pc3f-x583-g7j2"

    def test_multiple_ghsa_ids(self) -> None:
        summary = (
            "GHSA-9h8m-3fm2-qjrq, GHSA-hfvc-g4fc-pqhx "
            "odh-data-science-pipelines-argo-workflowcontroller-v3-5 "
            "go.opentelemetry.io/otel/sdk 1.43.0 3.5.1 GA RHOAI"
        )
        assert _extract_vuln_id(summary) == "GHSA-9h8m-3fm2-qjrq, GHSA-hfvc-g4fc-pqhx"

    def test_mixed_ghsa_pysec(self) -> None:
        summary = (
            "GHSA-7gcm-g887-7qv7, PYSEC-2026-1805 odh-pipelines-components-v3-5 "
            "protobuf 6.33.5&introduced=6.30.0rc1 3.5.1 GA RHOAI"
        )
        assert _extract_vuln_id(summary) == "GHSA-7gcm-g887-7qv7, PYSEC-2026-1805"

    def test_embargoed_cve(self) -> None:
        summary = (
            "EMBARGOED CVE-2026-18621 rhoai/odh-ml-pipelines-api-server-v2-rhel9: "
            "DSP: V1 Argo template path [rhoai-3.4]"
        )
        assert _extract_vuln_id(summary) == "CVE-2026-18621"

    def test_snyk_cwe(self) -> None:
        summary = (
            "Snyk - [CWE-295] - [high] - [main] - "
            "red-hat-data-services/pipelines-components - "
            "components/data_processing/autorag/documents_indexing/component.py "
            "- Improper Certificate Validation - SSL Verification Bypass"
        )
        assert _extract_vuln_id(summary) == "CWE-295"

    def test_snyk_bracket_prefix(self) -> None:
        summary = "[Snyk] Resolve dspo RBAC High level snyk errors"
        assert _extract_vuln_id(summary) == "[Snyk]"

    def test_no_vuln_id(self) -> None:
        summary = "Automate CVE Triage for AI Pipelines"
        assert _extract_vuln_id(summary) is None

    def test_argo_workflows_no_vuln_id(self) -> None:
        summary = (
            "argo-workflows: CODEOWNERS covers only *.proto — "
            "RH-fork build files have no mandatory reviewer"
        )
        assert _extract_vuln_id(summary) is None

    def test_four_ghsa_ids(self) -> None:
        summary = (
            "GHSA-9493-h29p-rfm2, GHSA-cgrx-mc8f-2prm, "
            "GHSA-qw9x-cqr3-wc7r, GHSA-xr7r-f8xq-vfvv "
            "odh-ai-gateway-payload-processing-e2e-v3-5 "
            "github.com/opencontainers/runc 1.2.8 3.5.1 GA RHOAI"
        )
        assert _extract_vuln_id(summary) == (
            "GHSA-9493-h29p-rfm2, GHSA-cgrx-mc8f-2prm, "
            "GHSA-qw9x-cqr3-wc7r, GHSA-xr7r-f8xq-vfvv"
        )


# ---------------------------------------------------------------------------
# TestExtractVersion
# ---------------------------------------------------------------------------


class TestExtractVersion:
    def test_rhoai_bracket_version(self) -> None:
        summary = (
            "CVE-2026-11824 rhoai/odh-ml-pipelines-driver-rhel9: "
            "SQLite: buffer overflow [rhoai-3.4]"
        )
        assert _extract_version(summary) == "rhoai-3.4"

    def test_rhoai_bracket_three_part(self) -> None:
        summary = "CVE-2025-61728 rhoai/odh-something: desc [rhoai-3.0]"
        assert _extract_version(summary) == "rhoai-3.0"

    def test_ga_rhoai_version(self) -> None:
        summary = (
            "CVE-2026-15308 odh-pipelines-components-v3-5 "
            "python3.12-libs 0:3.12.13-3.el9_8.1 3.5.1 GA RHOAI"
        )
        assert _extract_version(summary) == "3.5.1 GA RHOAI"

    def test_no_version(self) -> None:
        summary = "Automate CVE Triage for AI Pipelines"
        assert _extract_version(summary) is None

    def test_snyk_no_version(self) -> None:
        summary = (
            "Snyk - [CWE-295] - [high] - [main] - "
            "red-hat-data-services/pipelines-components - "
            "components/training/autorag/component.py - "
            "Improper Certificate Validation"
        )
        assert _extract_version(summary) is None


# ---------------------------------------------------------------------------
# TestExtractDescription
# ---------------------------------------------------------------------------


class TestExtractDescription:
    def test_cve_with_bracket_version(self) -> None:
        summary = (
            "CVE-2026-56859 rhoai/odh-ml-pipelines-driver-rhel9: "
            "Go: Denial of Service via XML decoding recursion depth issue [rhoai-3.4]"
        )
        assert _extract_description(summary) == (
            "Go: Denial of Service via XML decoding recursion depth issue"
        )

    def test_cve_with_ga_version(self) -> None:
        summary = (
            "CVE-2026-15308 odh-pipelines-components-v3-5 "
            "python3.12-libs 0:3.12.13-3.el9_8.1 3.5.1 GA RHOAI"
        )
        assert _extract_description(summary) == ""

    def test_no_colon(self) -> None:
        summary = "Automate CVE Triage for AI Pipelines"
        assert _extract_description(summary) == ""

    def test_embargoed_cve(self) -> None:
        summary = (
            "EMBARGOED CVE-2026-18621 rhoai/odh-ml-pipelines-api-server-v2-rhel9: "
            "DSP: V1 Argo template path accepts arbitrary Workflow spec [rhoai-3.4]"
        )
        assert _extract_description(summary) == (
            "DSP: V1 Argo template path accepts arbitrary Workflow spec"
        )

    def test_snyk_cwe(self) -> None:
        summary = (
            "Snyk - [CWE-295] - [high] - [main] - "
            "red-hat-data-services/pipelines-components - "
            "components/data_processing/autorag/documents_indexing/component.py "
            "- Improper Certificate Validation - SSL Verification Bypass"
        )
        assert _extract_description(summary) == ""


# ---------------------------------------------------------------------------
# TestGroupIssues
# ---------------------------------------------------------------------------


class TestGroupIssues:
    def test_groups_by_vuln_then_version(self) -> None:
        issues = [
            _issue("R-1", "CVE-2026-100 image-a: desc [rhoai-3.4]"),
            _issue("R-2", "CVE-2026-100 image-b: desc [rhoai-3.3]"),
            _issue("R-3", "CVE-2026-200 image-c: desc [rhoai-3.4]"),
        ]
        groups = _group_issues(issues)
        assert "CVE-2026-100" in groups
        assert "CVE-2026-200" in groups
        assert "rhoai-3.4" in groups["CVE-2026-100"]
        assert "rhoai-3.3" in groups["CVE-2026-100"]
        assert len(groups["CVE-2026-100"]["rhoai-3.4"]) == 1
        assert len(groups["CVE-2026-100"]["rhoai-3.3"]) == 1
        assert len(groups["CVE-2026-200"]["rhoai-3.4"]) == 1

    def test_no_vuln_id_grouped_under_other(self) -> None:
        issues = [_issue("R-1", "Automate CVE Triage for AI Pipelines")]
        groups = _group_issues(issues)
        assert "Other" in groups

    def test_no_version_grouped_under_unversioned(self) -> None:
        issues = [_issue("R-1", "[Snyk] Resolve dspo RBAC High level snyk errors")]
        groups = _group_issues(issues)
        assert "[Snyk]" in groups
        assert "unversioned" in groups["[Snyk]"]

    def test_empty_input(self) -> None:
        assert _group_issues([]) == {}

    def test_versions_sorted_descending(self) -> None:
        issues = [
            _issue("R-1", "CVE-2026-100 image: desc [rhoai-2.25]"),
            _issue("R-2", "CVE-2026-100 image: desc [rhoai-3.4]"),
            _issue("R-3", "CVE-2026-100 image: desc [rhoai-3.3]"),
        ]
        groups = _group_issues(issues)
        versions = list(groups["CVE-2026-100"].keys())
        assert versions == ["rhoai-3.4", "rhoai-3.3", "rhoai-2.25"]

    def test_unversioned_comes_last(self) -> None:
        issues = [
            _issue("R-1", "CVE-2026-100 image: no version"),
            _issue("R-2", "CVE-2026-100 image: desc [rhoai-3.4]"),
        ]
        groups = _group_issues(issues)
        versions = list(groups["CVE-2026-100"].keys())
        assert versions == ["rhoai-3.4", "unversioned"]

    def test_ga_rhoai_version_sorts_with_rhoai(self) -> None:
        issues = [
            _issue("R-1", "CVE-2026-100 pkg 3.5.1 GA RHOAI"),
            _issue("R-2", "CVE-2026-100 image: desc [rhoai-3.4]"),
        ]
        groups = _group_issues(issues)
        versions = list(groups["CVE-2026-100"].keys())
        assert versions == ["3.5.1 GA RHOAI", "rhoai-3.4"]

    def test_multiple_issues_same_vuln_same_version(self) -> None:
        issues = [
            _issue("R-1", "CVE-2026-100 image-a: desc [rhoai-3.4]"),
            _issue(
                "R-2",
                "CVE-2026-100 image-b: desc [rhoai-3.4]",
                "u@r.com",
                "In Progress",
            ),
        ]
        groups = _group_issues(issues)
        assert len(groups["CVE-2026-100"]["rhoai-3.4"]) == 2


# ---------------------------------------------------------------------------
# TestRenderMarkdown
# ---------------------------------------------------------------------------


class TestRenderMarkdown:
    def test_renders_header(self) -> None:
        md = _render_markdown({})
        assert "# Open Security Issues — AI Pipelines" in md

    def test_renders_vuln_section(self) -> None:
        groups = {"CVE-2026-100": {"rhoai-3.4": [_issue("RHOAIENG-1")]}}
        md = _render_markdown(groups)
        assert "## CVE-2026-100" in md
        assert "[RHOAIENG-1]" in md
        assert "https://issues.redhat.com/browse/RHOAIENG-1" in md

    def test_renders_table_columns(self) -> None:
        groups = {
            "CVE-2026-100": {
                "rhoai-3.4": [
                    _issue(
                        "RHOAIENG-1",
                        assignee="u@r.com",
                        status="In Progress",
                        duedate="2026-09-15",
                    ),
                ],
            },
        }
        md = _render_markdown(groups)
        assert "| Key " in md
        assert "| Due Date " in md
        assert "| Assignee " in md
        assert "| Status " in md
        assert "| Summary " in md
        assert "u@r.com" in md
        assert "In Progress" in md
        assert "2026-09-15" in md

    def test_empty_assignee_renders_dash(self) -> None:
        groups = {"CVE-2026-100": {"rhoai-3.4": [_issue("RHOAIENG-1")]}}
        md = _render_markdown(groups)
        lines = [line for line in md.splitlines() if "RHOAIENG-1" in line]
        assert len(lines) == 1
        assert "| — |" in lines[0]

    def test_empty_duedate_renders_dash(self) -> None:
        groups = {"CVE-2026-100": {"rhoai-3.4": [_issue("RHOAIENG-1")]}}
        md = _render_markdown(groups)
        lines = [line for line in md.splitlines() if "RHOAIENG-1" in line]
        assert len(lines) == 1
        assert "| — | — |" in lines[0]

    def test_unversioned_uses_no_version_header(self) -> None:
        groups = {
            "[Snyk]": {
                "unversioned": [_issue("RHOAIENG-1", "[Snyk] something")],
            },
        }
        md = _render_markdown(groups)
        assert "## [Snyk]" in md
        assert "### unversioned" not in md

    def test_single_version_no_h3(self) -> None:
        groups = {"CVE-2026-100": {"rhoai-3.4": [_issue("RHOAIENG-1")]}}
        md = _render_markdown(groups)
        assert "## CVE-2026-100" in md
        assert "### rhoai-3.4" not in md

    def test_multiple_versions_get_h3_with_description(self) -> None:
        groups = {
            "CVE-2026-100": {
                "rhoai-3.4": [
                    _issue(
                        "RHOAIENG-1",
                        "CVE-2026-100 rhoai/image: buffer overflow [rhoai-3.4]",
                    ),
                ],
                "rhoai-3.3": [
                    _issue(
                        "RHOAIENG-2",
                        "CVE-2026-100 rhoai/image: buffer overflow [rhoai-3.3]",
                    ),
                ],
            },
        }
        md = _render_markdown(groups)
        assert "### rhoai-3.4 — buffer overflow" in md
        assert "### rhoai-3.3 — buffer overflow" in md

    def test_multiple_versions_h3_no_description(self) -> None:
        groups = {
            "CVE-2026-100": {
                "rhoai-3.4": [_issue("RHOAIENG-1", "CVE-2026-100 no-colon here")],
                "rhoai-3.3": [_issue("RHOAIENG-2", "CVE-2026-100 no-colon here")],
            },
        }
        md = _render_markdown(groups)
        assert "### rhoai-3.4\n" in md
        assert "### rhoai-3.3\n" in md

    def test_pipe_in_summary_escaped(self) -> None:
        groups = {
            "CVE-2026-100": {
                "rhoai-3.4": [
                    _issue("RHOAIENG-1", "CVE-2026-100 foo | bar [rhoai-3.4]"),
                ],
            },
        }
        md = _render_markdown(groups)
        lines = [line for line in md.splitlines() if "RHOAIENG-1" in line]
        assert len(lines) == 1
        assert "foo \\| bar" in lines[0]


# ---------------------------------------------------------------------------
# TestFetchIssues
# ---------------------------------------------------------------------------


class TestFetchIssues:
    def test_calls_jira_search_per_query(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(gcr, "_get_email", lambda: "e@r.com")
        monkeypatch.setattr(gcr, "_get_api_token", lambda: "token")
        calls: list[str] = []

        def fake_jira_search(jql: str, email: str, token: str) -> list[dict[str, str]]:
            calls.append(jql)
            return []

        monkeypatch.setattr(gcr, "_jira_search", fake_jira_search)
        _fetch_issues()
        assert len(calls) == 4

    def test_deduplicates_across_queries(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(gcr, "_get_email", lambda: "e@r.com")
        monkeypatch.setattr(gcr, "_get_api_token", lambda: "token")

        def fake_jira_search(jql: str, email: str, token: str) -> list[dict[str, str]]:
            return [_issue("RHOAIENG-1")]

        monkeypatch.setattr(gcr, "_jira_search", fake_jira_search)
        rows = _fetch_issues()
        assert len(rows) == 1

    def test_merges_unique_issues(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(gcr, "_get_email", lambda: "e@r.com")
        monkeypatch.setattr(gcr, "_get_api_token", lambda: "token")
        call_count = 0

        def fake_jira_search(jql: str, email: str, token: str) -> list[dict[str, str]]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [_issue("R-1")]
            if call_count == 2:
                return [_issue("R-2")]
            return []

        monkeypatch.setattr(gcr, "_jira_search", fake_jira_search)
        rows = _fetch_issues()
        assert len(rows) == 2

    def test_all_queries_have_component_and_status(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(gcr, "_get_email", lambda: "e@r.com")
        monkeypatch.setattr(gcr, "_get_api_token", lambda: "token")
        queries: list[str] = []

        def fake_jira_search(jql: str, email: str, token: str) -> list[dict[str, str]]:
            queries.append(jql)
            return []

        monkeypatch.setattr(gcr, "_jira_search", fake_jira_search)
        _fetch_issues()
        for jql in queries:
            assert 'component = "AI Pipelines"' in jql
            assert "statusCategory != Done" in jql
            assert "status NOT IN (Resolved, Closed)" in jql


# ---------------------------------------------------------------------------
# TestBuildParser
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_default_output(self) -> None:
        args = _build_parser().parse_args([])
        assert args.output == "./open-cves-ai-pipelines.md"

    def test_custom_output(self) -> None:
        args = _build_parser().parse_args(["--output", "/tmp/report.md"])
        assert args.output == "/tmp/report.md"


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------


class TestMain:
    def test_writes_report_to_file(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: object,
    ) -> None:
        import pathlib

        assert isinstance(tmp_path, pathlib.Path)
        output = tmp_path / "report.md"
        monkeypatch.setattr(gcr, "_get_email", lambda: "e@r.com")
        monkeypatch.setattr(gcr, "_get_api_token", lambda: "token")
        monkeypatch.setattr(
            gcr,
            "_jira_search",
            lambda jql, email, token: [
                _issue(
                    "RHOAIENG-1",
                    "CVE-2026-100 image: desc [rhoai-3.4]",
                    duedate="2026-09-15",
                )
            ],
        )
        monkeypatch.setattr(
            "sys.argv",
            ["generate_cve_report.py", "--output", str(output)],
        )
        from generate_cve_report import main

        main()
        content = output.read_text()
        assert "# Open Security Issues — AI Pipelines" in content
        assert "CVE-2026-100" in content
        assert "RHOAIENG-1" in content
        assert "2026-09-15" in content

    def test_empty_results_still_writes_header(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: object,
    ) -> None:
        import pathlib

        assert isinstance(tmp_path, pathlib.Path)
        output = tmp_path / "report.md"
        monkeypatch.setattr(gcr, "_get_email", lambda: "e@r.com")
        monkeypatch.setattr(gcr, "_get_api_token", lambda: "token")
        monkeypatch.setattr(gcr, "_jira_search", lambda jql, email, token: [])
        monkeypatch.setattr(
            "sys.argv",
            ["generate_cve_report.py", "--output", str(output)],
        )
        from generate_cve_report import main

        main()
        content = output.read_text()
        assert "# Open Security Issues — AI Pipelines" in content
