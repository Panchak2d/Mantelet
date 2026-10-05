# Docs sync map

Reader: anyone changing code, settings, or documents in this project.

Last reviewed: Batch 1, 5 October 2026

Documents must never fall behind the project. When you change something in the left column, check every document in the right column. If one describes something you changed, update it in the same change. If none needs updating, say so in your pull request or patch notes and say why.

## Map

| If this changes | Check these documents |
|---|---|
| Anything a user can run | `README.md`, `docs/development/setup.md`, `CHANGELOG.md` |
| Test, metric, or threshold | `docs/research/`, `research/claims-ledger.md`, `docs/limits.md` |
| Experiment result | `research/claims-ledger.md`, `docs/how-it-works.md`, `docs/limits.md` |
| Dependency or tool version | `docs/development/setup.md`, `pyproject.toml` |
| Safety or ethics rule | `SAFETY.md`, `CONTRIBUTING.md`, `docs/start-here.md` |
| Folder structure | `docs/development/architecture.md`, `README.md` |
| Law, hotline, or takedown process | `docs/for-families.md`, the relevant guide |

## Code areas

| Code area | Check these documents |
|---|---|
| `scripts/check_docs.py` (its rules or settings) | `docs/development/style-guide.md`, `CONTRIBUTING.md`, `docs/development/architecture.md` |
| `.github/workflows/ci.yml` | `CONTRIBUTING.md`, `docs/development/setup.md` |
| `.github/ISSUE_TEMPLATE/` and `PULL_REQUEST_TEMPLATE.md` | `CONTRIBUTING.md`, `SAFETY.md`, `SECURITY.md` |
| `pyproject.toml` (name, licence, Python version, dependencies) | `README.md`, `docs/development/setup.md`, `LICENSE-docs.md` if the licence changes |
| `src/mantelet/` | `docs/development/architecture.md`, `docs/how-it-works.md`, `README.md` |
| `tests/` | `docs/development/architecture.md` |

## Each batch

1. Check each area the batch touched against the tables above.
2. Update `CURRENT_BATCH` at the top of `scripts/check_docs.py`.
3. Update `CHANGELOG.md` only for changes a user would notice. Match the style already in the file.
4. Add an entry to `docs/development/batch-log.md`.
5. If a real change has no document, write the small missing piece now or add it to the backlog in `PLAN.md`.
