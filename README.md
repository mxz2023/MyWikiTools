# MyWikiTools

[简体中文](README.zh.md)

**Repository:** [github.com/mxz2023/MyWikiTools](https://github.com/mxz2023/MyWikiTools)

Monorepo of small **CLI tools** (each installable with **pipx**). Agent **Skills** live under `skills/` at the repo root.

## Tools

| Tool | Commands | Directory | Docs |
|------|----------|-----------|------|
| Garmin Personal API | `gmp`, `garmin-personal` | [`tools/garmin-personal-cli/`](tools/garmin-personal-cli/) | [README](tools/garmin-personal-cli/README.md) |
| *(add next tool here)* | | `tools/<name>/` | |

**Install Garmin CLI** (from a clone):

```bash
./scripts/install.sh
# same as: ./tools/garmin-personal-cli/scripts/install.sh
```

**Install from GitHub** (no clone):

```bash
pipx install "git+https://github.com/mxz2023/MyWikiTools.git@master#subdirectory=tools/garmin-personal-cli"
gmp setup
```

## Repository layout

```
MyWikiTools/
├── README.md
├── skills/                          # Agent skills (one dir per tool)
│   └── <tool>-cli/SKILL.md
├── tools/
│   └── <tool>-cli/
│       ├── pyproject.toml           # own package + console_scripts
│       ├── README.md
│       ├── src/<python_package>/
│       ├── tests/
│       └── scripts/install.sh       # optional
└── scripts/
    ├── install.sh                   # shortcuts (e.g. default tool)
    └── test-all.sh                  # run tests in every tool
```

## Adding a new CLI

1. Copy the shape of `tools/garmin-personal-cli/` (new `pyproject.toml`, `src/`, `tests/`).
2. Add `skills/<tool>-cli/SKILL.md` and optionally `.cursor/skills/<tool>-cli` → symlink to `skills/`.
3. Register the tool in this README table.
4. Extend `scripts/test-all.sh` if you add a new package path.

## Agent skills

Skills stay at **`skills/<tool>-cli/`** so paths like  
`npx skills add mxz2023/MyWikiTools@garmin-personal-cli` keep working.

Per-tool details: see each tool’s README under `tools/`.

## License

Apache-2.0 (per tool package where noted).
