"""Skill installer for Cursor — symlinks skills into personal or project targets."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

_SIBLING_REF_RE = re.compile(r"`\.\./([^/`\s]+)/")
_FILE_REF_RE = re.compile(r"`\.\./([^/`\s]+)/([^`\s]+)")
_FRONTMATTER_RE = re.compile(r"^\s*---\s*\r?\n(.*?)\r?\n---", re.DOTALL)

_SKILLS_DIR_NAME = "skills"
_SKILL_MD = "SKILL.md"
_SKILL_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def _validate_skill_name(name: str) -> None:
    """Reject names containing path separators or not matching the naming convention."""
    # Explicit traversal check as defense-in-depth before the regex.
    if (
        "/" in name
        or "\\" in name
        or name in (".", "..")
        or not _SKILL_NAME_RE.match(name)
    ):
        print(
            f"error: invalid skill name '{name}': "
            "must be lowercase alphanumeric with hyphens (e.g. 'go-code-review')",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _skills_root() -> Path:
    return _repo_root() / _SKILLS_DIR_NAME


def _available_skills(skills_root: Path) -> list[str]:
    """Return sorted names of directories under *skills_root* that contain a SKILL.md."""
    if not skills_root.is_dir():
        return []
    return sorted(
        d.name
        for d in skills_root.iterdir()
        if d.is_dir() and (d / _SKILL_MD).is_file()
    )


def detect_dependencies(skill_dir: Path) -> set[str]:
    """Scan SKILL.md for ``../sibling-dir/`` references and return sibling directory names."""
    skill_md = skill_dir / _SKILL_MD
    if not skill_md.is_file():
        return set()
    text = skill_md.read_text(encoding="utf-8")
    return set(_SIBLING_REF_RE.findall(text))


def _validate_frontmatter(text: str, skill_name: str) -> list[str]:
    """Check YAML frontmatter for required *name* and *description* fields."""
    errors: list[str] = []
    fm_match = _FRONTMATTER_RE.match(text)
    if not fm_match:
        errors.append(f"{skill_name}: {_SKILL_MD} frontmatter missing 'name'")
        errors.append(f"{skill_name}: {_SKILL_MD} frontmatter missing 'description'")
        return errors

    try:
        fields = yaml.safe_load(fm_match.group(1))
    except yaml.YAMLError:
        fields = None
    if not isinstance(fields, dict):
        fields = {}

    name_val = fields.get("name")
    if not isinstance(name_val, str) or not name_val.strip():
        errors.append(f"{skill_name}: {_SKILL_MD} frontmatter missing 'name'")
    desc_val = fields.get("description")
    if not isinstance(desc_val, str) or not desc_val.strip():
        errors.append(f"{skill_name}: {_SKILL_MD} frontmatter missing 'description'")
    return errors


def _validate_dependencies(skill_dir: Path, skills_root: Path) -> list[str]:
    """Check that dependency names are valid and their directories exist."""
    errors: list[str] = []
    for dep_name in detect_dependencies(skill_dir):
        if not _SKILL_NAME_RE.match(dep_name):
            errors.append(f"{skill_dir.name}: invalid dependency name '{dep_name}'")
        elif not (skills_root / dep_name).is_dir():
            errors.append(
                f"{skill_dir.name}: dependency directory '{dep_name}' not found under {skills_root}"
            )
    return errors


def _validate_file_refs(text: str, skill_name: str, skills_root: Path) -> list[str]:
    """Check that ``../sibling/file`` references don't escape and exist on disk."""
    errors: list[str] = []
    for m in _FILE_REF_RE.finditer(text):
        sibling, rel_file = m.group(1), m.group(2)
        sibling_dir = skills_root / sibling
        full_path = (sibling_dir / rel_file).resolve()
        if not full_path.is_relative_to(sibling_dir.resolve()):
            errors.append(
                f"{skill_name}: referenced file '../{sibling}/{rel_file}' escapes outside '{sibling}/'"
            )
        elif sibling_dir.is_dir() and not full_path.is_file():
            errors.append(
                f"{skill_name}: referenced file '../{sibling}/{rel_file}' does not exist"
            )
    return errors


def validate_skill(skill_dir: Path, skills_root: Path) -> list[str]:
    """Run all pre-install checks. Return a list of error strings (empty means valid)."""
    skill_md = skill_dir / _SKILL_MD
    if not skill_md.is_file():
        return [f"{skill_dir.name}: missing {_SKILL_MD}"]

    text = skill_md.read_text(encoding="utf-8")
    errors: list[str] = []
    errors.extend(_validate_frontmatter(text, skill_dir.name))
    errors.extend(_validate_dependencies(skill_dir, skills_root))
    errors.extend(_validate_file_refs(text, skill_dir.name, skills_root))
    return errors


def installed_skills(target_dir: Path, skills_root: Path) -> set[str]:
    """Return skill names symlinked in *target_dir* that point back to *skills_root* and contain SKILL.md."""
    if not target_dir.is_dir():
        return set()
    result: set[str] = set()
    resolved_root = skills_root.resolve()
    for entry in target_dir.iterdir():
        if not entry.is_symlink():
            continue
        target = entry.resolve()
        if target.is_relative_to(resolved_root) and (target / _SKILL_MD).is_file():
            result.add(entry.name)
    return result


def _orphaned_dep_candidates(target_dir: Path, skills_root: Path) -> set[str]:
    """Return names of symlinks in *target_dir* that point into *skills_root* but are not skills."""
    resolved_root = skills_root.resolve()
    candidates: set[str] = set()
    for entry in target_dir.iterdir():
        if not entry.is_symlink():
            continue
        target = entry.resolve()
        if target.is_relative_to(resolved_root) and not (target / _SKILL_MD).is_file():
            candidates.add(entry.name)
    return candidates


def _handle_existing_link(link: Path, source: Path, *, force: bool) -> bool:
    """Handle a conflict at *link*. Returns True if *link* was cleared and is ready for creation."""
    if not link.exists() and not link.is_symlink():
        return True

    if not link.is_symlink():
        kind = "directory" if link.is_dir() else "file"
        print(
            f"warning: {link} is an existing {kind}, skipping (will never overwrite non-symlink paths)",
            file=sys.stderr,
        )
        return False

    if link.resolve() == source.resolve():
        return False

    if force:
        link.unlink()
        return True

    print(
        f"warning: {link} is a symlink to {link.resolve()}, skipping (use --force to replace)",
        file=sys.stderr,
    )
    return False


def _create_symlink(
    name: str,
    source: Path,
    target_dir: Path,
    *,
    force: bool = False,
) -> bool:
    """Create a symlink ``target_dir/name -> source``, handling conflicts.

    Returns True if a new symlink was created, False otherwise.
    """
    link = target_dir / name

    if not _handle_existing_link(link, source, force=force):
        return False

    try:
        link.symlink_to(source)
    except OSError as exc:
        print(
            f"error: failed to create symlink {link} -> {source}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    return True


def install_skill(
    skill_name: str,
    target_dir: Path,
    skills_root: Path,
    force: bool = False,
) -> None:
    """Validate, then symlink *skill_name* and its dependencies into *target_dir*."""
    _validate_skill_name(skill_name)
    skill_dir = skills_root / skill_name

    if not skill_dir.is_dir():
        available = _available_skills(skills_root)
        msg = f"error: skill '{skill_name}' not found under {skills_root}"
        if available:
            msg += f"\navailable skills: {', '.join(available)}"
        print(msg, file=sys.stderr)
        raise SystemExit(1)

    errors = validate_skill(skill_dir, skills_root)
    if errors:
        print("validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        raise SystemExit(1)

    target_dir.mkdir(parents=True, exist_ok=True)

    created: list[str] = []

    if _create_symlink(skill_name, skill_dir, target_dir, force=force):
        created.append(skill_name)

    deps = detect_dependencies(skill_dir)
    for dep_name in sorted(deps):
        if _create_symlink(dep_name, skills_root / dep_name, target_dir, force=force):
            created.append(dep_name)

    if created:
        print(f"installed {', '.join(created)} into {target_dir}", file=sys.stderr)
    else:
        print(f"{skill_name} is already installed in {target_dir}", file=sys.stderr)


def uninstall_skill(
    skill_name: str,
    target_dir: Path,
    skills_root: Path,
) -> None:
    """Remove symlinks for *skill_name* and orphaned dependencies from *target_dir*."""
    _validate_skill_name(skill_name)
    if not target_dir.is_dir():
        print(
            f"warning: '{skill_name}' is not installed (target directory does not exist)",
            file=sys.stderr,
        )
        return

    skill_link = target_dir / skill_name
    resolved_root = skills_root.resolve()

    if not skill_link.is_symlink():
        print(
            f"warning: '{skill_name}' is not installed in {target_dir}", file=sys.stderr
        )
        return

    if not skill_link.resolve().is_relative_to(resolved_root):
        print(
            f"warning: {skill_link} does not point into {skills_root}, skipping",
            file=sys.stderr,
        )
        return

    skill_dir = skills_root / skill_name
    deps = detect_dependencies(skill_dir) if skill_dir.is_dir() else set()

    skill_link.unlink()
    print(f"removed {skill_name}", file=sys.stderr)

    remaining_skills = installed_skills(target_dir, skills_root)
    needed_deps: set[str] = set()
    for remaining in remaining_skills:
        remaining_dir = skills_root / remaining
        if remaining_dir.is_dir():
            needed_deps |= detect_dependencies(remaining_dir)

    if not deps:
        deps = _orphaned_dep_candidates(target_dir, skills_root)

    for dep_name in sorted(deps):
        dep_link = target_dir / dep_name
        if not dep_link.is_symlink():
            continue
        if dep_name in needed_deps:
            print(f"keeping {dep_name} (still needed by other skills)", file=sys.stderr)
            continue
        if not dep_link.resolve().is_relative_to(resolved_root):
            print(
                f"warning: {dep_link} does not point into {skills_root}, skipping",
                file=sys.stderr,
            )
            continue
        dep_link.unlink()
        print(f"removed {dep_name}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install or uninstall Cursor skills via symlinks.",
    )
    parser.add_argument(
        "--skill", required=True, help="Name of the skill to install/uninstall"
    )

    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--personal",
        action="store_true",
        help="Install to ~/.cursor/skills/ (all projects)",
    )
    target_group.add_argument(
        "--project", type=str, metavar="PATH", help="Install to <PATH>/.cursor/skills/"
    )

    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the skill instead of installing it",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace conflicting symlinks (never real directories)",
    )

    args = parser.parse_args()

    skills_root = _skills_root()

    if args.personal:
        target_dir = Path.home() / ".cursor" / "skills"
    else:
        target_dir = Path(args.project) / ".cursor" / "skills"

    if args.uninstall:
        uninstall_skill(args.skill, target_dir, skills_root)
    else:
        install_skill(args.skill, target_dir, skills_root, force=args.force)


if __name__ == "__main__":
    main()
