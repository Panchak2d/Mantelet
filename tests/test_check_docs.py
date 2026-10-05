import check_docs

LONG_DASH = "\u2014"
EN_DASH = "\u2013"
HEADER = "Reader: a test reader.\nLast reviewed: 4 October 2026\n"


def messages(problems):
    return [message for _, message in problems]


def test_long_dash_is_reported():
    problems = check_docs.check_dashes(f"one {LONG_DASH} two")
    assert problems == [(1, "long dash found. Use a full stop, comma, colon or 'and'")]


def test_en_dash_is_reported():
    assert len(check_docs.check_dashes(f"1{EN_DASH}2")) == 1


def test_dash_inside_code_block_is_ignored():
    text = f"```\n{LONG_DASH}\n```\nplain line"
    assert check_docs.check_dashes(text) == []


def test_banned_word_is_reported_with_line_number():
    problems = check_docs.check_banned_phrases("fine line\nWe will leverage this.")
    assert problems == [(2, "banned phrase: 'leverage'")]


def test_banned_word_inside_longer_word_is_not_reported():
    assert check_docs.check_banned_phrases("The pivotality of it.") == []


def test_banned_phrase_with_curly_apostrophe_is_reported():
    assert len(check_docs.check_banned_phrases("In today\u2019s world, things change.")) == 1


def test_not_just_but_pattern_is_reported():
    text = "It is not just a tool, but a promise."
    assert messages(check_docs.check_banned_phrases(text)) == [
        "banned pattern: 'not just X, but Y'"
    ]


def test_emoji_is_reported_once_per_line():
    assert len(check_docs.check_emoji("two \U0001F600\U0001F600 here")) == 1


def test_check_mark_symbol_is_reported():
    assert len(check_docs.check_emoji("done \u2713\u2705")) == 1


def test_plain_text_has_no_emoji():
    assert check_docs.check_emoji("Plain words only.") == []


def test_broken_link_is_reported(tmp_path):
    page = tmp_path / "page.md"
    problems = check_docs.check_links("See [it](missing.md).", page, tmp_path)
    assert problems == [(1, "broken link: missing.md")]


def test_working_link_with_heading_part_passes(tmp_path):
    (tmp_path / "other.md").write_text("x", encoding="utf-8")
    page = tmp_path / "page.md"
    assert check_docs.check_links("See [it](other.md#part).", page, tmp_path) == []


def test_web_mail_and_heading_only_links_are_not_checked(tmp_path):
    text = "[a](https://example.org) [b](mailto:a@example.org) [c](#top)"
    assert check_docs.check_links(text, tmp_path / "page.md", tmp_path) == []


def test_link_starting_with_slash_is_checked_from_repo_root(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("x", encoding="utf-8")
    page = tmp_path / "other" / "page.md"
    assert check_docs.check_links("[a](/docs/a.md)", page, tmp_path) == []


def test_header_with_reader_and_current_review_passes():
    assert check_docs.check_header(HEADER) == []


def test_missing_reader_line_is_reported():
    text = "Last reviewed: 4 October 2026\n"
    assert messages(check_docs.check_header(text)) == ["no 'Reader:' line in the first 12 lines"]


def test_missing_last_reviewed_line_is_reported():
    problems = check_docs.check_header("Reader: someone.\n")
    assert "no 'Last reviewed" in problems[0][1]


def test_syllable_counts_for_simple_words():
    assert check_docs.count_syllables("cat") == 1
    assert check_docs.count_syllables("photo") == 2
    assert check_docs.count_syllables("make") == 1
    assert check_docs.count_syllables("table") == 2


def test_easy_text_is_under_the_reading_limit():
    text = "We make a photo. You see a cat. The cat is big. It sat on the mat."
    assert check_docs.check_reading_level(text) == []


def test_hard_text_is_over_the_reading_limit():
    text = (
        "Adversarial perturbation robustness evaluation necessitates comprehensive "
        "consideration of transformation-invariant optimization methodologies."
    )
    assert "reading grade" in check_docs.check_reading_level(text)[0][1]


def test_reading_grade_ignores_code_blocks_and_headings():
    plain = "# Title\nWe see a cat.\n```\nenormously complicated incomprehensible\n```\n"
    assert check_docs.reading_grade(plain) == check_docs.reading_grade("We see a cat.\n")


def test_learning_notes_do_not_need_a_header():
    assert not check_docs.needs_header("learning/notes.md")
    assert check_docs.needs_header("learning/README.md")
    assert not check_docs.needs_header(".github/PULL_REQUEST_TEMPLATE.md")
    assert check_docs.needs_header("docs/index.md")


def test_clean_repo_passes_and_returns_zero(tmp_path, capsys):
    (tmp_path / "README.md").write_text(HEADER + "\nWe make a cat.\n", encoding="utf-8")
    assert check_docs.main(tmp_path) == 0
    assert "No problems found" in capsys.readouterr().out


def test_repo_with_a_problem_returns_one_and_names_the_file(tmp_path, capsys):
    page = tmp_path / "docs" / "page.md"
    page.parent.mkdir()
    page.write_text(HEADER + "\nWe leverage it.\n", encoding="utf-8")
    assert check_docs.main(tmp_path) == 1
    assert "docs/page.md:4: banned phrase: 'leverage'" in capsys.readouterr().out


def test_style_guide_and_plan_may_list_banned_phrases(tmp_path):
    for name in ("the project plan", "docs/development/style-guide.md"):
        page = tmp_path / name
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(HEADER + "\nAvoid leverage.\n", encoding="utf-8")
    assert check_docs.check_repo(tmp_path) == []


def test_hidden_and_environment_folders_are_skipped(tmp_path):
    hidden = tmp_path / ".venv" / "lib"
    hidden.mkdir(parents=True)
    (hidden / "x.md").write_text("no header here", encoding="utf-8")
    assert check_docs.find_markdown_files(tmp_path) == []
