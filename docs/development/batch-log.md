# Batch log

Reader: a contributor or reviewer who wants to know what each batch did and why.

Last reviewed: Batch 1, 5 October 2026

One entry per batch, newest last. Each entry is short on purpose.

## Batch 0: the plan (4 October 2026)

- Wrote the project plan under the working title VEIL: the question, the safety rules, the 15-batch roadmap, the research design, the documentation system, and the learning plan.
- No code. Plan version 1.
- Several facts in the plan were checked to exist during planning. Titles and authors in the learning section were not yet checked and are marked as such.
- Open decisions were listed in section 12 of the plan for the owner to answer.

## Batch 2: research foundation and family guide rules (5 October 2026)

- **Research.** Wrote the full test plan with fixed success numbers (Y=25% noticeable change limit, X=50 point drop in attacker success, 50% survival rate). Mapped the attacker levels (0 to 5) and threats (T1 to T3) in the threat model. Set the ethics rules (no minors, synthetic faces or adult volunteers only, harmless stand-in edits). Checked every author, date, and link in the bibliography against the real sources.
- **Docs.** Rewrote the family guide from a stub into the first draft, maintaining a grade 8 reading level. Placed all public claims in the claims ledger marked correctly.
- **Learner task.** Assigned a task to add a banned phrase and write a test for it.
- **Built.** `docs/research/threat-model.md`, `docs/research/test-plan.md`, `docs/research/data-and-ethics.md`.
- **Not done.** Implementation of the tests. The project still has no machine learning code.

## Batch 1: scaffold, documentation foundation, and rename (5 October 2026)

- **Name.** VEIL was replaced by Mantelet. A mantelet is a short cloak and a portable shield. On 5 October 2026 the exact name "mantelet" returned 404 on PyPI, npm, crates.io, and as a GitHub user or organisation, so it is free there. Not checked: AUR, Homebrew, conda-forge, Docker Hub, domains, trademarks. The domain mantelet.com is owned by someone else. Free today is not reserved.
- **Decisions.** Apache-2.0 for code, CC BY 4.0 for text, GitHub account Panchak2d, EndeavourOS laptop with an MX330, owner's Python level basic. No page on how the project is built for now. It is a backlog line.
- **Built.** The full file tree, the safety and policy files, all documents from the plan, issue and pull request forms, CI, and `scripts/check_docs.py` with tests.
- **Versions.** Python 3.13 pinned for development and 3.11 as the lowest accepted. pytest 9.1.1 and ruff 0.16.10. Build backend hatchling. CI actions at checkout v7 and setup-python v7.
- **Hardware finding.** PyTorch's newest CUDA builds drop Pascal cards such as the MX330. The plan is CPU first, and Batches 9 to 12 need an outside GPU.
- **Not done.** The install steps were not run on EndeavourOS. The CI workflow has not run on GitHub. Two acceptance items need the owner: a clean install from the setup page, and a non-technical reader test of the start page.
