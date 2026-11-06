"""Shared local installer. Python 3.8+, no external dependencies."""

import os
import shutil
import tempfile
from pathlib import Path


class InstallError(Exception):
    def __init__(self, message, code=64):
        super().__init__(message)
        self.code = code


def target_directory(args):
    if args.dir is not None:
        if not args.dir.strip():
            raise InstallError("Destination directory must not be empty.")
        return Path(args.dir).expanduser().absolute()
    if args.global_install:
        # Preserve the historical --global target.
        return Path.home() / ".gemini" / "config" / "skills"
    if args.claude or (not args.agents and (Path.cwd() / ".claude").is_dir()):
        return Path.cwd() / ".claude" / "skills"
    return Path.cwd() / ".agents" / "skills"


def overlaps(left, right):
    return left == right or left in right.parents or right in left.parents


def install(skills, names, target, dry_run=False, update=False):
    """Validate the entire selection, stage copies, then replace each directory.

    A failed replacement restores that skill's previous directory. Earlier
    successful replacements remain installed; this is not a batch transaction.
    """
    target = Path(target)
    if update:
        if not target.is_dir():
            raise InstallError("Target directory does not exist; run install first.", 2)
        names = sorted(name for name in skills if (target / name).is_dir())
    else:
        names = list(dict.fromkeys(names or sorted(skills)))
    missing = [name for name in names if name not in skills]
    if missing:
        raise InstallError("Unknown skill(s): " + ", ".join(missing), 2)

    # Reject source overlaps before mkdir/copy and symlinked install destinations.
    sources = [Path(data["_dir"]).resolve() for data in skills.values()]
    for name in names:
        dest = target / name
        if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
            raise InstallError("Destination must be a regular directory: " + str(dest))
        if any(overlaps(dest.resolve(), src) for src in sources):
            raise InstallError("Installation destination overlaps source skills: " + str(dest))
        source = Path(skills[name]["_dir"])
        if any(path.is_symlink() for path in source.rglob("*")):
            raise InstallError("Skill source contains a symbolic link: " + name)

    result = {"target": str(target), "dry_run": dry_run, "skills": names,
              "operation": "update" if update else "install"}
    if dry_run or not names:
        return result

    target.mkdir(parents=True, exist_ok=True)
    # Stage on the same filesystem so each rename is atomic. A lock prevents
    # two installer processes from replacing the same destination concurrently.
    lock = target / ".ai-polish-skills.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        raise InstallError("Another installation may be running. If it stopped, remove " + str(lock), 73)
    work = None
    preserve_work = False
    try:
        work = Path(tempfile.mkdtemp(prefix=".ai-polish-skills-", dir=str(target)))
        for name in names:
            staged = work / name
            shutil.copytree(skills[name]["_dir"], staged,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
            for script in (staged / "scripts").glob("*.py"):
                script.chmod(script.stat().st_mode | 0o111)
        for name in names:
            dest, staged, backup = target / name, work / name, work / (name + ".backup")
            existed = dest.exists()
            if existed:
                os.replace(str(dest), str(backup))
            try:
                os.replace(str(staged), str(dest))
            except OSError:
                if existed:
                    # If restoration also fails, retain the staging directory
                    # and its backup for manual recovery.
                    try:
                        os.replace(str(backup), str(dest))
                    except OSError:
                        preserve_work = True
                        raise InstallError("Replacement failed. Previous files saved at " + str(backup), 73)
                raise
    finally:
        if work is not None and not preserve_work:
            shutil.rmtree(work)
        lock.rmdir()
    return result
