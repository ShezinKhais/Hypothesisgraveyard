# HypothesisGraveyard

Searches a research topic on Semantic Scholar, extracts hypothesis sentences from paper abstracts, then checks whether each hypothesis was ever engaged with by later citations. Papers whose hypotheses were only cited as background - or never cited at all - are marked as abandoned.

The motivation: science produces many more hypotheses than it can test, and citation counts alone do not tell you whether an idea was taken seriously or just referenced in a literature review.

---

## How it works

1. Papers matching the query are fetched from Semantic Scholar (an API key is optional but recommended; see below)
2. Abstracts are scanned for hypothesis language: proposal markers ("we propose", "we hypothesise"), hedging ("this suggests", "may indicate"), possibility ("could be", "it is possible that"), and future predictions
3. Citation contexts are retrieved for each paper
4. A citation is classed as "engaging" if it confirms, challenges, or extends the work - not just cites it as background
5. A neglect score is computed per paper: `1 - (engaging citations / citation contexts examined)`. A paper for which no citation context could be retrieved is assigned 1.00 as a floor rather than measured, and the report labels it separately
6. Papers with neglect score >= 0.7 are marked as buried. The threshold is `--threshold`
7. Results are rendered as a self-contained HTML graveyard page

---

## Usage

```bash
pip install -r requirements.txt

# Try it offline with bundled sample data (no network or API key needed)
python -m hypothesisgraveyard.cli dig "anything" --demo --no-html

# Search a topic and generate a graveyard
python -m hypothesisgraveyard.cli dig "gut-brain axis"

# Filter by year range
python -m hypothesisgraveyard.cli dig "CRISPR off-target" --from-year 2018 --to-year 2023

# Export as JSON and show only the 10 most neglected
python -m hypothesisgraveyard.cli dig "quantum cognition" --top 10 --json results.json

# Fetch more papers, write the page somewhere specific, and move the cut
python -m hypothesisgraveyard.cli dig "gut-brain axis" --limit 100     --html graveyard.html --threshold 0.8

# Test hypothesis extraction on a single abstract
python -m hypothesisgraveyard.cli extract "We propose that gut bacteria modulate dopamine synthesis."
```

### Live data and rate limits

Live queries use the Semantic Scholar API, whose free tier throttles
unauthenticated traffic heavily. For live use, request a free API key from
Semantic Scholar and set it in the `SEMANTIC_SCHOLAR_API_KEY` environment
variable. Without a key, use `--demo` to run against the bundled sample data.

---

## The report

Unless `--no-html` is passed, a run writes a single self-contained page. It
fetches nothing and opens from disk.

The papers are listed most neglected first, each with the hypothesis sentence
that was extracted, the marker that caught it, and the counts behind its score.
Above them is the distribution: one stroke per paper at its neglect score, with
a rule drawn at the burial threshold, so the cut being made is visible as a cut
and the distance from a stroke to the rule shows how close that paper came to
landing on the other side.

Each paper also carries a sentence saying what its score rests on, because the
same 1.00 can mean very different things. A paper whose twenty retrieved
contexts all cite it as background has been read and passed over. A paper that
returned no contexts at all has not been measured, and the page says so, marks
its stroke differently, states its status as buried by default rather than
buried, and reports how many papers in the run are in that position.

---

## Limitations

The premise of this tool is that a citation count cannot tell you whether an
idea was engaged with. The score is an attempt at that distinction, and these
are the places it does not hold.

**Absence of evidence scores the same as evidence of neglect.** A paper nobody
ever cited and a paper cited three hundred times where every retrieved context
was background-only both come out at 1.00 and both are marked buried. The
scorer has nothing to divide by in the first case, so it assigns the maximum as
a floor. The report separates the two in words, in its status label and in the
shape of the stroke, and it counts how many papers in a run were never measured,
but the number itself does not distinguish them. Read the contexts-examined
figure beside any 1.00.

**Coverage is partial and uneven.** Semantic Scholar returns a context snippet
for only some citations, with worse coverage for older and paywalled work. The
denominator is the contexts actually retrieved, not the citations that exist, so
a paper with ninety-five citations may be scored on two of them. That choice is
deliberate, since dividing a sampled numerator by a full citation count would
understate engagement for every paper, but it does mean a score can rest on very
little.

**Engagement is inferred from marker phrases and Semantic Scholar's own intent
labels.** A citation counts as engaging if its context carries a word like
confirm, contradict or replicate, or if the API labelled it methodology or
result. A paper that engages seriously in its own words, without any of those
markers and without an intent label, is counted as neglect.

**A hypothesis is one sentence from an abstract.** Hedging language is a
reasonable proxy for a hypothesis, but it also catches ordinary scientific
caution in a paper whose real claim is elsewhere, and it misses a hypothesis
stated flatly.

**Nothing here distinguishes a neglected idea from a wrong one.** Most
hypotheses that go unengaged go unengaged because the field moved on for good
reason. The output is a list of things that were not followed up, which is a
starting point for a question, not an argument that anything was overlooked.

---

## Testing

Install the dependencies and run the suite:

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt pytest   # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m pytest -v
```

Exercise the CLI directly with `python -m hypothesisgraveyard.cli --help`.

---

## Project structure

```
hypothesisgraveyard/
├── hypothesisgraveyard/
│   ├── scholar.py      # Semantic Scholar search and citation fetch
│   ├── demo_data.py    # bundled sample data for --demo
│   ├── hypothesis.py   # hypothesis sentence extraction
│   ├── scorer.py       # neglect score computation
│   ├── visualiser.py   # standalone HTML output
│   └── cli.py
└── tests/
    ├── test_hypothesis.py
    ├── test_scholar_parsing.py
    ├── test_visualiser.py
    ├── test_demo.py
    └── test_scorer.py
```

---

## Stack

Python 3.10, Requests, Typer, Rich

An API key is optional but recommended for live use; `--demo` needs neither key nor network.
