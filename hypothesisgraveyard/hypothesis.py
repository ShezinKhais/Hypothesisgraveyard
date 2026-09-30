"""Extract hypothesis sentences from paper abstracts using signal words."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class HypothesisSentence:
    text: str
    confidence: float   # 0.0 - 1.0
    signal: str         # which signal group matched


# Five signal groups. The weight is how strongly the phrasing indicates a
# hypothesis: an explicit proposal is the clearest, followed by hedged claims
# and novelty claims, then vague possibility and future-work language.

_PROPOSE = (re.compile(
    r'\b(we propose|we hypothesi[sz]e[sd]?|we conjecture|we theori[sz]e|'
    r'we postulate|we argue that|our hypothesis|the hypothesis that)\b',
    re.I), 1.0)

_HEDGE = (re.compile(
    r'\b(this suggests?|these results suggest|the data suggest|'
    r'may indicate|might indicate|could indicate|appears to|'
    r'seems to|evidence suggests?)\b',
    re.I), 0.9)

_POSSIBILITY = (re.compile(
    r'\b(it is possible (that)?|could be|might be|may be|'
    r'potentially|one possibility is|we speculate)\b',
    re.I), 0.7)

_FUTURE = (re.compile(
    r'\b(future (work|studies|research) (should|will|may)|'
    r'remains to be (shown|demonstrated|tested)|'
    r'warrants? further (investigation|study))\b',
    re.I), 0.6)

_NOVEL = (re.compile(
    r'\b(novel (hypothesis|theory|model|framework)|'
    r'first (to show|to demonstrate|evidence)|'
    r'to our knowledge|hitherto unknown)\b',
    re.I), 0.9)

# Ordered strongest signal first. extract() takes the highest weight rather than
# the first hit, so this order only decides ties: _HEDGE and _NOVEL both weigh
# 0.9, and listing hedge first makes it win when a sentence carries both.
_SIGNALS = [("propose", _PROPOSE), ("hedge", _HEDGE), ("novel", _NOVEL),
            ("possibility", _POSSIBILITY), ("future", _FUTURE)]

# The weakest signal group. A min_confidence below this admits every match,
# which is the useful default: callers raise it to demand stronger phrasing.
MIN_SIGNAL_WEIGHT = 0.6

# Abbreviations that should not be treated as sentence endings
_ABBREV = re.compile(r'\b(et al|vs|i\.e|e\.g|Fig|vol|pp|Dr|Prof|no|approx)\.$', re.I)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, being careful with abbreviations."""
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    merged = []
    carry  = ""
    for part in parts:
        candidate = (carry + " " + part).strip() if carry else part
        if _ABBREV.search(candidate.rstrip()):
            carry = candidate
        else:
            merged.append(candidate)
            carry = ""
    if carry:
        merged.append(carry)
    return merged


class HypothesisExtractor:
    """Scans abstracts for hypothesis-like sentences."""

    def extract(self, abstract: str,
                min_confidence: float = MIN_SIGNAL_WEIGHT) -> list[HypothesisSentence]:
        """Return sentences that look like hypotheses.

        min_confidence is compared against the weight of the signal group that
        matched, so the meaningful range is MIN_SIGNAL_WEIGHT to 1.0. The old
        default of 0.4 sat below every group and so admitted every match while
        reading like a filter.
        """
        results = []
        for sentence in _split_sentences(abstract):
            best_conf   = 0.0
            best_signal = ""
            for signal_name, (pattern, weight) in _SIGNALS:
                if pattern.search(sentence):
                    if weight > best_conf:
                        best_conf   = weight
                        best_signal = signal_name
            if best_conf >= min_confidence:
                results.append(HypothesisSentence(
                    text=sentence.strip(),
                    confidence=best_conf,
                    signal=best_signal,
                ))
        return results

    def has_hypothesis(self, abstract: str) -> bool:
        """Quick check - does this abstract contain any hypothesis language?"""
        return len(self.extract(abstract)) > 0
