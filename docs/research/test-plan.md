# Test plan

Reader: a researcher who wants to know exactly how we measure success and failure, and what numbers count as passing.

Last reviewed: 5 October 2026

This page fixes the pass and fail numbers before any experiment runs. The plan as planned requires this. The numbers below are chosen with written reasons. They will not change after we see results. If we change any of them later, we say so here and explain why.

## Metrics

We do not use average similarity scores as the main result. We use three metrics.

**Attacker success rate.** How often an attack still works. For example, how often a face match still succeeds after we protect a photo. A lower number is better for the defender. We measure it at a fixed threshold, not as an average.

**Noticeable change rate.** How often volunteers can tell a protected photo from the original. A lower number is better. We measure it with a two alternative forced choice test, described below.

**Survival rate.** The share of the protection effect that is left after normal photo processing, such as shrinking or compressing. A higher number is better.

## Fixed numbers

These numbers are fixed. They are chosen with reasons drawn from the research we read in this step. See the [bibliography](../../research/bibliography.md) for the sources.

### Visibility limit (Y)

The noticeable change rate must be at most **25 percent** in a two alternative forced choice test.

Reason: in a two alternative forced choice test, a volunteer sees two images and guesses which one is the original. If they cannot see the change, they guess, and they are right about half the time. A 25 percent "notice" rate is below that chance line, which means volunteers are not seeing the change. Anything above 25 percent means people are seeing it, and the method fails the visibility gate. We treat this number as a **Guess** until the later human study calibrates it. We label it as such.

### Effect threshold (X)

The attacker success rate must drop by at least **50 percentage points** relative to the unprotected baseline.

Reason: a smaller drop is unlikely to deter a casual attacker. The Honig et al. paper shows that even large drops can be undone by adaptive attacks. A 50 point drop is a floor that makes a real difference, not a rounding artefact. For example, if an edit works 90 percent of the time without protection, it must work at most 40 percent of the time with it. The exact baseline depends on the model and is fixed per experiment.

### Survival rate

At least **50 percent** of the effect must survive the platform processing pipeline.

Reason: if the protection washes out below half after ordinary processing, it is not useful in practice. A photo that goes through a social site is shrunk and compressed before anyone sees it. The DCT-Shield paper is the reference for designing a protection that survives JPEG. Our pipeline is fixed below.

## The platform processing pipeline

We apply these transformations to every protected photo before testing whether the protection survived. They match what a typical social site does. The exact code is built.

| Step | Setting |
|---|---|
| Resize | Long side to 512 pixels, using a standard resampling filter |
| Crop | Centre crop to 80 percent of the resized image |
| JPEG | Quality 75 |

These numbers are fixed. They are a stand-in for what real platforms do, not an exact copy of any one site. Real sites differ. We chose 512 because it is a common display size. We chose quality 75 because it is the middle of the range sites use. We chose 80 percent crop because it is a moderate crop that does not remove the face.

## The transformations and attack tools

These are fixed and built in steps 3 and 5.

| What | Built in | Purpose |
|---|---|---|
| JPEG, resize, crop, blur, noise | later | The changes platforms apply |
| Red team attack tools | later | The attacks for levels 2 and 3 |

The red team attacks use methods that are already public. They attack our own protections. They do not target people. See [SAFETY.md](../../SAFETY.md) rule 7.

## The datasets

These datasets are chosen carefully. Each dataset is listed with its licence before use. The [data and ethics policy](data-and-ethics.md) sets the rules. Synthetic faces and consenting adults only. No images of people under 18.

## Attacker levels per experiment

Each experiment states which attacker levels it targets. The levels are in the [threat model](threat-model.md).

| Experiment step | Levels tested |
|---|---|
| later baseline | Level 0, no protection |
| later first protection | Levels 0, 1, 2 |
| later reproduced protection | Levels 0, 1, 2, 3 |
| later final | Levels 0, 1, 2, 3, 4, 5 |

Level 5 is tested by waiting: we protect photos now and attack them with models released later.

## Decision gates

| Gate | After | Question | Pass requires | If no |
|---|---|---|---|---|
| 1 | later | Does a protection on a small model survive the red team within the visibility limit? | X met and Y met | Stop adding methods. Study why, publish the finding, move effort to the family and provenance tracks |
| 2 | later | Does it work on a real editing pipeline after JPEG and resize? | X met and survival rate met | Same |
| 3 | later | Does it survive levels 0 to 4 and transfer to at least one other model? | X met across levels 0 to 4, and transfer shown | Release as a negative result. The guides and provenance work continue |

A "no" at a gate is a useful result and is treated as one. We publish it.

## What we will not do with these numbers

- We will not change them after seeing results. If a result is close to a threshold, we do not move the threshold. We report the gap.
- We will not average across attacks to hide a single attack that still works. The worst case is the result.
- We will not report only the best run. Every run is logged with its seed and the versions of every tool.
