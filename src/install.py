"""Skill installer for Cursor — symlinks skills into personal or project targets."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

_SIBLING_REF_RE = re.compile(r"`\.\./([^/`\s]+)/")
_FILE_REF_RE = re.compile(r"`\.\./([^/`\s]+)/([^`\s]+)")
_FRONTMATTER_RE = re.compile(r"^\s*---\s*\r?\n(.*?)\r?\n---", re.DOTALL)

_SKILLS_DIR_NAME = "skills"
_SKILL_MD = "SKILL.md"
_SKILL_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
_CURSOR_DIR_NAME = ".cursor"
_DB_DIR = ".ai-skills"
_DB_FILE = "installed-skills.yaml"


@dataclass
class ReinstallReport:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    failures: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path(db_path: Path | None = None) -> Path:
    return db_path if db_path is not None else Path.home() / _DB_DIR / _DB_FILE


def _normalize_project_path(project: str | Path) -> str:
    return str(Path(project).expanduser().resolve(strict=False))


def _entry_key(entry: dict[str, Any]) -> tuple[str, str, str | None]:
    skill = str(entry.get("skill", ""))
    target = str(entry.get("target", ""))
    project_path = entry.get("project_path")
    if isinstance(project_path, str):
        project_path = _normalize_project_path(project_path)
    else:
        project_path = None
    return skill, target, project_path


def load_installed_db(
    *, db_path: Path | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Load installed-skills DB, always returning {'entries': [...]}."""
    path = _db_path(db_path)
    if not path.exists():
        return {"entries": []}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"error: failed to read DB file {path}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except yaml.YAMLError as exc:
        print(f"error: invalid YAML in DB file {path}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if data is None:
        return {"entries": []}
    if not isinstance(data, dict):
        print(
            f"error: invalid DB schema in {path}: expected a mapping with 'entries'",
            file=sys.stderr,
        )
        raise SystemExit(1)

    raw_entries = data.get("entries", [])
    if not isinstance(raw_entries, list):
        print(
            f"error: invalid DB schema in {path}: 'entries' must be a list",
            file=sys.stderr,
        )
        raise SystemExit(1)

    entries: list[dict[str, Any]] = []
    for item in raw_entries:
        if not isinstance(item, dict):
            entries.append(
                {
                    "status": "error",
                    "last_error": "invalid entry type: expected mapping",
                    "updated_at": _now_iso(),
                }
            )
            continue
        entry = dict(item)
        entry["status"] = entry.get("status", "ok")
        entry["updated_at"] = entry.get("updated_at", _now_iso())
        if "last_error" not in entry:
            entry["last_error"] = None
        if entry.get("target") == "project" and isinstance(
            entry.get("project_path"), str
        ):
            entry["project_path"] = _normalize_project_path(entry["project_path"])
        entries.append(entry)
    return {"entries": entries}


def save_installed_db(
    data: dict[str, list[dict[str, Any]]], *, db_path: Path | None = None
) -> None:
    """Persist installed-skills DB to ~/.ai-skills/installed-skills.yaml."""
    path = _db_path(db_path)
    payload = yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
    tmp_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_name = f".{path.name}.tmp-{os.getpid()}-{_now_iso().replace(':', '-')}"
        tmp_path = path.parent / tmp_name
        with tmp_path.open("w", encoding="utf-8") as tmp_file:
            tmp_file.write(payload)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, path)
        _fsync_dir_best_effort(path.parent)
    except OSError as exc:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        print(f"error: failed to write DB file {path}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _fsync_dir_best_effort(directory: Path) -> None:
    """Best-effort directory fsync for rename durability."""
    # Not all platforms/filesystems support directory fsync; ignore unsupported cases.
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        return
    finally:
        os.close(fd)


def track_installed_entry(
    skill_name: str,
    *,
    personal: bool = False,
    project: Path | str | None = None,
    db_path: Path | None = None,
) -> None:
    """Upsert a successful install record into the DB."""
    target = "personal" if personal else "project"
    if target == "project" and project is None:
        print(
            "error: project path is required when tracking a project install",
            file=sys.stderr,
        )
        raise SystemExit(1)

    data = load_installed_db(db_path=db_path)
    entries = data["entries"]
    project_path = _normalize_project_path(project) if project is not None else None
    key = (skill_name, target, project_path)

    updated = False
    for entry in entries:
        if _entry_key(entry) == key:
            entry["status"] = "ok"
            entry["last_error"] = None
            entry["updated_at"] = _now_iso()
            if target == "project":
                entry["project_path"] = project_path
            else:
                entry.pop("project_path", None)
            updated = True
            break
    if not updated:
        new_entry: dict[str, Any] = {
            "skill": skill_name,
            "target": target,
            "status": "ok",
            "last_error": None,
            "updated_at": _now_iso(),
        }
        if target == "project":
            new_entry["project_path"] = project_path
        entries.append(new_entry)
    save_installed_db(data, db_path=db_path)


def remove_installed_entry(
    skill_name: str,
    *,
    personal: bool = False,
    project: Path | str | None = None,
    db_path: Path | None = None,
) -> bool:
    """Remove install record matching skill+target key. Returns True if removed."""
    target = "personal" if personal else "project"
    if target == "project" and project is None:
        print(
            "error: project path is required when removing a project install",
            file=sys.stderr,
        )
        raise SystemExit(1)
    project_path = _normalize_project_path(project) if project is not None else None
    key = (skill_name, target, project_path)

    data = load_installed_db(db_path=db_path)
    entries = data["entries"]
    kept: list[dict[str, Any]] = []
    removed = False
    for entry in entries:
        if _entry_key(entry) == key:
            removed = True
            continue
        kept.append(entry)
    if removed:
        data["entries"] = kept
        save_installed_db(data, db_path=db_path)
    return removed


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


def _target_skills_dir(base_dir: Path) -> Path:
    return base_dir / _CURSOR_DIR_NAME / _SKILLS_DIR_NAME


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
        errors.append(f"{skill_name}: {_SKILL_MD} has invalid YAML frontmatter")
        return errors
    if not isinstance(fields, dict):
        errors.append(f"{skill_name}: {_SKILL_MD} has invalid YAML frontmatter")
        return errors

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
        link.symlink_to(source, target_is_directory=source.is_dir())
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

    skill_link = target_dir / skill_name
    if _create_symlink(skill_name, skill_dir, target_dir, force=force):
        created.append(skill_name)
    elif not (skill_link.is_symlink() and skill_link.resolve() == skill_dir.resolve()):
        return

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
) -> bool:
    """Remove symlinks for *skill_name* and orphaned dependencies from *target_dir*."""
    _validate_skill_name(skill_name)
    if not target_dir.is_dir():
        print(
            f"warning: '{skill_name}' is not installed (target directory does not exist)",
            file=sys.stderr,
        )
        return False

    skill_link = target_dir / skill_name
    resolved_root = skills_root.resolve()

    if not skill_link.is_symlink():
        print(
            f"warning: '{skill_name}' is not installed in {target_dir}", file=sys.stderr
        )
        return False

    if not skill_link.resolve().is_relative_to(resolved_root):
        print(
            f"warning: {skill_link} does not point into {skills_root}, skipping",
            file=sys.stderr,
        )
        return False

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
    return True


def _is_installed_skill_link(
    skill_name: str, target_dir: Path, skills_root: Path
) -> bool:
    link = target_dir / skill_name
    source = skills_root / skill_name
    return link.is_symlink() and link.resolve() == source.resolve()


def _mark_entry_error(entry: dict[str, Any], message: str) -> None:
    entry["status"] = "error"
    entry["last_error"] = message
    entry["updated_at"] = _now_iso()


def _mark_entry_ok(entry: dict[str, Any]) -> None:
    entry["status"] = "ok"
    entry["last_error"] = None
    entry["updated_at"] = _now_iso()


def _record_failure(report: ReinstallReport, detail: str) -> None:
    report.failed += 1
    report.failures.append(detail)


def _record_entry_failure(
    report: ReinstallReport, entry: dict[str, Any], skill_name: str, message: str
) -> None:
    _mark_entry_error(entry, message)
    _record_failure(report, f"{skill_name}: {message}")


def _extract_skill_name(entry: dict[str, Any]) -> tuple[str | None, str | None]:
    skill_name = entry.get("skill")
    if not isinstance(skill_name, str) or not skill_name:
        return None, "missing required 'skill'"
    return skill_name, None


def _resolve_reinstall_target(entry: dict[str, Any]) -> tuple[Path | None, str | None]:
    target = entry.get("target")
    if target == "personal":
        return _target_skills_dir(Path.home()), None
    if target == "project":
        project_path = entry.get("project_path")
        if not isinstance(project_path, str) or not project_path:
            return None, "missing required 'project_path' for project target"
        normalized = _normalize_project_path(project_path)
        entry["project_path"] = normalized
        return _target_skills_dir(Path(normalized)), None
    return None, f"unknown target '{target}'"


def _run_reinstall_for_entry(
    skill_name: str, target_dir: Path, skills_root: Path, *, force: bool
) -> str | None:
    try:
        install_skill(skill_name, target_dir, skills_root, force=force)
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, str) and code.strip():
            return f"install failed: {code.strip()}"
        if code not in (None, 0):
            return f"install failed (exit code: {code})"
        return "install failed"

    if not _is_installed_skill_link(skill_name, target_dir, skills_root):
        return "install incomplete (conflict or skipped)"
    return None


def _print_reinstall_report(report: ReinstallReport) -> None:
    print("reinstall-all report", file=sys.stderr)
    print(f"  total: {report.total}", file=sys.stderr)
    print(f"  succeeded: {report.succeeded}", file=sys.stderr)
    print(f"  failed: {report.failed}", file=sys.stderr)
    for item in report.failures:
        print(f"  - {item}", file=sys.stderr)


def reinstall_all(
    *, skills_root: Path, force: bool = False, db_path: Path | None = None
) -> ReinstallReport:
    """Reinstall all tracked entries from DB, continuing on errors."""
    data = load_installed_db(db_path=db_path)
    entries = data["entries"]
    report = ReinstallReport(total=len(entries))

    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            _record_failure(report, f"entry[{idx}]: invalid entry type")
            continue

        skill_name, skill_error = _extract_skill_name(entry)
        if skill_error or skill_name is None:
            message = skill_error or "missing required 'skill'"
            _mark_entry_error(entry, message)
            _record_failure(report, f"entry[{idx}]: {message}")
            continue

        target_dir, target_error = _resolve_reinstall_target(entry)
        if target_error or target_dir is None:
            message = target_error or "invalid target"
            _record_entry_failure(report, entry, skill_name, message)
            continue

        install_error = _run_reinstall_for_entry(
            skill_name, target_dir, skills_root, force=force
        )
        if install_error:
            _record_entry_failure(report, entry, skill_name, install_error)
            continue

        _mark_entry_ok(entry)
        report.succeeded += 1

    save_installed_db(data, db_path=db_path)
    _print_reinstall_report(report)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install, uninstall, or reinstall tracked Cursor skills via symlinks.",
    )
    parser.add_argument("--skill", help="Name of the skill to install/uninstall")

    target_group = parser.add_mutually_exclusive_group(required=False)
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
    parser.add_argument(
        "--reinstall-all",
        action="store_true",
        help="Reinstall all tracked skills from ~/.ai-skills/installed-skills.yaml",
    )
    return parser


def _validate_cli_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    if args.reinstall_all and (
        args.skill or args.personal or args.project or args.uninstall
    ):
        parser.error(
            "--reinstall-all cannot be combined with --skill/--personal/--project/--uninstall"
        )
    if args.reinstall_all:
        return
    if not args.skill:
        parser.error("--skill is required unless --reinstall-all is used")
    if args.personal == bool(args.project):
        parser.error(
            "exactly one of --personal or --project is required unless --reinstall-all is used"
        )


def _resolve_cli_target(args: argparse.Namespace) -> tuple[Path, bool, Path | None]:
    if args.personal:
        return _target_skills_dir(Path.home()), True, None
    project_path = Path(args.project).expanduser().resolve(strict=False)
    return _target_skills_dir(project_path), False, project_path


def _process_single_skill_command(args: argparse.Namespace, skills_root: Path) -> None:
    target_dir, personal, project_path = _resolve_cli_target(args)

    if args.uninstall:
        removed = uninstall_skill(args.skill, target_dir, skills_root)
        if removed:
            remove_installed_entry(
                args.skill,
                personal=personal,
                project=project_path if not personal else None,
            )
    else:
        install_skill(args.skill, target_dir, skills_root, force=args.force)
        if _is_installed_skill_link(args.skill, target_dir, skills_root):
            track_installed_entry(
                args.skill,
                personal=personal,
                project=project_path if not personal else None,
            )


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    _validate_cli_args(args, parser)

    skills_root = _skills_root()
    if args.reinstall_all:
        reinstall_all(skills_root=skills_root, force=args.force)
        return

    _process_single_skill_command(args, skills_root)


if __name__ == "__main__":
    main()
