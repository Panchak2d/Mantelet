# How it works

Reader: a curious learner or researcher who wants to understand the technical idea.

Last reviewed: Batch 1, 5 October 2026

This page is mostly empty. It is filled in as the experiments happen: the first protection test is planned for Batch 6. We do not describe how something works until we have built and tested it.

## The idea we want to test

An AI editing tool looks at a photo and changes it. Some research tries to add tiny changes to the photo that people cannot see, but that confuse the tool. The hope is that the edit then fails or looks wrong.

We do not know if this works well enough to matter. See [Limits](limits.md).

## What we plan to measure

- Whether a person can see the change.
- Whether the edit still works, using harmless stand-in edits.
- Whether the effect survives shrinking, cropping, and compressing the photo.
- Whether someone who knows about our method can remove it.

The plan for this is in the [research overview](research/README.md). The exact numbers are fixed in Batch 2, before any experiment runs.

## What goes on this page later

- The method, in plain words, with a picture.
- The results, with the failures.
- Links to the code that made each result.
