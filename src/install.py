"""Skill installer — packs and installs skills via striatum (Cursor or Claude)."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

from utils.subprocess import run as _run

_SKILLS_DIR_NAME = "skills"
_ARTIFACT_JSON = "artifact.json"
_STRIATUM_BUILD_DIR = "build"
_SKILL_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
# Values passed to striatum ``skill install|uninstall --target …``.
STRIATUM_INSTALL_TARGETS = ("cursor", "claude")


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


def _validate_targets(targets: Sequence[str]) -> None:
    """Reject empty lists or values not in ``STRIATUM_INSTALL_TARGETS``."""
    if not targets:
        print("error: at least one --target is required", file=sys.stderr)
        raise SystemExit(1)
    allowed = ", ".join(STRIATUM_INSTALL_TARGETS)
    for target in targets:
        if target not in STRIATUM_INSTALL_TARGETS:
            print(
                f"error: invalid target {target!r}: must be one of {allowed}",
                file=sys.stderr,
            )
            raise SystemExit(1)


def _dedupe_targets(targets: Sequence[str]) -> list[str]:
    """Deduplicate *targets* while preserving order."""
    return list(dict.fromkeys(targets))


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


def _as_json_object(value: object, *, label: str) -> dict[str, object]:
    """Narrow *value* to ``dict[str, object]``, or raise TypeError."""
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a JSON object")
    result: dict[str, object] = {}
    for key, val in value.items():
        if not isinstance(key, str):
            raise TypeError(f"{label} keys must be strings")
        result[key] = val
    return result


def _read_artifact_version(skill_dir: Path) -> str:
    data = _load_artifact(skill_dir)
    try:
        metadata = _as_json_object(data["metadata"], label="metadata")
        return str(metadata["version"])
    except (KeyError, TypeError) as exc:
        print(f"error: invalid artifact.json in {skill_dir}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _read_artifact_name(skill_dir: Path) -> str:
    data = _load_artifact(skill_dir)
    try:
        metadata = _as_json_object(data["metadata"], label="metadata")
        return str(metadata["name"])
    except (KeyError, TypeError) as exc:
        print(f"error: invalid artifact.json in {skill_dir}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _read_artifact_kind(skill_dir: Path) -> str:
    data = _load_artifact(skill_dir)
    try:
        return str(data["kind"])
    except KeyError as exc:
        print(f"error: invalid artifact.json in {skill_dir}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _read_dependencies(skill_dir: Path) -> list[dict[str, str]]:
    """Parse v1alpha2 OCI dependencies from artifact.json.

    Each dependency must have ``source == "oci"``, ``registry``,
    ``repository``, and ``tag``.
    """
    data = _load_artifact(skill_dir)
    raw = data.get("dependencies", [])
    if not isinstance(raw, list):
        print(
            f"error: invalid 'dependencies' in {skill_dir / _ARTIFACT_JSON}: expected a list",
            file=sys.stderr,
        )
        raise SystemExit(1)
    artifact_path = skill_dir / _ARTIFACT_JSON
    result: list[dict[str, str]] = []
    for i, item in enumerate(raw):
        try:
            dep = _as_json_object(item, label=f"dependency [{i}]")
        except TypeError as exc:
            print(
                f"error: dependency [{i}] in {artifact_path} must be an object: {exc}",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        source = dep.get("source")
        if source != "oci":
            print(
                f"error: dependency [{i}] in {artifact_path} "
                f"has unsupported source {source!r}; only 'oci' is supported",
                file=sys.stderr,
            )
            raise SystemExit(1)
        for key in ("registry", "repository", "tag"):
            if key not in dep:
                print(
                    f"error: dependency [{i}] in {artifact_path} "
                    f"is missing required key '{key}'",
                    file=sys.stderr,
                )
                raise SystemExit(1)
        result.append({k: str(v) for k, v in dep.items()})
    return result


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

    def _walk(skill: str) -> None:
        if skill in visited:
            return
        if skill in in_progress:
            print(f"error: dependency cycle detected: {skill}", file=sys.stderr)
            raise SystemExit(1)
        in_progress.add(skill)
        skill_dir = skills_root / skill
        for dep in _read_dependencies(skill_dir):
            dep_name = dep["repository"]
            _validate_skill_name(dep_name)
            dep_dir = skills_root / dep_name
            actual_version = _read_artifact_version(dep_dir)
            declared_version = dep["tag"]
            if actual_version != declared_version:
                print(
                    f"error: {skill} declares dependency {dep_name}:{declared_version} "
                    f"but local artifact has version {actual_version}",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            _walk(dep_name)
        in_progress.discard(skill)
        visited.add(skill)
        ordered.append(skill)

    for root in roots:
        _walk(root)
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

    build_dir = skill_dir / _STRIATUM_BUILD_DIR
    if build_dir.is_symlink() or (build_dir.exists() and not build_dir.is_dir()):
        build_dir.unlink()
    elif build_dir.is_dir():
        shutil.rmtree(build_dir)

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
    install_target: str,
    project: str | None = None,
    force: bool = False,
) -> None:
    skills_only = [
        name for name in names if _read_artifact_kind(skills_root / name) == "Skill"
    ]
    n = len(skills_only)
    installed_ok: list[str] = []
    for i, name in enumerate(skills_only, start=1):
        skill_dir = skills_root / name
        version = _read_artifact_version(skill_dir)
        artifact_name = _read_artifact_name(skill_dir)
        ref = _reference(registry, artifact_name, version)

        cmd = [striatum, "skill", "install", "--target", install_target, ref]
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
    targets: Sequence[str],
    project: str | None = None,
    force: bool = False,
) -> None:
    """Pack, push, and install a skill and all its transitive dependencies.

    Each dependency is installed as its own skill for every *target* (sibling
    directories under the layout striatum uses for that install target).
    Pack+push runs once; striatum install runs per target.
    ``uninstall_skill`` removes only the named skill; see the root README
    *Installing Skills* for uninstall notes.
    """
    _validate_skill_name(skill_name)
    _validate_targets(targets)
    unique_targets = _dedupe_targets(targets)
    skills_root = _skills_root()
    registry = _registry()
    striatum = _find_striatum()

    all_skills = _resolve_all_deps(skill_name, skills_root)

    _pack_push_ordered(all_skills, skills_root, registry, striatum=striatum)
    for t in unique_targets:
        _install_ordered_skills(
            all_skills,
            skills_root,
            registry,
            striatum=striatum,
            install_target=t,
            project=project,
            force=force,
        )


def install_all_skills(
    *,
    targets: Sequence[str],
    project: str | None = None,
    force: bool = False,
) -> None:
    """Pack, push, and install every skill under ``skills/`` (each once, dependency order)."""
    _validate_targets(targets)
    unique_targets = _dedupe_targets(targets)
    skills_root = _skills_root()
    order = _global_install_order(skills_root)
    if not order:
        return

    registry = _registry()
    striatum = _find_striatum()

    _pack_push_ordered(order, skills_root, registry, striatum=striatum)
    for t in unique_targets:
        _install_ordered_skills(
            order,
            skills_root,
            registry,
            striatum=striatum,
            install_target=t,
            project=project,
            force=force,
        )


def uninstall_skill(
    skill_name: str,
    *,
    targets: Sequence[str],
    project: str | None = None,
) -> None:
    """Uninstall one skill via striatum from each *target*.

    Does not remove other skills that were installed as transitive
    dependencies of this skill. Uninstall those separately if needed.
    """
    _validate_skill_name(skill_name)
    _validate_targets(targets)
    unique_targets = _dedupe_targets(targets)
    striatum = _find_striatum()

    for t in unique_targets:
        cmd = [striatum, "skill", "uninstall", "--target", t, skill_name]
        if project:
            cmd.extend(["--project", str(project)])
        _run(cmd)
        print(f"uninstalled {skill_name} from {t}", file=sys.stderr)


def reinstall_all(*, targets: Sequence[str], force: bool = False) -> None:
    """Reinstall all tracked skills via striatum for each *target*."""
    _validate_targets(targets)
    unique_targets = _dedupe_targets(targets)
    striatum = _find_striatum()
    for t in unique_targets:
        cmd = [striatum, "skill", "install", "--reinstall-all", "--target", t]
        if force:
            cmd.append("--force")
        _run(cmd)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Pack, push, and install skills via striatum and an OCI registry "
            "(Cursor or Claude)."
        ),
    )
    parser.add_argument("--skill", help="Name of the skill to install/uninstall")
    parser.add_argument(
        "--target",
        required=True,
        nargs="+",
        choices=STRIATUM_INSTALL_TARGETS,
        help="Striatum install target(s) (passed through to striatum --target)",
    )

    target_group = parser.add_mutually_exclusive_group(required=False)
    target_group.add_argument(
        "--personal",
        action="store_true",
        help=(
            "Install to personal skills dir for the chosen --target "
            "(e.g. ~/.cursor/skills/ or Claude equivalent; all projects)"
        ),
    )
    target_group.add_argument(
        "--project",
        type=str,
        metavar="PATH",
        help=(
            "Install to project-local skills dir for the chosen --target "
            "(e.g. <PATH>/.cursor/skills/ or Claude equivalent)"
        ),
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
        reinstall_all(targets=args.target, force=args.force)
        return

    project_path = (
        str(Path(args.project).expanduser().resolve(strict=False))
        if args.project
        else None
    )

    if args.install_all:
        install_all_skills(targets=args.target, project=project_path, force=args.force)
        return

    if args.uninstall:
        uninstall_skill(
            args.skill,
            targets=args.target,
            project=project_path,
        )
    else:
        install_skill(
            args.skill,
            targets=args.target,
            project=project_path,
            force=args.force,
        )


if __name__ == "__main__":
    main()
