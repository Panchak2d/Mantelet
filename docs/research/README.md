# Research overview

This section holds the research design of Mantelet: what question we ask, why, what we measure, what result would count as success or failure, and how we keep ourselves honest. Start here, then read the pages in the list below.

## Purpose

Fake nude images of real people are made from ordinary photos. Existing help acts after an image exists (see the [help guide](../get-help.md)). We want to know whether a photo can be changed before it is shared, in a way people cannot see, so that making a fake from it becomes much harder. The [background page](../background.md) explains the problem and the evidence for its size.

## Why this needs careful research

Earlier studies report that hidden photo changes often fail when an attacker tries to remove them, or after resizing and JPEG compression. A tool that quietly stops working is worse than no tool. A parent who trusts it may stop being careful. So we test first, against attackers, and publish what we find.

## The result we are looking for

The project succeeds when we can say, with public and repeatable data, which of these is true:

- A protection works within fixed limits of visibility, effect and survival, against stated attackers and models.
- A protection fails, and we show where and why.
- A protection works for some attackers and models and not others, and we show the boundary.

A negative result counts as success for the project. It is the outcome we have most reason to expect, and it tells people where not to put their trust.

## Pages in this section

- [Research topics](topics.md): what we have looked into, what the sources say, and where each answer is recorded.
- [Threat model](threat-model.md): who might attack and what we try to stop.
- [Test plan](test-plan.md): how we measure success and failure, with fixed numbers.
- [Results](results.md): what has been measured so far, and what is still empty.
- [Data and ethics policy](data-and-ethics.md): what data we use and how we follow the safety rules.
- [Datasets and models](../../research/datasets-and-models.md): the licence of every dataset and model, and what we do not know about them.
- [Compute options](../../research/compute-options.md): the free and rented GPU services for later steps, and what their terms allow.

## Where we are

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
