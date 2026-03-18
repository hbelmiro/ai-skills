"""Tests for src/install.py — skill installer via striatum."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from install import (
    _available_skills,
    _load_artifact,
    _read_artifact_name,
    _read_artifact_version,
    _read_dependencies,
    _resolve_all_deps,
    _run,
    _validate_skill_name,
    install_skill,
    pack_and_push,
    reinstall_all,
    uninstall_skill,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_artifact(
    skills_root: Path,
    name: str,
    version: str = "1.0.0",
    dependencies: list[dict[str, str]] | None = None,
    with_skill_md: bool = True,
    raw_json: str | None = None,
) -> Path:
    skill_dir = skills_root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    if raw_json is not None:
        (skill_dir / "artifact.json").write_text(raw_json, encoding="utf-8")
    else:
        artifact: dict[str, object] = {
            "apiVersion": "striatum.dev/v1alpha1",
            "kind": "Skill",
            "metadata": {"name": name, "version": version},
            "spec": {"entrypoint": "SKILL.md", "files": ["SKILL.md"]},
        }
        if dependencies:
            artifact["dependencies"] = dependencies
        (skill_dir / "artifact.json").write_text(
            json.dumps(artifact, indent=2), encoding="utf-8"
        )
    if with_skill_md:
        (skill_dir / "SKILL.md").write_text(
            dedent(f"""\
                ---
                name: {name}
                description: A skill.
                ---

                # {name}
            """),
            encoding="utf-8",
        )
    return skill_dir


@pytest.fixture()
def skills_root(tmp_path: Path) -> Path:
    return tmp_path / "skills"


def _fake_run_factory() -> tuple[list[list[str]], object]:
    """Return (calls_list, fake_run_fn) for monkeypatching _run."""
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    return calls, fake_run


# ---------------------------------------------------------------------------
# _validate_skill_name
# ---------------------------------------------------------------------------


class TestValidateSkillName:
    @pytest.mark.parametrize(
        "bad_name",
        ["../escape", "a/b", ".", "..", "UPPER", "has space", "under_score", "a\\b"],
    )
    def test_rejects_invalid_names(self, bad_name: str) -> None:
        with pytest.raises(SystemExit):
            _validate_skill_name(bad_name)

    @pytest.mark.parametrize("good_name", ["go-code-review", "a", "skill-1", "a1b"])
    def test_accepts_valid_names(self, good_name: str) -> None:
        _validate_skill_name(good_name)


# ---------------------------------------------------------------------------
# _load_artifact / _read_artifact_version / _read_artifact_name / _read_dependencies
# ---------------------------------------------------------------------------


class TestArtifactReading:
    def test_read_version(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "my-skill", version="2.3.0")
        assert _read_artifact_version(skills_root / "my-skill") == "2.3.0"

    def test_read_name(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "my-skill")
        assert _read_artifact_name(skills_root / "my-skill") == "my-skill"

    def test_read_dependencies_present(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "my-skill",
            dependencies=[{"name": "dep-a", "version": "1.0.0"}],
        )
        deps = _read_dependencies(skills_root / "my-skill")
        assert deps == [{"name": "dep-a", "version": "1.0.0"}]

    def test_read_dependencies_absent(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "my-skill")
        deps = _read_dependencies(skills_root / "my-skill")
        assert deps == []

    def test_read_version_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            _read_artifact_version(tmp_path / "nonexistent")

    def test_read_name_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            _read_artifact_name(tmp_path / "nonexistent")

    def test_read_dependencies_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            _read_dependencies(tmp_path / "nonexistent")

    def test_load_artifact_malformed_json(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "bad", raw_json="{invalid json")
        with pytest.raises(SystemExit):
            _load_artifact(skills_root / "bad")

    def test_read_version_missing_metadata_key(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "bad", raw_json='{"kind": "Skill"}')
        with pytest.raises(SystemExit):
            _read_artifact_version(skills_root / "bad")

    def test_read_name_missing_metadata_key(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "bad", raw_json='{"kind": "Skill"}')
        with pytest.raises(SystemExit):
            _read_artifact_name(skills_root / "bad")

    def test_read_dependencies_invalid_type(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "bad",
            raw_json='{"metadata": {"name": "bad", "version": "1.0.0"}, "dependencies": "not-a-list"}',
        )
        with pytest.raises(SystemExit):
            _read_dependencies(skills_root / "bad")


# ---------------------------------------------------------------------------
# _available_skills
# ---------------------------------------------------------------------------


class TestAvailableSkills:
    def test_lists_skills_with_artifact_json(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "skill-a")
        _make_artifact(skills_root, "skill-b")
        (skills_root / "not-a-skill").mkdir(parents=True)
        assert _available_skills(skills_root) == ["skill-a", "skill-b"]

    def test_empty_when_no_dir(self, tmp_path: Path) -> None:
        assert _available_skills(tmp_path / "nonexistent") == []


# ---------------------------------------------------------------------------
# _resolve_all_deps
# ---------------------------------------------------------------------------


class TestResolveAllDeps:
    def test_no_deps(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "standalone")
        assert _resolve_all_deps("standalone", skills_root) == ["standalone"]

    def test_single_dep(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "base")
        _make_artifact(
            skills_root,
            "child",
            dependencies=[{"name": "base", "version": "1.0.0"}],
        )
        result = _resolve_all_deps("child", skills_root)
        assert result == ["base", "child"]

    def test_transitive_deps(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "review-shared")
        _make_artifact(
            skills_root,
            "go-code-review",
            dependencies=[{"name": "review-shared", "version": "1.0.0"}],
        )
        _make_artifact(
            skills_root,
            "python-code-review",
            dependencies=[{"name": "review-shared", "version": "1.0.0"}],
        )
        _make_artifact(
            skills_root,
            "kfp-review",
            dependencies=[
                {"name": "go-code-review", "version": "1.0.0"},
                {"name": "python-code-review", "version": "1.0.0"},
            ],
        )
        result = _resolve_all_deps("kfp-review", skills_root)
        assert result.index("review-shared") < result.index("go-code-review")
        assert result.index("review-shared") < result.index("python-code-review")
        assert result.index("go-code-review") < result.index("kfp-review")
        assert result.index("python-code-review") < result.index("kfp-review")
        assert len(result) == 4

    def test_deduplicates_shared_dep(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "shared")
        _make_artifact(
            skills_root,
            "a",
            dependencies=[{"name": "shared", "version": "1.0.0"}],
        )
        _make_artifact(
            skills_root,
            "b",
            dependencies=[{"name": "shared", "version": "1.0.0"}],
        )
        _make_artifact(
            skills_root,
            "root",
            dependencies=[
                {"name": "a", "version": "1.0.0"},
                {"name": "b", "version": "1.0.0"},
            ],
        )
        result = _resolve_all_deps("root", skills_root)
        assert result.count("shared") == 1

    def test_cycle_detected(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "a",
            dependencies=[{"name": "b", "version": "1.0.0"}],
        )
        _make_artifact(
            skills_root,
            "b",
            dependencies=[{"name": "a", "version": "1.0.0"}],
        )
        with pytest.raises(SystemExit):
            _resolve_all_deps("a", skills_root)

    def test_self_cycle_detected(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "self-ref",
            dependencies=[{"name": "self-ref", "version": "1.0.0"}],
        )
        with pytest.raises(SystemExit):
            _resolve_all_deps("self-ref", skills_root)


# ---------------------------------------------------------------------------
# _run
# ---------------------------------------------------------------------------


class TestRun:
    def test_success(self) -> None:
        result = _run(["echo", "hello"])
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_failure_exits(self) -> None:
        with pytest.raises(SystemExit):
            _run(["false"])


# ---------------------------------------------------------------------------
# pack_and_push
# ---------------------------------------------------------------------------


class TestPackAndPush:
    def test_calls_validate_pack_push(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "my-skill")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")
        monkeypatch.setattr("install._run", fake_run)

        pack_and_push(
            "my-skill",
            skills_root,
            "localhost:5050/skills",
            striatum="/usr/bin/striatum",
        )

        assert len(calls) == 3
        assert calls[0][1] == "validate"
        assert calls[1][1] == "pack"
        assert calls[2][1] == "push"
        assert "localhost:5050/skills/my-skill:1.0.0" in calls[2]

    def test_missing_skill_exits(self, skills_root: Path) -> None:
        skills_root.mkdir(parents=True, exist_ok=True)
        with pytest.raises(SystemExit):
            pack_and_push(
                "nonexistent",
                skills_root,
                "localhost:5050/skills",
                striatum="/usr/bin/striatum",
            )

    def test_cleans_stale_layout(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skill_dir = _make_artifact(skills_root, "my-skill")
        layout = skill_dir / ".striatum"
        layout.mkdir()
        (layout / "stale").write_text("old", encoding="utf-8")

        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")
        monkeypatch.setattr(
            "install._run",
            lambda *a, **kw: subprocess.CompletedProcess([], 0, "", ""),
        )

        pack_and_push(
            "my-skill",
            skills_root,
            "localhost:5050/skills",
            striatum="/usr/bin/striatum",
        )
        assert not (layout / "stale").exists()

    def test_rejects_invalid_skill_name(self, skills_root: Path) -> None:
        with pytest.raises(SystemExit):
            pack_and_push(
                "../escape",
                skills_root,
                "localhost:5050/skills",
                striatum="/usr/bin/striatum",
            )


# ---------------------------------------------------------------------------
# install_skill
# ---------------------------------------------------------------------------


class TestInstallSkill:
    def test_packs_deps_then_installs(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "review-shared")
        _make_artifact(
            skills_root,
            "go-review",
            dependencies=[{"name": "review-shared", "version": "1.0.0"}],
        )

        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        install_skill("go-review")

        push_calls = [c for c in calls if len(c) > 1 and c[1] == "push"]
        assert len(push_calls) == 2
        assert "review-shared" in push_calls[0][-1]
        assert "go-review" in push_calls[1][-1]

        install_calls = [c for c in calls if len(c) > 2 and c[2] == "install"]
        assert len(install_calls) == 1
        assert "--target" in install_calls[0]
        assert "cursor" in install_calls[0]

    def test_project_flag_passed(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        install_skill("my-skill", project="/tmp/my-project")

        install_calls = [c for c in calls if len(c) > 2 and c[2] == "install"]
        assert "--project" in install_calls[0]
        assert "/tmp/my-project" in install_calls[0]

    def test_force_flag_passed(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        install_skill("my-skill", force=True)

        install_calls = [c for c in calls if len(c) > 2 and c[2] == "install"]
        assert "--force" in install_calls[0]

    def test_missing_registry_exits(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.delenv("STRIATUM_REGISTRY", raising=False)
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        with pytest.raises(SystemExit):
            install_skill("my-skill")

    def test_rejects_invalid_skill_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")
        with pytest.raises(SystemExit):
            install_skill("../escape")


# ---------------------------------------------------------------------------
# uninstall_skill
# ---------------------------------------------------------------------------


class TestUninstallSkill:
    def test_calls_striatum_uninstall(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        uninstall_skill("my-skill")

        assert len(calls) == 1
        assert "uninstall" in calls[0]
        assert "my-skill" in calls[0]

    def test_project_flag_passed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        uninstall_skill("my-skill", project="/tmp/proj")

        assert "--project" in calls[0]
        assert "/tmp/proj" in calls[0]

    def test_rejects_invalid_skill_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")
        with pytest.raises(SystemExit):
            uninstall_skill("../escape")


# ---------------------------------------------------------------------------
# reinstall_all
# ---------------------------------------------------------------------------


class TestReinstallAll:
    def test_calls_striatum_reinstall(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        reinstall_all()

        assert len(calls) == 1
        assert "--reinstall-all" in calls[0]
        assert "--target" in calls[0]
        assert "cursor" in calls[0]

    def test_force_flag_passed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        reinstall_all(force=True)

        assert "--force" in calls[0]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


INSTALL_SCRIPT = Path(__file__).resolve().parent.parent / "install.py"


def _run_cli(
    *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INSTALL_SCRIPT), *args],
        capture_output=True,
        env=env,
        text=True,
        timeout=10,
    )


class TestCli:
    def test_personal_and_project_mutually_exclusive(self) -> None:
        result = _run_cli("--personal", "--project", "/tmp/proj", "--skill", "my-skill")
        assert result.returncode != 0

    def test_missing_skill_flag_errors(self) -> None:
        result = _run_cli("--personal")
        assert result.returncode != 0

    def test_neither_personal_nor_project_errors(self) -> None:
        result = _run_cli("--skill", "my-skill")
        assert result.returncode != 0

    def test_reinstall_all_conflicts_with_skill_target_flags(self) -> None:
        result = _run_cli(
            "--reinstall-all", "--skill", "my-skill", "--project", "/tmp/proj"
        )
        assert result.returncode != 0

    def test_reinstall_all_conflicts_with_uninstall(self) -> None:
        result = _run_cli("--reinstall-all", "--uninstall")
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Integration: real skills directory
# ---------------------------------------------------------------------------


class TestSmoke:
    """End-to-end round-trip against the real skills directory using striatum + registry."""

    @pytest.fixture(autouse=True)
    def _require_striatum_and_registry(self) -> None:
        import shutil as _shutil

        if _shutil.which("striatum") is None:
            pytest.skip("striatum not on PATH")
        reg = os.environ.get("STRIATUM_REGISTRY", "").strip()
        if not reg:
            pytest.skip("STRIATUM_REGISTRY not set")

    def test_install_and_uninstall_via_cli(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        target_dir = project_dir / ".cursor" / "skills"

        env = dict(os.environ)

        result = _run_cli(
            "--skill", "go-code-review", "--project", str(project_dir), env=env
        )
        assert result.returncode == 0, result.stderr

        assert (target_dir / "go-code-review").is_dir()
        assert (target_dir / "go-code-review" / "SKILL.md").is_file()
        assert (target_dir / "review-shared").is_dir()

        result = _run_cli(
            "--skill",
            "go-code-review",
            "--project",
            str(project_dir),
            "--uninstall",
            env=env,
        )
        assert result.returncode == 0, result.stderr
        assert not (target_dir / "go-code-review").exists()
