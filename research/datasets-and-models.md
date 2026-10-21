# Datasets and models

Reader: a researcher or contributor who wants to know which data and models we may use, under which licence, and what we do not know about them.

Last reviewed: 9 October 2026

[SAFETY.md](../SAFETY.md) rule 4 says every dataset and model has its licence recorded before anyone uses it. This page is that record. The code enforces it: an experiment only runs on a dataset that is in `src/mantelet/datasets.py` with the status `approved`. Nothing listed here is stored in the repository. Datasets go in a `data/` folder and model files go in `data/models/`. Git ignores both.

## What a dataset must pass

1. **No real person.** The faces are made by a computer, not photographed.
2. **A licence that allows our use.** We use the data only to measure, and we publish numbers, never images.
3. **Faces that look like adults.** [SAFETY.md](../SAFETY.md) rule 2 forbids images of people under 18. A computer-made face is not a person, but we treat a face that looks like a child as if it were one. The basis for believing the faces look adult must be written down. If the publisher says nothing, the dataset stays at `needs review`.
4. **Faces framed with some background.** The face detector needs room around the face. Tight 112 pixel crops may not be found.

Passing is a human decision. To approve a dataset, the owner looks through a sample of it, writes the basis and the date in the Notes column below, and changes the status in `src/mantelet/datasets.py` to `approved`. The test suite fails if this page and the register disagree.

## Datasets

| Id | Dataset | Licence | Status | Adult basis | Notes |
|---|---|---|---|---|---|
| `facesynthetics` | [Face Synthetics](https://github.com/microsoft/FaceSynthetics), Microsoft. 100,000 rendered portraits, 512 by 512 pixels. A sample of 100 images (34 MB) is a separate download | [Research Use of Data Agreement v1.0](https://github.com/microsoft/FaceSynthetics/blob/main/LICENSE.txt), non-commercial research | approved | Reviewed all 100 sample images on 2026-10-21. All faces look adult | First choice. The portraits are centred and have background. Use the sample zip. The zip also holds segmentation images and landmark files, which the loader skips |
| `digiface1m` | [DigiFace-1M](https://github.com/microsoft/DigiFace1M), Microsoft. 1.22 million rendered face crops of 112 pixels | [Research Use of Data Agreement v1.0](https://github.com/microsoft/DigiFace1M/blob/main/LICENSE), non-commercial research | needs review | Not documented by the publisher | Each download part is several gigabytes. The crops are tight, so the detector may not find faces in them. Use Face Synthetics first |

Two points about the licence apply to both datasets:

- The agreement allows non-commercial research only. It counts anything developed from the data, including a trained model, as a Result that may not be used in a commercial offering. Our code is Apache-2.0. A protection model trained on these images in a later step would carry the non-commercial limit. We decide that before any such training (claim C-026).
- Measuring on the data and publishing numbers about it is research use. Redistributing images is not part of our plan.

Other synthetic face sets exist. We have not checked their licences, so they are not listed.

## Models

The face detector and recogniser are ONNX files from the [OpenCV Zoo](https://github.com/opencv/opencv_zoo), fetched at one pinned commit by `scripts/fetch_models.py` and checked against a pinned size and SHA-256 hash. The code refuses to load a file that does not match.

| Model | File | Licence of the file | What it was trained on |
|---|---|---|---|
| YuNet, face detector | `face_detection_yunet_2023mar.onnx` | MIT | The Zoo page names the WIDER Face validation set for its accuracy figures. It does not state the training data. We did not check the WIDER Face terms |
| SFace, face recogniser | `face_recognition_sface_2021dec.onnx` | Apache-2.0 | Not stated. The paper reports models trained on CASIA-WebFace, VGGFace2 and MS-Celeb-1M, which are collections of photos of real people gathered from the web. We do not know which one this file used |

The licence of a file does not settle where its training photos came from. Face recognition models of this quality are almost all trained on photos of real people who did not agree to it. We use the model only to measure and never to identify anyone. We have not found a strong open face recogniser trained on consented or synthetic data only. If you know one, open an issue (claim C-023).

The match rule is a cosine similarity of at least 0.363, the value published by the SFace authors in the Zoo code. It was set on photos of real people, so it may not suit synthetic faces (claim C-022).

## Software we depend on for this

OpenCV runs both models. We pin `opencv-python-headless` to the 4.x series. Version 5.0.0.93 exists on PyPI. The Zoo notes that the OpenCV 5 engine treats the fixed-size detector file differently, and we have not tested it. Moving to version 5 is a deliberate change that needs a new check.
