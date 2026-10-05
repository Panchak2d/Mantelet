# Data and ethics policy

Reader: a researcher or contributor who wants to know what data we use, where it comes from, and the rules we follow.

Last reviewed: Batch 2, 5 October 2026

This page turns the safety rules in [SAFETY.md](../../SAFETY.md) into concrete rules for research data. The safety rules are hard and have no exceptions. This page explains how we follow them.

## No images of people under 18

We never use images of people under 18. Not in the repo, not in tests, not in datasets, not in issues, not in pull requests. Not even with permission.

Claims about children are reasoned from tests on adults and on synthetic faces. Every document that says something about children says so. This is [SAFETY.md](../../SAFETY.md) rule 2.

## No real people without consent

We use two kinds of face images:

1. **Synthetic faces.** Faces made by a computer program that do not belong to a real person. These are our main source. We record the generator and its licence before use.
2. **Adult volunteers who gave written consent.** Used only for the human perception study in Batch 8. The consent record is kept outside the repo. The consent form must say what the study does, how long it takes, that the person can stop at any time, and how the data is used and stored.

We do not scrape social media. We do not use any real face without written consent. This is [SAFETY.md](../../SAFETY.md) rule 3.

## No nude or sexual images

We never create or edit images into nude or sexual images of any real or realistic person. We test with harmless stand-in edits, such as changing the colour of a shirt or filling in a background patch. This is [SAFETY.md](../../SAFETY.md) rule 1. See the [threat model](threat-model.md) for the stand-in edit approach.

## Licence first

Every dataset and model has its licence recorded before use. Some face models are research only and cannot be used outside a study. We check each one. The list of datasets and models with their licences is built in Batch 4. This is [SAFETY.md](../../SAFETY.md) rule 4.

## Research ethics

The human perception study in Batch 8 follows the [Belmont Report](https://www.hhs.gov/ohrp/regulations-and-policy/the-belmont-report/index.html), which is the standard reference for research ethics in the United States. Its three principles are respect for persons, beneficence, and justice. We also follow our own institution's or country's rules for studies with volunteers, where they apply.

The study design, the consent form, and the data handling are written in Batch 8 and reviewed before the study runs.

## What we will not do

- We will not scrape photos of real people from any source.
- We will not use a real face without written consent.
- We will not generate nude or sexual images, even for testing.
- We will not use any dataset or model whose licence does not allow our use.
- We will not add undressing, face swap, or similar abuse features. Such contributions are closed without discussion. This is [SAFETY.md](../../SAFETY.md) rule 5.

## Reporting abuse

If anyone finds abusive material involving a child in an issue, pull request, or dataset, do not share or copy it. Report it to your national hotline or NCMEC's CyberTipline and tell the maintainer privately. This is [SAFETY.md](../../SAFETY.md) rule 6.
