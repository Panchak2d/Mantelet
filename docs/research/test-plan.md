# Test plan

Reader: a researcher who wants to know exactly how we measure success and failure, and what numbers count as passing.

Last reviewed: 23 October 2026

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

## Crop positions

The fixed pipeline always crops from the centre. On a 512 pixel long side that starts the crop 51 pixels in, which is 3 pixels off the 8 pixel grid that JPEG works on (claim C-021). One position tests one case. So the code can also start the crop at a seeded random corner (`random_crop_offset`, `platform_pipeline_random_crop` in `src/mantelet/image.py`) and `src/mantelet/cropsweep.py` measures survival through the fixed pipeline at three kinds of corner: the centre, 16 seeded random corners, and up to 36 corners that lie on the 8 pixel grid (six left values times six top values, spread evenly and including the first and last).

The numbers do not change: long side 512, crop 80 percent, JPEG 75. Only the place where the crop starts is free.

Survival through the pipeline is measured like this. The ideal change is the protection's change (protected photo minus original) shrunk and cropped without JPEG, kept as decimal numbers. The actual change is the protected photo minus the original photo, both run through the pipeline at the same corner. Survival is how far the actual change lies along the ideal one. 1 means the pipeline removed nothing and 0 means it removed all of it. For each photo the report gives the centre, the mean over random corners, the mean over grid corners and the worst corner.

The pass number of 50 percent is judged at the centre crop, as fixed above. The other corners are reported beside it and are never used to rescue a failure at the centre. If the centre passes and some corners fail, the report shows the gap and we say so. We do not move the number. This is the same rule as for the milder profile. We added the crop positions on 22 October 2026, before any protection result exists.

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

**The known band attack uses the protection's own band.** A protection declares the band of spatial frequencies it writes its change into, or none (`Protection.band`). The level 3 known band attack is built from that band and is left out for a protection that declares none, because there is no band to remove. `toy-band` and `toy-band-shared` declare the band they use. `toy-white` declares none, since fine random grain has no band. A real protection must declare its own band or structure before it meets level 3, and a protection with a structure that is not a band needs its own attack. The quality floor and the survival number are unchanged.

**Face match and edit success.** Survival alone does not show whether a model is fooled (claim C-033). The red team records therefore carry two more columns for every attack result that stays above the quality floor.

- `face_match`: the face model finds a face in the attacked photo and the cosine similarity to the face in the unprotected original is at least 0.363. A face not found counts as no match, and a photo whose original face is not found is left out of the face numbers and counted. These are the baseline counting rules. The column stays empty when no face model is given. The face match after the fixed pipeline in `pipeline.csv` follows the same rule, with the centre crop as the processed photo, and has a similarity column.
- `edit_success`: a stand-in edit, run on the attacked photo, worked. It needs an editing model, which is built in step 9, so the column is empty in every run until then and the report says it was not measured.

The attacker wins on a photo when any admissible result, up to the attacker level, still has a face match (or a working edit). This is the worst case rule again. The attacker success rate is the share of photos with a face found in the original where the attacker wins, with a 95 percent Wilson interval. It includes the unattacked protected photo, so level 0 shows what the protection does on its own. The unprotected baseline for the 50 point drop is the baseline match rate in the same conditions.

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

## The copy check of the SFace copy

A protection is tuned against a PyTorch copy of SFace, and the red team judges it with the SFace file run through OpenCV. If the two disagree, a result on the copy says nothing about the red team's face match. `scripts/check_sface_copy.py` therefore compares the two on real aligned faces before any protection is tuned. OpenCV gives SFace an aligned 112 by 112 crop as RGB values from 0 to 255 with no mean and no scaling (claim C-042), and the copy takes the same input.

Fixed on 22 October 2026, before any copy result exists, and a Guess until the first run:

- At least 10 faces are found in the sampled photos.
- For every face, the cosine between the OpenCV vector and the copy's vector is at least 0.999.
- For every pair of faces, the cosine similarity measured with OpenCV's vectors and with the copy's differs by at most 0.01.

The reason: two float32 implementations of the same network agree far more closely than these limits, so a copy that misses them is wrong and not merely noisy. We also count the pairs where the copy and OpenCV disagree on the same person decision at 0.363. That count is reported and is not a pass limit. If the copy fails, no protection is tuned against it. A pass says the copy reproduces OpenCV on these faces and says nothing about any protection.

## The first protection

The first protection is projected gradient descent (PGD) against the PyTorch copy of SFace (`src/mantelet/protect.py`). It changes the pixels that feed the aligned face crop by at most a budget, a whole number of pixel values out of 255, so as to push the face vector of the crop away from the vector of the unprotected face. The real face model in the red team stays OpenCV's. A photo with no face found is left unchanged.

Fixed on 23 October 2026, before any protection result exists. Every number is a Guess until a run tests it.

- **Alignment.** The change is tuned through the same alignment OpenCV uses: a similarity transform from the five landmarks to fixed target points, then a bilinear warp to 112 by 112 (claim C-045). Only pixels that reach the crop receive a gradient, so the change stays near the face.
- **Settings.** 40 steps, step size one twentieth of the budget, a random start, one restart. Sources disagree on the defaults (claim C-046), so we followed the setting reported for the original method and did not tune it.
- **Two kinds.** `pgd` is tuned on the photo as it is. `pgd-jpeg` is also tuned through a random shift of 0 to 7 pixels and a differentiable JPEG at a random quality from 60 to 90 (claims C-047 and C-048). The quality range does not centre on 75 on purpose, so the protection is not tuned to the quality the fixed pipeline uses. Both are reported. Neither is tuned against any attack.
- **Budgets.** The sweep runs 1, 2, 3, 4, 6, 8, 12 and 16 by default. At a budget of 8 no pixel moves by more than 8, so the PSNR cannot fall below 30.07 dB. Larger budgets can fall under the quality floor, and the graph shows where.
- **Budget used for Gate 1.** The largest budget in the sweep at which every sampled photo stays at or above the quality floor. A photo below the floor at a budget is left out of that budget's survival and face numbers and counted on its own. Other budgets are reported beside it and never used to rescue a failure.
- **Declared band.** A protection declares the band its change lives in, because the level 3 known band attack is built from it. The band is measured at a budget of 8 on photos kept apart from the test set. Among bands that cover at most a quarter of all spatial frequencies, the one holding the most energy of the change is declared (`measure_band`). The share of energy inside it is reported, because a change spread over all frequencies has no real band and the known band attack is then weak. The collusion attack is aimed at a pattern shared between photos, and this change differs in every photo.

### What counts as the effect

Survival says whether the change is still in the photo. The effect is the drop in the face match, measured beside the unprotected photo through the same code, photos and pipeline (the `none` control in the red team run). The counting rule for a face that is not found, "no match", would credit the protection with faces that the processing lost on its own, so for the effect it is refined. The refinement is fixed before any protection result exists and the baseline rules above are otherwise unchanged.

- A photo whose unprotected, processed face does not match the original is left out of the effect and counted on its own. Photo 000061 in the first red team run is such a photo: the face was found in the original and lost after the fixed resize and crop.
- On the counted photos, a protected photo whose face is no longer found counts as an attacker win, because an attacker can find the face with another detector. The rate that counts it as no match is reported beside it.
- The drop is 100 points minus the attacker win rate, because the unprotected baseline is a match on every counted photo.
- Every report shows the three states of the protected photo: matches, found but no match, lost.

### How Gate 1 is judged

- The attacker levels are 0 to 2, as in the table below. Level 3 and the other crop corners are run and reported beside them, and they are never used to rescue a failure.
- The effect is the larger of two attacker success rates: through the fixed pipeline at the centre crop, and the best result of attackers up to level 2, where the unattacked photo with a lost face also counts as an attacker win.
- The other fixed numbers apply: survival at least 50 percent at the centre crop, PSNR at least 30 dB and SSIM at least 0.90 for every counted photo at the chosen budget, and a drop of at least 50 points.
- **Visibility cannot be measured yet.** The limit of 25 percent noticing needs the human study in Batch 8. Until then only PSNR and SSIM are reported. The Gate 1 report says so, and a result can be a failure on another number but cannot be a full pass.
- **On record before the run:** a protection tuned without compression is known to lose much of its effect under JPEG (claim C-047), so plain `pgd` may well miss the survival number at budgets that stay above 30 dB. That would show that this kind of protection fails the fixed pipeline. It would not show that no protection can pass.

### The check of the pieces

Before any protection is swept, `scripts/check_protection.py` checks three pieces on real faces: our crop against OpenCV's alignment, the gradient against a finite difference, and our JPEG against Pillow's. Fixed on 23 October 2026, before any result, and a Guess:

- At least 10 faces. For every face, the cosine between OpenCV's vector for OpenCV's crop and the copy's vector for our crop is at least 0.999.
- For 3 faces, the relative gap between autograd and a finite difference in float64 is at most 0.01.
- The mean pixel gap between our JPEG and Pillow's JPEG at quality 75 is at most 1.0 on the sampled photos.

If any limit is missed, no protection is swept until the piece is fixed.

**First run, 23 October 2026 (owner's machine, 20 Face Synthetics faces).** The crop missed: the lowest cosine was 0.998911 against the limit of 0.999. The gradient met its limit (worst gap 1.12e-3) and the JPEG met its limit (mean gap 0.446). The cause is that OpenCV hands the recogniser a crop of whole pixel values, and our crop kept the smooth values. On made-up 512 pixel photos, rounding our crop cut its mean gap to OpenCV's from 0.142 to 0.012 pixel values, so the matrix and the interpolation agree (claim C-050, a Guess until the re-run). The crop now rounds the same way in the forward pass and lets the gradient pass straight through. The limits did not move. The check is run again, and `scripts/diagnose_crop.py` splits any further miss into matrix, interpolation and rounding.

## The datasets

Each dataset is listed with its licence before use in the [register](../../research/datasets-and-models.md). The [data and ethics policy](data-and-ethics.md) sets the rules. Synthetic faces and consenting adults only. No images of people under 18. The first baseline uses the Face Synthetics sample once the owner has approved it.

## Attacker levels per experiment

Each experiment states which attacker levels it targets. The levels are in the [threat model](threat-model.md).

| Experiment step | Levels tested |
|---|---|
| later baseline | Level 0, no protection |
| later first protection | Levels 0, 1, 2 judged. Level 3 run and reported beside them |
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
