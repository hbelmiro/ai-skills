"""Tests for src/install.py — skill installer for Cursor."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from install import (
    detect_dependencies,
    install_skill,
    installed_skills,
    load_installed_db,
    reinstall_all,
    remove_installed_entry,
    save_installed_db,
    track_installed_entry,
    uninstall_skill,
    validate_skill,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_skill(
    skills_root: Path,
    name: str,
    skill_md_content: str | None = None,
    extra_files: dict[str, str] | None = None,
) -> Path:
    """Create a minimal skill directory under *skills_root*."""
    skill_dir = skills_root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    if skill_md_content is not None:
        (skill_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")
    if extra_files:
        for rel_path, content in extra_files.items():
            p = skill_dir / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    return skill_dir


def _valid_frontmatter(name: str = "my-skill", description: str = "A skill.") -> str:
    return dedent(f"""\
        ---
        name: {name}
        description: {description}
        ---

        # {name}
    """)


@pytest.fixture()
def skills_root(tmp_path: Path) -> Path:
    return tmp_path / "skills"


@pytest.fixture()
def target_dir(tmp_path: Path) -> Path:
    return tmp_path / "target"


def _skill_with_dep_content(
    name: str = "my-skill",
    description: str = "A skill.",
    dep: str = "review-shared",
    dep_file: str = "checklist.md",
) -> str:
    return dedent(f"""\
        ---
        name: {name}
        description: {description}
        ---

        1. Read `../{dep}/{dep_file}`.
    """)


@pytest.fixture()
def skill_with_dep(skills_root: Path) -> Path:
    """A skill that depends on ``review-shared/checklist.md``."""
    _make_skill(
        skills_root,
        "review-shared",
        extra_files={"checklist.md": "content"},
    )
    return _make_skill(
        skills_root,
        "my-skill",
        _skill_with_dep_content(),
    )


@pytest.fixture()
def two_skills_shared_dep(skills_root: Path) -> tuple[Path, Path]:
    """Two skills (skill-a, skill-b) that both depend on review-shared."""
    _make_skill(
        skills_root,
        "review-shared",
        extra_files={"checklist.md": "content"},
    )
    a = _make_skill(
        skills_root,
        "skill-a",
        _skill_with_dep_content(name="skill-a", description="Skill A."),
    )
    b = _make_skill(
        skills_root,
        "skill-b",
        _skill_with_dep_content(name="skill-b", description="Skill B."),
    )
    return a, b


# ---------------------------------------------------------------------------
# detect_dependencies
# ---------------------------------------------------------------------------


class TestDetectDependencies:
    def test_parses_sibling_references(self, skills_root: Path) -> None:
        content = dedent("""\
            ---
            name: my-skill
            description: A skill.
            ---

            1. Read `../review-shared/general-review-requirements.md`.
            2. Read `../review-shared/go-review-checklist.md`.
            3. Apply checks from `../other-dep/checks.md`.
        """)
        skill_dir = _make_skill(skills_root, "my-skill", content)
        deps = detect_dependencies(skill_dir)
        assert deps == {"review-shared", "other-dep"}

    def test_deduplicates_references(self, skills_root: Path) -> None:
        content = dedent("""\
            ---
            name: my-skill
            description: A skill.
            ---

            1. Read `../review-shared/file-a.md`.
            2. Read `../review-shared/file-b.md`.
            3. Read `../review-shared/file-c.md`.
        """)
        skill_dir = _make_skill(skills_root, "my-skill", content)
        deps = detect_dependencies(skill_dir)
        assert deps == {"review-shared"}

    def test_ignores_local_file_references(self, skills_root: Path) -> None:
        content = dedent("""\
            ---
            name: my-skill
            description: A skill.
            ---

            1. Apply checks from `kfp-review-checklist.md`.
            2. Read `../review-shared/general.md`.
        """)
        skill_dir = _make_skill(skills_root, "my-skill", content)
        deps = detect_dependencies(skill_dir)
        assert deps == {"review-shared"}

    def test_no_skill_md_returns_empty(self, skills_root: Path) -> None:
        skill_dir = _make_skill(skills_root, "bare-skill")
        deps = detect_dependencies(skill_dir)
        assert deps == set()


# ---------------------------------------------------------------------------
# validate_skill
# ---------------------------------------------------------------------------


class TestValidateSkill:
    def test_valid_skill(self, skills_root: Path) -> None:
        _make_skill(
            skills_root,
            "review-shared",
            extra_files={"general.md": "content"},
        )
        _make_skill(
            skills_root,
            "my-skill",
            _skill_with_dep_content(dep_file="general.md"),
        )
        errors = validate_skill(skills_root / "my-skill", skills_root)
        assert errors == []

    def test_missing_skill_md(self, skills_root: Path) -> None:
        _make_skill(skills_root, "no-md")
        errors = validate_skill(skills_root / "no-md", skills_root)
        assert any("SKILL.md" in e for e in errors)

    def test_missing_name_in_frontmatter(self, skills_root: Path) -> None:
        content = dedent("""\
            ---
            description: A skill.
            ---

            # No name
        """)
        _make_skill(skills_root, "no-name", content)
        errors = validate_skill(skills_root / "no-name", skills_root)
        assert any("name" in e.lower() for e in errors)

    def test_missing_description_in_frontmatter(self, skills_root: Path) -> None:
        content = dedent("""\
            ---
            name: my-skill
            ---

            # No description
        """)
        _make_skill(skills_root, "no-desc", content)
        errors = validate_skill(skills_root / "no-desc", skills_root)
        assert any("description" in e.lower() for e in errors)

    def test_empty_name_in_frontmatter(self, skills_root: Path) -> None:
        content = dedent("""\
            ---
            name:
            description: A skill.
            ---

            # Empty name
        """)
        _make_skill(skills_root, "empty-name", content)
        errors = validate_skill(skills_root / "empty-name", skills_root)
        assert any("name" in e.lower() for e in errors)

    def test_empty_description_in_frontmatter(self, skills_root: Path) -> None:
        content = dedent("""\
            ---
            name: my-skill
            description:
            ---

            # Empty description
        """)
        _make_skill(skills_root, "empty-desc", content)
        errors = validate_skill(skills_root / "empty-desc", skills_root)
        assert any("description" in e.lower() for e in errors)

    def test_invalid_yaml_frontmatter(self, skills_root: Path) -> None:
        content = dedent("""\
            ---
            name: [unclosed
            ---

            # Bad YAML
        """)
        _make_skill(skills_root, "bad-yaml", content)
        errors = validate_skill(skills_root / "bad-yaml", skills_root)
        assert any("invalid yaml" in e.lower() for e in errors)
        assert not any("missing 'name'" in e for e in errors)

    def test_returns_all_errors_at_once(self, skills_root: Path) -> None:
        content = dedent("""\
            ---
            description: A skill.
            ---

            1. Read `../nonexistent-dep/file.md`.
        """)
        _make_skill(skills_root, "multi-err", content)
        errors = validate_skill(skills_root / "multi-err", skills_root)
        assert any("name" in e.lower() for e in errors)
        assert any("nonexistent-dep" in e for e in errors)
        assert len(errors) >= 2

    def test_crlf_frontmatter(self, skills_root: Path) -> None:
        content = "---\r\nname: crlf-skill\r\ndescription: A CRLF skill.\r\n---\r\n\r\n# crlf-skill\r\n"
        _make_skill(skills_root, "crlf-skill", content)
        errors = validate_skill(skills_root / "crlf-skill", skills_root)
        assert errors == []

    def test_leading_blank_lines_before_frontmatter(self, skills_root: Path) -> None:
        content = "\n\n---\nname: blank-lead\ndescription: Leading blanks.\n---\n\n# blank-lead\n"
        _make_skill(skills_root, "blank-lead", content)
        errors = validate_skill(skills_root / "blank-lead", skills_root)
        assert errors == []

    def test_missing_dep_directory(self, skills_root: Path) -> None:
        _make_skill(
            skills_root,
            "my-skill",
            _skill_with_dep_content(dep="nonexistent-dep", dep_file="file.md"),
        )
        errors = validate_skill(skills_root / "my-skill", skills_root)
        assert any("nonexistent-dep" in e for e in errors)

    def test_missing_dep_file(self, skills_root: Path) -> None:
        _make_skill(skills_root, "review-shared")
        _make_skill(
            skills_root,
            "my-skill",
            _skill_with_dep_content(dep_file="missing-file.md"),
        )
        errors = validate_skill(skills_root / "my-skill", skills_root)
        assert any("missing-file.md" in e for e in errors)

    def test_invalid_dep_name_flagged(self, skills_root: Path) -> None:
        content = dedent("""\
            ---
            name: my-skill
            description: A skill.
            ---

            1. Read `../../escape/file.md`.
        """)
        _make_skill(skills_root, "my-skill", content)
        errors = validate_skill(skills_root / "my-skill", skills_root)
        assert any("invalid dependency" in e.lower() for e in errors)

    def test_file_ref_path_traversal_flagged(self, skills_root: Path) -> None:
        content = dedent("""\
            ---
            name: my-skill
            description: A skill.
            ---

            1. Read `../review-shared/../../etc/passwd`.
        """)
        _make_skill(skills_root, "review-shared", extra_files={"checklist.md": "ok"})
        _make_skill(skills_root, "my-skill", content)
        errors = validate_skill(skills_root / "my-skill", skills_root)
        assert any("escapes" in e.lower() or "outside" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# install_skill
# ---------------------------------------------------------------------------


class TestInstallSkill:
    def test_creates_symlinks_for_skill_and_deps(
        self, skills_root: Path, target_dir: Path, skill_with_dep: Path
    ) -> None:
        install_skill("my-skill", target_dir, skills_root)

        skill_link = target_dir / "my-skill"
        dep_link = target_dir / "review-shared"
        assert skill_link.is_symlink()
        assert dep_link.is_symlink()
        assert skill_link.resolve() == (skills_root / "my-skill").resolve()
        assert dep_link.resolve() == (skills_root / "review-shared").resolve()

    def test_creates_target_dir_if_missing(
        self, skills_root: Path, target_dir: Path
    ) -> None:
        _make_skill(skills_root, "simple", _valid_frontmatter("simple"))
        assert not target_dir.exists()

        install_skill("simple", target_dir, skills_root)

        assert target_dir.is_dir()
        assert (target_dir / "simple").is_symlink()

    def test_no_dependencies(self, skills_root: Path, target_dir: Path) -> None:
        _make_skill(skills_root, "standalone", _valid_frontmatter("standalone"))

        install_skill("standalone", target_dir, skills_root)

        assert (target_dir / "standalone").is_symlink()
        symlinks = [p for p in target_dir.iterdir() if p.is_symlink()]
        assert len(symlinks) == 1

    def test_idempotent(
        self, skills_root: Path, target_dir: Path, skill_with_dep: Path
    ) -> None:
        install_skill("my-skill", target_dir, skills_root)
        install_skill("my-skill", target_dir, skills_root)

        assert (target_dir / "my-skill").is_symlink()
        assert (target_dir / "review-shared").is_symlink()

    def test_second_skill_shared_dep(
        self,
        skills_root: Path,
        target_dir: Path,
        two_skills_shared_dep: tuple[Path, Path],
    ) -> None:
        install_skill("skill-a", target_dir, skills_root)
        install_skill("skill-b", target_dir, skills_root)

        assert (target_dir / "skill-a").is_symlink()
        assert (target_dir / "skill-b").is_symlink()
        assert (target_dir / "review-shared").is_symlink()

    def test_conflict_real_dir_warns_and_skips(
        self, skills_root: Path, target_dir: Path
    ) -> None:
        _make_skill(skills_root, "my-skill", _valid_frontmatter("my-skill"))
        target_dir.mkdir(parents=True)
        (target_dir / "my-skill").mkdir()
        (target_dir / "my-skill" / "existing-file.txt").write_text(
            "keep me", encoding="utf-8"
        )

        install_skill("my-skill", target_dir, skills_root)

        assert not (target_dir / "my-skill").is_symlink()
        assert (target_dir / "my-skill" / "existing-file.txt").read_text(
            encoding="utf-8"
        ) == "keep me"

    def test_conflict_real_dir_not_overwritten_with_force(
        self, skills_root: Path, target_dir: Path
    ) -> None:
        _make_skill(skills_root, "my-skill", _valid_frontmatter("my-skill"))
        target_dir.mkdir(parents=True)
        (target_dir / "my-skill").mkdir()

        install_skill("my-skill", target_dir, skills_root, force=True)

        assert not (target_dir / "my-skill").is_symlink()

    def test_conflict_real_file_warns_and_skips(
        self,
        skills_root: Path,
        target_dir: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _make_skill(skills_root, "my-skill", _valid_frontmatter("my-skill"))
        target_dir.mkdir(parents=True)
        (target_dir / "my-skill").write_text("I am a file", encoding="utf-8")

        install_skill("my-skill", target_dir, skills_root)

        assert not (target_dir / "my-skill").is_symlink()
        assert (target_dir / "my-skill").read_text(encoding="utf-8") == "I am a file"
        captured = capsys.readouterr()
        assert "existing file" in captured.err

    def test_conflict_symlink_warns_and_skips(
        self, skills_root: Path, target_dir: Path
    ) -> None:
        _make_skill(skills_root, "my-skill", _valid_frontmatter("my-skill"))
        target_dir.mkdir(parents=True)
        other = target_dir.parent / "other"
        other.mkdir()
        (target_dir / "my-skill").symlink_to(other)

        install_skill("my-skill", target_dir, skills_root)

        assert (target_dir / "my-skill").resolve() == other.resolve()

    def test_force_replaces_conflicting_symlink(
        self, skills_root: Path, target_dir: Path
    ) -> None:
        _make_skill(skills_root, "my-skill", _valid_frontmatter("my-skill"))
        target_dir.mkdir(parents=True)
        other = target_dir.parent / "other"
        other.mkdir()
        (target_dir / "my-skill").symlink_to(other)

        install_skill("my-skill", target_dir, skills_root, force=True)

        assert (target_dir / "my-skill").is_symlink()
        assert (target_dir / "my-skill").resolve() == (
            skills_root / "my-skill"
        ).resolve()

    def test_conflict_does_not_install_deps(
        self, skills_root: Path, target_dir: Path, skill_with_dep: Path
    ) -> None:
        target_dir.mkdir(parents=True)
        (target_dir / "my-skill").mkdir()

        install_skill("my-skill", target_dir, skills_root)

        assert not (target_dir / "my-skill").is_symlink()
        assert not (target_dir / "review-shared").exists()

    def test_validate_blocks_install(self, skills_root: Path, target_dir: Path) -> None:
        _make_skill(skills_root, "bad-skill")

        with pytest.raises(SystemExit):
            install_skill("bad-skill", target_dir, skills_root)

        if target_dir.exists():
            symlinks = [p for p in target_dir.iterdir() if p.is_symlink()]
            assert symlinks == []

    def test_missing_skill_lists_available(
        self, skills_root: Path, target_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _make_skill(skills_root, "real-skill", _valid_frontmatter("real-skill"))

        with pytest.raises(SystemExit):
            install_skill("nonexistent", target_dir, skills_root)

        captured = capsys.readouterr()
        assert "real-skill" in captured.err

    @pytest.mark.parametrize(
        "bad_name",
        ["../escape", "a/b", ".", "..", "UPPER", "has space", "under_score"],
    )
    def test_install_rejects_invalid_skill_name(
        self,
        skills_root: Path,
        target_dir: Path,
        bad_name: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with pytest.raises(SystemExit):
            install_skill(bad_name, target_dir, skills_root)

        assert "invalid skill name" in capsys.readouterr().err

        if target_dir.exists():
            assert list(target_dir.iterdir()) == []


# ---------------------------------------------------------------------------
# uninstall_skill
# ---------------------------------------------------------------------------


class TestUninstallSkill:
    def test_removes_skill_symlink(self, skills_root: Path, target_dir: Path) -> None:
        _make_skill(skills_root, "my-skill", _valid_frontmatter("my-skill"))
        install_skill("my-skill", target_dir, skills_root)
        assert (target_dir / "my-skill").is_symlink()

        removed = uninstall_skill("my-skill", target_dir, skills_root)
        assert removed is True

        assert not (target_dir / "my-skill").exists()

    def test_not_installed_warns_gracefully(
        self, skills_root: Path, target_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _make_skill(skills_root, "my-skill", _valid_frontmatter("my-skill"))
        target_dir.mkdir(parents=True)

        removed = uninstall_skill("my-skill", target_dir, skills_root)
        assert removed is False

        captured = capsys.readouterr()
        assert "not installed" in captured.err.lower()

    def test_target_dir_missing(
        self, skills_root: Path, target_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert not target_dir.exists()

        removed = uninstall_skill("my-skill", target_dir, skills_root)
        assert removed is False

        captured = capsys.readouterr()
        assert "not installed" in captured.err.lower()

    def test_does_not_remove_symlink_pointing_elsewhere(
        self, skills_root: Path, target_dir: Path
    ) -> None:
        target_dir.mkdir(parents=True)
        other = target_dir.parent / "other"
        other.mkdir()
        (target_dir / "my-skill").symlink_to(other)

        removed = uninstall_skill("my-skill", target_dir, skills_root)
        assert removed is False

        assert (target_dir / "my-skill").is_symlink()
        assert (target_dir / "my-skill").resolve() == other.resolve()

    def test_shared_dep_kept_when_other_skill_needs_it(
        self,
        skills_root: Path,
        target_dir: Path,
        two_skills_shared_dep: tuple[Path, Path],
    ) -> None:
        install_skill("skill-a", target_dir, skills_root)
        install_skill("skill-b", target_dir, skills_root)

        removed = uninstall_skill("skill-a", target_dir, skills_root)
        assert removed is True

        assert not (target_dir / "skill-a").exists()
        assert (target_dir / "skill-b").is_symlink()
        assert (target_dir / "review-shared").is_symlink()

    def test_shared_dep_removed_when_no_other_skill_needs_it(
        self, skills_root: Path, target_dir: Path, skill_with_dep: Path
    ) -> None:
        install_skill("my-skill", target_dir, skills_root)
        removed = uninstall_skill("my-skill", target_dir, skills_root)
        assert removed is True

        assert not (target_dir / "my-skill").exists()
        assert not (target_dir / "review-shared").exists()

    def test_cleans_deps_when_source_dir_deleted(
        self, skills_root: Path, target_dir: Path, skill_with_dep: Path
    ) -> None:
        install_skill("my-skill", target_dir, skills_root)
        assert (target_dir / "review-shared").is_symlink()

        shutil.rmtree(skills_root / "my-skill")

        removed = uninstall_skill("my-skill", target_dir, skills_root)
        assert removed is True

        assert not (target_dir / "my-skill").exists()
        assert not (target_dir / "review-shared").exists()

    @pytest.mark.parametrize(
        "bad_name",
        ["../escape", "a/b", ".", "..", "UPPER", "has space", "under_score"],
    )
    def test_uninstall_rejects_invalid_skill_name(
        self,
        skills_root: Path,
        target_dir: Path,
        bad_name: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with pytest.raises(SystemExit):
            uninstall_skill(bad_name, target_dir, skills_root)

        assert "invalid skill name" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# installed_skills
# ---------------------------------------------------------------------------


class TestInstalledSkills:
    def test_empty_target_dir(self, skills_root: Path, target_dir: Path) -> None:
        target_dir.mkdir(parents=True)
        result = installed_skills(target_dir, skills_root)
        assert result == set()

    def test_missing_target_dir(self, skills_root: Path, target_dir: Path) -> None:
        assert not target_dir.exists()
        result = installed_skills(target_dir, skills_root)
        assert result == set()

    def test_returns_only_skills_not_deps(
        self, skills_root: Path, target_dir: Path, skill_with_dep: Path
    ) -> None:
        install_skill("my-skill", target_dir, skills_root)

        result = installed_skills(target_dir, skills_root)

        assert result == {"my-skill"}


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


def _db_path_for(home_dir: Path) -> Path:
    return home_dir / ".ai-skills" / "installed-skills.yaml"


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

    def test_reinstall_all_does_not_require_skill(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))
        env = dict(os.environ)
        env["HOME"] = str(fake_home)

        result = _run_cli("--reinstall-all", env=env)
        assert result.returncode == 0

    def test_reinstall_all_conflicts_with_skill_target_flags(self) -> None:
        result = _run_cli(
            "--reinstall-all", "--skill", "my-skill", "--project", "/tmp/proj"
        )
        assert result.returncode != 0

    def test_reinstall_all_conflicts_with_uninstall(self) -> None:
        result = _run_cli("--reinstall-all", "--uninstall")
        assert result.returncode != 0


class TestReinstallAllAndDb:
    @staticmethod
    def _setup_home(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> tuple[Path, Path]:
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))
        return fake_home, _db_path_for(fake_home)

    def _setup_conflicting_personal_reinstall_case(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> tuple[Path, Path, Path]:
        fake_home, db_path = self._setup_home(tmp_path, monkeypatch)
        _make_skill(skills_root, "simple", _valid_frontmatter("simple"))
        target_dir = fake_home / ".cursor" / "skills"
        target_dir.mkdir(parents=True)
        other = tmp_path / "other-dir"
        other.mkdir()
        (target_dir / "simple").symlink_to(other)
        save_installed_db(
            {
                "entries": [
                    {
                        "skill": "simple",
                        "target": "personal",
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
            db_path=db_path,
        )
        return target_dir, other, db_path

    def test_install_tracks_personal_record(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_home, db_path = self._setup_home(tmp_path, monkeypatch)

        _make_skill(skills_root, "simple", _valid_frontmatter("simple"))
        target_dir = fake_home / ".cursor" / "skills"
        install_skill("simple", target_dir, skills_root)
        track_installed_entry("simple", personal=True, db_path=db_path)

        db = load_installed_db(db_path=db_path)
        assert db["entries"] == [
            {
                "skill": "simple",
                "target": "personal",
                "status": "ok",
                "last_error": None,
                "updated_at": db["entries"][0]["updated_at"],
            }
        ]

    def test_install_tracks_project_record_with_path(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        _make_skill(skills_root, "simple", _valid_frontmatter("simple"))
        target_dir = project_dir / ".cursor" / "skills"
        install_skill("simple", target_dir, skills_root)
        track_installed_entry("simple", project=project_dir, db_path=db_path)

        db = load_installed_db(db_path=db_path)
        assert db["entries"] == [
            {
                "skill": "simple",
                "target": "project",
                "project_path": str(project_dir.resolve()),
                "status": "ok",
                "last_error": None,
                "updated_at": db["entries"][0]["updated_at"],
            }
        ]

    def test_upsert_prevents_duplicate_records_for_same_key(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_home, db_path = self._setup_home(tmp_path, monkeypatch)

        _make_skill(skills_root, "simple", _valid_frontmatter("simple"))
        target_dir = fake_home / ".cursor" / "skills"
        install_skill("simple", target_dir, skills_root)

        track_installed_entry("simple", personal=True, db_path=db_path)
        track_installed_entry("simple", personal=True, db_path=db_path)

        db = load_installed_db(db_path=db_path)
        assert len(db["entries"]) == 1

    def test_uninstall_removes_matching_record_only(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        project_a = tmp_path / "a"
        project_b = tmp_path / "b"
        project_a.mkdir()
        project_b.mkdir()
        _make_skill(skills_root, "simple", _valid_frontmatter("simple"))

        track_installed_entry("simple", project=project_a, db_path=db_path)
        track_installed_entry("simple", project=project_b, db_path=db_path)

        removed = remove_installed_entry("simple", project=project_a, db_path=db_path)
        assert removed is True

        db = load_installed_db(db_path=db_path)
        assert db["entries"] == [
            {
                "skill": "simple",
                "target": "project",
                "project_path": str(project_b.resolve()),
                "status": "ok",
                "last_error": None,
                "updated_at": db["entries"][0]["updated_at"],
            }
        ]

    def test_uninstall_removes_entry_even_if_errored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        save_installed_db(
            {
                "entries": [
                    {
                        "skill": "bad-skill",
                        "target": "personal",
                        "status": "error",
                        "last_error": "boom",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
            db_path=db_path,
        )
        removed = remove_installed_entry("bad-skill", personal=True, db_path=db_path)
        assert removed is True
        db = load_installed_db(db_path=db_path)
        assert db["entries"] == []

    def test_uninstall_noop_should_not_remove_db_record(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_home, db_path = self._setup_home(tmp_path, monkeypatch)

        _make_skill(skills_root, "simple", _valid_frontmatter("simple"))
        track_installed_entry("simple", personal=True, db_path=db_path)

        target_dir = fake_home / ".cursor" / "skills"
        removed = uninstall_skill("simple", target_dir, skills_root)
        assert removed is False

        db = load_installed_db(db_path=db_path)
        assert len(db["entries"]) == 1
        assert db["entries"][0]["skill"] == "simple"

    def test_reinstall_all_missing_db_is_noop(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._setup_home(tmp_path, monkeypatch)

        report = reinstall_all(skills_root=skills_root)
        assert report.total == 0
        assert report.succeeded == 0
        assert report.failed == 0

    def test_reinstall_all_empty_entries_is_noop(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        save_installed_db({"entries": []}, db_path=db_path)
        report = reinstall_all(skills_root=skills_root, db_path=db_path)
        assert report.total == 0
        assert report.succeeded == 0
        assert report.failed == 0

    def test_reinstall_all_replays_personal_and_project_entries(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_home, db_path = self._setup_home(tmp_path, monkeypatch)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        _make_skill(skills_root, "simple", _valid_frontmatter("simple"))

        save_installed_db(
            {
                "entries": [
                    {
                        "skill": "simple",
                        "target": "personal",
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    },
                    {
                        "skill": "simple",
                        "target": "project",
                        "project_path": str(project_dir),
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:01+00:00",
                    },
                ]
            },
            db_path=db_path,
        )

        report = reinstall_all(skills_root=skills_root, db_path=db_path)
        assert report.total == 2
        assert report.succeeded == 2
        assert report.failed == 0
        assert (fake_home / ".cursor" / "skills" / "simple").is_symlink()
        assert (project_dir / ".cursor" / "skills" / "simple").is_symlink()

    def test_reinstall_all_continues_on_failure_and_marks_error(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        _make_skill(skills_root, "good-skill", _valid_frontmatter("good-skill"))

        save_installed_db(
            {
                "entries": [
                    {
                        "skill": "missing-skill",
                        "target": "personal",
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    },
                    {
                        "skill": "good-skill",
                        "target": "personal",
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:01+00:00",
                    },
                ]
            },
            db_path=db_path,
        )

        report = reinstall_all(skills_root=skills_root, db_path=db_path)
        assert report.total == 2
        assert report.succeeded == 1
        assert report.failed == 1

        db = load_installed_db(db_path=db_path)
        bad = next(e for e in db["entries"] if e["skill"] == "missing-skill")
        good = next(e for e in db["entries"] if e["skill"] == "good-skill")
        assert bad["status"] == "error"
        assert isinstance(bad.get("last_error"), str)
        assert bad["last_error"]
        assert good["status"] == "ok"
        assert good.get("last_error") in (None, "")

    def test_reinstall_all_prints_final_report(
        self,
        skills_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        save_installed_db(
            {
                "entries": [
                    {
                        "skill": "missing-skill",
                        "target": "personal",
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
            db_path=db_path,
        )
        reinstall_all(skills_root=skills_root, db_path=db_path)
        err = capsys.readouterr().err
        assert "reinstall-all report" in err.lower()
        assert "total: 1" in err.lower()
        assert "failed: 1" in err.lower()
        assert "missing-skill" in err

    def test_reinstall_all_marks_missing_skill_field_as_error(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        save_installed_db(
            {
                "entries": [
                    {
                        "target": "personal",
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
            db_path=db_path,
        )
        report = reinstall_all(skills_root=skills_root, db_path=db_path)
        assert report.failed == 1
        db = load_installed_db(db_path=db_path)
        assert db["entries"][0]["status"] == "error"

    def test_reinstall_all_marks_project_missing_path_as_error(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        save_installed_db(
            {
                "entries": [
                    {
                        "skill": "simple",
                        "target": "project",
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
            db_path=db_path,
        )
        report = reinstall_all(skills_root=skills_root, db_path=db_path)
        assert report.failed == 1
        db = load_installed_db(db_path=db_path)
        assert db["entries"][0]["status"] == "error"

    def test_reinstall_all_marks_unknown_target_as_error(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        save_installed_db(
            {
                "entries": [
                    {
                        "skill": "simple",
                        "target": "unknown",
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
            db_path=db_path,
        )
        report = reinstall_all(skills_root=skills_root, db_path=db_path)
        assert report.failed == 1

    def test_project_path_is_normalized_on_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        raw_project = tmp_path / "nested" / ".." / "project-dir"
        (tmp_path / "project-dir").mkdir()

        track_installed_entry("simple", project=raw_project, db_path=db_path)
        db = load_installed_db(db_path=db_path)
        assert db["entries"][0]["project_path"] == str(
            (tmp_path / "project-dir").resolve()
        )

    def test_reinstall_all_uses_normalized_project_path(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        _make_skill(skills_root, "simple", _valid_frontmatter("simple"))
        project_dir = tmp_path / "project-dir"
        project_dir.mkdir()
        save_installed_db(
            {
                "entries": [
                    {
                        "skill": "simple",
                        "target": "project",
                        "project_path": str(project_dir / ".." / "project-dir"),
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
            db_path=db_path,
        )

        report = reinstall_all(skills_root=skills_root, db_path=db_path)
        assert report.succeeded == 1
        assert (project_dir / ".cursor" / "skills" / "simple").is_symlink()

    def test_reinstall_all_without_force_keeps_conflicting_symlink(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target_dir, other, db_path = self._setup_conflicting_personal_reinstall_case(
            skills_root, tmp_path, monkeypatch
        )

        report = reinstall_all(skills_root=skills_root, db_path=db_path, force=False)
        assert report.failed == 1
        assert (target_dir / "simple").resolve() == other.resolve()

    def test_reinstall_all_with_force_replaces_conflicting_symlink(
        self, skills_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target_dir, _, db_path = self._setup_conflicting_personal_reinstall_case(
            skills_root, tmp_path, monkeypatch
        )

        report = reinstall_all(skills_root=skills_root, db_path=db_path, force=True)
        assert report.succeeded == 1
        assert (target_dir / "simple").resolve() == (skills_root / "simple").resolve()

    def test_save_db_permission_error_surfaces_actionable_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_home, _ = self._setup_home(tmp_path, monkeypatch)

        blocked = fake_home / ".ai-skills"
        blocked.write_text("not-a-directory", encoding="utf-8")

        with pytest.raises(SystemExit):
            save_installed_db({"entries": []})

    def test_reinstall_all_reports_db_save_failure(
        self,
        skills_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        _make_skill(skills_root, "simple", _valid_frontmatter("simple"))
        save_installed_db(
            {
                "entries": [
                    {
                        "skill": "simple",
                        "target": "personal",
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
            db_path=db_path,
        )

        def _boom(*_: object, **__: object) -> None:
            raise OSError("write failed")

        monkeypatch.setattr("install.os.replace", _boom)
        with pytest.raises(SystemExit):
            reinstall_all(skills_root=skills_root, db_path=db_path)
        assert "write failed" in capsys.readouterr().err

    def test_save_db_replace_failure_preserves_existing_content(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)
        save_installed_db(
            {
                "entries": [
                    {
                        "skill": "stable",
                        "target": "personal",
                        "status": "ok",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
            db_path=db_path,
        )
        before = db_path.read_text(encoding="utf-8")

        def _boom(*_: object, **__: object) -> None:
            raise OSError("replace failed")

        monkeypatch.setattr("install.os.replace", _boom)
        with pytest.raises(SystemExit):
            save_installed_db(
                {
                    "entries": [
                        {
                            "skill": "changed",
                            "target": "personal",
                            "status": "ok",
                            "updated_at": "2026-01-02T00:00:00+00:00",
                        }
                    ]
                },
                db_path=db_path,
            )

        assert db_path.read_text(encoding="utf-8") == before

    def test_load_db_backfills_missing_status_and_updated_at(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)

        save_installed_db(
            {"entries": [{"skill": "simple", "target": "personal"}]}, db_path=db_path
        )
        db = load_installed_db(db_path=db_path)
        entry = db["entries"][0]
        assert entry["status"] == "ok"
        assert entry["updated_at"]

    def test_load_db_invalid_top_level_schema_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_text("- invalid\n", encoding="utf-8")

        with pytest.raises(SystemExit):
            load_installed_db(db_path=db_path)

    def test_load_db_invalid_entries_schema_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, db_path = self._setup_home(tmp_path, monkeypatch)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_text("entries: not-a-list\n", encoding="utf-8")

        with pytest.raises(SystemExit):
            load_installed_db(db_path=db_path)


# ---------------------------------------------------------------------------
# Integration / smoke test
# ---------------------------------------------------------------------------


class TestSmoke:
    """End-to-end CLI round-trip against the real skills directory."""

    def test_install_and_uninstall_via_cli(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        target_dir = project_dir / ".cursor" / "skills"

        result = _run_cli(
            "--skill", "python-code-review", "--project", str(project_dir)
        )
        assert result.returncode == 0, result.stderr

        assert (target_dir / "python-code-review").is_symlink()
        assert (target_dir / "python-code-review" / "SKILL.md").is_file()
        assert (target_dir / "review-shared").is_symlink()

        result = _run_cli(
            "--skill", "python-code-review", "--project", str(project_dir)
        )
        assert result.returncode == 0, result.stderr
        assert "already installed" in result.stderr

        result = _run_cli(
            "--skill",
            "python-code-review",
            "--project",
            str(project_dir),
            "--uninstall",
        )
        assert result.returncode == 0, result.stderr

        assert not (target_dir / "python-code-review").exists()
        assert not (target_dir / "review-shared").exists()

    def test_reinstall_all_via_cli(self, tmp_path: Path) -> None:
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        env = dict(os.environ)
        env["HOME"] = str(fake_home)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        target_dir = project_dir / ".cursor" / "skills"

        result = _run_cli(
            "--skill", "python-code-review", "--project", str(project_dir), env=env
        )
        assert result.returncode == 0, result.stderr
        assert (target_dir / "python-code-review").is_symlink()
        assert (target_dir / "review-shared").is_symlink()

        (target_dir / "python-code-review").unlink()
        (target_dir / "review-shared").unlink()
        assert not (target_dir / "python-code-review").exists()
        assert not (target_dir / "review-shared").exists()

        result = _run_cli("--reinstall-all", env=env)
        assert result.returncode == 0, result.stderr
        assert "reinstall-all report" in result.stderr.lower()
        assert "failed: 0" in result.stderr.lower()
        assert (target_dir / "python-code-review").is_symlink()
        assert (target_dir / "review-shared").is_symlink()
