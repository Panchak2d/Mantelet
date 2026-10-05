# Style guide

Reader: anyone who writes or edits a document in this project.

Last reviewed: 5 October 2026

These rules keep the documents easy to read and honest. The docs checker (`python scripts/check_docs.py`) enforces the ones a program can check. It cannot tell if writing sounds natural. Reading a page aloud and fixing the places where you stumble is part of the process.

Plain-language guidance to read first: plainlanguage.gov.

## Rules

- Write for a smart reader who has never heard of machine learning.
- Use short sentences. One idea each. Aim for about grade 8 reading level on family pages.
- Say what something is before you name it. Explain every technical word the first time, and add it to the [glossary](../glossary.md).
- Use no long dashes or en dashes. Use a full stop, a comma, a colon, or the word "and".
- Use no emoji. Use few bold words. Write headings that say what the section answers.
- Use "we" for the project and "you" for the reader.
- Give an example whenever an idea is abstract.
- Say what we do not know. Never round a guess up to a fact.
- End a page when the content ends. Do not add a closing summary that repeats the page.
- Technical words such as "robust" are allowed where they have a defined meaning. Explain them once in the glossary.

## Words and patterns to avoid

The checker looks for these: delve, leverage, utilize, seamless, crucial, pivotal, landscape, tapestry, testament, "it is important to note", "in today's world", and the pattern "not just X, but Y".

Also avoid lists of exactly three adjectives. The checker cannot find these. Look for them when you read.

## What every page must have

Near the top, two lines:

```text
Reader: who this page is for.

Last reviewed: Step N, D Month YYYY
```

The checker flags a page if either line is missing, or if the review is more than 3 steps old.

Practice notes in the `learning/` folder are exempt, because they are your own notes.

## Checker settings

The reading level limit, the number of steps before a page counts as old, and the current step number are set at the top of `scripts/check_docs.py`. The current step number is changed once per step.

## Claims

Every public claim goes in the [claims ledger](../../research/claims-ledger.md) with one label: **Measured**, **Reported**, or **Guess**. Never write that Mantelet "protects" anyone. Say what was measured, on what, and when.

## Safety in writing

Never describe a harmful edit in detail. Never include an image of a person. See [SAFETY.md](../../SAFETY.md).

## Reading level

The checker uses the Flesch-Kincaid grade formula with a simple syllable guess. It is approximate and can be wrong for short pages or for pages full of names. Treat a failure as a prompt to read the page again, not as proof that the page is bad.
