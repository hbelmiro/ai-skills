"""Tests for src/install.py — skill installer for Cursor."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from install import (
    detect_dependencies,
    install_skill,
    installed_skills,
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


# ---------------------------------------------------------------------------
# uninstall_skill
# ---------------------------------------------------------------------------


class TestUninstallSkill:
    def test_removes_skill_symlink(self, skills_root: Path, target_dir: Path) -> None:
        _make_skill(skills_root, "my-skill", _valid_frontmatter("my-skill"))
        install_skill("my-skill", target_dir, skills_root)
        assert (target_dir / "my-skill").is_symlink()

        uninstall_skill("my-skill", target_dir, skills_root)

        assert not (target_dir / "my-skill").exists()

    def test_not_installed_warns_gracefully(
        self, skills_root: Path, target_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _make_skill(skills_root, "my-skill", _valid_frontmatter("my-skill"))
        target_dir.mkdir(parents=True)

        uninstall_skill("my-skill", target_dir, skills_root)

        captured = capsys.readouterr()
        assert "not installed" in captured.err.lower()

    def test_target_dir_missing(
        self, skills_root: Path, target_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert not target_dir.exists()

        uninstall_skill("my-skill", target_dir, skills_root)

        captured = capsys.readouterr()
        assert "not installed" in captured.err.lower()

    def test_does_not_remove_symlink_pointing_elsewhere(
        self, skills_root: Path, target_dir: Path
    ) -> None:
        target_dir.mkdir(parents=True)
        other = target_dir.parent / "other"
        other.mkdir()
        (target_dir / "my-skill").symlink_to(other)

        uninstall_skill("my-skill", target_dir, skills_root)

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

        uninstall_skill("skill-a", target_dir, skills_root)

        assert not (target_dir / "skill-a").exists()
        assert (target_dir / "skill-b").is_symlink()
        assert (target_dir / "review-shared").is_symlink()

    def test_shared_dep_removed_when_no_other_skill_needs_it(
        self, skills_root: Path, target_dir: Path, skill_with_dep: Path
    ) -> None:
        install_skill("my-skill", target_dir, skills_root)
        uninstall_skill("my-skill", target_dir, skills_root)

        assert not (target_dir / "my-skill").exists()
        assert not (target_dir / "review-shared").exists()


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


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INSTALL_SCRIPT), *args],
        capture_output=True,
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
