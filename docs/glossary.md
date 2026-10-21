# Glossary

Reader: anyone who meets a technical word in these documents and wants a plain meaning.

Last reviewed: 21 October 2026

Words are listed in alphabetical order. We add a word the first time a document uses it.

**Admissible result.** An attacked photo that is still close enough to the original to be useful: a PSNR of at least 30 dB and an SSIM of at least 0.90. A result below that does not count as a successful attack.

**Adversarial perturbation.** A tiny change to a photo that people cannot see but that confuses a computer program. The word "perturbation" just means "small change".

**Attacker success rate.** How often an attack still works. For example, how often a face match still succeeds after we protect a photo. A lower number is better for the defender.

**Baseline.** A measurement made with no protection applied. It shows what ordinary processing does on its own, so a later result can be judged against it.

**Claims ledger.** The public list of every claim the project makes, each with a label that says how we know it. See [research/claims-ledger.md](../research/claims-ledger.md).

**Collusion attack.** An attack that uses many protected photos. If every photo carries the same hidden pattern, averaging the photos cancels the different picture content and keeps the pattern. The attacker then subtracts it. It does not work on a pattern that differs in every photo.

**Content credentials.** A label attached to an image that says where it came from and how it was changed. Anyone can remove the label, for example by taking a screenshot.

**Deepfake.** A fake image, video, or audio made by a computer program that looks or sounds real.

**Diffusion model.** A kind of AI program that makes or edits images by starting from noise and cleaning it up step by step.

**Embedding.** A list of numbers that a program makes from a face. Two photos of the same person should give lists that point in nearly the same direction.

**False match.** The recogniser says two photos show the same person when they do not.

**Fine-tuning.** Teaching an existing AI model more about one thing, for example the face of one person, by training it on a few extra photos.

**GPU.** A computer chip that is fast at the kind of maths AI needs. Many AI models need a strong one. Our laptop has a small one.

**Hash.** A short code made from a file. The same file always gives the same code, and the file cannot be rebuilt from the code. Take It Down uses hashes so the image itself is not sent. This is how the service describes itself.

**Inpainting.** Filling in or replacing part of a photo with new content made by a program.

**PSNR.** Peak signal to noise ratio. A score in decibels for how close two photos are. A higher number means more alike. Identical photos have no finite value.

**Perceptual budget.** How much a photo is allowed to change before a person can notice. It is a limit we set.

**Provenance.** The history of an image: where it came from and what happened to it.

**RMS.** Root mean square. The typical size of a set of changes. A pattern with an RMS of 2 changes a pixel value by about 2 on a scale of 0 to 255.

**Red team.** People, or tools, that attack a defence to find where it breaks. Ours is built before the defence, so we cannot fool ourselves. See the [test plan](research/test-plan.md).

**Robust.** Still working after some kind of change or attack. When we say a method is robust, we say which change or attack.

**SSIM.** Structural similarity. A score from 0 to 1 that compares local patterns of light and detail in two photos. 1 means identical.

**Stand-in edit.** A harmless edit used in place of a harmful one, for example changing the colour of a shirt. We never make nude or sexual images, so we measure with stand-ins.

**Survival.** In the red team, the share of a protection's own change that is still in the photo after an attack. 1 means all of it and 0 means none.

**Survival rate.** The share of a protection's effect that is left after normal photo processing, such as shrinking or compressing.

**Synthetic face.** A face made by a computer program that does not belong to a real person.

**Threat model.** A written description of who might attack, what they can do, and what we are trying to stop.

**Toy protection.** A made-up pattern we add to a photo to test the red team. It does nothing against any editing model or face matcher. We know exactly what it did, so we know what the red team should find.
