# Research topics

Reader: a researcher or contributor who wants to know what we have looked into, what the sources say, and where each answer is recorded.

Last reviewed: 22 October 2026

This page is a map. It does not repeat the evidence. Every claim lives in the [claims ledger](../../research/claims-ledger.md) with a label: Measured, Reported or Guess. Every paper and source is in the [bibliography](../../research/bibliography.md). When a topic gets a new result, update its row here in the same change.

## What we have looked into

| Topic | Question | What the sources say | Recorded in | Status |
|---|---|---|---|---|
| Protection that hides changes in a photo | Do hidden changes keep working once an attacker tries to remove them? | Simple tricks tend to stop working once someone attacks them on purpose. They also often fail after ordinary steps such as JPEG and blur. Several steps in a row can break a protection that survives one step alone | C-001, C-020, bibliography "Protection research" | Reported. We have not repeated any of the work |
| Testing a defence honestly | How do we test a protection so we do not fool ourselves? | Six papers on attacking and testing defences, from 2014 to 2020. We checked that each exists with the stated authors, title and year | Bibliography "Adversarial machine learning", [test plan](test-plan.md) | Sources checked. Not repeated |
| What platforms do to a photo | What size and JPEG quality does a photo have after it is posted? | Reported values differ between studies and change over time. Sites shrink only above a size limit. Our own choices (crop of 80 percent, long side 512) have no source | C-016, C-017, C-018, C-019, C-021 | Mixed. Some Reported, the rest Guess or not claimed |
| Face matching | When do two photos show the same person? | The SFace threshold of 0.363 was set on photos of real people. SFace is trained on web-collected photos of real people. The OpenCV 5 engine handles the YuNet file differently, so we stay on OpenCV 4 | C-022, C-023, C-027 | The threshold is a Guess for synthetic faces. The rest is Reported |
| Measuring how different two photos look | How do we score a change in a photo? | We built mean squared error, PSNR, the largest pixel change and SSIM. LPIPS is in the bibliography and is not built | `src/mantelet/metrics.py`, bibliography "Faces and image quality" | Built and tested. No perceptual study yet |
| Attacking a protection | Which attacks should the red team run, and does it find known weaknesses? | Gaussian noising, DiffPure and noisy upscaling are reported to beat several protections. Cleanup filters from the feature squeezing paper and the watermark estimation attack are older public methods. We built the ones that need no GPU and tested them on toy protections whose weaknesses we know | C-028, C-029, C-030, C-031, C-032, C-033, C-034 | The toy result is Measured on made-up photos and on 20 Face Synthetics photos. Everything else is Reported or Guess. The diffusion based attacks are not built |
| Test data and its licences | Which face datasets and models may we use, and under what terms? | Face Synthetics and DigiFace-1M allow non-commercial research only. Neither publisher states an age range for the faces, so the owner reviews a sample before approval | C-024, C-025, C-026, [datasets and models](../../research/datasets-and-models.md) | Reported. Our reading of a licence is not legal advice |
| Pass and fail numbers | What counts as a protection that works? | The limits we fixed in the [test plan](test-plan.md) come from our own reasoning | C-013, C-014, C-015 | Guess. Not yet checked by our own study |
| Diffusion models | How do the editing models work? | Background reading only: one paper, one explainer and one course. No claim depends on it yet | Bibliography "Diffusion models" | Background |
| Takedown and reporting | Where can a person get an image removed? | NCMEC runs Take It Down for people under 18. StopNCII.org is for adults. Both use a hash, so the image itself is not sent | C-003, C-008, C-009, [for families](../for-families.md) | Reported |
| Research ethics | What rules protect people in our studies? | The Belmont Report sets three principles: respect for persons, beneficence and justice | C-007, [data and ethics](data-and-ethics.md) | Reported |
| Provenance | What do content credentials prove? | The C2PA specification and the Content Authenticity Initiative both say credentials can be stripped | C-010 | Reported |
| Honest statistics | Where can a reader learn to report results fairly? | Statistics Done Wrong and the Khan Academy statistics course exist and are free | C-011, C-012 | Reported |
| Computer hardware | Can the development laptop run the later experiments? | PyTorch no longer builds for NVIDIA Pascal cards such as the MX330 in the newest CUDA versions. The card has about 2 GB of memory, which is likely too small for the editing models | C-004, C-005 | C-004 Reported. C-005 Guess |

## Not researched yet

- Takedown rules outside the United States. Start from official government and hotline sites, not blogs.
- Whether common editing models shrink a photo to about 512 pixels (C-018).
- Whether a crop that lines up with the 8 pixel JPEG grid changes the result (C-021).
- Official platform documents for the JPEG quality and size numbers (C-016, C-017). Today they come from forensic studies.
- Whether a protection works on a model other than the one it was tuned on, and on models released later.
- Whether people can see the changes. The perceptual study has not been designed yet.
