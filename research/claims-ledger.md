# Claims ledger

Reader: a researcher, reviewer, or reader who wants to check how we know what we say.

Last reviewed: 5 October 2026

Every public claim in this project is listed here. Each has one label:

- **Measured:** we ran it, the results are in the repository, and they can be repeated.
- **Reported:** a paper or an official source says so, and we have not repeated it.
- **Guess:** our own idea, not tested.

No claim is Measured yet. Nothing has been run.

| ID | Claim | Label | Source or note |
|---|---|---|---|
| C-001 | Simple tricks that hide changes in a photo tend to stop working once someone attacks them on purpose | Reported | Honig, Rando, Carlini, Tramer, arXiv 2406.12027. Listed in the plan as checked to exist. We have not repeated the work |
| C-002 | Results on harmless stand-in edits carry over to harmful edits | Guess | Our own assumption. Every report must say so |
| C-003 | NCMEC runs Take It Down for images of people under 18, and it works with a hash so the image itself is not sent | Reported | NCMEC pages at missingkids.org, read 5 October 2026 |
| C-004 | NVIDIA Pascal cards (such as the MX330) are not supported by PyTorch CUDA 12.8 and newer builds. Version 2.14 is the last with CUDA 12.x builds | Reported | PyTorch developer forum posts by PyTorch maintainers, read 5 October 2026. Recheck |
| C-005 | The MX330 has about 2 GB of video memory, which is too small for the image editing models planned for later steps | Guess | Spec sheets confirm the memory size. The conclusion about the models is our reasoning and is checked |
| C-006 | Mantelet protects photos from being misused | Not claimed | We make no such claim. See [Limits](../docs/limits.md) |
| C-007 | The Belmont Report exists and establishes three principles for research ethics: respect for persons, beneficence, and justice | Reported | US Department of Health and Human Services Office for Human Research Protections, read 5 October 2026 |
| C-008 | NCMEC's Take It Down service works with a hash so the image itself is not sent | Reported | NCMEC pages at missingkids.org, confirmed 5 October 2026 |
| C-009 | StopNCII.org exists and is for images of adults | Reported | StopNCII.org website, confirmed 5 October 2026 |
| C-010 | The C2PA specification and Content Authenticity Initiative state that content credentials can be stripped | Reported | C2PA.org and contentauthenticity.org, read 5 October 2026 |
| C-011 | Statistics Done Wrong is free at statisticsdonewrong.com | Reported | Website confirmed 5 October 2026 |
| C-012 | Khan Academy has a free statistics course | Reported | Website confirmed 5 October 2026 |
| C-013 | A 25 percent noticeable change rate in a 2AFC test represents volunteers guessing, not seeing the change | Guess | Our reasoning from perceptual test conventions. Not yet validated by our own study |
| C-014 | A 50 percentage point drop in attacker success is a meaningful deterrent to casual attackers | Guess | Our reasoning from the Honig et al. results. Literature shows smaller drops are often undone by adaptive attacks |
| C-015 | A 50 percent survival rate after platform processing is the minimum for practical use | Guess | Our reasoning. If protection washes out below half, it is not useful in practice |
