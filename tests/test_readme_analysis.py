from reporadar.analysis.readme import (
    extract_headings,
    extract_keywords,
    extract_summary,
    extract_title,
    summarize_readme,
)

SAMPLE = """# RepoRadar

[![CI](https://img.shields.io/badge/ci-passing-green)](x)

RepoRadar mines GitHub for promising AI and LLM QA repositories.

## Features

- scoring
- clustering

## Install
"""


def test_extract_title_from_heading():
    assert extract_title(SAMPLE) == "RepoRadar"


def test_extract_title_falls_back_to_first_line():
    assert extract_title("Just a plain line\nmore") == "Just a plain line"


def test_extract_title_none_when_empty():
    assert extract_title("   \n\n") is None


def test_extract_summary_skips_badges_and_headings():
    summary = extract_summary(SAMPLE)
    assert summary is not None
    assert summary.startswith("RepoRadar mines GitHub")
    assert "shields.io" not in summary


def test_extract_summary_truncates_long_text():
    text = "# T\n\n" + "word " * 200
    summary = extract_summary(text, max_chars=80)
    assert summary is not None
    assert len(summary) <= 81  # 80 + ellipsis char tolerance


def test_extract_headings():
    assert extract_headings(SAMPLE) == ["Features", "Install"]


def test_extract_keywords_returns_salient_terms():
    keywords = extract_keywords(SAMPLE, limit=5)
    assert "reporadar" in keywords
    assert "the" not in keywords


def test_summarize_readme_bundles_fields():
    result = summarize_readme(SAMPLE)
    assert result.title == "RepoRadar"
    assert result.summary is not None
    assert "Features" in result.headings


def test_summarize_empty_readme():
    result = summarize_readme("")
    assert result.title is None
    assert result.summary is None
    assert result.headings == []
