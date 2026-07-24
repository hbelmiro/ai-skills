"""Tests for src/release.py — automated release version management."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from release import (
    _set_release_version,
    _skills_with_artifacts,
    _update_artifacts,
    _update_init_py,
    _update_pyproject,
    _update_test_install,
    _validate_version,
)

_PYPROJECT_SNAPSHOT = "999.0.0+SNAPSHOT"
_ARTIFACT_SNAPSHOT = "999-SNAPSHOT"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_pyproject(repo_root: Path, version: str = _PYPROJECT_SNAPSHOT) -> Path:
    path = repo_root / "pyproject.toml"
    path.write_text(
        dedent(f"""\
            [project]
            name = "ai-skills"
            version = "{version}"
            description = "A monorepo"
            requires-python = ">=3.14"
        """),
        encoding="utf-8",
    )
    return path


def _make_init_py(repo_root: Path, version: str = _PYPROJECT_SNAPSHOT) -> Path:
    src = repo_root / "src"
    src.mkdir(parents=True, exist_ok=True)
    path = src / "__init__.py"
    path.write_text(
        f'"""AI Skills monorepo package."""\n\n__version__ = "{version}"\n',
        encoding="utf-8",
    )
    return path


def _make_test_install(repo_root: Path, version: str = _ARTIFACT_SNAPSHOT) -> Path:
    tests = repo_root / "src" / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    path = tests / "test_install.py"
    path.write_text(
        dedent(f"""\
            \"\"\"Tests for install.py.\"\"\"
            DEFAULT_SKILL_VERSION = "{version}"
            _DEFAULT_REGISTRY = "quay.io/hbelmiro"
        """),
        encoding="utf-8",
    )
    return path


def _make_artifact(
    skills_root: Path,
    name: str,
    version: str = _ARTIFACT_SNAPSHOT,
    deps: list[tuple[str, str]] | None = None,
    raw_text: str | None = None,
) -> Path:
    """Create a skill directory with artifact.json.

    *deps* is a list of (repository, tag) tuples for OCI dependencies.
    *raw_text* overrides the generated JSON with an exact string.
    """
    skill_dir = skills_root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    if raw_text is not None:
        (skill_dir / "artifact.json").write_text(raw_text, encoding="utf-8")
    else:
        dep_lines = ""
        if deps:
            entries = []
            for repo, tag in deps:
                entries.append(
                    f'    {{ "source": "oci", "registry": "quay.io/hbelmiro", '
                    f'"repository": "{repo}", "tag": "{tag}" }}'
                )
            dep_lines = ',\n  "dependencies": [\n' + ",\n".join(entries) + "\n  ]"
        text = (
            "{\n"
            '  "apiVersion": "striatum.dev/v1alpha2",\n'
            '  "kind": "Skill",\n'
            '  "metadata": {\n'
            f'    "name": "{name}",\n'
            f'    "version": "{version}"\n'
            "  },\n"
            '  "spec": {\n'
            '    "entrypoint": "SKILL.md",\n'
            '    "files": ["SKILL.md"]\n'
            "  }" + dep_lines + "\n"
            "}\n"
        )
        (skill_dir / "artifact.json").write_text(text, encoding="utf-8")
    return skill_dir


def _make_repo(
    tmp_path: Path,
    *,
    skill_names: list[str] | None = None,
    skill_deps: dict[str, list[tuple[str, str]]] | None = None,
    prompt_names: list[str] | None = None,
    prompt_deps: dict[str, list[tuple[str, str]]] | None = None,
    workflow_names: list[str] | None = None,
    workflow_deps: dict[str, list[tuple[str, str]]] | None = None,
) -> Path:
    """Create a minimal repo structure for integration tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _make_pyproject(repo)
    _make_init_py(repo)
    _make_test_install(repo)
    skills_root = repo / "skills"
    skills_root.mkdir()
    for name in skill_names or []:
        deps = (skill_deps or {}).get(name)
        _make_artifact(skills_root, name, deps=deps)
    if prompt_names:
        prompts_root = repo / "prompts"
        prompts_root.mkdir()
        for name in prompt_names:
            deps = (prompt_deps or {}).get(name)
            _make_artifact(prompts_root, name, deps=deps)
    if workflow_names:
        workflows_root = repo / "workflows"
        workflows_root.mkdir()
        for name in workflow_names:
            deps = (workflow_deps or {}).get(name)
            _make_artifact(workflows_root, name, deps=deps)
    return repo


# ---------------------------------------------------------------------------
# _validate_version
# ---------------------------------------------------------------------------


class TestValidateVersion:
    @pytest.mark.parametrize("version", ["0.6.0", "1.0.0", "10.20.30"])
    def test_accepts_valid_semver(self, version: str) -> None:
        _validate_version(version)

    @pytest.mark.parametrize(
        "version",
        [
            "v0.6.0",
            "0.6.0-rc1",
            "0.6.0+build",
            "0.6",
            "1",
            "",
            "999-SNAPSHOT",
            "abc",
        ],
    )
    def test_rejects_invalid(self, version: str) -> None:
        with pytest.raises(SystemExit):
            _validate_version(version)


# ---------------------------------------------------------------------------
# _skills_with_artifacts
# ---------------------------------------------------------------------------


class TestSkillsWithArtifacts:
    def test_finds_skills_with_artifact_json(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _make_artifact(skills, "alpha")
        _make_artifact(skills, "beta")
        (skills / "no-artifact").mkdir(parents=True)
        result = _skills_with_artifacts(skills)
        assert result == [skills / "alpha", skills / "beta"]

    def test_skips_dirs_without_artifact_json(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "empty-dir").mkdir()
        (skills / "file-only").mkdir()
        (skills / "file-only" / "README.md").write_text("hi", encoding="utf-8")
        result = _skills_with_artifacts(skills)
        assert result == []

    def test_returns_sorted(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _make_artifact(skills, "zebra")
        _make_artifact(skills, "alpha")
        result = _skills_with_artifacts(skills)
        assert result == [skills / "alpha", skills / "zebra"]


# ---------------------------------------------------------------------------
# _update_pyproject
# ---------------------------------------------------------------------------


class TestUpdatePyproject:
    def test_exits_when_pattern_not_found(self, tmp_path: Path) -> None:
        _make_pyproject(tmp_path, version="already-released")
        with pytest.raises(SystemExit):
            _update_pyproject(tmp_path, _PYPROJECT_SNAPSHOT, "0.6.0")

    def test_replaces_snapshot_with_release(self, tmp_path: Path) -> None:
        _make_pyproject(tmp_path)
        _update_pyproject(tmp_path, _PYPROJECT_SNAPSHOT, "0.6.0")
        content = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
        assert 'version = "0.6.0"' in content
        assert _PYPROJECT_SNAPSHOT not in content

    def test_preserves_other_content(self, tmp_path: Path) -> None:
        _make_pyproject(tmp_path)
        _update_pyproject(tmp_path, _PYPROJECT_SNAPSHOT, "0.6.0")
        content = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
        assert 'name = "ai-skills"' in content
        assert 'requires-python = ">=3.14"' in content

    def test_replaces_release_back_to_snapshot(self, tmp_path: Path) -> None:
        _make_pyproject(tmp_path, version="0.6.0")
        _update_pyproject(tmp_path, "0.6.0", _PYPROJECT_SNAPSHOT)
        content = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
        assert f'version = "{_PYPROJECT_SNAPSHOT}"' in content


# ---------------------------------------------------------------------------
# _update_init_py
# ---------------------------------------------------------------------------


class TestUpdateInitPy:
    def test_replaces_snapshot_with_release(self, tmp_path: Path) -> None:
        _make_init_py(tmp_path)
        _update_init_py(tmp_path, _PYPROJECT_SNAPSHOT, "0.6.0")
        content = (tmp_path / "src" / "__init__.py").read_text(encoding="utf-8")
        assert '__version__ = "0.6.0"' in content
        assert _PYPROJECT_SNAPSHOT not in content

    def test_replaces_release_back_to_snapshot(self, tmp_path: Path) -> None:
        _make_init_py(tmp_path, version="0.6.0")
        _update_init_py(tmp_path, "0.6.0", _PYPROJECT_SNAPSHOT)
        content = (tmp_path / "src" / "__init__.py").read_text(encoding="utf-8")
        assert f'__version__ = "{_PYPROJECT_SNAPSHOT}"' in content


# ---------------------------------------------------------------------------
# _update_test_install
# ---------------------------------------------------------------------------


class TestUpdateTestInstall:
    def test_replaces_snapshot_with_release(self, tmp_path: Path) -> None:
        _make_test_install(tmp_path)
        _update_test_install(tmp_path, _ARTIFACT_SNAPSHOT, "0.6.0")
        content = (tmp_path / "src" / "tests" / "test_install.py").read_text(
            encoding="utf-8"
        )
        assert 'DEFAULT_SKILL_VERSION = "0.6.0"' in content
        assert _ARTIFACT_SNAPSHOT not in content

    def test_replaces_release_back_to_snapshot(self, tmp_path: Path) -> None:
        _make_test_install(tmp_path, version="0.6.0")
        _update_test_install(tmp_path, "0.6.0", _ARTIFACT_SNAPSHOT)
        content = (tmp_path / "src" / "tests" / "test_install.py").read_text(
            encoding="utf-8"
        )
        assert f'DEFAULT_SKILL_VERSION = "{_ARTIFACT_SNAPSHOT}"' in content


# ---------------------------------------------------------------------------
# _update_artifacts
# ---------------------------------------------------------------------------


class TestUpdateArtifacts:
    def test_exits_when_version_pattern_not_found(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _make_artifact(skills, "my-skill", version="already-released")
        with pytest.raises(SystemExit):
            _update_artifacts(skills, _ARTIFACT_SNAPSHOT, "0.6.0")

    def test_updates_metadata_version(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _make_artifact(skills, "my-skill")
        _update_artifacts(skills, _ARTIFACT_SNAPSHOT, "0.6.0")
        content = (skills / "my-skill" / "artifact.json").read_text(encoding="utf-8")
        assert '"version": "0.6.0"' in content
        assert _ARTIFACT_SNAPSHOT not in content

    def test_updates_dependency_tags(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _make_artifact(skills, "child", deps=[("review-shared", _ARTIFACT_SNAPSHOT)])
        _update_artifacts(skills, _ARTIFACT_SNAPSHOT, "0.6.0")
        content = (skills / "child" / "artifact.json").read_text(encoding="utf-8")
        assert '"tag": "0.6.0"' in content
        assert _ARTIFACT_SNAPSHOT not in content

    def test_preserves_compact_formatting(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _make_artifact(skills, "child", deps=[("review-shared", _ARTIFACT_SNAPSHOT)])
        _update_artifacts(skills, _ARTIFACT_SNAPSHOT, "0.6.0")
        content = (skills / "child" / "artifact.json").read_text(encoding="utf-8")
        assert '{ "source": "oci"' in content

    def test_handles_no_dependencies(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _make_artifact(skills, "standalone")
        _update_artifacts(skills, _ARTIFACT_SNAPSHOT, "0.6.0")
        content = (skills / "standalone" / "artifact.json").read_text(encoding="utf-8")
        assert '"version": "0.6.0"' in content
        assert "dependencies" not in content

    def test_updates_multiple_skills(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _make_artifact(skills, "alpha")
        _make_artifact(skills, "beta", deps=[("alpha", _ARTIFACT_SNAPSHOT)])
        _update_artifacts(skills, _ARTIFACT_SNAPSHOT, "0.6.0")
        for name in ("alpha", "beta"):
            content = (skills / name / "artifact.json").read_text(encoding="utf-8")
            assert '"version": "0.6.0"' in content
            assert _ARTIFACT_SNAPSHOT not in content

    def test_preserves_non_version_fields(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _make_artifact(skills, "my-skill")
        _update_artifacts(skills, _ARTIFACT_SNAPSHOT, "0.6.0")
        content = (skills / "my-skill" / "artifact.json").read_text(encoding="utf-8")
        assert '"apiVersion": "striatum.dev/v1alpha2"' in content
        assert '"kind": "Skill"' in content
        assert '"name": "my-skill"' in content

    def test_skips_dirs_without_artifact_json(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _make_artifact(skills, "has-artifact")
        (skills / "no-artifact").mkdir(parents=True)
        (skills / "no-artifact" / "README.md").write_text("hi", encoding="utf-8")
        _update_artifacts(skills, _ARTIFACT_SNAPSHOT, "0.6.0")
        assert not (skills / "no-artifact" / "artifact.json").exists()

    def test_updates_multiple_dependency_tags(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        _make_artifact(
            skills,
            "multi-dep",
            deps=[
                ("dep-a", _ARTIFACT_SNAPSHOT),
                ("dep-b", _ARTIFACT_SNAPSHOT),
            ],
        )
        _update_artifacts(skills, _ARTIFACT_SNAPSHOT, "0.6.0")
        content = (skills / "multi-dep" / "artifact.json").read_text(encoding="utf-8")
        assert content.count('"tag": "0.6.0"') == 2
        assert _ARTIFACT_SNAPSHOT not in content


# ---------------------------------------------------------------------------
# _set_release_version (integration)
# ---------------------------------------------------------------------------


class TestSetReleaseVersion:
    def test_updates_all_files(self, tmp_path: Path) -> None:
        repo = _make_repo(
            tmp_path,
            skill_names=["review-shared", "go-review"],
            skill_deps={"go-review": [("review-shared", _ARTIFACT_SNAPSHOT)]},
        )

        _set_release_version(repo, "1.0.0")

        pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
        assert 'version = "1.0.0"' in pyproject
        assert _PYPROJECT_SNAPSHOT not in pyproject

        init_py = (repo / "src" / "__init__.py").read_text(encoding="utf-8")
        assert '__version__ = "1.0.0"' in init_py
        assert _PYPROJECT_SNAPSHOT not in init_py

        test_install = (repo / "src" / "tests" / "test_install.py").read_text(
            encoding="utf-8"
        )
        assert 'DEFAULT_SKILL_VERSION = "1.0.0"' in test_install
        assert _ARTIFACT_SNAPSHOT not in test_install

        for name in ("review-shared", "go-review"):
            artifact = (repo / "skills" / name / "artifact.json").read_text(
                encoding="utf-8"
            )
            assert '"version": "1.0.0"' in artifact
            assert _ARTIFACT_SNAPSHOT not in artifact

        go_artifact = (repo / "skills" / "go-review" / "artifact.json").read_text(
            encoding="utf-8"
        )
        assert '"tag": "1.0.0"' in go_artifact

    def test_updates_artifacts_in_skills_prompts_and_workflows(
        self, tmp_path: Path
    ) -> None:
        repo = _make_repo(
            tmp_path,
            skill_names=["generic-review"],
            skill_deps={"generic-review": [("review-shared", _ARTIFACT_SNAPSHOT)]},
            prompt_names=["review-shared"],
            workflow_names=["thorough-review"],
            workflow_deps={"thorough-review": [("review-shared", _ARTIFACT_SNAPSHOT)]},
        )

        _set_release_version(repo, "2.0.0")

        skill_artifact = (
            repo / "skills" / "generic-review" / "artifact.json"
        ).read_text(encoding="utf-8")
        assert '"version": "2.0.0"' in skill_artifact
        assert _ARTIFACT_SNAPSHOT not in skill_artifact

        prompt_artifact = (
            repo / "prompts" / "review-shared" / "artifact.json"
        ).read_text(encoding="utf-8")
        assert '"version": "2.0.0"' in prompt_artifact
        assert _ARTIFACT_SNAPSHOT not in prompt_artifact

        workflow_artifact = (
            repo / "workflows" / "thorough-review" / "artifact.json"
        ).read_text(encoding="utf-8")
        assert '"version": "2.0.0"' in workflow_artifact
        assert _ARTIFACT_SNAPSHOT not in workflow_artifact
