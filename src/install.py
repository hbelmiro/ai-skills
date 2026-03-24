"""Skill installer for Cursor — packs and installs skills via striatum."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_SKILLS_DIR_NAME = "skills"
_ARTIFACT_JSON = "artifact.json"
_STRIATUM_LAYOUT_DIR = ".striatum"
_SKILL_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def _find_striatum() -> str:
    """Return the path to the striatum binary, or exit if not found."""
    path = shutil.which("striatum")
    if path is None:
        print("error: striatum not found on PATH", file=sys.stderr)
        raise SystemExit(1)
    return path


def _registry() -> str:
    """Return the OCI registry base from STRIATUM_REGISTRY, or exit if unset."""
    reg = os.environ.get("STRIATUM_REGISTRY", "").strip()
    if not reg:
        print(
            "error: STRIATUM_REGISTRY environment variable is required "
            "(e.g. localhost:5050/skills)",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return reg.rstrip("/")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _skills_root() -> Path:
    return _repo_root() / _SKILLS_DIR_NAME


def _validate_skill_name(name: str) -> None:
    """Reject names containing path separators or not matching the naming convention."""
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


def _run(
    args: list[str], *, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a command, printing stderr on failure."""
    result = subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=120)
    if result.returncode != 0:
        msg = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"exit code {result.returncode}"
        )
        print(f"error: {args[0]}: {msg}", file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def _reference(registry: str, name: str, version: str) -> str:
    return f"{registry}/{name}:{version}"


def _load_artifact(skill_dir: Path) -> dict[str, object]:
    """Load and return the parsed artifact.json from *skill_dir*, or exit on error."""
    artifact_path = skill_dir / _ARTIFACT_JSON
    if not artifact_path.is_file():
        print(f"error: {artifact_path} not found", file=sys.stderr)
        raise SystemExit(1)
    with artifact_path.open(encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as exc:
            print(f"error: invalid JSON in {artifact_path}: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc


def _read_artifact_version(skill_dir: Path) -> str:
    data = _load_artifact(skill_dir)
    try:
        return str(data["metadata"]["version"])  # type: ignore[index]
    except (KeyError, TypeError) as exc:
        print(f"error: invalid artifact.json in {skill_dir}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _read_artifact_name(skill_dir: Path) -> str:
    data = _load_artifact(skill_dir)
    try:
        return str(data["metadata"]["name"])  # type: ignore[index]
    except (KeyError, TypeError) as exc:
        print(f"error: invalid artifact.json in {skill_dir}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _read_dependencies(skill_dir: Path) -> list[dict[str, str]]:
    data = _load_artifact(skill_dir)
    raw = data.get("dependencies", [])
    if not isinstance(raw, list):
        print(
            f"error: invalid 'dependencies' in {skill_dir / _ARTIFACT_JSON}: expected a list",
            file=sys.stderr,
        )
        raise SystemExit(1)
    for i, dep in enumerate(raw):
        if not isinstance(dep, dict) or "name" not in dep or "version" not in dep:
            print(
                f"error: dependency [{i}] in {skill_dir / _ARTIFACT_JSON} "
                "must be an object with 'name' and 'version' keys",
                file=sys.stderr,
            )
            raise SystemExit(1)
    return raw  # type: ignore[return-value]


def _available_skills(skills_root: Path) -> list[str]:
    if not skills_root.is_dir():
        return []
    return sorted(
        d.name
        for d in skills_root.iterdir()
        if d.is_dir() and (d / _ARTIFACT_JSON).is_file()
    )


def _ordered_skills_postorder(roots: list[str], skills_root: Path) -> list[str]:
    """Dependency order for *roots*: each skill once, dependencies before dependents."""
    ordered: list[str] = []
    visited: set[str] = set()
    in_progress: set[str] = set()

    def _walk(name: str) -> None:
        if name in visited:
            return
        if name in in_progress:
            print(f"error: dependency cycle detected: {name}", file=sys.stderr)
            raise SystemExit(1)
        in_progress.add(name)
        skill_dir = skills_root / name
        for dep in _read_dependencies(skill_dir):
            dep_name = dep["name"]
            _validate_skill_name(dep_name)
            dep_dir = skills_root / dep_name
            actual_version = _read_artifact_version(dep_dir)
            declared_version = dep["version"]
            if actual_version != declared_version:
                print(
                    f"error: {name} declares dependency {dep_name}:{declared_version} "
                    f"but local artifact has version {actual_version}",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            _walk(dep_name)
        in_progress.discard(name)
        visited.add(name)
        ordered.append(name)

    for name in roots:
        _walk(name)
    return ordered


def _resolve_all_deps(skill_name: str, skills_root: Path) -> list[str]:
    """Topologically resolve transitive dependencies (leaves first)."""
    return _ordered_skills_postorder([skill_name], skills_root)


def _global_install_order(skills_root: Path) -> list[str]:
    """Topological order of every skill under *skills_root* (dependencies before dependents)."""
    return _ordered_skills_postorder(_available_skills(skills_root), skills_root)


def pack_and_push(
    skill_name: str, skills_root: Path, registry: str, *, striatum: str
) -> None:
    """Pack a skill and push it to the registry."""
    _validate_skill_name(skill_name)
    skill_dir = skills_root / skill_name
    if not skill_dir.is_dir():
        available = _available_skills(skills_root)
        msg = f"error: skill '{skill_name}' not found under {skills_root}"
        if available:
            msg += f"\navailable skills: {', '.join(available)}"
        print(msg, file=sys.stderr)
        raise SystemExit(1)

    version = _read_artifact_version(skill_dir)
    name = _read_artifact_name(skill_dir)
    if name != skill_name:
        print(
            f"error: metadata.name '{name}' in {skill_dir / _ARTIFACT_JSON} "
            f"does not match directory name '{skill_name}'",
            file=sys.stderr,
        )
        raise SystemExit(1)
    ref = _reference(registry, name, version)

    layout_dir = skill_dir / _STRIATUM_LAYOUT_DIR
    if layout_dir.is_symlink() or (layout_dir.exists() and not layout_dir.is_dir()):
        layout_dir.unlink()
    elif layout_dir.is_dir():
        shutil.rmtree(layout_dir)

    _run([striatum, "validate"], cwd=skill_dir)
    _run([striatum, "pack"], cwd=skill_dir)
    _run([striatum, "push", ref], cwd=skill_dir)
    print(f"packed and pushed {ref}", file=sys.stderr)


def _pack_push_ordered(
    names: list[str],
    skills_root: Path,
    registry: str,
    *,
    striatum: str,
) -> None:
    for name in names:
        pack_and_push(name, skills_root, registry, striatum=striatum)


def _install_ordered_skills(
    names: list[str],
    skills_root: Path,
    registry: str,
    *,
    striatum: str,
    project: str | None = None,
    force: bool = False,
) -> None:
    n = len(names)
    installed_ok: list[str] = []
    for i, name in enumerate(names, start=1):
        skill_dir = skills_root / name
        version = _read_artifact_version(skill_dir)
        artifact_name = _read_artifact_name(skill_dir)
        ref = _reference(registry, artifact_name, version)

        cmd = [striatum, "skill", "install", "--target", "cursor", ref]
        if project:
            cmd.extend(["--project", str(project)])
        if force:
            cmd.append("--force")

        print(f"installing {name} ({i}/{n})", file=sys.stderr)
        try:
            _run(cmd)
        except SystemExit:
            if installed_ok:
                print(
                    "error: successful installs before failure: "
                    + ", ".join(installed_ok),
                    file=sys.stderr,
                )
            raise
        installed_ok.append(name)
        print(f"installed {name}", file=sys.stderr)


def install_skill(
    skill_name: str,
    *,
    project: str | None = None,
    force: bool = False,
) -> None:
    """Pack, push, and install a skill and all its transitive dependencies.

    Each dependency is installed as its own Cursor skill (sibling directories
    under ``.cursor/skills/``). ``uninstall_skill`` removes only the named
    skill; see the root README *Installing Skills* for uninstall notes.
    """
    _validate_skill_name(skill_name)
    skills_root = _skills_root()
    registry = _registry()
    striatum = _find_striatum()

    all_skills = _resolve_all_deps(skill_name, skills_root)

    _pack_push_ordered(all_skills, skills_root, registry, striatum=striatum)
    _install_ordered_skills(
        all_skills,
        skills_root,
        registry,
        striatum=striatum,
        project=project,
        force=force,
    )


def install_all_skills(
    *,
    project: str | None = None,
    force: bool = False,
) -> None:
    """Pack, push, and install every skill under ``skills/`` (each once, dependency order)."""
    skills_root = _skills_root()
    order = _global_install_order(skills_root)
    if not order:
        return

    registry = _registry()
    striatum = _find_striatum()

    _pack_push_ordered(order, skills_root, registry, striatum=striatum)
    _install_ordered_skills(
        order,
        skills_root,
        registry,
        striatum=striatum,
        project=project,
        force=force,
    )


def uninstall_skill(
    skill_name: str,
    *,
    project: str | None = None,
) -> None:
    """Uninstall one skill via striatum.

    Does not remove other skills that were installed as transitive
    dependencies of this skill. Uninstall those separately if needed.
    """
    _validate_skill_name(skill_name)
    striatum = _find_striatum()

    cmd = [striatum, "skill", "uninstall", "--target", "cursor", skill_name]
    if project:
        cmd.extend(["--project", str(project)])

    _run(cmd)
    print(f"uninstalled {skill_name}", file=sys.stderr)


def reinstall_all(*, force: bool = False) -> None:
    """Reinstall all tracked skills via striatum."""
    striatum = _find_striatum()
    cmd = [striatum, "skill", "install", "--reinstall-all", "--target", "cursor"]
    if force:
        cmd.append("--force")
    _run(cmd)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pack, push, and install Cursor skills via striatum and an OCI registry.",
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
        help="Overwrite conflicting versions",
    )
    parser.add_argument(
        "--reinstall-all",
        action="store_true",
        help="Reinstall all tracked skills from striatum install DB",
    )
    parser.add_argument(
        "--install-all",
        action="store_true",
        help="Pack, push, and install every skill in this repository's skills/ directory",
    )
    return parser


def _validate_cli_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    if args.reinstall_all and (
        args.skill
        or args.personal
        or args.project
        or args.uninstall
        or args.install_all
    ):
        parser.error(
            "--reinstall-all cannot be combined with --skill/--personal/--project/"
            "--uninstall/--install-all"
        )
    if args.reinstall_all:
        return

    if args.install_all and (args.skill or args.uninstall):
        parser.error("--install-all cannot be combined with --skill or --uninstall")
    if args.install_all:
        if args.personal == bool(args.project):
            parser.error(
                "exactly one of --personal or --project is required with --install-all"
            )
        return

    if not args.skill:
        parser.error(
            "--skill is required unless --reinstall-all or --install-all is used"
        )
    if args.personal == bool(args.project):
        parser.error(
            "exactly one of --personal or --project is required unless "
            "--reinstall-all is used"
        )


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    _validate_cli_args(args, parser)

    if args.reinstall_all:
        reinstall_all(force=args.force)
        return

    project_path = (
        str(Path(args.project).expanduser().resolve(strict=False))
        if args.project
        else None
    )

    if args.install_all:
        install_all_skills(project=project_path, force=args.force)
        return

    if args.uninstall:
        uninstall_skill(
            args.skill,
            project=project_path,
        )
    else:
        install_skill(
            args.skill,
            project=project_path,
            force=args.force,
        )


if __name__ == "__main__":
    main()
