# Docs sync map

Reader: anyone changing code, settings, or documents in this project.

Last reviewed: 23 October 2026

Documents must never fall behind the project. When you change something in the left column, check every document in the right column. If one describes something you changed, update it in the same change. If none needs updating, say so in your pull request or patch notes and say why.

## Map

| If this changes | Check these documents |
|---|---|
| Anything a user can run | `README.md`, `docs/development/setup.md`, `CHANGELOG.md` |
| Test, metric, or threshold | `docs/research/`, `research/claims-ledger.md`, `docs/limits.md` |
| Experiment result | `research/claims-ledger.md`, `docs/research/topics.md`, `docs/how-it-works.md`, `docs/limits.md` |
| Dependency or tool version | `docs/development/setup.md`, `pyproject.toml` |
| Safety or ethics rule | `SAFETY.md`, `CONTRIBUTING.md`, `docs/start-here.md` |
| Folder structure | `docs/development/architecture.md`, `README.md` |
| Law, hotline, or takedown process | `docs/for-families.md`, the relevant guide |

## Code areas

| Code area | Check these documents |
|---|---|
| `scripts/check_docs.py` (its rules or settings) | `docs/development/style-guide.md`, `CONTRIBUTING.md`, `docs/development/architecture.md` |
| `uv.lock` | `docs/development/setup.md`, `docs/development/architecture.md` |
| `.github/workflows/ci.yml` | `CONTRIBUTING.md`, `docs/development/setup.md` |
| `.github/ISSUE_TEMPLATE/` and `PULL_REQUEST_TEMPLATE.md` | `CONTRIBUTING.md`, `SAFETY.md`, `SECURITY.md` |
| `pyproject.toml` (name, licence, Python version, dependencies) | `README.md`, `docs/development/setup.md`, `LICENSE-docs.md` if the licence changes |
| `src/mantelet/` | `docs/development/architecture.md`, `docs/how-it-works.md`, `README.md` |
| `src/mantelet/datasets.py` (the register) | `research/datasets-and-models.md`, `docs/research/data-and-ethics.md` |
| `src/mantelet/faces.py` (model files, thresholds) | `research/datasets-and-models.md`, `docs/research/test-plan.md`, `research/claims-ledger.md` |
| `src/mantelet/baseline.py` and `metrics.py` (conditions, scores, counting rules) | `docs/research/test-plan.md`, `docs/how-it-works.md` |
| `src/mantelet/sface_copy.py`, `scripts/check_sface_copy.py`, the `ml` extra | `docs/development/setup.md`, `docs/research/test-plan.md`, `docs/development/architecture.md`, `research/claims-ledger.md`, `CHANGELOG.md` |
| `src/mantelet/protect.py`, `diffjpeg.py`, `protectcheck.py`, `budgetsweep.py`, `effect.py`, `scripts/check_protection.py`, `scripts/run_budget_sweep.py` (the first protection, its checks and sweep, the effect rule) | `docs/development/setup.md`, `docs/research/test-plan.md`, `docs/development/architecture.md`, `research/claims-ledger.md`, `docs/limits.md`, `docs/how-it-works.md`, `docs/glossary.md`, `CHANGELOG.md` |
| `src/mantelet/budgetgraph.py` (budget graph) | `docs/development/architecture.md`, `docs/research/test-plan.md`, `CHANGELOG.md` |
| `src/mantelet/image.py` and `cropsweep.py` (pipeline, crop positions) | `docs/research/test-plan.md`, `docs/development/architecture.md`, `research/claims-ledger.md` |
| `scripts/check_gpu.py`, the `ml` extra in `pyproject.toml` | `docs/development/setup.md`, `research/compute-options.md`, `research/claims-ledger.md` |
| `src/mantelet/attacks.py`, `toy.py` and `redteam.py` (attacks, toy protections, quality floor, survival) | `docs/research/test-plan.md`, `docs/research/threat-model.md`, `research/claims-ledger.md`, `docs/how-it-works.md`, `docs/glossary.md` |
| `scripts/` (anything a user can run) | `docs/development/setup.md`, `docs/development/architecture.md`, `CHANGELOG.md` |
| `tests/` | `docs/development/architecture.md` |

## Each step

1. Check each area the step touched against the tables above.
2. Update `CHANGELOG.md` only for changes a user would notice. Match the style already in the file.
3. If a real change has no document, write the small missing piece now or open an issue that names the missing document.
