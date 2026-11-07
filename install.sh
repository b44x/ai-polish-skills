#!/usr/bin/env bash
# Thin bootstrap: all catalogue and installation behavior lives in scripts/cli.py.
# Works from a checkout and via: curl -fsSL <install.sh URL> | bash -s -- [args]
set -euo pipefail

fail() { printf 'Error: %s\n' "$1" >&2; exit "$2"; }
command -v python3 >/dev/null 2>&1 || fail 'Python 3.8+ is required.' 69
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || fail 'Python 3.8+ is required.' 69

# Preserve the original shorthand: no command means install (all or named skills).
case "${1:-}" in
  list|ls|search|find|info|show|install|update|validate|test|--help|-h) ;;
  *) set -- install "$@" ;;
esac

# A piped script has no BASH_SOURCE; never guess that cwd is its source.
SCRIPT_DIR=""
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
  SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
fi
if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/scripts/cli.py" && -d "$SCRIPT_DIR/skills" ]]; then
  exec python3 "$SCRIPT_DIR/scripts/cli.py" "$@"
fi

command -v curl >/dev/null 2>&1 || fail 'curl is required for remote installation.' 69
TEMP_DIR="$(mktemp -d)" || fail 'Cannot create a temporary directory.' 73
trap 'rm -rf -- "$TEMP_DIR"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
TARBALL_URL='https://github.com/b44x/ai-polish-skills/archive/refs/heads/main.tar.gz'
curl --fail --silent --show-error --location --connect-timeout 15 --max-time 180 \
  --retry 2 --output "$TEMP_DIR/source.tar.gz" "$TARBALL_URL" || fail 'Could not download the skill catalogue.' 69

# Validate archive paths/types before extraction (also works on Python 3.8).
python3 - "$TEMP_DIR" <<'PY'
import pathlib
import sys
import tarfile

root = pathlib.Path(sys.argv[1])
try:
    with tarfile.open(str(root / "source.tar.gz"), "r:gz") as archive:
        members = archive.getmembers()
        if not members or len(members) > 10000 or sum(m.size for m in members) > 512 * 1024 * 1024:
            raise ValueError("Invalid archive size")
        for member in members:
            path = pathlib.PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "ai-polish-skills-main":
                raise ValueError("Invalid archive path")
            if not (member.isfile() or member.isdir()):
                raise ValueError("Archive links and special files are not supported")
        archive.extractall(str(root), members=members)
    if not (root / "ai-polish-skills-main" / "scripts" / "cli.py").is_file():
        raise ValueError("Missing catalogue CLI")
except (OSError, tarfile.TarError, ValueError) as exc:
    print("Error: Cannot unpack the skill catalogue: " + str(exc), file=sys.stderr)
    sys.exit(69)
PY
# Do not exec: the EXIT trap must clean the downloaded source after the CLI exits.
python3 "$TEMP_DIR/ai-polish-skills-main/scripts/cli.py" "$@"
