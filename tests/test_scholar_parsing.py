"""Tests for how API responses are turned into CitationContext records.

The neglect score is a ratio over the citations retrieved, so anything the
parser silently drops changes the number this project reports.
"""

from html import escape

import pytest

from hypothesisgraveyard.scholar import ScholarClient, CitationContext
from hypothesisgraveyard.scorer import NeglectScorer, _is_engaging
from hypothesisgraveyard.visualiser import render_html
from hypothesisgraveyard.hypothesis import HypothesisSentence
from hypothesisgraveyard.scholar import Paper, Author


class _StubClient(ScholarClient):
    """A client whose _get returns a canned payload instead of calling the API."""

    def __init__(self, payload):
        super().__init__(demo=False)
        self._payload = payload

    def _get(self, url, params=None):
        return self._payload


def _citation(contexts, intents=("background",), title="Citing paper"):
    return {
        "citingPaper": {"title": title, "year": 2021},
        "contexts": contexts,
        "intents": list(intents),
    }


class TestFetchCitations:
    def test_citation_without_context_snippets_is_still_counted(self):
        # The API sends "contexts": [] rather than omitting the key, so a dict
        # default never fires. These citations used to vanish entirely, which
        # deleted exactly the evidence of neglect the tool measures.
        client = _StubClient({"data": [_citation([])]})
        ctxs = client.fetch_citations("paper1")
        assert len(ctxs) == 1
        assert ctxs[0].context == ""
        assert ctxs[0].citing_title == "Citing paper"

    def test_missing_contexts_key_is_still_counted(self):
        client = _StubClient({"data": [{"citingPaper": {"title": "T", "year": 2020},
                                        "intents": []}]})
        assert len(client.fetch_citations("paper1")) == 1

    def test_each_snippet_becomes_its_own_context(self):
        client = _StubClient({"data": [_citation(["first say", "second say"])]})
        ctxs = client.fetch_citations("paper1")
        assert [c.context for c in ctxs] == ["first say", "second say"]

    def test_mixed_payload_keeps_every_citation(self):
        client = _StubClient({"data": [_citation([]), _citation(["one"]), _citation([])]})
        assert len(client.fetch_citations("paper1")) == 3

    def test_neglect_counts_the_silent_citations(self):
        # Three citations, one of which engages. Dropping the two empty ones
        # would report full engagement instead of one third.
        client = _StubClient({"data": [
            _citation([]),
            _citation([]),
            _citation(["this confirms the earlier finding"], intents=["result"]),
        ]})
        ctxs = client.fetch_citations("paper1")
        paper = Paper(paper_id="p", title="T", year=2020,
                      authors=[Author(name="Smith J")], abstract="", citation_count=3)
        entry = NeglectScorer().score(paper, [], ctxs)
        assert entry.engaging_count == 1
        assert entry.neglect_score == pytest.approx(1 - 1 / 3, abs=1e-3)


class TestIsEngaging:
    def test_background_only_is_not_engagement(self):
        assert not _is_engaging(CitationContext("T", 2020, "", ["background"]))

    def test_intent_case_does_not_matter(self):
        assert not _is_engaging(CitationContext("T", 2020, "", ["Background"]))
        assert _is_engaging(CitationContext("T", 2020, "", ["Result"]))

    def test_result_intent_engages_without_a_snippet(self):
        assert _is_engaging(CitationContext("T", 2020, "", ["result"]))

    def test_engagement_language_engages_without_an_intent(self):
        assert _is_engaging(CitationContext("T", 2020, "we refute this", []))

    def test_bare_citation_with_neither_is_not_engagement(self):
        assert not _is_engaging(CitationContext("T", 2020, "", []))


class TestHtmlEscaping:
    def test_paper_titles_are_escaped(self):
        # Titles and abstracts come from the API, so markup inside one must not
        # become part of the page.
        paper = Paper(paper_id="p", title="<script>alert(1)</script> Study",
                      year=2020, authors=[Author(name="Smith & Jones")],
                      abstract="", citation_count=0)
        entry = NeglectScorer().score(
            paper,
            [HypothesisSentence(text="<img src=x onerror=alert(2)>",
                                confidence=1.0, signal="propose")],
            [],
        )
        page = render_html([entry], topic="<b>topic</b>", survival_rate=0.0)
        assert "<script>alert(1)</script>" not in page
        assert "<img src=x onerror=alert(2)>" not in page
        assert escape("<script>alert(1)</script> Study") in page
        assert "<b>topic</b>" not in page
