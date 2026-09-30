"""Render a self-contained HTML report of neglected hypotheses.

The report is one file with no external requests, so it opens from disk with no
network. Its hero is the distribution of neglect across the topic with the
buried threshold drawn on it, because the interesting question is not how one
paper scored but what shape the field has: a few badly ignored papers, or a
uniform spread.
"""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from hypothesisgraveyard.scorer import GraveyardEntry

# Neglect is defined on 0 to 1, so the axis domain is fixed rather than fitted
# to the data. An axis that rescaled itself per run could not be compared
# between runs, which is most of the point of drawing the distribution.
_DOMAIN_TICKS = (0.0, 0.25, 0.5, 0.75, 1.0)

_MARK_PITCH = 14     # px between stacked rows of marks (10px mark, 4px gap)
_MARK_SEP   = 0.035  # domain distance two marks need in order to share a row
_MIN_ROWS   = 3      # keeps the plot from collapsing when every score coincides

_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


_CSS = """
:root {
  /* ground */
  --ground:      #EDEFEA;
  --lift:        #F7F8F5;
  --sink:        #E3E6DF;

  /* ink */
  --ink:         #191D1C;
  --ink-mid:     #4E5754;
  --ink-soft:    #7C8683;

  /* structure */
  --rule:        #CFD4CC;
  --rule-firm:   #A8B0AC;

  /* the one structural accent: oxidised blue */
  --mark:        #1D4E63;
  --mark-soft:   #7FA3B2;

  /* semantic data inks, desaturated like printing ink */
  --confirm:     #2F6B4F;
  --challenge:   #A33B2A;
  --extend:      #8A6A1F;
  --quiet:       #8C9491;

  --measure:     68ch;

  --sans: ui-sans-serif, "Segoe UI Variable Display", "Segoe UI", Inter,
          system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, "Cascadia Code", "SF Mono", "Consolas",
          "Liberation Mono", monospace;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:    #14171A;
    --lift:      #1C2024;
    --sink:      #0F1215;
    --ink:       #E4E8E6;
    --ink-mid:   #A6AEAB;
    --ink-soft:  #7B8582;
    --rule:      #2E343A;
    --rule-firm: #454D53;
    --mark:      #6FB3CE;
    --mark-soft: #3C6478;
    --confirm:   #6FBE93;
    --challenge: #E08472;
    --extend:    #D9B45C;
    --quiet:     #6E7773;
  }
}

:root[data-theme="dark"] {
  --ground:    #14171A;
  --lift:      #1C2024;
  --sink:      #0F1215;
  --ink:       #E4E8E6;
  --ink-mid:   #A6AEAB;
  --ink-soft:  #7B8582;
  --rule:      #2E343A;
  --rule-firm: #454D53;
  --mark:      #6FB3CE;
  --mark-soft: #3C6478;
  --confirm:   #6FBE93;
  --challenge: #E08472;
  --extend:    #D9B45C;
  --quiet:     #6E7773;
}

* { box-sizing: border-box; }

body { margin: 0; background: var(--ground); color: var(--ink);
       font-family: var(--sans); font-size: 15px; line-height: 1.6;
       -webkit-text-size-adjust: 100%; }

.page { max-width: 900px; margin: 0 auto; padding: 32px 16px 48px; }

.title { margin: 0 0 8px; font-size: 30px; line-height: 1.15; font-weight: 600;
         letter-spacing: -0.02em; overflow-wrap: break-word; }

.standfirst { margin: 0 0 24px; max-width: var(--measure); color: var(--ink-mid); }

.figures { display: flex; flex-wrap: wrap; gap: 16px 32px; margin: 0;
           padding: 12px 0; list-style: none;
           border-top: 2px solid var(--rule-firm);
           border-bottom: 1px solid var(--rule); }
.figure-label { display: block; font-size: 12px; line-height: 1.3;
                font-weight: 500; color: var(--ink-soft); }
.figure-value { display: block; margin-top: 4px; font-size: 22px; line-height: 1;
                font-weight: 550; font-variant-numeric: tabular-nums; }

.section { margin-top: 32px; }
.section-title { margin: 0 0 16px; padding-bottom: 8px; font-size: 17px;
                 line-height: 1.3; font-weight: 600;
                 border-bottom: 2px solid var(--rule-firm); }

/* the distribution of neglect, and the cut the threshold makes in it */
.dist { margin: 0; }
.track { position: relative; margin: 0 16px; }
.threshold-row { position: relative; height: 20px; }
.threshold-label { position: absolute; bottom: 2px; font-size: 12px;
                   line-height: 1.3; font-weight: 500; color: var(--mark);
                   white-space: nowrap; }
.threshold-label.before { padding-right: 6px; text-align: right; }
.threshold-label.after  { padding-left: 6px; }
.plot { position: relative; }
.rule-threshold { position: absolute; top: 0; bottom: -8px; width: 2px;
                  margin-left: -1px; background: var(--mark); }
.mark { position: absolute; bottom: 0; width: 3px; height: 10px;
        margin-left: -1.5px; }
.mark-buried { background: var(--challenge); }
.mark-alive  { background: var(--confirm); }
.mark-unmeasured { width: 7px; margin-left: -3.5px; background: none;
                   border: 1px solid var(--quiet); }
.axis { position: relative; height: 24px; border-top: 2px solid var(--rule-firm); }
.axis-tick { position: absolute; top: 0; width: 1px; height: 4px;
             margin-left: -0.5px; background: var(--rule-firm); }
.axis-label { position: absolute; top: 8px; transform: translateX(-50%);
              font-size: 12px; line-height: 1.3; color: var(--ink-soft);
              font-variant-numeric: tabular-nums; white-space: nowrap; }
.dist-caption { margin: 16px 0 0; max-width: var(--measure); font-size: 12px;
                line-height: 1.5; color: var(--ink-soft); }
.dist-caption p { margin: 0 0 6px; }
.dist-caption p:last-child { margin-bottom: 0; }

/* per-paper entries, on the same scale as the distribution above */
.entries { margin: 0; padding: 0; list-style: none;
           border-top: 1px solid var(--rule); }
.entry { display: grid; grid-template-columns: 56px minmax(0, 1fr);
         gap: 0 16px; padding: 12px 0; border-bottom: 1px solid var(--rule); }
.gutter { padding-top: 5px; }
.gutter-scale { position: relative; height: 12px; margin: 0 4px;
                border-bottom: 1px solid var(--rule); }
.gutter-threshold { position: absolute; top: -2px; bottom: -1px; width: 1px;
                    margin-left: -0.5px; background: var(--mark-soft); }
.gutter-tick { position: absolute; bottom: 0; width: 3px; height: 10px;
               margin-left: -1.5px; }
.gutter-value { display: block; margin-top: 4px; font-size: 12px;
                line-height: 1.3; color: var(--ink-mid);
                font-variant-numeric: tabular-nums; }

.hypothesis { margin: 0; max-width: var(--measure); font-size: 17px;
              line-height: 1.45; }
.hypothesis-absent { margin: 0; max-width: var(--measure); color: var(--ink-mid); }
.source { margin: 8px 0 0; max-width: var(--measure); font-size: 13.5px;
          line-height: 1.45; color: var(--ink-mid); }
.source-title { color: var(--ink); }
.metrics { display: flex; flex-wrap: wrap; gap: 4px 16px; margin: 8px 0 0;
           padding: 0; }
.metric { display: flex; align-items: baseline; gap: 6px; }
.metric-label { font-size: 12px; line-height: 1.3; color: var(--ink-soft); }
.metric-value { font-size: 13.5px; line-height: 1.45;
                font-variant-numeric: tabular-nums; }
.status-buried { color: var(--challenge); font-weight: 600; }
.status-alive  { color: var(--confirm);   font-weight: 600; }
.note { margin: 8px 0 0; padding-left: 12px; max-width: var(--measure);
        font-size: 13.5px; line-height: 1.5; color: var(--ink-mid);
        border-left: 3px solid var(--quiet); }

.cut { padding: 12px 0; max-width: var(--measure); font-size: 12px;
       line-height: 1.5; color: var(--mark);
       border-top: 2px solid var(--mark);
       border-bottom: 1px solid var(--rule); }

.empty { margin: 0; max-width: var(--measure); }

.provenance { margin: 32px 0 0; padding-top: 12px; max-width: var(--measure);
              font-size: 12px; line-height: 1.5; color: var(--ink-soft);
              border-top: 1px solid var(--rule); }
"""


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def _pos(score: float) -> float:
    """Position of a score as a percentage along the fixed 0 to 1 axis."""
    return min(max(score, 0.0), 1.0) * 100


def _examined(entry: GraveyardEntry) -> int:
    return len(entry.citation_contexts)


def _mark_rows(scores: list[float]) -> list[int]:
    """Assign each score a stacking row so that neighbouring marks do not overlap.

    Rows fill from the axis upwards in ascending score order, so the same set of
    scores always draws the same picture: no jitter, nothing random.
    """
    rows: list[float] = []
    assigned = [0] * len(scores)
    for i in sorted(range(len(scores)), key=lambda j: scores[j]):
        for row, last in enumerate(rows):
            if scores[i] - last >= _MARK_SEP:
                rows[row]   = scores[i]
                assigned[i] = row
                break
        else:
            rows.append(scores[i])
            assigned[i] = len(rows) - 1
    return assigned


def _distribution_html(entries: list[GraveyardEntry], threshold: float) -> str:
    """One labelled axis over the domain, every paper on it, threshold drawn across."""
    scores = [e.neglect_score for e in entries]
    rows   = _mark_rows(scores)
    height = max(_MIN_ROWS, max(rows) + 1) * _MARK_PITCH

    marks = []
    for entry, row in zip(entries, rows):
        if _examined(entry) == 0:
            shape = "mark-unmeasured"
            state = "no citation contexts retrieved"
        elif entry.is_buried:
            shape = "mark-buried"
            state = "buried"
        else:
            shape = "mark-alive"
            state = "surviving"
        label = (f"{entry.paper.title} ({entry.paper.year}): "
                 f"neglect {entry.neglect_score:.2f}, {state}")
        marks.append(
            f'<span class="mark {shape}" style="left:{_pos(entry.neglect_score):.4f}%;'
            f'bottom:{row * _MARK_PITCH}px" title="{_esc(label)}"></span>'
        )

    ticks = []
    for tick in _DOMAIN_TICKS:
        ticks.append(f'<span class="axis-tick" style="left:{_pos(tick):.4f}%"></span>'
                     f'<span class="axis-label" style="left:{_pos(tick):.4f}%">'
                     f'{tick:.2f}</span>')

    # The label hangs off whichever side of the rule has room for it, so a low
    # threshold cannot push its own caption off the left edge.
    side = "before" if threshold >= 0.35 else "after"
    edge = (f"right:{100 - _pos(threshold):.4f}%" if side == "before"
            else f"left:{_pos(threshold):.4f}%")

    unmeasured = sum(1 for e in entries if _examined(e) == 0)
    floor_note = ""
    if unmeasured:
        floor_note = (
            f'<p>{unmeasured} of {len(entries)} papers returned no citation '
            f'context at all. They sit at 1.00 because that is the floor the '
            f'scorer assigns when there is nothing to examine, not because '
            f'anyone read them and moved on, so they are drawn hollow.</p>'
        )

    return f"""<figure class="dist">
  <div class="track">
    <div class="threshold-row">
      <span class="threshold-label {side}" style="{edge}">buried at {threshold:.2f}</span>
    </div>
    <div class="plot" style="height:{height}px">
      <span class="rule-threshold" style="left:{_pos(threshold):.4f}%"></span>
      {''.join(marks)}
    </div>
    <div class="axis">
      {''.join(ticks)}
    </div>
  </div>
  <figcaption class="dist-caption">
    <p>Each stroke is one paper at its neglect score. 0.00 means every citation
    context examined engaged with the hypothesis, 1.00 means none did. Strokes on
    or right of the rule at {threshold:.2f} count as buried, so the rule is the
    cut being made, and the distance from a stroke to the rule is how close that
    paper came to falling on the other side.</p>
    {floor_note}
  </figcaption>
</figure>"""


def _entry_html(entry: GraveyardEntry, threshold: float) -> str:
    """One row: the hypothesis as its content, its score as a tick in the gutter."""
    examined = _examined(entry)
    buried   = entry.is_buried

    tick_shape = "mark-unmeasured" if examined == 0 else (
        "mark-buried" if buried else "mark-alive")
    status_class = "status-buried" if buried else "status-alive"
    status_text  = "buried by default" if examined == 0 else (
        "buried" if buried else "surviving")

    if entry.strongest_hypothesis:
        strongest = max(entry.hypotheses, key=lambda h: h.confidence)
        claim  = f'<p class="hypothesis">{_esc(entry.strongest_hypothesis)}</p>'
        signal = (f'<span class="metric"><span class="metric-label">signal</span>'
                  f'<span class="metric-value">{_esc(strongest.signal)} at '
                  f'{strongest.confidence:.1f}</span></span>')
    else:
        claim = ('<p class="hypothesis-absent">No hypothesis sentence was '
                 'extracted from this abstract, so there is no claim to track '
                 'here. The score describes how the citations read, nothing '
                 'more.</p>')
        signal = ""

    # A paper nobody cited and a paper cited without engagement both score 1.00,
    # and conflating them is the one dishonest thing this report could do.
    if examined == 0 and entry.paper.citation_count == 0:
        note = ('<p class="note">No citations are recorded for this paper, so no '
                'citation context was examined. The 1.00 is the floor the scorer '
                'assigns to an empty sample, not a measurement of neglect.</p>')
    elif examined == 0:
        note = (f'<p class="note">Semantic Scholar reports '
                f'{entry.paper.citation_count} citations but returned no citation '
                f'context, so engagement could not be assessed. The 1.00 is the '
                f'floor the scorer assigns to an empty sample, not a measurement '
                f'of neglect.</p>')
    elif entry.engaging_count == 0 and examined == 1:
        note = ('<p class="note">The one citation context examined cites this '
                'paper as background only. That is a measurement rather than a '
                'floor, but it rests on a single context.</p>')
    elif entry.engaging_count == 0:
        note = (f'<p class="note">All {examined} citation contexts examined cite '
                f'this paper as background only. That is a measurement: the work '
                f'was read and passed over.</p>')
    else:
        note = ""

    metrics = [
        f'<span class="metric"><span class="metric-label">status</span>'
        f'<span class="metric-value {status_class}">{status_text}</span></span>',
        f'<span class="metric"><span class="metric-label">contexts examined</span>'
        f'<span class="metric-value">{examined}</span></span>',
        f'<span class="metric"><span class="metric-label">engaging</span>'
        f'<span class="metric-value">{entry.engaging_count}</span></span>',
        f'<span class="metric"><span class="metric-label">citations reported</span>'
        f'<span class="metric-value">{entry.paper.citation_count}</span></span>',
    ]
    if signal:
        metrics.append(signal)

    year = _esc(entry.paper.year) if entry.paper.year else "year not recorded"

    return f"""<li class="entry">
  <div class="gutter">
    <div class="gutter-scale">
      <span class="gutter-threshold" style="left:{_pos(threshold):.4f}%"></span>
      <span class="gutter-tick {tick_shape}"
            style="left:{_pos(entry.neglect_score):.4f}%"></span>
    </div>
    <span class="gutter-value">{entry.neglect_score:.2f}</span>
  </div>
  <div class="entry-body">
    {claim}
    <p class="source"><span class="source-title">{_esc(entry.paper.title)}</span>.
      {_esc(entry.author_string)}, {year}.</p>
    <p class="metrics">{''.join(metrics)}</p>
    {note}
  </div>
</li>"""


def _figure_item(label: str, value: str) -> str:
    return (f'<li><span class="figure-label">{_esc(label)}</span>'
            f'<span class="figure-value">{_esc(value)}</span></li>')


def _today() -> str:
    today = date.today()
    return f"{today.day} {_MONTHS[today.month - 1]} {today.year}"


def render_html(entries: list[GraveyardEntry], topic: str,
                survival_rate: float, output_path: Path = None,
                threshold: float = 0.7) -> str:
    """Render the full report and optionally write it to output_path.

    threshold is the neglect score at which a paper counts as buried. It is the
    parameter a reader most needs in order to judge the result, so it is drawn on
    the distribution and repeated in every row's gutter.
    """
    ordered    = sorted(entries, key=lambda e: e.neglect_score, reverse=True)
    buried     = [e for e in ordered if e.is_buried]
    surviving  = [e for e in ordered if not e.is_buried]
    unmeasured = sum(1 for e in ordered if _examined(e) == 0)

    figures = [
        _figure_item("Papers analysed", str(len(ordered))),
        _figure_item("Buried", str(len(buried))),
        _figure_item("Surviving", str(len(surviving))),
        _figure_item("Survival rate", f"{survival_rate:.0%}"),
        _figure_item("Buried at neglect", f"{threshold:.2f}"),
    ]
    if unmeasured:
        figures.append(_figure_item("Without citation contexts", str(unmeasured)))

    if ordered:
        rows = [_entry_html(e, threshold) for e in buried]
        if buried and surviving:
            rows.append(
                f'<li class="cut">Threshold {threshold:.2f}. Papers below this '
                f'line were engaged with often enough to survive it.</li>'
            )
        rows.extend(_entry_html(e, threshold) for e in surviving)
        body = f"""  <section class="section">
    <h2 class="section-title">Distribution of neglect</h2>
    {_distribution_html(ordered, threshold)}
  </section>

  <section class="section">
    <h2 class="section-title">Papers, most neglected first</h2>
    <ul class="entries">
      {''.join(rows)}
    </ul>
  </section>"""
    else:
        body = f"""  <section class="section">
    <h2 class="section-title">Nothing to report</h2>
    <p class="empty">No paper found for {_esc(topic)} yielded a hypothesis
    sentence with a citation record to score, so there is no distribution to draw
    and no row to list. Widen the year range or the paper limit, or try a broader
    topic.</p>
  </section>"""

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HypothesisGraveyard: {_esc(topic)}</title>
  <style>{_CSS}</style>
</head>
<body>
<main class="page">
  <h1 class="title">HypothesisGraveyard</h1>
  <p class="standfirst">Hypothesis sentences pulled from abstracts on
    {_esc(topic)}, each scored by how little the citations that followed engaged
    with it. Reported {_today()}.</p>
  <ul class="figures">
    {''.join(figures)}
  </ul>

{body}

  <p class="provenance">Papers, citation counts and citation contexts from
    Semantic Scholar. A citation counts as engaging when it confirms, challenges
    or extends the work; neglect is one minus the share of examined contexts that
    did so.</p>
</main>
</body>
</html>"""

    if output_path:
        Path(output_path).write_text(page, encoding="utf-8")

    return page
