# create-aipipelines-jira-issue

Creates a Jira issue in the RHOAIENG project with AI Pipelines component,
team field, priority, and optional sprint assignment.

## Contents

- `SKILL.md` — entrypoint with instructions for Claude
- `create_jira_ticket.py` — self-contained Python CLI script (stdlib only)
- `README.md` — this file

## Prerequisites

- [striatum](https://github.com/hbelmiro/striatum) (to install the skill)
- [`acli`](https://developer.atlassian.com/cloud/acli/guides/install-acli/)
  installed and authenticated with an
  [API token](https://id.atlassian.com/manage-profile/security/api-tokens)
- Python 3.x (stdlib only, no pip/uv needed)

## Install

```
striatum install --target claude|cursor|codex quay.io/hbelmiro/create-aipipelines-jira-issue:<version>
```
