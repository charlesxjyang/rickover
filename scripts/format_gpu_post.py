#!/usr/bin/env python3
"""
Turn the transcribed table of contents on the GPU Nuclear assessment post into
working in-page links.

The 1983 report is the only document in the corpus with a real table of
contents, so this is deliberately specific to that post rather than general.

Targets are matched by text, scanning forward in document order, because the
report repeats several headings verbatim: Section I (Summary) restates
"A. Scope" and "B. Method" word for word, and the seven criteria appear twice —
defined in Section II-E, then assessed in Section III-B. The table of contents
points at the Section II and Section III-B occurrences, so a forward-only
cursor picks the right one without relying on paragraph numbers.

It then marks every section heading in the body blue and bold, linking each
back up to the contents, so a new section is visible while reading.

It also sets the quoted passages as indented quote blocks with their citations,
and restores the two-line layout the original uses for the Appendix B person
list and the Appendix C biographies.

Every pass is independently guarded, so this is safe to re-run.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POST = ROOT / "posts" / "assessment-of-gpu-nuclear-corporation.html"

# (anchor id, label as it reads in the table of contents, regex for the body heading)
# Order matters: each target is found at or after the previous one.
SECTIONS = [
    ("summary",                           "I. SUMMARY",                           r"^I\.\s*SUMMARY\b"),
    ("methods-and-criteria",              "II. METHODS AND CRITERIA",             r"^II\.\s*METHODS AND CRITERIA\b"),
    ("methods-scope",                     "A. Scope",                             r"^A\.\s*Scope\b"),
    ("methods-method",                    "B. Method",                            r"^B\.\s*Method\b"),
    ("methods-document-review",           "C. Document Review",                   r"^C\.\s*Document Review\b"),
    ("methods-interviews",                "D. Interviews",                        r"^D\.\s*Interviews\b"),
    ("methods-criteria",                  "E. Criteria of Management Competence", r"^E\.\s*Criteria of Management Competence\b"),
    ("assessment",                        "III. ASSESSMENT",                      r"^III\.\s*ASSESSMENT\b"),
    ("assessment-introduction",           "A. Introduction",                      r"^A\.\s*Introduction\b"),
    ("assessment-against-criteria",       "B. Assessment Against Criteria",       r"^B\.\s*Assessment Against Criteria\b"),
    ("criterion-1-rising-standard",       "1. Rising Standard of Accuracy",       r"^\(1\)\s*Rising Standard"),
    ("criterion-2-technical-competence",  "2. Technical Competence",              r"^\(2\)\s*Technical Competence"),
    ("criterion-3-facing-facts",          "3. Facing Facts",                      r"^\(3\)\s*Facing Facts"),
    ("criterion-4-respect-for-radiation", "4. Respect for Radiation",             r"^\(4\)\s*Respect for Radiation"),
    ("criterion-5-training",              "5. The Importance of Training",        r"^\(5\)\s*The Importance of Training"),
    ("criterion-6-total-responsibility",  "6. Concept of Total Responsibility",   r"^\(6\)\s*Concept of Total Responsibility"),
    ("criterion-7-learn-from-experience", "7. Capacity to Learn from Experience", r"^\(7\)\s*Capacity to Learn from Experience"),
    ("conclusions-and-recommendations",   "IV. CONCLUSIONS AND RECOMMENDATIONS",  r"^IV\.\s*Conclusions and Recommendations"),
    ("appendix-a",                        "A. Documents Reviewed",                r"^APPENDIX A$"),
    ("appendix-b",                        "B. Persons Interviewed",               r"^APPENDIX B$"),
    ("appendix-c",                        "C. Assessment Team Members",           r"^APPENDIX C$"),
]

# Indent level in the rendered contents list, keyed by anchor id.
LEVEL = {
    "summary": 1, "methods-and-criteria": 1, "assessment": 1,
    "conclusions-and-recommendations": 1,
    "methods-scope": 2, "methods-method": 2, "methods-document-review": 2,
    "methods-interviews": 2, "methods-criteria": 2,
    "assessment-introduction": 2, "assessment-against-criteria": 2,
    "appendix-a": 2, "appendix-b": 2, "appendix-c": 2,
}
LEVEL.update({a: 3 for a, _, _ in SECTIONS if a.startswith("criterion-")})

TOC_CSS = """    .toc { margin-bottom: 2rem; }
    .toc p { font-weight: 600; margin-bottom: 0.5rem; }
    .toc ul { list-style: none; margin: 0; padding: 0; }
    .toc li { margin: 0.2rem 0; line-height: 1.5; }
    .toc-1 { margin-top: 0.5rem; }
    .toc-2 { padding-left: 1.25rem; }
    .toc-3 { padding-left: 2.5rem; }
    .toc-label { color: #374151; }
    .ocr-text [id] { scroll-margin-top: 1.5rem; }
"""

SECTION_CSS = """    .ocr-text a.sec { font-weight: 600; color: #1d4ed8; text-decoration: none; }
    .ocr-text a.sec:hover { color: #1e40af; text-decoration: underline; }
"""

# Headings printed in full capitals that are genuinely section headings. Listed
# explicitly so the title block and the "H. G. RICKOVER" signature are left alone.
ALLCAPS_HEADINGS = {
    "PREFACE",
    "DOCUMENTS REVIEWED", "PERSONS INTERVIEWED", "ASSESSMENT TEAM MEMBERS",
    "GPU NUCLEAR MANAGEMENT", "TMI-1 MANAGEMENT", "OYSTER CREEK MANAGEMENT",
}

# Enumerator, then the heading's own title, then the period that closes it.
# "A. Scope. This is an assessment..." yields "A. Scope."
LEAD_RE = re.compile(r"^((?:\(\d\)|[A-E]\.|(?:I{1,3}|IV)\.)\s*[^.]*\.)")


def heading_span(text, idx, first_appendix):
    """Return the leading substring of `text` to mark, or None to leave it be.

    `first_appendix` guards the person lists: Appendix B entries such as
    "E. E. Kintner, Vice-President/Director, Administration" and "D. Smith,
    Senior Reactor Operator" are indistinguishable by shape from subsection
    headings like "D. Interviews.", so letter-enumerated headings are only
    recognised before the appendices begin.
    """
    if text in ALLCAPS_HEADINGS or re.match(r"^APPENDIX [ABC]$", text):
        return text
    if re.match(r"^(I{1,3}|IV)\.\s", text) or re.match(r"^\(\d\)\s+[A-Z]", text):
        pass
    elif re.match(r"^[A-E]\.\s", text) and idx < first_appendix:
        pass
    else:
        return None
    m = LEAD_RE.match(text)
    return m.group(1) if m else text


QUOTE_CSS = """    .ocr-text blockquote.quote { margin: 1rem 0 1rem 1.5rem; padding-left: 1rem;
      border-left: 3px solid #d1d5db; color: #374151; line-height: 1.75; }
    .ocr-text blockquote.quote + blockquote.quote { margin-top: -0.5rem; }
    .ocr-text blockquote.quote .cit { display: block; margin-top: 0.35rem;
      font-size: 0.875rem; color: #6b7280; }
"""

APPENDIX_CSS = """    .ocr-text p.person { margin-bottom: 0.6rem; line-height: 1.5; }
    .ocr-text p.person .pname { display: block; font-weight: 600; }
    .ocr-text p.person .prole { display: block; padding-left: 1.25rem; color: #4b5563; }
    .ocr-text p.bioname { font-weight: 600; margin-top: 1.75rem; margin-bottom: 0.4rem; }
    .ocr-text p.degrees { color: #4b5563; }
"""

# Source citations that trail a quoted passage, e.g. "(Kemeny, page 71, para 3.d)".
CITE_RE = re.compile(r"\s*(\((?:Kemeny|Rogovin)[^)]*\))\s*$", re.I)

# A Kemeny recommendation that the original breaks across a page, leaving a
# stray closing quote mark mid-sentence. Rejoined into one passage.
SPLIT_HEAD = 'should be required"'
SPLIT_TAIL = "to train regularly on the simulator."

# Appendix B prints a name, then that person's role on the next line. The OCR
# joins them with a comma; this splits them back apart. Handles plain initials
# ("R. C. Arnold"), spelled-out first names ("Frank Ciganik") and generational
# suffixes ("J. L. Sullivan, Jr.").
PERSON_RE = re.compile(
    r"^((?:(?:[A-Z]\.\s*){1,3}|(?:[A-Z][a-z]+\s+))[A-Z][A-Za-z'\u2019-]+"
    r"(?:,\s*(?:Jr|Sr|II|III)\.?)?),\s*(.+)$"
)
APPENDIX_B_GROUPS = {"GPU NUCLEAR MANAGEMENT", "TMI-1 MANAGEMENT", "OYSTER CREEK MANAGEMENT"}
BIO_NAME_RE = re.compile(r"^[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][A-Za-z'\u2019-]+$")
DEGREES_RE = re.compile(r"^B\.\s?[A-Z]\.,")


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def read_body(html):
    """Return (match, body, paragraph matches, paragraph texts) for the ocr-text div."""
    div = re.search(r'(<div class="ocr-text text-gray-800">)(.*?)(\n?\s*</div>)', html, re.S)
    if not div:
        sys.exit("ERROR: could not find the ocr-text div")
    body = div.group(2)
    paras = list(re.finditer(r"<p(?:\s[^>]*)?>(.*?)</p>", body, re.S))
    return div, body, paras, [strip_tags(m.group(1)) for m in paras]


def add_style(html, css):
    """Insert a css block after the existing .ocr-text paragraph rule."""
    rule = "    .ocr-text p { margin-bottom: 1rem; line-height: 1.75; }\n"
    if rule not in html:
        sys.exit("ERROR: could not find the .ocr-text style rule to extend")
    return html.replace(rule, rule + css, 1)


def apply_edits(body, edits):
    """Apply (start, end, replacement) edits back to front so offsets stay valid."""
    for start, end, repl in sorted(edits, key=lambda e: e[0], reverse=True):
        body = body[:start] + repl + body[end:]
    return body


def link_contents(html):
    """Pass 1: replace the transcribed contents with a linked nav, and id the targets."""
    if 'id="table-of-contents"' in html:
        print("Pass 1: contents links already present.")
        return html

    div, body, paras, texts = read_body(html)

    try:
        toc_start = next(i for i, t in enumerate(texts) if t.upper() == "TABLE OF CONTENTS")
        toc_end = next(i for i, t in enumerate(texts) if i > toc_start and t.upper() == "PREFACE")
    except StopIteration:
        sys.exit("ERROR: could not delimit the table of contents (expected TABLE OF CONTENTS .. PREFACE)")

    targets, cursor = {}, toc_end
    for anchor, _label, pattern in SECTIONS:
        idx = next((i for i in range(cursor, len(texts)) if re.match(pattern, texts[i])), None)
        if idx is None:
            sys.exit(f"ERROR: no body heading matched {anchor} (/{pattern}/) at or after paragraph {cursor}")
        targets[anchor] = idx
        cursor = idx

    items = []
    for anchor, label, _ in SECTIONS:
        if anchor == "appendix-a":   # group heading, as printed in the original
            items.append('            <li class="toc-1 toc-label">APPENDICES</li>')
        items.append(f'            <li class="toc-{LEVEL[anchor]}"><a href="#{anchor}">{label}</a></li>')

    nav = (
        '<nav id="table-of-contents" class="toc" aria-label="Table of contents">\n'
        '          <p>TABLE OF CONTENTS</p>\n'
        '          <ul>\n' + "\n".join(items) + '\n          </ul>\n'
        '        </nav>'
    )

    edits = []
    for anchor, idx in targets.items():
        m = paras[idx]
        opening = re.match(r"<p(\s[^>]*)?>", m.group(0)).group(0)
        if "id=" in opening:
            sys.exit(f"ERROR: paragraph {idx} already carries an id")
        edits.append((m.start(), m.start() + len(opening), opening[:-1] + f' id="{anchor}">'))
    edits.append((paras[toc_start].start(), paras[toc_end - 1].end(), nav))

    html = html[:div.start(2)] + apply_edits(body, edits) + html[div.end(2):]
    html = add_style(html, TOC_CSS)
    print(f"Pass 1: {len(SECTIONS)} contents links, {len(targets)} anchors "
          f"(paragraphs {min(targets.values())}-{max(targets.values())})")
    return html


def mark_sections(html):
    """Pass 2: mark each body section heading, linked back to the contents."""
    if 'class="sec"' in html:
        print("Pass 2: section marks already present.")
        return html

    div, body, paras, texts = read_body(html)

    first_appendix = next((i for i, t in enumerate(texts) if t == "APPENDIX A"), None)
    if first_appendix is None:
        sys.exit("ERROR: could not find APPENDIX A, needed to bound the person lists")

    edits, marked = [], []
    for i, (m, text) in enumerate(zip(paras, texts)):
        span = heading_span(text, i, first_appendix)
        if not span:
            continue
        inner = m.group(1)
        # Only mark a heading sitting at the very start of the paragraph's text.
        if not inner.lstrip().startswith(span):
            print(f"  skipped [{i}]: {span[:50]!r} is not at the paragraph start")
            continue
        offset = m.start(1) + inner.index(span)
        link = f'<a class="sec" href="#table-of-contents">{span}</a>'
        edits.append((offset, offset + len(span), link))
        marked.append((i, span))

    html = html[:div.start(2)] + apply_edits(body, edits) + html[div.end(2):]
    html = add_style(html, SECTION_CSS)
    print(f"Pass 2: marked {len(marked)} section headings")
    for i, span in marked:
        print(f"    [{i:>3}] {span}")
    return html


def join_split_quote(html):
    """Pass 3: rejoin the Kemeny quote the original breaks across a page."""
    if SPLIT_HEAD not in html:
        print("Pass 3: split quote already joined.")
        return html

    div, body, paras, texts = read_body(html)
    hits = [i for i, t in enumerate(texts)
            if t.endswith(SPLIT_HEAD) and i + 1 < len(texts) and texts[i + 1].startswith(SPLIT_TAIL)]
    if len(hits) != 1:
        sys.exit(f"ERROR: expected exactly one split quote, found {len(hits)}")
    i = hits[0]

    head, tail = paras[i], paras[i + 1]
    merged = head.group(1).rstrip()
    if not merged.endswith('"'):
        sys.exit("ERROR: split quote head does not end with a quote mark")
    merged = merged[:-1].rstrip() + " " + tail.group(1).strip()   # drop the stray mark

    body = apply_edits(body, [(head.start(1), tail.end(), merged + "</p>")])
    print(f"Pass 3: joined the quote split across paragraphs {i} and {i+1}")
    return html[:div.start(2)] + body + html[div.end(2):]


def mark_quotes(html):
    """Pass 4: set the quoted passages as indented quote blocks."""
    if 'blockquote class="quote"' in html:
        print("Pass 4: quote blocks already present.")
        return html

    div, body, paras, texts = read_body(html)

    edits, quoted = [], []
    for i, (m, text) in enumerate(zip(paras, texts)):
        if not (text.startswith('"') or CITE_RE.search(text)):
            continue
        if "id=" in m.group(0) or 'class="sec"' in m.group(0):
            print(f"  skipped [{i}]: paragraph carries an anchor or section mark")
            continue
        inner = m.group(1).strip()
        cite = CITE_RE.search(inner)
        if cite:
            inner = inner[: cite.start()].rstrip() + f'<cite class="cit">{cite.group(1)}</cite>'
        edits.append((m.start(), m.end(), f'<blockquote class="quote">{inner}</blockquote>'))
        quoted.append((i, bool(cite), texts[i][:58]))

    body = apply_edits(body, edits)
    html = html[:div.start(2)] + body + html[div.end(2):]
    html = add_style(html, QUOTE_CSS)
    print(f"Pass 4: set {len(quoted)} quote blocks ({sum(1 for _, c, _ in quoted if c)} with citations)")
    for i, c, t in quoted:
        print(f"    [{i:>3}]{' cite' if c else '     '} {t}")
    return html


def format_appendices(html):
    """Pass 5: restore the original's layout for the person list and biographies."""
    if 'class="person"' in html:
        print("Pass 5: appendix formatting already present.")
        return html

    div, body, paras, texts = read_body(html)

    def find(label):
        idx = next((i for i, t in enumerate(texts) if t == label), None)
        if idx is None:
            sys.exit(f"ERROR: could not find {label!r}")
        return idx

    b_start, c_start = find("PERSONS INTERVIEWED"), find("ASSESSMENT TEAM MEMBERS")

    edits, people, bios, degrees = [], 0, [], 0

    # Appendix B: name on its own line, role indented beneath it.
    for i in range(b_start + 1, c_start - 1):
        text = texts[i]
        if text in APPENDIX_B_GROUPS or not text:
            continue
        m = PERSON_RE.match(text)
        if not m:
            print(f"  unsplit [{i}]: {text[:70]}")
            continue
        name, role = m.group(1), m.group(2)
        edits.append((paras[i].start(), paras[i].end(),
                      f'<p class="person"><span class="pname">{name}</span>'
                      f'<span class="prole">{role}</span></p>'))
        people += 1

    # Appendix C: biography name as a heading, degrees set as a secondary line.
    for i in range(c_start + 1, len(texts)):
        text, m = texts[i], paras[i]
        if BIO_NAME_RE.match(text):
            edits.append((m.start(), m.end(), f'<p class="bioname">{m.group(1).strip()}</p>'))
            bios.append(text)
        elif DEGREES_RE.match(text):
            edits.append((m.start(), m.end(), f'<p class="degrees">{m.group(1).strip()}</p>'))
            degrees += 1

    body = apply_edits(body, edits)
    html = html[:div.start(2)] + body + html[div.end(2):]
    html = add_style(html, APPENDIX_CSS)
    print(f"Pass 5: {people} person entries split; {len(bios)} biographies, {degrees} degree lines")
    for n in bios:
        print(f"    bio: {n}")
    return html


def main():
    html = POST.read_text(encoding="utf-8")
    before = html
    html = link_contents(html)
    html = mark_sections(html)
    html = join_split_quote(html)
    html = mark_quotes(html)
    html = format_appendices(html)
    if html == before:
        print("Nothing to do.")
        return 0
    POST.write_text(html, encoding="utf-8")
    print(f"Wrote {POST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
