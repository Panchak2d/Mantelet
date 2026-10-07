# Claims ledger

Reader: a researcher, reviewer, or reader who wants to check how we know what we say.

Last reviewed: 8 October 2026

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
| C-016 | Facebook recompresses uploaded JPEG photos at quality factors of roughly 61 to 92, depending on the study. Twitter recompresses at 85 only when the upload is 85 or higher | Reported | arXiv 2504.20658 (TrueFake), arXiv 1810.02062, arXiv 1806.03787. Values differ between studies and change over time. Official platform documents not found. Read 8 October 2026 |
| C-017 | Sites shrink a photo only above a size limit. Reported limits: Instagram 1080, WhatsApp 1600, Facebook 960 or 2048 (2016) and 720 wide (2025), Twitter or X 2048 (2016) and 1200 wide (2025) | Reported | arXiv 1610.06347 (2016), arXiv 2504.20658 (2025). The two studies disagree for Facebook and X, so platforms change. Official platform documents not found. Read 8 October 2026 |
| C-018 | Common image editing models work at about 512 pixels, so an attacker may shrink a photo to that size before editing | Guess | Our prior knowledge, not searched. Check before Batch 6 |
| C-019 | Social sites crop uploaded photos by 20 percent from the centre | Not claimed | No source found. Instagram only limits the shape of the photo. The 80 percent crop is our own choice |
| C-020 | Protective perturbations often fail under ordinary transformations such as JPEG and blur, and optimising against random transformations (EOT) helps little at medium strength. Several transformations in a row can fail where one alone does not | Reported | Zhao et al., CVPR 2024, arXiv 2312.00084. arXiv 2604.23688. arXiv 2512.07228 reports that uniform sampling of transformations is suboptimal. We found no paper that tests crop position on its own. Read 8 October 2026 |
| C-021 | Where a crop starts, compared with the 8 pixel grid used by JPEG and by image models, changes whether a protection survives | Guess | Our reasoning. The fixed pipeline always starts its crop 3 pixels off the 8 pixel grid on the long side, so it tests one case only. A related result for patch-based vision models is in arXiv 2510.13643. Test before Gate 1 |
