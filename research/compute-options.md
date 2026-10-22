# Compute options

Reader: the project owner and any contributor who plans a step that needs a GPU, and a researcher who wants to know where the experiments ran and under which terms.

Last reviewed: 22 October 2026

Steps 9 to 12 run diffusion editing models. The owner's laptop has an NVIDIA MX330 with about 2 GB of video memory, which cannot realistically run them (claim C-005). Those steps need an outside GPU: a free notebook service or a rented machine. This page records what each option allows, as far as we could read it. Terms change, so every row has a read date. Read the current terms again before the first run on a service.

What we run on a GPU: protections tuned against open models, and harmless stand-in edits such as a recoloured shirt or a filled background patch. We never create nude or sexual images ([SAFETY.md](../SAFETY.md) rule 1). Some services ban "deepfakes" or adult content without defining the word. Our work is closer to defence research than to making fakes, but a service that scans for patterns could still flag a notebook that runs an image editing model. Whether a service would object is **Guess**. Where the terms are unclear, ask the service first or choose another one.

## Free notebook services

| Service | What it gives | Limits we read | Restrictions that matter for us | Read |
|---|---|---|---|---|
| Google Colab, free tier | A hosted notebook with a GPU that varies over time | Google does not publish usage limits. Free notebooks run at most 12 hours, depending on availability. Idle notebooks time out | The FAQ disallows "creating deepfakes" on every managed runtime. It also disallows file hosting, proxies and several other uses. On the free tier it disallows remote control and running a web interface instead of the notebook | 22 October 2026, from the official FAQ |
| Kaggle Notebooks | A hosted notebook with one P100 or two T4 GPUs | About 30 GPU hours a week, which can change. Sessions run up to 12 hours. Phone verification is needed to switch on a GPU | We did not read the Kaggle terms of use themselves. The numbers come from pages that quote the Kaggle documentation | 22 October 2026, secondary sources |

Two points about the table:

- The Colab ban on "creating deepfakes" is the main risk for our later steps. A notebook that runs an image editing model on faces, even for a harmless stand-in edit, is close enough to the banned category that Google could end the session or limit the account. We cannot tell from the FAQ where Google draws the line. Do not run edits of face photos on Colab without asking Google first. Running only the protection code and the face matcher there is much further from the ban.
- The Kaggle P100 is a Pascal card (compute capability 6.0). PyTorch builds for CUDA 12.8 and newer do not include it. Kaggle supplies its own PyTorch, so check `torch.cuda.get_arch_list()` in the first cell of any notebook, or run `scripts/check_gpu.py`.

## Rented GPUs

| Service | What it gives | Restrictions we read | Read |
|---|---|---|---|
| RunPod | Rented GPU machines billed by time | The terms of service were last updated on 24 March 2026. A page that tracks them quotes a list of unauthorised content that includes "pornography or graphic adult content". We read the start of the terms on the RunPod site and not the full text. Our runs contain no such content | 22 October 2026, partly secondary |
| Vast.ai | A market where independent providers rent out machines | The terms describe renting machines from independent providers. We read only the opening paragraph, so we do not know the acceptable use rules. A provider owns the machine, so a provider's own rules may add to the terms | 22 October 2026, opening paragraph only |

Not read: Lightning AI, Paperspace, Modal, Hugging Face Spaces and the big cloud providers. Add a row when one of them is looked at.

## What we decided

- Plan on a rented machine for steps 9 to 12. It gives a card with enough memory and a quota we control, and Colab names deepfakes in its ban. We have not shown that a rental service is safer on content, because we read little of their terms. Read the full terms of the chosen service before the first run and add what they say to this page.
- Use a free notebook only for work that does not edit faces: the face matcher, the pipeline, the red team filters and the protection tuning. Check its terms again first.
- Keep every run to approved datasets and harmless stand-in edits, as everywhere else in the project.
- The results of a run on someone else's machine go into the claims ledger with the service named, the card and the library versions, because a result we cannot repeat is not Measured.

## What the laptop can still do

The laptop runs everything up to and including step 8 on the CPU, and the first protection experiments too, because a small face model fits in ordinary memory. See [Setup](../docs/development/setup.md) for the PyTorch install and the driver note for the MX330.

## Sources

- Google Colab FAQ, "Which activities are restricted in Colab?" (research.google.com/colaboratory/faq.html), read 22 October 2026. Primary.
- Kaggle documentation pages on notebooks and efficient GPU use (kaggle.com/docs/notebooks, kaggle.com/docs/efficient-gpu-usage). Not opened directly. Quoted by third party summaries, read 22 October 2026.
- RunPod terms of service (runpod.io/terms), last updated 24 March 2026. First paragraphs read. The list of unauthorised content comes from a terms tracking site.
- Vast.ai terms of use (vast.ai/terms). First paragraphs read.
