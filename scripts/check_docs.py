"""Check the Markdown documents in this repository against the project's writing rules.

Run it from the top folder of the repository:

    python scripts/check_docs.py

It prints one line for each problem and exits with code 1 if it found any.
Each check below takes the text of one file and returns a list of problems.
A problem is a pair: (line number, message).
"""

import re
import sys
from pathlib import Path

CURRENT_BATCH = 2
MAX_BATCHES_BEHIND = 3
MAX_READING_GRADE = 8.0

FAMILY_PAGES = {"README.md", "docs/start-here.md", "docs/for-families.md"}
SKIPPED_FOLDERS = {".git", ".venv", ".pytest_cache", ".ruff_cache", "node_modules"}
FILES_THAT_MAY_LIST_BANNED_PHRASES = {
    "PLAN.md",
    "docs/development/style-guide.md",
    "research/bibliography.md",
}

DASHES = {"\u2014": "long dash", "\u2013": "en dash"}

BANNED_PHRASES = [
    "delve", "delves", "delving",
    "leverage", "leverages", "leveraging",
    "utilize", "utilizes", "utilizing",
    "seamless", "seamlessly",
    "crucial", "pivotal",
    "landscape", "landscapes",
    "tapestry", "testament",
    "it is important to note",
    "in today's world",
]
NOT_JUST_BUT_PATTERN = re.compile(r"\bnot just\b[^.!?]{1,80}\bbut\b", re.IGNORECASE)

# Each pair is the first and last character code of a block of symbols.
EMOJI_RANGES = [
    (0x1F000, 0x1FAFF),
    (0x2600, 0x27BF),
    (0x2B00, 0x2BFF),
    (0x200D, 0x200D),
    (0xFE0F, 0xFE0F),
]

LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
REVIEWED_PATTERN = re.compile(r"^Last reviewed: Batch (\d+), \d{1,2} [A-Za-z]+ \d{4}$")


def find_markdown_files(root):
    files = []
    for path in sorted(root.rglob("*.md")):
        folders = path.relative_to(root).parts
        if any(folder in SKIPPED_FOLDERS for folder in folders):
            continue
        files.append(path)
    return files


def prose_lines(text):
    """Return (line number, line) for every line that is not inside a code block."""
    lines = []
    inside_code_block = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith("```"):
            inside_code_block = not inside_code_block
            continue
        if not inside_code_block:
            lines.append((number, line))
    return lines


def needs_header(relative_path):
    """Practice notes in learning/ and the GitHub templates do not need a header."""
    if relative_path.startswith(".github/"):
        return False
    if relative_path.startswith("learning/") and relative_path != "learning/README.md":
        return False
    return True


def check_dashes(text):
    problems = []
    for number, line in prose_lines(text):
        for dash, name in DASHES.items():
            if dash in line:
                problems.append((number, f"{name} found. Use a full stop, comma, colon or 'and'"))
    return problems


def check_banned_phrases(text):
    problems = []
    for number, line in prose_lines(text):
        lowered = line.lower().replace("\u2019", "'")
        for phrase in BANNED_PHRASES:
            if re.search(r"\b" + re.escape(phrase) + r"\b", lowered):
                problems.append((number, f"banned phrase: '{phrase}'"))
        if NOT_JUST_BUT_PATTERN.search(lowered):
            problems.append((number, "banned pattern: 'not just X, but Y'"))
    return problems


def is_emoji(character):
    code = ord(character)
    for first, last in EMOJI_RANGES:
        if first <= code <= last:
            return True
    return False


def check_emoji(text):
    problems = []
    for number, line in prose_lines(text):
        for character in line:
            if is_emoji(character):
                problems.append((number, f"emoji or symbol found: U+{ord(character):04X}"))
                break
    return problems


def check_links(text, file_path, root):
    problems = []
    for number, line in prose_lines(text):
        for target in LINK_PATTERN.findall(line):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#")[0]
            if target.startswith("/"):
                destination = root / target.lstrip("/")
            else:
                destination = file_path.parent / target
            if not destination.exists():
                problems.append((number, f"broken link: {target}"))
    return problems


def check_header(text):
    problems = []
    top_lines = text.splitlines()[:12]
    if not any(line.startswith("Reader:") for line in top_lines):
        problems.append((1, "no 'Reader:' line in the first 12 lines"))

    reviewed_batch = None
    for line in top_lines:
        match = REVIEWED_PATTERN.match(line)
        if match:
            reviewed_batch = int(match.group(1))
    if reviewed_batch is None:
        problems.append((1, "no 'Last reviewed: Batch N, D Month YYYY' line in the first 12 lines"))
    elif reviewed_batch > CURRENT_BATCH:
        problems.append((1, f"last reviewed in Batch {reviewed_batch}, which has not happened yet"))
    elif CURRENT_BATCH - reviewed_batch > MAX_BATCHES_BEHIND:
        problems.append((1, f"last reviewed in Batch {reviewed_batch}. Review it again"))
    return problems


def count_syllables(word):
    """Estimate syllables by counting groups of vowels. It is rough, not exact."""
    word = word.lower()
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and not word.endswith("le") and count > 1:
        count -= 1
    return max(count, 1)


def plain_sentences_text(text):
    """Strip Markdown so that only the sentences a reader would read are left."""
    pieces = []
    for _, line in prose_lines(text):
        line = line.strip()
        if not line or line.startswith(("#", "|", "<!--", "Reader:", "Last reviewed:")):
            continue
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = line.replace("`", "").replace("*", "")
        line = re.sub(r"^(>|-|\d+\.)\s*", "", line).strip()
        line = re.sub(r"^\[[ xX]\]\s*", "", line)
        if line and line[-1] not in ".!?":
            line += "."
        if line:
            pieces.append(line)
    return " ".join(pieces)


def reading_grade(text):
    """Flesch-Kincaid grade level. Returns None if the text has no sentences."""
    plain = plain_sentences_text(text)
    sentences = [s for s in re.split(r"[.!?]+(?:\s|$)", plain) if s.strip()]
    words = re.findall(r"[A-Za-z']+", plain)
    if not sentences or not words:
        return None
    syllables = sum(count_syllables(word) for word in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)
    return 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59


def check_reading_level(text):
    grade = reading_grade(text)
    if grade is not None and grade > MAX_READING_GRADE:
        message = (
            f"reading grade is {grade:.1f}, the limit is {MAX_READING_GRADE}. "
            "Use shorter sentences and simpler words"
        )
        return [(1, message)]
    return []


def check_file(path, root):
    text = path.read_text(encoding="utf-8")
    relative_path = path.relative_to(root).as_posix()

    problems = []
    problems.extend(check_dashes(text))
    if relative_path not in FILES_THAT_MAY_LIST_BANNED_PHRASES:
        problems.extend(check_banned_phrases(text))
    problems.extend(check_emoji(text))
    problems.extend(check_links(text, path, root))
    if needs_header(relative_path):
        problems.extend(check_header(text))
    if relative_path in FAMILY_PAGES:
        problems.extend(check_reading_level(text))

    return [f"{relative_path}:{number}: {message}" for number, message in sorted(problems)]


def check_repo(root):
    messages = []
    for path in find_markdown_files(root):
        messages.extend(check_file(path, root))
    return messages


def main(root=None):
    if root is None:
        root = Path(__file__).resolve().parent.parent
    messages = check_repo(root)
    for message in messages:
        print(message)
    file_count = len(find_markdown_files(root))
    if messages:
        print(f"\n{len(messages)} problem(s) found in {file_count} files.")
        return 1
    print(f"Checked {file_count} files. No problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
