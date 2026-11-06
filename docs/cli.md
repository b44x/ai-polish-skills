# Installer and management CLI contract

`install.sh` is a Bash bootstrap for `scripts/cli.py`. Installation logic lives only in `scripts/installer.py`. Both entry points use Python 3.8+ and the standard library; no pip packages are required.

## Language and output

- Management command names, flags, help, diagnostics and JSON keys use English.
- Skill names are stable identifiers. Polish descriptions, search terms, source quotations and domain data retain their original language.
- Individual skills keep their documented language and JSON contracts; this refactor does not change their public commands.
- `list`, `search`, `info`, `install` and `update` support `--json`: one JSON value on stdout, no banner or ANSI escapes. Empty searches return `[]` and exit 0.
- Human-readable management output uses colors only on a terminal, unless `NO_COLOR` is set. Errors go to stderr.
- `validate` and `test` delegate to the existing development tools, which retain their own reporting and exit statuses.

## Commands and compatibility

```bash
./install.sh                         # install all available skills
./install.sh nbp krs                 # legacy shorthand
./install.sh install nbp krs         # explicit equivalent
./install.sh list --json
./install.sh search paczkomat --json
./install.sh info nbp --json
./install.sh install nbp --agents --dry-run --json
./install.sh update --dir './custom skills' --json
```

Direct Python calls require a subcommand: `python3 scripts/cli.py install nbp`.
Aliases `ls`, `find`, `show` and `--antigravity` / `-a` remain supported.

Exactly one destination selector may be provided:

| Selector | Destination |
|---|---|
| None | `.claude/skills` if `.claude` exists in the current working directory; otherwise `.agents/skills` |
| `--agents`, `--antigravity`, `-a` | `.agents/skills` |
| `--claude`, `-c` | `.claude/skills` |
| `--dir`, `-d` | Explicit path, with `~` expansion |
| `--global`, `-g` | Legacy target `~/.gemini/config/skills` |

Paths are relative to the caller's working directory, not the checkout. `--global` is a legacy destination selector, not a universal global install mode for every agent. Conflicting selectors and missing option arguments fail with exit 64. Unknown skill names fail with exit 2 before any skill is installed.

## Sources and updates

Running the wrapper from a checkout uses that checkout, including uncommitted changes. Running the published script through `curl | bash` downloads `main` to a temporary directory and uses the same Python CLI. Remote use requires curl and network access, including remote discovery and help. Temporary downloads are removed on normal exit, failures and handled interrupts.

`update` copies only skills that both exist in the selected destination and are known to the source catalogue. Unrelated directories are left untouched. It never pulls Git changes. To update from a newer checkout, update the checkout first; to update from published `main`:

```bash
curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s -- update --agents
```

`--dry-run` validates the selection and reports intended changes without creating destination directories, locks or copies. A remote dry run still downloads the catalogue temporarily.

## Replacing installed files

Installation replaces the entire selected skill directory, including local modifications. All selected copies are staged before replacing any existing skill. Each failed replacement attempts to restore that skill's previous directory. If restoration also fails, the backup is retained and its path is reported. Earlier successful replacements remain installed: this is not a transaction across the entire batch and does not guarantee recovery from power loss or `SIGKILL`.

Source/destination overlaps and symbolic links in skill sources or at individual skill destinations are rejected. Bytecode caches and `.DS_Store` are excluded. Python scripts receive executable permissions. A destination lock prevents simultaneous installer processes; if a process is killed, remove `.ai-polish-skills.lock` only after confirming no installation is running.

## Management exit codes

| Code | Meaning |
|---|---|
| 0 | Success, including help, dry run and empty search/update selection |
| 2 | Unknown skill or missing update destination |
| 64 | Invalid arguments or unsafe source/destination selection |
| 69 | Missing bootstrap dependency, failed download or invalid archive |
| 73 | Filesystem failure or busy installation destination |

Python management errors are JSON on stderr. Bootstrap errors are readable English on stderr. The skill execution contract remains 0 / 2 / 64 / 69 as documented in `AGENTS.md`.

## Verification

Run `python3 -m unittest discover -s scripts -p test_installer.py` for installer regression tests, including a piped bootstrap against an offline archive. These tests are also discovered by `python3 scripts/test_skills.py`.
