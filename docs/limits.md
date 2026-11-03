# Limits

This page lists what Mantelet cannot do, what our research cannot show, and how to read our claims. It grows as we learn more. We would rather you know the limits than trust the project too much.

## Mantelet does not protect anyone yet

There is no tool. No photo has been protected. Code for a first protection exists for researchers. On 20 synthetic faces it did not pass our first test, because simple cleanup brings the face match back. The other runs check our own measuring and attack tools, on toy protections that do nothing against any model. Please do not rely on this project to keep any photo safe. If you need help now, read [Get help](get-help.md).

## If a tool exists one day, it will still have limits

- **A copy can be unprotected.** One unprotected photo of the same person is enough to get around any protection on the other photos.
- **Photos already online stay online.** A protection can only be added before a photo is shared. It cannot fix a photo that is already out there.
- **Attackers can adapt.** Earlier research reports that hidden changes to photos often stop working once someone attacks them on purpose. We do not yet know if ours will do better. We test this on purpose, and we publish the result, even if it is bad.
- **Photo processing can wash it out.** Sites and apps shrink, crop and compress photos. That may remove the hidden changes. We plan to measure how much.
- **New tools can beat old protections.** An attacker may save a photo and attack it later with a newer tool. We cannot change a photo after it is published.
- **We do not know if it works on the tools that matter.** Our tests will use open models. Closed commercial tools are out of scope unless someone shares results with us.
- **It does not remove or prove anything.** A protection does not take down an existing image. It does not show who made a fake.

## What our research cannot show

- **We cannot test on children.** The project never uses images of people under 18. Any claim about children is reasoned from tests on adults and on computer-made faces. Every document that says something about children says so.
- **We cannot test on harmful edits.** The project never makes nude or sexual images. We test with harmless stand-in edits, such as changing a shirt colour. We guess that the results carry over to harmful edits. That is a **Guess**, and every report says so.
- **We do not cover video or audio.**
- **A face model is not an editing model.** Our first protection targets a face recognition model. Even a good result there says nothing about editing.
- **Visibility is not measured yet.** The human study that decides whether people can see a change has not run. Until it does, no result can be a full pass.

## What this project is not

- It is not legal advice. Laws differ by country and change. The [help guide](get-help.md) gives its sources and what it could not confirm.
- It is not a replacement for taking down images, reporting them or talking to a trusted adult.
- It is not a detector. It does not tell you whether a photo is fake.

## How to read our claims

Each public claim is listed in the [claims ledger](../research/claims-ledger.md) with one label:

- **Measured:** we ran it and the results are in the repository.
- **Reported:** a paper says so and we have not repeated it.
- **Guess:** our own idea, not tested.

The Measured claims use toy protections, made-up photos, or 20 synthetic faces with one face model and the first protection. None shows that a protection works. See [results](research/results.md).

If a research gate fails, we say so on the front page and move our effort to the guides.
