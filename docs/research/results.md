# Results

This page holds the measured results of Mantelet. It says what has been measured, what each result does and does not show, and which results are still missing. No protection has been tested on real faces yet, so there is no result on a real protection here.

## Status

| Result | State |
|---|---|
| Measuring tools and red team attacks tested on toy protections | Measured. Shown below |
| Baseline on synthetic faces | Not published. Waits for the owner's run |
| First protection on real faces (Gate 1) | Not run |
| Human perception study | Not started |
| Real editing pipeline (Gate 2) | Not started |
| Attacker levels and transfer to other models (Gate 3) | Not started |

## What has been measured

Three claims in the [claims ledger](../../research/claims-ledger.md) are Measured: C-031, C-034 and C-035. All use made-up photos, or 20 Face Synthetics photos, with toy protections. A toy protection adds a hidden pattern that does nothing against any editing model or face matcher. Toys exist so that we know the right answer and can check that the red team finds a planted weakness without breaking a sound control.

| Claim | Result | Data |
|---|---|---|
| C-031 | On made-up test photos, cleanup filters remove most of the fine toy grain at acceptable quality. The collusion attack removes a toy pattern shared by every photo and leaves one that differs per photo | Made-up photos, repeatable tests |
| C-034 | On 20 Face Synthetics photos, the red team found the planted weakness and did not break the control. No photo was left out for any toy | 20 photos, seed 0 |
| C-035 | A smooth toy pattern keeps at least 80 percent survival through the fixed pipeline at every tested crop corner. Fine toy grain keeps under 20 percent at every corner | Made-up 512 pixel photos |

### Figure: toy survival after attack

![Bar chart of mean survival after attack for four toy cases, with the 50 percent pass number marked](figures/toy-survival.svg)

*Mean survival of the toy pattern after the red team attacks, over 20 Face Synthetics photos. Survival is 1 when nothing was removed and 0 when all of it was. The dashed line is the 50 percent pass number from the [test plan](test-plan.md). The values are the means in claim C-034. These are toy protections that do nothing against any model. This figure checks our measuring and attack tools. It is not a Mantelet protection result and says nothing about whether a real protection works.*

How to read it:

- Fine random grain is almost fully removed by cleanup filters (mean survival 0.056). This is the planted weak toy, and the tools found it.
- A pattern shared by every photo is removed by the collusion attack (0.009). This is the planted design flaw, and the tools found it.
- A pattern that differs in every photo survives the collusion attack (0.963). This is the sound control, and the tools did not break it.
- The same per-photo pattern drops to a mean of 0.465 under non-local means denoising. 6 of the 20 photos stay at 50 percent or more.

The figure shows means only. The ledger holds means and not the per-photo values, so the figure cannot show spread or error bars. We have not published per-photo data for this run.

## What these results do not show

- They say nothing about a real protection, a face model or an editing model.
- The quality floor behind them (PSNR of at least 30 dB and SSIM of at least 0.90) is a Guess.
- They are about 20 synthetic faces. They are not about real people, and never about children.

## Results we will add

This page grows when data exists. The rule is fixed here so that we cannot choose figures after seeing results.

| When this exists | Figures we will generate from the run's CSV files | Where they go |
|---|---|---|
| Baseline on synthetic faces | Face match rate per baseline condition with 95 percent Wilson intervals | This page |
| Gate 1 run | Per-photo survival, PSNR, SSIM and face match, as distributions with error bars. The budget sweep. Pipeline survival at the centre crop and at other crop corners. The three states of a protected photo: match, found but no match, lost | This page |
| Human perception study | Share who notice the change, per budget, with intervals | This page |
| Gate 2 run | Attacker success rate before and after JPEG and resize, with intervals | This page |
| Gate 3 run | Attacker success rate by attacker level, and transfer to other models, with intervals | This page |

Figures are drawn by our own code as SVG, with no plotting library. Each figure states the data it came from, the seed and the number of photos. A failure is plotted the same way as a pass.

## How to repeat a result

The red team run is `scripts/run_redteam.py`. See [Setup](../development/setup.md). The toy figure is made by `scripts/make_toy_figure.py`.
