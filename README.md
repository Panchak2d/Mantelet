# Mantelet

**An open research project on making it much harder to turn an ordinary photo of a woman or a child into a fake nude image.**

> **Mantelet does not protect anyone yet.** There is no tool to download or use. The first protection did not pass its first test, on 20 synthetic faces. A photo that has been through a future version could still be misused, and one unprotected photo of the same person could defeat it. Please do not rely on this project to keep any photo safe. If you need help now, read [Get help](docs/get-help.md).

## Abstract

Programs that make fake nude images of real people need one photo of the target. One line of research tries to add changes to a photo that people cannot see, so that an editing program fails or produces a broken result. Earlier studies report that such changes often stop working when someone attacks them on purpose, or after ordinary steps such as resizing and JPEG compression. We do not know whether a protection of this kind can work well enough to matter.

Mantelet tests this question in the open. We build the measuring tools and the attacks first, fix the pass and fail numbers before any experiment, and publish every result, including failures. In parallel we maintain a practical [guide for people who have been targeted](docs/get-help.md), which does not depend on the research succeeding.

## Problem statement

Fake nude images made from ordinary photos harm real people. Surveys and hotline data show the problem is large and growing, but each number measures something different and none gives a clean count of victims. The [background page](docs/background.md) lists the figures we can verify, what each one measures, and what they cannot tell us.

Today's routes help after an image exists: takedown services, platform reports and the law. None stops a fake from being made. A technique that raised the cost of making one would complement them. Whether such a technique exists is the open question.

## Objectives

1. Find out, with public and repeatable measurements, whether hidden changes to a photo can stop or damage a fake-image edit while staying invisible to people.
2. Measure how that effect holds up against the processing real sites apply and against attackers who know the method.
3. Publish what we find, including a negative result, with every claim labelled by how we know it.
4. Give people who have been targeted clear, sourced steps they can use today.

## Research questions

1. How much can a photo change before a person notices?
2. Does a change that small stop an edit from working?
3. Does it still work after JPEG, resizing, cropping and blur?
4. Does it work on a different model than the one we tuned it on?
5. Does it work on a model released later?
6. What happens when the attacker knows about Mantelet?
7. Can we make it work without a long calculation for every photo?

## Approach

- **Measure before we build.** The image toolkit, the difference scores, the face-match measure and the red team attacks exist before any real protection. They are tested on toy protections that do nothing against any model, so we know the right answer.
- **Fix the numbers in advance.** The [test plan](docs/research/test-plan.md) sets thresholds for visibility, effect and survival before any result. We do not move them after we see results.
- **Judge by the worst case.** For each photo the attacker keeps the best result. We do not average away a working attack.
- **Use harmless stand-in edits.** We never make nude or sexual images. We test with edits such as changing a shirt colour and assume the results carry over. That assumption is a Guess, and every report says so.
- **Label every claim.** The [claims ledger](research/claims-ledger.md) marks each public claim Measured, Reported or Guess.

See the [research overview](docs/research/README.md), the [threat model](docs/research/threat-model.md) and [how it works](docs/how-it-works.md).

## Current status

| Part | State |
|---|---|
| Image toolkit, difference scores, face match, baseline runner, report generator | Built and tested on made-up images |
| Red team attacks and toy protections | Built. Run on 20 synthetic faces with toy protections only |
| First protection (projected gradient descent against an open face model) | Built and run on 20 synthetic faces. Did not pass Gate 1 |
| Gate 1 report | Done on 20 synthetic faces, not passed. The next step is the owner's decision. See [results](docs/research/results.md) |
| Human perception study | Not started |
| Help guide | Published, with a sources table |

The Measured claims show our measuring tools work and how the first protection did on 20 synthetic faces. They do not show that any protection works. See [results](docs/research/results.md).

## Expected outcomes

We would count any of these as a result:

- **A protection passes its gate.** It reaches the fixed effect, visibility and survival numbers against the attacker levels tested. We would then report the limits and test it on more models.
- **A protection fails.** It is removed by a basic attacker, or it does not survive resizing and JPEG. We publish the failure with the data. This matches what earlier research led us to expect.
- **Mixed result.** It works against some attackers and not others. We publish where the line is.

A negative result is a result. It tells parents and schools not to rely on this kind of protection, and it sends effort to the routes that work today. If a gate fails, we say so on this page.

## Limitations

- Tests use open models. Closed commercial tools are out of scope unless someone shares results.
- We never test on images of children. Claims about children are reasoned from adults and synthetic faces.
- We do not cover video or audio.
- A photo already online cannot be changed afterwards.
- Face recognition models are not editing models. A result on one says nothing about the other.

The full list is on the [Limits](docs/limits.md) page.

## Ethics and safety

The hard rules are in [SAFETY.md](SAFETY.md). This project never makes sexual or nude images of anyone. It never uses images of children. It never uses real people without written consent. The [data and ethics policy](docs/research/data-and-ethics.md) turns these into rules for data.

## Roadmap

Gate 1 asks whether a protection on a small model survives the red team within the visibility limit. Gate 2 asks whether it works on a real editing pipeline after JPEG and resize. Gate 3 asks whether it survives attacker levels 0 to 4 and transfers to another model. Provenance work and a policy brief follow, then a full report. A "no" at a gate moves our effort to the guides. When data from Gates 1 to 3 exists, we publish per-photo results in [results](docs/research/results.md).

## Where to start

- **You were targeted, or you care for someone who was:** [Get help](docs/get-help.md).
- **You want the facts and numbers:** [Background](docs/background.md).
- **You want to know what this cannot do:** [Limits](docs/limits.md).
- **You are a researcher:** [Research overview](docs/research/README.md) and the [claims ledger](research/claims-ledger.md).
- **You want to help with code:** [Contributing](CONTRIBUTING.md) and [Setup](docs/development/setup.md).
- **All pages:** [Documentation index](docs/index.md).

## How to cite

Cite the repository and the exact commit you used. Cite a claim by its ledger number, for example "C-034 in the Mantelet claims ledger". We have not released a versioned citation yet.

## The name

A mantelet is a short cloak. It is also a portable shield. The name says what we hope to build, and does not claim we have built it.

## Licences

The code is under the Apache License 2.0 (see [LICENSE](LICENSE)). The documents are under CC BY 4.0 (see [LICENSE-docs.md](LICENSE-docs.md)).

## Contact

Security problems: see [SECURITY.md](SECURITY.md). Conduct concerns: see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
