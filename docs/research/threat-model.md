# Threat model

Reader: a researcher or contributor who wants to know who we defend against and what we try to stop.

Last reviewed: Batch 2, 5 October 2026

This page writes down who might attack, what they can do, and what we are trying to stop. The research plan in [PLAN.md](../../PLAN.md) section 9 fixes the threats and the attacker levels. This page explains them in full.

## What we try to stop

| Code | Threat | Priority |
|---|---|---|
| T1 | One photo goes into an editing or inpainting tool built on open models | First |
| T2 | A model is fine-tuned on a handful of photos of one person | Second |
| T3 | A face recognition system is trained on scraped photos | Last, only if time allows |

T1 is first because it is the easiest attack for an ordinary person to run today. Open editing models are free to download and need only one photo.

T2 is second because it needs a handful of photos of one person and a small amount of extra training. It is a real attack, but it takes more work than T1.

T3 is last because face recognition systems are trained on large scraped datasets, not on a few photos of one person. We list it because a protection that stops editing might also stop recognition, but we do not depend on that.

## Out of scope

We do not test:

- Video or audio.
- Closed commercial models, unless someone shares results with us.
- Anything that needs us to create nude or sexual images, even for testing.

See [SAFETY.md](../../SAFETY.md) for the hard rules.

## Harmless stand-in edits

We never create nude or sexual images, so we measure whether a protection works using a stand-in edit. Examples:

- Recolour a shirt.
- Replace a masked background patch with new content.
- Change a hairstyle on a synthetic adult face.

We then measure two things: did the edit succeed, and is the person still recognisable. If the protection works on the stand-in edit, we say so. The assumption that the result carries over to a harmful edit is a **Guess**, and every report says so. See claim C-002 in the [claims ledger](../../research/claims-ledger.md).

## What "working" means

For T1 and T2, a protection works when the edit fails or the person is no longer recognisable. We measure both:

- **Edit success rate**: how often the edit still produces a usable image.
- **Face match rate**: how often a face matcher still identifies the person after the edit.

A protection counts as working only if the edit success rate drops by at least the fixed amount, and the face match rate does not stay high. The exact numbers are in the [test plan](test-plan.md).

## Attacker levels

We test against attackers who know different amounts. A published photo cannot be changed afterwards, so the higher levels matter most.

| Level | What the attacker knows | What they can do | Example |
|---|---|---|---|
| 0 | Nothing | Runs a normal edit tool on the photo | Someone pastes a photo into a free app |
| 1 | Knows Mantelet exists | Adds a step that might remove a known kind of protection | Runs a basic cleanup filter they heard about |
| 2 | Knows the general method | Tries the standard attacks on that kind of protection | Tries the attacks named in the papers we read |
| 3 | Has our code | Runs our own red team tools on the photo | Uses the tools we build in Batch 5 |
| 4 | Builds an attack specifically against Mantelet | Designs a new attack aimed at our method | Tunes an attack to our exact protection |
| 5 | Saved our photos and attacks later with newer models | Waits for a stronger model, then attacks | Keeps the photo, attacks it next year |

Level 5 is the hardest and the most important. A photo that is already online cannot be reprotected when a new tool comes out. If a protection only works against level 0, it gives a false sense of safety.

## What we are not modelling

We are not modelling a determined human adversary with unlimited time and compute. We model the open model pipeline that an ordinary person can run. A nation state or a well funded research lab can likely break any protection we build. We say so plainly.

We are also not modelling the case where the attacker already has many photos of the person from before any protection was added. One unprotected photo defeats the protection. See [Limits](../limits.md).

## How this maps to the batches

| Batch | What it does for the threat model |
|---|---|
| 2 | This page and the [test plan](test-plan.md) are written |
| 3 | The image toolkit builds the transformations platforms apply |
| 4 | The first baseline measures edit success and face match on synthetic faces |
| 5 | The red team builds the attack tools for levels 2 and 3 |
| 6 | First protection experiments and **Gate 1** |
| 12 | Attacker levels 0 to 5 tested and **Gate 3** |
