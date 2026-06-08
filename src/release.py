"""Automated release — bumps versions, tags, and creates a GitHub Release."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from utils.subprocess import run as _run

_PYPROJECT_SNAPSHOT = "999.0.0+SNAPSHOT"
_ARTIFACT_SNAPSHOT = "999-SNAPSHOT"
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _validate_version(version: str) -> None:
    if not _SEMVER_RE.match(version):
        print(
            f"error: invalid version '{version}': expected X.Y.Z (e.g. 0.6.0)",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _check_preconditions(version: str, previous_tag: str, repo_root: Path) -> None:
    _validate_version(version)

    subprocess.run(
        ["git", "fetch", "--tags"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=30,
    )

    tag = f"v{version}"
    result = subprocess.run(
        ["git", "tag", "--list", tag],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=10,
    )
    if tag in result.stdout.splitlines():
        print(f"error: tag {tag} already exists", file=sys.stderr)
        raise SystemExit(1)

    result = subprocess.run(
        ["git", "tag", "--list", previous_tag],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=10,
    )
    if previous_tag not in result.stdout.splitlines():
        print(f"error: previous tag {previous_tag} does not exist", file=sys.stderr)
        raise SystemExit(1)

    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=10,
    )
    branch = result.stdout.strip()
    if branch != "main":
        print(f"error: must be on main branch (currently on {branch})", file=sys.stderr)
        raise SystemExit(1)

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=10,
    )
    if result.stdout.strip():
        print("error: working tree is not clean", file=sys.stderr)
        raise SystemExit(1)


def _skills_with_artifacts(skills_root: Path) -> list[Path]:
    if not skills_root.is_dir():
        return []
    return sorted(
        d
        for d in skills_root.iterdir()
        if d.is_dir() and (d / "artifact.json").is_file()
    )


def _replace_in_file(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"error: expected pattern not found in {path}: {old!r}", file=sys.stderr)
        raise SystemExit(1)
    updated = content.replace(old, new)
    path.write_text(updated, encoding="utf-8")


def _update_pyproject(repo_root: Path, old: str, new: str) -> None:
    _replace_in_file(
        repo_root / "pyproject.toml",
        f'version = "{old}"',
        f'version = "{new}"',
    )


def _update_init_py(repo_root: Path, old: str, new: str) -> None:
    _replace_in_file(
        repo_root / "src" / "__init__.py",
        f'__version__ = "{old}"',
        f'__version__ = "{new}"',
    )


def _update_test_install(repo_root: Path, old: str, new: str) -> None:
    _replace_in_file(
        repo_root / "src" / "tests" / "test_install.py",
        f'DEFAULT_SKILL_VERSION = "{old}"',
        f'DEFAULT_SKILL_VERSION = "{new}"',
    )


def _update_artifacts(skills_root: Path, old: str, new: str) -> None:
    version_pattern = f'"version": "{old}"'
    tag_pattern = f'"tag": "{old}"'
    for skill_dir in _skills_with_artifacts(skills_root):
        path = skill_dir / "artifact.json"
        content = path.read_text(encoding="utf-8")
        if version_pattern not in content:
            print(
                f"error: expected pattern not found in {path}: {version_pattern!r}",
                file=sys.stderr,
            )
            raise SystemExit(1)
        content = content.replace(version_pattern, f'"version": "{new}"')
        content = content.replace(tag_pattern, f'"tag": "{new}"')
        path.write_text(content, encoding="utf-8")


def _set_release_version(repo_root: Path, version: str) -> None:
    _update_pyproject(repo_root, _PYPROJECT_SNAPSHOT, version)
    _update_init_py(repo_root, _PYPROJECT_SNAPSHOT, version)
    _update_test_install(repo_root, _ARTIFACT_SNAPSHOT, version)
    for dir_name in ("skills", "prompts"):
        artifact_dir = repo_root / dir_name
        if artifact_dir.is_dir():
            _update_artifacts(artifact_dir, _ARTIFACT_SNAPSHOT, version)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automate a release: bump versions, tag, and create a GitHub Release.",
    )
    parser.add_argument("previous_tag", help="Previous release tag (e.g. v0.5.0)")
    parser.add_argument("version", help="New version to release (e.g. 0.6.0)")
    args = parser.parse_args()

    previous_tag: str = args.previous_tag
    version: str = args.version
    tag = f"v{version}"
    repo_root = _repo_root()
    branch = f"release-{version}"

    _check_preconditions(version, previous_tag, repo_root)

    print(f"creating release branch {branch}", file=sys.stderr)
    _run(["git", "checkout", "-b", branch], cwd=repo_root)

    try:
        print(f"setting version to {version}", file=sys.stderr)
        _set_release_version(repo_root, version)

        print("syncing uv.lock", file=sys.stderr)
        _run(["uv", "lock"], cwd=repo_root)

        print("running tests", file=sys.stderr)
        _run(["uv", "run", "pytest"], cwd=repo_root)

        print("committing release", file=sys.stderr)
        _run(["git", "add", "-A"], cwd=repo_root)
        _run(
            ["git", "commit", "-m", f"chore: release {tag}"],
            cwd=repo_root,
        )

        print(f"tagging {tag}", file=sys.stderr)
        _run(["git", "tag", tag], cwd=repo_root)

        print(f"pushing tag {tag}", file=sys.stderr)
        _run(["git", "push", "origin", tag], cwd=repo_root)

        print("creating GitHub Release", file=sys.stderr)
        _run(
            [
                "gh",
                "release",
                "create",
                tag,
                "--generate-notes",
                "--notes-start-tag",
                previous_tag,
            ],
            cwd=repo_root,
        )

        print(f"release {tag} complete", file=sys.stderr)
    finally:
        print("discarding uncommitted changes", file=sys.stderr)
        subprocess.run(
            ["git", "checkout", "."],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=10,
        )
        print("switching back to main", file=sys.stderr)
        subprocess.run(
            ["git", "checkout", "main"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=10,
        )
        print(f"deleting local branch {branch}", file=sys.stderr)
        subprocess.run(
            ["git", "branch", "-D", branch],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=10,
        )


if __name__ == "__main__":
    main()
