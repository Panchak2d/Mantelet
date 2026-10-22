# Research overview

Reader: a researcher or contributor who wants to know what the research track is trying to do.

Last reviewed: 22 October 2026

This page is a short summary. The full research design is written in these pages:

- [Research topics](topics.md): what we have looked into, what the sources say, and where each answer is recorded.
- [Threat model](threat-model.md): who might attack and what we try to stop.
- [Test plan](test-plan.md): how we measure success and failure, with fixed numbers.
- [Data and ethics policy](data-and-ethics.md): what data we use and how we follow the safety rules.
- [Datasets and models](../../research/datasets-and-models.md): the licence of every dataset and model, and what we do not know about them.
- [Compute options](../../research/compute-options.md): the free and rented GPU services for later steps, and what their terms allow.

No experiment on a real protection has run yet. The measuring tools and the red team attack tools are built and tested on made-up images and toy protections.

## The question

Can we make it much harder to turn an ordinary photo into a fake sexual or nude image, by adding changes to the photo that people cannot see?

## What we try to stop

| Code | Threat | Priority |
|---|---|---|
| T1 | One photo goes into an editing or inpainting tool built on open models | First |
| T2 | A model is fine-tuned on a handful of photos of one person | Second |
| T3 | A face recognition system is trained on scraped photos | Last, only if time allows |

Out of scope: video, audio, closed commercial models, and anything that needs us to create abusive images.

## The questions

1. How much can a photo change before a person notices?
2. Does a change that small stop an edit from working?
3. Does it still work after JPEG, resizing, cropping, and blur?
4. Does it work on a different model than the one we tuned it on?
5. Does it work on a model released later?
6. What happens when the attacker knows about Mantelet?
7. Can we make it work without a long calculation for every photo?

## How we decide

We do not use average similarity scores as the main result. We use attacker success rate, noticeable change rate, and survival rate after normal photo processing. The [test plan](test-plan.md) defines each one and fixes the pass and fail numbers before any experiment.

## Decision gates

| Gate | After | Question |
|---|---|---|
| 1 | later | Does a protection on a small model survive the red team within the visibility limit? |
| 2 | later | Does it work on a real editing pipeline after JPEG and resize? |
| 3 | later | Does it survive attacker levels 0 to 4 and transfer to at least one other model? |

A "no" at a gate is a useful result. We publish it, and move effort to the guides.

## Safety

All research follows [SAFETY.md](../../SAFETY.md). We use harmless stand-in edits, synthetic faces, and consenting adults only.
