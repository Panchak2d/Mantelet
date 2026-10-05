# Glossary

Reader: anyone who meets a technical word in these documents and wants a plain meaning.

Last reviewed: 5 October 2026

Words are listed in alphabetical order. We add a word the first time a document uses it.

**Adversarial perturbation.** A tiny change to a photo that people cannot see but that confuses a computer program. The word "perturbation" just means "small change".

**Attacker success rate.** How often an attack still works. For example, how often a face match still succeeds after we protect a photo. A lower number is better for the defender.

**Claims ledger.** The public list of every claim the project makes, each with a label that says how we know it. See [research/claims-ledger.md](../research/claims-ledger.md).

**Content credentials.** A label attached to an image that says where it came from and how it was changed. Anyone can remove the label, for example by taking a screenshot.

**Deepfake.** A fake image, video, or audio made by a computer program that looks or sounds real.

**Diffusion model.** A kind of AI program that makes or edits images by starting from noise and cleaning it up step by step.

**Fine-tuning.** Teaching an existing AI model more about one thing, for example the face of one person, by training it on a few extra photos.

**GPU.** A computer chip that is fast at the kind of maths AI needs. Many AI models need a strong one. Our laptop has a small one.

**Hash.** A short code made from a file. The same file always gives the same code, and the file cannot be rebuilt from the code. Take It Down uses hashes so the image itself is not sent. This is how the service describes itself.

**Inpainting.** Filling in or replacing part of a photo with new content made by a program.

**Perceptual budget.** How much a photo is allowed to change before a person can notice. It is a limit we set.

**Provenance.** The history of an image: where it came from and what happened to it.

**Red team.** People who attack a defence to find where it breaks. Ours is built before the defence, so we cannot fool ourselves.

**Robust.** Still working after some kind of change or attack. When we say a method is robust, we say which change or attack.

**Stand-in edit.** A harmless edit used in place of a harmful one, for example changing the colour of a shirt. We never make nude or sexual images, so we measure with stand-ins.

**Survival rate.** The share of a protection's effect that is left after normal photo processing, such as shrinking or compressing.

**Synthetic face.** A face made by a computer program that does not belong to a real person.

**Threat model.** A written description of who might attack, what they can do, and what we are trying to stop.
