# How it works

Reader: a curious learner or researcher who wants to understand the technical idea.

Last reviewed: 23 October 2026

This page is mostly empty. It will be filled in as the experiments happen. We do not describe how something works until we have built and tested it.

## The idea we want to test

An AI editing tool looks at a photo and changes it. Some research tries to add tiny changes to the photo that people cannot see, but that confuse the tool. The hope is that the edit then fails or looks wrong.

We do not know if this works well enough to matter. See [Limits](limits.md).

## What we plan to measure

- Whether a person can see the change.
- Whether the edit still works, using harmless stand-in edits.
- Whether the effect survives shrinking, cropping, and compressing the photo.
- Whether someone who knows about our method can remove it.

The plan for this is in the [research overview](research/README.md).

## How we measure

We built the measuring tools before any protection, so we cannot fool ourselves. No result on a real protection has been produced with them yet.

- **Pixel change.** Four numbers say how far two photos of the same size differ. The mean squared error is the average of the squared pixel differences. PSNR turns that into a scale in decibels where a higher number means more alike. The largest pixel change is the single biggest jump in any pixel. SSIM compares local patterns of light and detail and gives 1 for identical photos. None of them says what a person notices.
- **Face match.** A face detector finds the face. A recogniser turns it into a list of numbers. Two faces match when their lists point in nearly the same direction, measured as a cosine similarity of at least 0.363. Both models were trained on photos we cannot vouch for, and the threshold was set on photos of real people. See the [register](../research/datasets-and-models.md).
- **Baseline.** Before any protection exists, we run photos through shrinking, cropping, compression, blur and noise and measure what is left. A protection must be judged against that, not against a perfect score.

- **Red team.** We built attacks that try to undo a protection before we built any protection. They are basic cleanup filters, the standard attacks from the papers we read, and attacks that use knowledge of how a protection is made. Each attack gets only the protected photo, never the original. We test them on toy protections, which add a hidden pattern that does nothing against any model, so we know the right answer. One toy is easy to remove on purpose. One has a design flaw on purpose: it adds the same pattern to every photo, so averaging many photos exposes it. One is different in every photo and has no such flaw. We then measure how much of the pattern is left, called survival, but only for attacked photos that still look close to the original. The attacks that need a diffusion model are not built yet. A toy result says nothing about a real protection.


- **First protection (built, not yet tested on real faces).** It changes the pixels around a face by a small, fixed amount so that one open face recognition model no longer sees the same person. A computer finds each change by trying small steps and keeping the ones that move the face away from the original, which is called projected gradient descent. We built a plain version and a version that is also tuned through JPEG compression, because a change tuned without compression is known to wash out. The numbers that decide whether either one passes, including a face that the processing alone loses, are fixed in the [test plan](research/test-plan.md) before any result exists. Whether it changes anything on real faces is not known yet. A face recognition model is not an editing model, so even a good result would say nothing about editing.

The exact settings are in the [test plan](research/test-plan.md).

## What goes on this page later

- The method, in plain words, with a picture.
- The results, with the failures.
- Links to the code that made each result.
