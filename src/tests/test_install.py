"""Tests for src/install.py — skill installer via striatum."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

import install as install_module

from install import (
    _available_skills,
    _global_install_order,
    _load_artifact,
    _read_artifact_name,
    _read_artifact_version,
    _read_dependencies,
    _resolve_all_deps,
    _run,
    _validate_skill_name,
    install_all_skills,
    install_skill,
    pack_and_push,
    reinstall_all,
    uninstall_skill,
)

# Synthetic artifacts in this module use the same dev version as skills on main.
DEFAULT_SKILL_VERSION = "0.5.0"
_DEFAULT_REGISTRY = "quay.io/hbelmiro"


def _oci_dep(
    name: str,
    version: str = DEFAULT_SKILL_VERSION,
    registry: str = _DEFAULT_REGISTRY,
) -> dict[str, str]:
    """Build a v1alpha2 OCI dependency dict for test fixtures."""
    return {"source": "oci", "registry": registry, "repository": name, "tag": version}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_artifact(
    skills_root: Path,
    name: str,
    version: str = DEFAULT_SKILL_VERSION,
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
            "apiVersion": "striatum.dev/v1alpha2",
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


def _striatum_target_from_argv(argv: list[str]) -> str:
    """Return the token after the last ``--target`` in a striatum argv list."""
    indices = [i for i, a in enumerate(argv) if a == "--target"]
    assert indices, f"expected --target in argv, got {argv!r}"
    return argv[indices[-1] + 1]


def _is_striatum_skill_install_argv(args: list[str]) -> bool:
    """True if *args* is a ``striatum skill install …`` argv.

    Global flags may appear before the ``skill`` subcommand (e.g.
    ``striatum --debug skill install``). Matches production argv from
    ``install_skill`` which builds ``[striatum, "skill", "install", ...]``.
    """
    try:
        i = args.index("skill")
    except ValueError:
        return False
    return i + 1 < len(args) and args[i + 1] == "install"


# ---------------------------------------------------------------------------
# _is_striatum_skill_install_argv
# ---------------------------------------------------------------------------


class TestIsStriatumSkillInstallArgv:
    @pytest.mark.parametrize(
        ("argv", "expected"),
        [
            (
                ["/usr/bin/striatum", "skill", "install", "--target", "cursor", "ref"],
                True,
            ),
            (
                [
                    "/usr/bin/striatum",
                    "--debug",
                    "skill",
                    "install",
                    "--target",
                    "cursor",
                ],
                True,
            ),
            (["/usr/bin/striatum", "skill", "pack"], False),
            (["/usr/bin/striatum", "validate"], False),
        ],
    )
    def test_detects_skill_install_shape(self, argv: list[str], expected: bool) -> None:
        assert _is_striatum_skill_install_argv(argv) is expected


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
# _validate_targets (via public entrypoints)
# ---------------------------------------------------------------------------


class TestValidateTargets:
    def test_install_skill_rejects_unknown_target(
        self,
        skills_root: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)

        with pytest.raises(SystemExit):
            install_skill("my-skill", targets=["vscode"])

        err = capsys.readouterr().err.lower()
        assert "invalid target" in err
        assert "vscode" in err

    def test_install_all_skills_rejects_unknown_target(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        empty = tmp_path / "skills"
        empty.mkdir()
        monkeypatch.setattr("install._skills_root", lambda: empty)

        with pytest.raises(SystemExit):
            install_all_skills(targets=["vscode"])

        assert "invalid target" in capsys.readouterr().err.lower()

    def test_uninstall_skill_rejects_unknown_target(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            uninstall_skill("my-skill", targets=["vscode"])

        assert "invalid target" in capsys.readouterr().err.lower()

    def test_reinstall_all_rejects_unknown_target(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            reinstall_all(targets=["vscode"])

        assert "invalid target" in capsys.readouterr().err.lower()

    def test_rejects_when_any_target_invalid(
        self,
        skills_root: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)

        with pytest.raises(SystemExit):
            install_skill("my-skill", targets=["cursor", "vscode"])

        err = capsys.readouterr().err.lower()
        assert "invalid target" in err
        assert "vscode" in err

    def test_rejects_empty_targets(
        self,
        skills_root: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)

        with pytest.raises(SystemExit):
            install_skill("my-skill", targets=[])


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
            dependencies=[_oci_dep("dep-a")],
        )
        deps = _read_dependencies(skills_root / "my-skill")
        assert deps == [_oci_dep("dep-a")]

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
            raw_json=json.dumps(
                {
                    "metadata": {"name": "bad", "version": DEFAULT_SKILL_VERSION},
                    "dependencies": "not-a-list",
                }
            ),
        )
        with pytest.raises(SystemExit):
            _read_dependencies(skills_root / "bad")

    def test_read_dependencies_missing_repository_key(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "bad",
            raw_json=json.dumps(
                {
                    "metadata": {"name": "bad", "version": DEFAULT_SKILL_VERSION},
                    "dependencies": [
                        {
                            "source": "oci",
                            "registry": _DEFAULT_REGISTRY,
                            "tag": DEFAULT_SKILL_VERSION,
                        }
                    ],
                }
            ),
        )
        with pytest.raises(SystemExit):
            _read_dependencies(skills_root / "bad")

    def test_read_dependencies_missing_tag_key(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "bad",
            raw_json=json.dumps(
                {
                    "metadata": {"name": "bad", "version": DEFAULT_SKILL_VERSION},
                    "dependencies": [
                        {
                            "source": "oci",
                            "registry": _DEFAULT_REGISTRY,
                            "repository": "dep-a",
                        }
                    ],
                }
            ),
        )
        with pytest.raises(SystemExit):
            _read_dependencies(skills_root / "bad")

    def test_read_dependencies_missing_source_key(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "bad",
            raw_json=json.dumps(
                {
                    "metadata": {"name": "bad", "version": DEFAULT_SKILL_VERSION},
                    "dependencies": [
                        {
                            "registry": _DEFAULT_REGISTRY,
                            "repository": "dep-a",
                            "tag": DEFAULT_SKILL_VERSION,
                        }
                    ],
                }
            ),
        )
        with pytest.raises(SystemExit):
            _read_dependencies(skills_root / "bad")

    def test_read_dependencies_unsupported_source(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "bad",
            raw_json=json.dumps(
                {
                    "metadata": {"name": "bad", "version": DEFAULT_SKILL_VERSION},
                    "dependencies": [
                        {
                            "source": "git",
                            "url": "https://example.com/repo.git",
                            "ref": "main",
                        }
                    ],
                }
            ),
        )
        with pytest.raises(SystemExit):
            _read_dependencies(skills_root / "bad")

    def test_read_dependencies_non_dict_element(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "bad",
            raw_json=json.dumps(
                {
                    "metadata": {"name": "bad", "version": DEFAULT_SKILL_VERSION},
                    "dependencies": ["not-a-dict"],
                }
            ),
        )
        with pytest.raises(SystemExit) as exc_info:
            _read_dependencies(skills_root / "bad")
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, TypeError)


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
            dependencies=[_oci_dep("base")],
        )
        result = _resolve_all_deps("child", skills_root)
        assert result == ["base", "child"]

    def test_transitive_deps(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "review-shared")
        _make_artifact(
            skills_root,
            "go-code-review",
            dependencies=[_oci_dep("review-shared")],
        )
        _make_artifact(
            skills_root,
            "python-code-review",
            dependencies=[_oci_dep("review-shared")],
        )
        _make_artifact(
            skills_root,
            "kfp-review",
            dependencies=[
                _oci_dep("go-code-review"),
                _oci_dep("python-code-review"),
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
            dependencies=[_oci_dep("shared")],
        )
        _make_artifact(
            skills_root,
            "b",
            dependencies=[_oci_dep("shared")],
        )
        _make_artifact(
            skills_root,
            "root",
            dependencies=[
                _oci_dep("a"),
                _oci_dep("b"),
            ],
        )
        result = _resolve_all_deps("root", skills_root)
        assert result.count("shared") == 1

    def test_cycle_detected(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "a",
            dependencies=[_oci_dep("b")],
        )
        _make_artifact(
            skills_root,
            "b",
            dependencies=[_oci_dep("a")],
        )
        with pytest.raises(SystemExit):
            _resolve_all_deps("a", skills_root)

    def test_self_cycle_detected(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "self-ref",
            dependencies=[_oci_dep("self-ref")],
        )
        with pytest.raises(SystemExit):
            _resolve_all_deps("self-ref", skills_root)

    def test_version_mismatch_exits(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "dep", version="2.0.0")
        _make_artifact(
            skills_root,
            "root",
            dependencies=[_oci_dep("dep")],
        )
        with pytest.raises(SystemExit):
            _resolve_all_deps("root", skills_root)

    def test_invalid_dep_name_exits(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "root",
            raw_json=json.dumps(
                {
                    "metadata": {"name": "root", "version": DEFAULT_SKILL_VERSION},
                    "dependencies": [
                        _oci_dep("../escape"),
                    ],
                }
            ),
        )
        with pytest.raises(SystemExit):
            _resolve_all_deps("root", skills_root)


# ---------------------------------------------------------------------------
# _global_install_order
# ---------------------------------------------------------------------------


class TestGlobalInstallOrder:
    def test_independent_skills_sorted(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "zebra")
        _make_artifact(skills_root, "alpha")
        _make_artifact(skills_root, "middle")
        assert _global_install_order(skills_root) == ["alpha", "middle", "zebra"]

    def test_linear_chain_dep_before_dependent(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "base")
        _make_artifact(
            skills_root,
            "child",
            dependencies=[_oci_dep("base")],
        )
        order = _global_install_order(skills_root)
        assert order == ["base", "child"]

    def test_diamond_shared_once_before_consumers_and_root(
        self, skills_root: Path
    ) -> None:
        _make_artifact(skills_root, "shared")
        _make_artifact(
            skills_root,
            "consumer-a",
            dependencies=[_oci_dep("shared")],
        )
        _make_artifact(
            skills_root,
            "consumer-b",
            dependencies=[_oci_dep("shared")],
        )
        _make_artifact(
            skills_root,
            "root",
            dependencies=[
                _oci_dep("consumer-a"),
                _oci_dep("consumer-b"),
            ],
        )
        order = _global_install_order(skills_root)
        assert order.count("shared") == 1
        assert order.index("shared") < order.index("consumer-a")
        assert order.index("shared") < order.index("consumer-b")
        assert order.index("consumer-a") < order.index("root")
        assert order.index("consumer-b") < order.index("root")
        assert len(order) == 4

    def test_cycle_detected(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "a",
            dependencies=[_oci_dep("b")],
        )
        _make_artifact(
            skills_root,
            "b",
            dependencies=[_oci_dep("a")],
        )
        with pytest.raises(SystemExit):
            _global_install_order(skills_root)

    def test_self_cycle_detected(self, skills_root: Path) -> None:
        _make_artifact(
            skills_root,
            "self-ref",
            dependencies=[_oci_dep("self-ref")],
        )
        with pytest.raises(SystemExit):
            _global_install_order(skills_root)

    def test_version_mismatch_exits(self, skills_root: Path) -> None:
        _make_artifact(skills_root, "dep", version="2.0.0")
        _make_artifact(
            skills_root,
            "root",
            dependencies=[_oci_dep("dep")],
        )
        with pytest.raises(SystemExit):
            _global_install_order(skills_root)

    def test_empty_skills_dir(self, tmp_path: Path) -> None:
        empty = tmp_path / "skills"
        empty.mkdir()
        assert _global_install_order(empty) == []


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
        assert f"localhost:5050/skills/my-skill:{DEFAULT_SKILL_VERSION}" in calls[2]

    def test_missing_skill_exits(self, skills_root: Path) -> None:
        skills_root.mkdir(parents=True, exist_ok=True)
        with pytest.raises(SystemExit):
            pack_and_push(
                "nonexistent",
                skills_root,
                "localhost:5050/skills",
                striatum="/usr/bin/striatum",
            )

    def test_cleans_stale_build_dir(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skill_dir = _make_artifact(skills_root, "my-skill")
        build_dir = skill_dir / "build"
        build_dir.mkdir()
        (build_dir / "stale").write_text("old", encoding="utf-8")

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
        assert not (build_dir / "stale").exists()

    def test_cleans_non_directory_build_path(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skill_dir = _make_artifact(skills_root, "my-skill")
        build_dir = skill_dir / "build"
        build_dir.write_text("I am a file", encoding="utf-8")

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
        assert not build_dir.exists()

    def test_name_mismatch_exits(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(
            skills_root,
            "my-skill",
            raw_json=json.dumps(
                {
                    "metadata": {
                        "name": "different-name",
                        "version": DEFAULT_SKILL_VERSION,
                    },
                    "spec": {"entrypoint": "SKILL.md", "files": ["SKILL.md"]},
                }
            ),
        )
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")
        monkeypatch.setattr(
            "install._run",
            lambda *a, **kw: subprocess.CompletedProcess([], 0, "", ""),
        )

        with pytest.raises(SystemExit):
            pack_and_push(
                "my-skill",
                skills_root,
                "localhost:5050/skills",
                striatum="/usr/bin/striatum",
            )

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
            dependencies=[_oci_dep("review-shared")],
        )

        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        install_skill("go-review", targets=["cursor"])

        push_calls = [c for c in calls if len(c) > 1 and c[1] == "push"]
        assert len(push_calls) == 2
        assert any("review-shared" in str(arg) for arg in push_calls[0])
        assert any("go-review" in str(arg) for arg in push_calls[1])

        install_calls = [c for c in calls if _is_striatum_skill_install_argv(c)]
        assert len(install_calls) == 2
        assert "--target" in install_calls[0]
        assert "cursor" in install_calls[0]
        assert any("review-shared" in str(arg) for arg in install_calls[0])
        assert any("go-review" in str(arg) for arg in install_calls[1])

    def test_multi_target_packs_once_installs_per_target(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        install_skill("my-skill", targets=["cursor", "claude"])

        push_calls = [c for c in calls if len(c) > 1 and c[1] == "push"]
        assert len(push_calls) == 1

        install_calls = [c for c in calls if _is_striatum_skill_install_argv(c)]
        assert len(install_calls) == 2
        targets_used = [_striatum_target_from_argv(c) for c in install_calls]
        assert targets_used == ["cursor", "claude"]

    def test_duplicate_targets_deduplicated(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        install_skill("my-skill", targets=["cursor", "cursor"])

        install_calls = [c for c in calls if _is_striatum_skill_install_argv(c)]
        assert len(install_calls) == 1
        assert _striatum_target_from_argv(install_calls[0]) == "cursor"

    def test_install_failure_prints_prior_successes(
        self,
        skills_root: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _make_artifact(skills_root, "review-shared")
        _make_artifact(
            skills_root,
            "go-review",
            dependencies=[_oci_dep("review-shared")],
        )

        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        install_attempts = 0

        def fake_run(
            args: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            nonlocal install_attempts
            if _is_striatum_skill_install_argv(args):
                install_attempts += 1
                if install_attempts >= 2:
                    raise SystemExit(1)
            return subprocess.CompletedProcess(args, 0, "", "")

        monkeypatch.setattr("install._run", fake_run)

        with pytest.raises(SystemExit):
            install_skill("go-review", targets=["cursor"])

        err = capsys.readouterr().err
        assert "successful installs before failure" in err
        assert "review-shared" in err

    def test_project_flag_passed(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        install_skill("my-skill", targets=["cursor"], project="/tmp/my-project")

        install_calls = [c for c in calls if _is_striatum_skill_install_argv(c)]
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

        install_skill("my-skill", targets=["cursor"], force=True)

        install_calls = [c for c in calls if _is_striatum_skill_install_argv(c)]
        assert "--force" in install_calls[0]

    def test_missing_registry_exits(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.delenv("STRIATUM_REGISTRY", raising=False)
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        with pytest.raises(SystemExit):
            install_skill("my-skill", targets=["cursor"])

    def test_rejects_invalid_skill_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")
        with pytest.raises(SystemExit):
            install_skill("../escape", targets=["cursor"])


# ---------------------------------------------------------------------------
# install_all_skills
# ---------------------------------------------------------------------------


class TestInstallAllSkills:
    def test_packs_and_installs_each_skill_once_in_dependency_order(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "review-shared")
        _make_artifact(
            skills_root,
            "go-review",
            dependencies=[_oci_dep("review-shared")],
        )

        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        install_all_skills(targets=["cursor"])

        push_calls = [c for c in calls if len(c) > 1 and c[1] == "push"]
        assert len(push_calls) == 2

        install_calls = [c for c in calls if _is_striatum_skill_install_argv(c)]
        assert len(install_calls) == 2
        assert any("review-shared" in str(arg) for arg in install_calls[0])
        assert any("go-review" in str(arg) for arg in install_calls[1])

    def test_multi_target_packs_once_installs_per_target(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        install_all_skills(targets=["cursor", "claude"])

        push_calls = [c for c in calls if len(c) > 1 and c[1] == "push"]
        assert len(push_calls) == 1

        install_calls = [c for c in calls if _is_striatum_skill_install_argv(c)]
        assert len(install_calls) == 2
        targets_used = [_striatum_target_from_argv(c) for c in install_calls]
        assert targets_used == ["cursor", "claude"]

    def test_empty_skills_no_subprocess_and_no_registry_required(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        empty = tmp_path / "skills"
        empty.mkdir()
        monkeypatch.delenv("STRIATUM_REGISTRY", raising=False)
        monkeypatch.setattr("install._skills_root", lambda: empty)

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        install_all_skills(targets=["cursor"])

        assert calls == []

    def test_project_and_force_passed_to_install(
        self, skills_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_artifact(skills_root, "my-skill")
        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        install_all_skills(targets=["cursor"], project="/tmp/my-project", force=True)

        install_calls = [c for c in calls if _is_striatum_skill_install_argv(c)]
        assert len(install_calls) == 1
        assert "--project" in install_calls[0]
        assert "/tmp/my-project" in install_calls[0]
        assert "--force" in install_calls[0]

    def test_install_failure_prints_prior_successes(
        self,
        skills_root: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _make_artifact(skills_root, "review-shared")
        _make_artifact(
            skills_root,
            "go-review",
            dependencies=[_oci_dep("review-shared")],
        )

        monkeypatch.setenv("STRIATUM_REGISTRY", "localhost:5050/skills")
        monkeypatch.setattr("install._skills_root", lambda: skills_root)
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        install_attempts = 0

        def fake_run(
            args: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            nonlocal install_attempts
            if _is_striatum_skill_install_argv(args):
                install_attempts += 1
                if install_attempts >= 2:
                    raise SystemExit(1)
            return subprocess.CompletedProcess(args, 0, "", "")

        monkeypatch.setattr("install._run", fake_run)

        with pytest.raises(SystemExit):
            install_all_skills(targets=["cursor"])

        err = capsys.readouterr().err
        assert "successful installs before failure" in err
        assert "review-shared" in err


# ---------------------------------------------------------------------------
# uninstall_skill
# ---------------------------------------------------------------------------


class TestUninstallSkill:
    @pytest.mark.parametrize("install_target", ["cursor", "claude"])
    def test_calls_striatum_uninstall(
        self, monkeypatch: pytest.MonkeyPatch, install_target: str
    ) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        uninstall_skill("my-skill", targets=[install_target])

        assert len(calls) == 1
        assert "uninstall" in calls[0]
        assert "my-skill" in calls[0]
        assert _striatum_target_from_argv(calls[0]) == install_target

    def test_multi_target_uninstalls_from_each(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        uninstall_skill("my-skill", targets=["cursor", "claude"])

        uninstall_calls = [c for c in calls if "uninstall" in c]
        assert len(uninstall_calls) == 2
        targets_used = [_striatum_target_from_argv(c) for c in uninstall_calls]
        assert targets_used == ["cursor", "claude"]

    def test_project_flag_passed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        uninstall_skill("my-skill", targets=["cursor"], project="/tmp/proj")

        assert "--project" in calls[0]
        assert "/tmp/proj" in calls[0]

    def test_rejects_invalid_skill_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")
        with pytest.raises(SystemExit):
            uninstall_skill("../escape", targets=["cursor"])


# ---------------------------------------------------------------------------
# reinstall_all
# ---------------------------------------------------------------------------


class TestReinstallAll:
    @pytest.mark.parametrize("install_target", ["cursor", "claude"])
    def test_calls_striatum_reinstall(
        self, monkeypatch: pytest.MonkeyPatch, install_target: str
    ) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        reinstall_all(targets=[install_target])

        assert len(calls) == 1
        assert "--reinstall-all" in calls[0]
        assert _striatum_target_from_argv(calls[0]) == install_target

    def test_multi_target_reinstalls_each(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        reinstall_all(targets=["cursor", "claude"])

        assert len(calls) == 2
        targets_used = [_striatum_target_from_argv(c) for c in calls]
        assert targets_used == ["cursor", "claude"]
        assert all("--reinstall-all" in c for c in calls)

    def test_force_flag_passed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("install.shutil.which", lambda _: "/usr/bin/striatum")

        calls, fake_run = _fake_run_factory()
        monkeypatch.setattr("install._run", fake_run)

        reinstall_all(targets=["cursor"], force=True)

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
        result = _run_cli(
            "--personal",
            "--project",
            "/tmp/proj",
            "--skill",
            "my-skill",
            "--target",
            "cursor",
        )
        assert result.returncode != 0

    def test_missing_target_errors(self) -> None:
        result = _run_cli("--personal", "--skill", "my-skill")
        assert result.returncode != 0
        combined = (result.stderr + result.stdout).lower()
        assert "--target" in combined

    def test_invalid_target_value_rejected(self) -> None:
        result = _run_cli("--target", "vscode", "--personal", "--skill", "my-skill")
        assert result.returncode != 0
        combined = (result.stderr + result.stdout).lower()
        assert "vscode" in combined

    def test_missing_skill_flag_errors(self) -> None:
        result = _run_cli("--personal", "--target", "cursor")
        assert result.returncode != 0

    def test_neither_personal_nor_project_errors(self) -> None:
        result = _run_cli("--skill", "my-skill", "--target", "cursor")
        assert result.returncode != 0

    def test_reinstall_all_conflicts_with_skill_target_flags(self) -> None:
        result = _run_cli(
            "--reinstall-all",
            "--target",
            "cursor",
            "--skill",
            "my-skill",
            "--project",
            "/tmp/proj",
        )
        assert result.returncode != 0

    def test_reinstall_all_conflicts_with_uninstall(self) -> None:
        result = _run_cli("--reinstall-all", "--target", "cursor", "--uninstall")
        assert result.returncode != 0

    def test_install_all_requires_target(self) -> None:
        result = _run_cli("--install-all", "--target", "cursor")
        assert result.returncode != 0

    def test_install_all_conflicts_with_skill(self) -> None:
        result = _run_cli(
            "--install-all",
            "--personal",
            "--skill",
            "go-code-review",
            "--target",
            "cursor",
        )
        assert result.returncode != 0

    def test_install_all_conflicts_with_uninstall(self) -> None:
        result = _run_cli(
            "--install-all", "--personal", "--uninstall", "--target", "cursor"
        )
        assert result.returncode != 0

    def test_install_all_conflicts_with_reinstall_all(self) -> None:
        result = _run_cli(
            "--install-all", "--personal", "--reinstall-all", "--target", "cursor"
        )
        assert result.returncode != 0

    def test_reinstall_all_conflicts_with_install_all(self) -> None:
        result = _run_cli(
            "--reinstall-all", "--personal", "--install-all", "--target", "cursor"
        )
        assert result.returncode != 0

    def test_main_install_all_personal_invokes_install_all_skills(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: dict[str, object] = {}

        def fake_install_all(
            *, targets: list[str], project: str | None, force: bool
        ) -> None:
            called["targets"] = targets
            called["project"] = project
            called["force"] = force

        monkeypatch.setattr(install_module, "install_all_skills", fake_install_all)
        monkeypatch.setattr(
            sys,
            "argv",
            ["install.py", "--personal", "--install-all", "--target", "claude"],
        )
        install_module.main()
        assert called == {"targets": ["claude"], "project": None, "force": False}

    def test_main_install_all_personal_forwards_force(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: dict[str, object] = {}

        def fake_install_all(
            *, targets: list[str], project: str | None, force: bool
        ) -> None:
            called["targets"] = targets
            called["project"] = project
            called["force"] = force

        monkeypatch.setattr(install_module, "install_all_skills", fake_install_all)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "install.py",
                "--personal",
                "--install-all",
                "--force",
                "--target",
                "cursor",
            ],
        )
        install_module.main()
        assert called == {"targets": ["cursor"], "project": None, "force": True}

    def test_main_install_skill_forwards_targets(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: dict[str, object] = {}

        def fake_install(
            skill_name: str, *, targets: list[str], project: str | None, force: bool
        ) -> None:
            called["skill_name"] = skill_name
            called["targets"] = targets
            called["project"] = project
            called["force"] = force

        monkeypatch.setattr(install_module, "install_skill", fake_install)
        monkeypatch.setattr(
            sys,
            "argv",
            ["install.py", "--personal", "--skill", "my-skill", "--target", "claude"],
        )
        install_module.main()
        assert called == {
            "skill_name": "my-skill",
            "targets": ["claude"],
            "project": None,
            "force": False,
        }

    def test_main_install_skill_forwards_multiple_targets(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: dict[str, object] = {}

        def fake_install(
            skill_name: str, *, targets: list[str], project: str | None, force: bool
        ) -> None:
            called["skill_name"] = skill_name
            called["targets"] = targets
            called["project"] = project
            called["force"] = force

        monkeypatch.setattr(install_module, "install_skill", fake_install)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "install.py",
                "--personal",
                "--skill",
                "my-skill",
                "--target",
                "cursor",
                "claude",
            ],
        )
        install_module.main()
        assert called == {
            "skill_name": "my-skill",
            "targets": ["cursor", "claude"],
            "project": None,
            "force": False,
        }

    def test_main_uninstall_skill_forwards_targets(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: dict[str, object] = {}

        def fake_uninstall(
            skill_name: str, *, targets: list[str], project: str | None
        ) -> None:
            called["skill_name"] = skill_name
            called["targets"] = targets
            called["project"] = project

        monkeypatch.setattr(install_module, "uninstall_skill", fake_uninstall)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "install.py",
                "--personal",
                "--skill",
                "my-skill",
                "--uninstall",
                "--target",
                "cursor",
                "claude",
            ],
        )
        install_module.main()
        assert called == {
            "skill_name": "my-skill",
            "targets": ["cursor", "claude"],
            "project": None,
        }

    def test_main_reinstall_all_forwards_targets(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: dict[str, object] = {}

        def fake_reinstall(*, targets: list[str], force: bool) -> None:
            called["targets"] = targets
            called["force"] = force

        monkeypatch.setattr(install_module, "reinstall_all", fake_reinstall)
        monkeypatch.setattr(
            sys,
            "argv",
            ["install.py", "--reinstall-all", "--target", "cursor", "claude"],
        )
        install_module.main()
        assert called == {"targets": ["cursor", "claude"], "force": False}

    def test_cli_accepts_multiple_targets(self) -> None:
        result = _run_cli(
            "--target", "cursor", "claude", "--personal", "--skill", "my-skill"
        )
        assert result.returncode != 2


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

    @pytest.mark.parametrize("install_target", ["cursor", "claude"])
    def test_install_and_uninstall_via_cli(
        self, tmp_path: Path, install_target: str
    ) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        env = dict(os.environ)

        result = _run_cli(
            "--skill",
            "go-code-review",
            "--project",
            str(project_dir),
            "--force",
            "--target",
            install_target,
            env=env,
        )
        assert result.returncode == 0, result.stderr

        if install_target == "cursor":
            target_dir = project_dir / ".cursor" / "skills"
            assert (target_dir / "go-code-review").is_dir()
            assert (target_dir / "go-code-review" / "SKILL.md").is_file()
            assert (target_dir / "review-shared").is_dir()

        result = _run_cli(
            "--skill",
            "go-code-review",
            "--project",
            str(project_dir),
            "--uninstall",
            "--target",
            install_target,
            env=env,
        )
        assert result.returncode == 0, result.stderr

        if install_target == "cursor":
            assert not (target_dir / "go-code-review").exists()
