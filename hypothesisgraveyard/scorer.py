"""Score each paper by how much its hypothesis was ignored by later citations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from hypothesisgraveyard.scholar import Paper, CitationContext
from hypothesisgraveyard.hypothesis import HypothesisSentence

# context keywords that signal a paper is actually engaging with the hypothesis
_ENGAGE_PATTERNS = re.compile(
    r'\b(confirm|support|consistent with|validate|replicate|extend|'
    r'contradict|challenge|refute|dispute|oppose|contrary to|'
    r'inconsistent with|fail to replicate|build on|advance)\b',
    re.I
)


def _is_engaging(ctx: CitationContext) -> bool:
    """Return True if a citation actually engages with the hypothesis."""
    # background-only intent = just a literature reference, not real engagement
    if [i.lower() for i in ctx.intents] == ["background"]:
        return False
    if _ENGAGE_PATTERNS.search(ctx.context):
        return True
    # A methodology or result intent is engagement on its own. Semantic Scholar
    # classifies the intent from the citing text, so it stands as evidence even
    # for the many citations the API returns with no context snippet attached.
    if any(i.lower() in ("methodology", "result") for i in ctx.intents):
        return True
    return False


@dataclass
class GraveyardEntry:
    paper: Paper
    hypotheses: list[HypothesisSentence]
    citation_contexts: list[CitationContext]
    engaging_count: int
    neglect_score: float   # 1.0 = fully ignored, 0.0 = fully engaged with
    is_buried: bool
    author_string: str
    strongest_hypothesis: str


class NeglectScorer:
    """Computes neglect scores and identifies buried hypotheses."""

    def __init__(self, buried_threshold: float = 0.7):
        self._threshold = buried_threshold

    def score(self, paper: Paper, hypotheses: list[HypothesisSentence],
              contexts: list[CitationContext]) -> GraveyardEntry:
        """Score one paper."""
        # Neglect is measured over the citation contexts actually retrieved so
        # that numerator and denominator describe the same population. Using
        # paper.citation_count as the denominator would divide a sampled count
        # of engaging contexts by the full citation total, which understates
        # engagement whenever only a subset of contexts was fetched.
        examined = len(contexts)
        engaging = sum(1 for c in contexts if _is_engaging(c))

        if examined == 0:
            neglect = 1.0
        else:
            neglect = 1.0 - (engaging / examined)

        # pick the highest-confidence hypothesis to display
        if hypotheses:
            strongest = max(hypotheses, key=lambda h: h.confidence).text
        else:
            strongest = ""

        # build author string
        if not paper.authors:
            author_str = "Unknown"
        elif len(paper.authors) == 1:
            author_str = paper.authors[0].name
        else:
            author_str = f"{paper.authors[0].name} et al."

        return GraveyardEntry(
            paper=paper,
            hypotheses=hypotheses,
            citation_contexts=contexts,
            engaging_count=engaging,
            neglect_score=round(neglect, 3),
            is_buried=neglect >= self._threshold,
            author_string=author_str,
            strongest_hypothesis=strongest,
        )

    def survival_rate(self, entries: list[GraveyardEntry]) -> float:
        """Fraction of entries that are NOT buried."""
        if not entries:
            return 0.0
        survived = sum(1 for e in entries if not e.is_buried)
        return survived / len(entries)

    def sort_by_neglect(self, entries: list[GraveyardEntry]) -> list[GraveyardEntry]:
        """Sort entries from most neglected to least neglected."""
        return sorted(entries, key=lambda e: e.neglect_score, reverse=True)
