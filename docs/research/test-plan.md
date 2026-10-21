# Test plan

Reader: a researcher who wants to know exactly how we measure success and failure, and what numbers count as passing.

Last reviewed: 21 October 2026

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

These numbers are fixed. They are a stand-in for what real platforms do, not an exact copy of any one site. Real sites differ. We chose quality 75 because it sits inside the range that studies report for Facebook (see claim C-016 in the [claims ledger](../../research/claims-ledger.md)). Those studies also report that sites shrink photos only above 1080 to 2048 pixels, so 512 is harsher than any site we found (C-017). We keep it because common editing models work at about 512 pixels, so an attacker may shrink the photo this far anyway (C-018). We chose 80 percent crop as a moderate crop. No study we found says sites crop this way (C-019).

This pipeline is therefore a harsh stress test, not a copy of a platform. A protection that survives it is a stronger result. A protection that fails it has not yet been shown to fail on a real site.

The crop keeps the face only when the face sits near the middle of the photo. A full-body photo has its face near the top, and the centre crop cuts the head off. Test images must be framed around the face, such as the aligned faces in common face datasets. The numbers above are unchanged.

## The milder second profile

The fixed pipeline is harsh on purpose. A second, milder profile shows what a photo meets on a site that only shrinks large photos and does not crop.

| Step | Setting |
|---|---|
| Resize | Only if the long side is above 1080 pixels, shrink it to 1080. Never enlarge |
| Crop | None |
| JPEG | Quality 85 |

Reason: the studies in claims C-016 and C-017 report Instagram shrinking only above 1080 pixels and Facebook quality factors up to 92. No study we found reports a crop (C-019).

The milder profile is measured and reported next to the fixed pipeline. It does not replace it. The pass numbers above still apply to the fixed pipeline, and a result on the milder profile is never used to rescue a failure on the fixed one. We added this profile on 9 October 2026, before any protection result exists.

## The measuring tools

These are built and are fixed before any protection result.

**Difference scores.** For two images of the same size we calculate four scores: mean squared error (MSE), peak signal to noise ratio (PSNR), the largest change to any pixel, and structural similarity (SSIM). They measure pixel change, not what a person notices. The human study decides visibility. The scores are calculated from their published formulas in `src/mantelet/metrics.py`. SSIM was checked against the scikit-image implementation and agreed to 12 decimal places on three test pairs. That check was run once by hand and is not part of the test suite.

**Face match.** The face detector is YuNet with a detection score threshold of 0.6. The recogniser is SFace. Two faces match when the cosine similarity of their face vectors is at least 0.363. Both numbers come from the OpenCV Zoo code (claim C-022). The rules for counting are:

- A photo whose original face is not found is left out of the face numbers and counted on its own.
- A face not found after processing counts as no match.
- The match rate is matches divided by the photos whose original face was found, with a 95 percent Wilson interval.

**False match check.** We also compare every pair of different photos. Any match there is a false match. It shows whether the threshold is too loose for the dataset. It assumes different photos show different people, so it can only overstate the false matches.

**Baseline conditions.** Each photo goes through the conditions below with no protection. The result is what ordinary processing does on its own. A protection result must be judged against it. The noise seeds are derived from the run seed, the photo and the condition, so a run can be repeated.

| Condition | What is done |
|---|---|
| identity | Nothing. A face must match itself |
| jpeg-75 | JPEG at quality 75 |
| blur-1 | Gaussian blur, radius 1 |
| noise-5, noise-15 | Gaussian noise with standard deviation 5 and 15 |
| platform-pipeline | The fixed pipeline |
| mild-pipeline | The milder profile |
| noise-15-then-pipeline | Noise 15, then the fixed pipeline |

A condition that changes the size of the photo cannot be scored pixel by pixel against the original. For a protection, the size-matched comparison is the protected photo against the unprotected photo after the same pipeline.

**Where the first baseline stands.** The tools and a test run on stand-in images exist. The baseline on synthetic faces needs the dataset review in the [register](../../research/datasets-and-models.md) and the model download, so it has not run yet. No baseline number is in the repository.

## The transformations and attack tools

These are fixed. The first two rows were built in steps 3 and 4. The third was built in step 5.

| What | Built in | Purpose |
|---|---|---|
| JPEG, resize, crop, blur, noise | built (`src/mantelet/image.py`) | The changes platforms apply |
| Difference scores, face match, baseline runner, report | built (`src/mantelet/metrics.py`, `faces.py`, `baseline.py`, `report.py`) | The measurements above |
| Attacks and toy protections | built (`src/mantelet/attacks.py`, `toy.py`, `redteam.py`) | The red team, described below |

The red team attacks use methods that are already public. They attack our own protections. They do not target people. See [SAFETY.md](../../SAFETY.md) rule 7.

## The red team

The red team tries to undo a protection. It was built and tested before any real protection exists. Its first test subject is a set of toy protections that we made up. A toy adds a hidden pattern we know exactly and does nothing against any editing model or face matcher. The toys exist so that we know the right answer: one is weak on purpose, one has a design flaw on purpose, and one has neither. A red team that cannot find the weak toy, or that breaks the sound one, is not ready to judge a real protection. The toy results say nothing about whether a real protection works. They are not a gate result.

**Attacks.** Every attack takes the protected photo and nothing else, so it cannot copy the original back. The set is fixed by attacker level, using the levels in the [threat model](threat-model.md):

| Level | Attacks | Source |
|---|---|---|
| 0 | No attack. A control that must show the protection fully present | |
| 1 | JPEG again, Gaussian blur, shrink and enlarge | Basic cleanup filters |
| 2 | Median filter, colour bit depth reduction, non-local means denoising, noise then JPEG, noise then denoising, blur then JPEG | Feature squeezing (claim C-029), Gaussian noising (claim C-028) and the chains of steps from claim C-020 |
| 3 | Removal of a known band of spatial frequencies, and the collusion attack, which averages many protected photos to estimate a pattern they share and subtracts it | The watermark estimation attack (claim C-030) |

Each attack has a list of strengths, such as the blur radius. The attacker tries every strength on every photo.

**Not built yet.** DiffPure and noisy upscaling (claim C-028) need a diffusion model and a GPU. They are built in step 9, when the red team meets the first reproduced protection. Until then the red team is a weaker attacker than the literature describes, and every report says so.

**Survival.** For the toy protections we measure how much of the protection's own change is left. The change is the protected photo minus the original. Survival is how far the attacked photo sits from the original along that change. It is 1 when nothing was removed and 0 when all of it was. The pass number is the one fixed above: at least 50 percent must survive. Survival measures whether the change is still in the photo. It does not measure whether a model is still fooled. A real protection is judged by attacker success rate as well.

**Quality floor.** An attacker needs a photo that still looks good. An attack result counts only when the attacked photo has a PSNR of at least 30 dB and an SSIM of at least 0.90 against the unprotected original. Reason: PSNR values for lossy image compression are reported between 30 and 50 dB (claim C-032), so 30 dB is the low end of ordinary compression damage. The SSIM number has no source. Both are a **Guess** until the human study calibrates them. We fixed them on 21 October 2026, before any protection result exists. A protected photo that is itself below the floor is left out of the survival numbers and counted, because it shows the protection is too visible and not that an attack worked.

**Worst case.** For every photo the attacker keeps the admissible result with the lowest survival. This is generous to the attacker, because a real attacker cannot see the survival. We report it for each attacker level, meaning the best of all attacks up to that level. We do not average across attacks. If one attack works, that is the result.

**Toy protections.** Each adds a pattern whose typical size is 2 pixel values, measured as the root mean square (RMS).

| Toy | What it is | What the red team should find |
|---|---|---|
| `toy-white` | Fine random grain, different in every photo | Cleanup filters remove most of it |
| `toy-band` | A smooth pattern in a band of coarse spatial frequencies, different in every photo | Cleanup filters remove less of it. The collusion attack fails, because a pattern that differs in every photo averages out |
| `toy-band-shared` | The same smooth pattern in every photo | The collusion attack removes it |

The tests in `tests/test_attacks.py` and `tests/test_redteam.py` check these expectations on made-up photos. A red team result is also a repeat of those expectations on real test photos: run `scripts/run_redteam.py` (see [Setup](../development/setup.md)).

## The datasets

Each dataset is listed with its licence before use in the [register](../../research/datasets-and-models.md). The [data and ethics policy](data-and-ethics.md) sets the rules. Synthetic faces and consenting adults only. No images of people under 18. The first baseline uses the Face Synthetics sample once the owner has approved it.

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
