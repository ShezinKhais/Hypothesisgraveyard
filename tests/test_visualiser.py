"""Tests for the HTML report: the threshold is shown, and 1.00 is not one thing."""

import pytest

from hypothesisgraveyard.scholar import Paper, Author, CitationContext
from hypothesisgraveyard.hypothesis import HypothesisSentence
from hypothesisgraveyard.scorer import NeglectScorer
from hypothesisgraveyard.visualiser import render_html


def _paper(citation_count: int = 0, title: str = "A hypothesis about X") -> Paper:
    return Paper(
        paper_id="abc123",
        title=title,
        year=2015,
        authors=[Author(name="Smith J")],
        abstract="We propose that X causes Y.",
        citation_count=citation_count,
    )


def _hyp() -> HypothesisSentence:
    return HypothesisSentence(text="We propose that X causes Y.",
                              confidence=1.0, signal="propose")


def _ctx(context: str, intents: list) -> CitationContext:
    return CitationContext(citing_title="Later paper", citing_year=2020,
                           context=context, intents=intents)


@pytest.fixture
def scorer():
    return NeglectScorer(buried_threshold=0.7)


class TestReport:
    def test_threshold_is_stated_and_drawn(self, scorer):
        entry = scorer.score(_paper(4), [_hyp()],
                             [_ctx("cited in passing", ["background"])])
        page = render_html([entry], topic="a topic", survival_rate=0.0,
                           threshold=0.7)
        assert "buried at 0.70" in page
        assert "rule-threshold" in page

    def test_uncited_paper_is_not_called_neglected(self, scorer):
        entry = scorer.score(_paper(0), [_hyp()], [])
        page = render_html([entry], topic="a topic", survival_rate=0.0)
        assert "No citations are recorded for this paper" in page
        assert "not a measurement of neglect" in page

    def test_cited_but_no_contexts_is_distinguished(self, scorer):
        entry = scorer.score(_paper(47), [_hyp()], [])
        page = render_html([entry], topic="a topic", survival_rate=0.0)
        assert "reports 47 citations but returned no citation context" in page

    def test_cited_and_ignored_is_a_measurement(self, scorer):
        contexts = [_ctx("as previously described", ["background"]),
                    _ctx("see also", ["background"])]
        entry = scorer.score(_paper(12), [_hyp()], contexts)
        page = render_html([entry], topic="a topic", survival_rate=0.0)
        assert "read and passed over" in page
        assert "floor" not in page

    def test_missing_hypothesis_is_admitted(self, scorer):
        entry = scorer.score(_paper(3), [], [_ctx("we confirm", ["result"])])
        page = render_html([entry], topic="a topic", survival_rate=1.0)
        assert "No hypothesis sentence was extracted" in page

    def test_empty_report_says_what_was_looked_for(self):
        page = render_html([], topic="an empty topic", survival_rate=0.0)
        assert "an empty topic" in page
        assert "Nothing to report" in page

    def test_titles_are_escaped(self, scorer):
        entry = scorer.score(_paper(1, title="X <script>alert(1)</script>"),
                             [_hyp()], [_ctx("we confirm", ["result"])])
        page = render_html([entry], topic="a topic", survival_rate=1.0)
        assert "<script>alert(1)</script>" not in page

    def test_report_makes_no_network_requests(self, scorer):
        entry = scorer.score(_paper(1), [_hyp()], [_ctx("we confirm", ["result"])])
        page = render_html([entry], topic="a topic", survival_rate=1.0)
        assert "http://" not in page and "https://" not in page

    def test_written_to_disk(self, scorer, tmp_path):
        entry = scorer.score(_paper(1), [_hyp()], [_ctx("we confirm", ["result"])])
        out = tmp_path / "report.html"
        render_html([entry], topic="a topic", survival_rate=1.0, output_path=out)
        assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
