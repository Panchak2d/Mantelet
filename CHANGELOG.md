# Changelog

Reader: someone using or following Mantelet who wants to know what changed.

Last reviewed: 8 October 2026

This file lists changes a user would notice.

## 0.0.1 (not released)

- Project started. There is no tool to use yet.
- An image toolkit and a demo script (`scripts/demo_pipeline.py`) exist for contributors. The script shrinks, crops, and compresses a photo the way a social site does. It does not protect the photo. It stops instead of overwriting a file unless you add `--force`.
- The toolkit needs Pillow 12.3 or newer. Older versions have known security bugs in how they read image files. It opens only photo formats, fills transparent areas with white, and rejects settings that used to crash Python, such as an infinite blur radius.
- The first draft of the family guide (`docs/for-families.md`) is available, explaining what to do if an image exists and linking to NCMEC Take It Down and StopNCII.org.
