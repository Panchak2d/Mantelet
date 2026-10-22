# Changelog

Reader: someone using or following Mantelet who wants to know what changed.

Last reviewed: 22 October 2026

This file lists changes a user would notice.

## 0.0.1 (not released)

- Project started. There is no tool to use yet.
- An image toolkit and a demo script (`scripts/demo_pipeline.py`) exist for contributors. The script shrinks, crops, and compresses a photo the way a social site does. It does not protect the photo. It stops instead of overwriting a file unless you add `--force`.
- The toolkit needs Pillow 12.3 or newer. Older versions have known security bugs in how they read image files. It opens only photo formats, fills transparent areas with white, and rejects settings that used to crash Python, such as an infinite blur radius.
- Measuring tools exist for contributors: four image difference scores, a face match using OpenCV, a register of datasets with their licences, a baseline runner (`scripts/run_baseline.py`) and a report generator. A script (`scripts/fetch_models.py`) downloads the two face model files and checks them. None of this protects a photo. The tools need OpenCV, and no baseline result has been produced yet.
- The demo script has a `--mild` option for a gentler version of the processing.
- Red team tools exist for contributors: attacks that try to undo a hidden pattern in a photo, three toy protections to test them on, and a script (`scripts/run_redteam.py`) that writes a report. The toys do nothing against any model, so this protects no photo. `scripts/make_report.py` now reads both kinds of results.
- The red team can now match each attacked photo against the face in the original, and it tests how much of a protection survives the pipeline at many crop positions. It still attacks toys only. `scripts/run_redteam.py` takes `--models-dir` for the face match. `scripts/check_gpu.py` reports your graphics card and whether PyTorch can use it. An optional `ml` install pins PyTorch 2.14. The compute options page records what free and rented GPU services allow.
- The first draft of the family guide (`docs/for-families.md`) is available, explaining what to do if an image exists and linking to NCMEC Take It Down and StopNCII.org.
