# Learning folder

Reader: the project owner, and any beginner who wants to practise alongside the project.

Last reviewed: 5 October 2026

This folder holds the small tasks you write yourself. Each step has one task. The code here is practice. It is not part of the main package until it has been reviewed and moved.

## How it works

1. Do the homework for the step. The list is in [the Python path](../docs/learning/python-path.md).
2. Write the task in your own words and your own code.
3. Save it in this folder.
4. At the start of the next step, it gets reviewed.

## Task for later: add a banned phrase

You need to understand strings, lists, and reading code to do this.

1. Open `scripts/check_docs.py` and find where `BANNED_PHRASES` is defined.
2. Add the word `"utilization"` to the list. (It is missing, though the verb form is there).
3. Open `tests/test_check_docs.py`. Find the test that checks for banned phrases.
4. Add a test case that checks your new word is caught.
5. Run `pytest` to prove your test fails if you remove the word from the list, and passes when it is there.
6. Create `step-02-notes.md` in this folder. Write down any errors you hit while writing the test and how you fixed them.
