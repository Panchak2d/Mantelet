# Contributing

Reader: someone who wants to help, from first-timer to experienced developer.

Last reviewed: Batch 1, 5 October 2026

Thank you for helping. This page tells you how to start, what we accept, and what we always refuse.

## Read these first

1. [SAFETY.md](SAFETY.md). These rules have no exceptions.
2. [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
3. [The style guide](docs/development/style-guide.md) if you write or edit documents.

## Set up

Follow [docs/development/setup.md](docs/development/setup.md). It was written for EndeavourOS. Other Linux systems are similar.

## What helps

- Fixing mistakes in the documents, or making them easier to read.
- Reporting a page that was confusing.
- Checking a source or a link.
- Small, clear improvements to the code and tests.

For anything big, open an issue first and describe your idea.

## What we always refuse

- Images of people in any form. This includes your own photo and photos of volunteers.
- Code that makes sexual or nude images, or undresses, or swaps faces.
- Datasets or models with no recorded licence.

## Before you open a pull request

1. Run the three checks: `ruff check .`, `pytest`, and `python scripts/check_docs.py`.
2. Look at [docs/development/docs-sync.md](docs/development/docs-sync.md). Update every document that your change affects, in the same pull request.
3. Write comments only when the code would otherwise be hard to understand. A comment says why the code does something. It never mentions batches, plans, or rules.
4. Name tests after the behaviour they check.

## Licences

By contributing, you agree that your code is under the Apache License 2.0 and your documents are under CC BY 4.0. See [LICENSE](LICENSE) and [LICENSE-docs.md](LICENSE-docs.md).
