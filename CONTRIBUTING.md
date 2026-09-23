# Contributing

This repo stores **AI agent skills** (`SKILL.md` format). Each skill is a separate
directory containing a `SKILL.md` file and optional resources.

## Layout

```
ai-skills/
├── skills/
│   ├── _template/            # template — copy it to start a new skill
│   │   ├── SKILL.md
│   │   ├── references/       # extra docs loaded on demand
│   │   └── scripts/          # scripts executed by the model
│   └── <skill-name>/         # one directory = one skill
├── scripts/
│   └── validate_skills.py    # frontmatter and structure validation
├── .github/
│   ├── workflows/            # CI: validation on every PR
│   ├── ISSUE_TEMPLATE/       # new skill proposal
│   └── pull_request_template.md
├── CONTRIBUTING.md           # this file
└── README.md
```

## Skill anatomy

```
skills/my-skill/
├── SKILL.md          # REQUIRED: frontmatter + instructions
├── references/       # optional: long docs, schemas, examples
├── scripts/          # optional: deterministic steps (py/sh)
└── assets/           # optional: templates, output files
```

### `SKILL.md`

```markdown
---
name: my-skill
description: What the skill does and WHEN to use it. This field decides whether the model loads the skill at all.
---

# Title

Step-by-step instructions...
```

Rules:

- **`name`** — kebab-case, identical to the directory name, max 64 characters.
- **`description`** — max 1024 characters. Say *what* it does and *when* to use it
  (keywords, typical user phrases). The model sees only this field before deciding to load the skill.
- **`SKILL.md` body** — keep it concise, ideally < 500 lines. Move details to
  `references/` and link to them from `SKILL.md` (progressive disclosure).
- **Prefer scripts** over prose wherever the result must be deterministic.
- **No secrets** — keep tokens, passwords and internal URLs out of the repo (use environment variables).
- **Language** — repo docs are in English. A skill may be written in another language
  when it is meant to operate in that language, but keep each skill consistent.

## Branches

Two long-lived branches plus short-lived working branches.

```
feature branches ──PR──▶ dev ──release PR──▶ main (tag vX.Y.Z)
                                              │
                         hotfix/* ◀───────────┘ ──PR──▶ main + back to dev
```

| Branch           | Purpose                                              | Branch from | Merge into      |
|------------------|------------------------------------------------------|-------------|-----------------|
| `main`           | released, stable skills; every merge is tagged       | —           | —               |
| `dev`            | day-to-day integration; **default branch**           | `main`      | `main`          |
| `skill/<name>`   | new skill                                            | `dev`       | `dev`           |
| `update/<name>`  | change to an existing skill                          | `dev`       | `dev`           |
| `fix/<desc>`     | bug fix                                              | `dev`       | `dev`           |
| `docs/<desc>`    | README, CONTRIBUTING, comments                       | `dev`       | `dev`           |
| `chore/<desc>`   | CI, scripts, housekeeping                            | `dev`       | `dev`           |
| `hotfix/<desc>`  | urgent fix of a released skill                       | `main`      | `main` + `dev`  |

Naming:

- lowercase kebab-case, no spaces, no personal or tool prefixes (`john/…`, `bot/…`);
- `<name>` is the skill directory name, e.g. `skill/jira-dev-task`;
- `<desc>` is 2–4 words, e.g. `fix/jira-fixversion-format`.

Rules:

1. No direct commits to `main` or `dev` — always open a PR.
2. One branch = one skill / one change. Easier to review and revert.
3. Working branch → `dev`: **squash merge**, delete the branch after merging.
4. `dev` → `main` (release): **merge commit**, then tag `vX.Y.Z` on `main`.
5. CI (`validate-skills`) must be green.

Recommended GitHub settings:

- Settings → General: default branch `dev`, allow squash + merge commits,
  automatically delete head branches.
- Settings → Branches: protect `main` and `dev` — require pull request,
  require status check `validate`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/), scope = skill name:

```
feat(jira-dev-task): add fixVersion lookup
fix(jira-dev-task): handle missing AB ticket
docs: describe skill installation
chore(ci): add frontmatter validation
```

## Versioning

- Releases are tags on `main` with semver: `v0.1.0`, `v0.2.0`… (release notes from commit history).
- A change to a skill's `description` or behavior that may break existing usage → bump minor
  (before `v1.0.0`) / major (after `v1.0.0`).

## Adding a new skill — step by step

```bash
git switch dev && git pull
git switch -c skill/my-skill
cp -r skills/_template skills/my-skill
# edit skills/my-skill/SKILL.md (name: my-skill)
python3 scripts/validate_skills.py
git add skills/my-skill
git commit -m "feat(my-skill): initial version"
git push -u origin skill/my-skill
# open a PR to dev
```

## Releasing

```bash
# open a PR dev → main, merge it with a merge commit, then:
git switch main && git pull
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

## Testing a skill

- Install the skill in the AI agent you use: copy or symlink the skill directory into the
  agent's skills directory, or upload it zipped, then run a task that should trigger it.
- Check both cases: the skill **should** trigger / **should not** trigger.
  Save example prompts in `references/examples.md`.
