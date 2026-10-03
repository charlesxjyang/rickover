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

Safe to re-run; it exits cleanly if the links are already in place.
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


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def main():
    html = POST.read_text(encoding="utf-8")

    if 'id="table-of-contents"' in html:
        print("Contents links already present — nothing to do.")
        return 0

    div = re.search(r'(<div class="ocr-text text-gray-800">)(.*?)(\n?\s*</div>)', html, re.S)
    if not div:
        sys.exit("ERROR: could not find the ocr-text div")
    body = div.group(2)

    paras = list(re.finditer(r"<p(?:\s[^>]*)?>(.*?)</p>", body, re.S))
    texts = [strip_tags(m.group(1)) for m in paras]

    # --- locate the transcribed contents block: "TABLE OF CONTENTS" .. "PREFACE"
    try:
        toc_start = next(i for i, t in enumerate(texts) if t.upper() == "TABLE OF CONTENTS")
        toc_end = next(i for i, t in enumerate(texts) if i > toc_start and t.upper() == "PREFACE")
    except StopIteration:
        sys.exit("ERROR: could not delimit the table of contents (expected TABLE OF CONTENTS .. PREFACE)")

    # --- resolve each section target, scanning forward past the contents block
    targets, cursor = {}, toc_end
    for anchor, label, pattern in SECTIONS:
        idx = next((i for i in range(cursor, len(texts)) if re.match(pattern, texts[i])), None)
        if idx is None:
            sys.exit(f"ERROR: no body heading matched {anchor} (/{pattern}/) at or after paragraph {cursor}")
        targets[anchor] = idx
        cursor = idx
    print(f"Resolved {len(targets)} section targets (paragraphs {min(targets.values())}-{max(targets.values())})")

    # --- build the replacement contents block
    items = []
    for anchor, label, _ in SECTIONS:
        if anchor == "appendix-a":   # group heading, as printed in the original
            items.append('            <li class="toc-1 toc-label">APPENDICES</li>')
        lvl = LEVEL[anchor]
        items.append(f'            <li class="toc-{lvl}"><a href="#{anchor}">{label}</a></li>')

    nav = (
        '<nav id="table-of-contents" class="toc" aria-label="Table of contents">\n'
        '          <p>TABLE OF CONTENTS</p>\n'
        '          <ul>\n' + "\n".join(items) + '\n          </ul>\n'
        '        </nav>'
    )

    # --- splice: replace the contents paragraphs, then add ids to the targets.
    # Work back to front so earlier offsets stay valid.
    edits = []
    for anchor, idx in targets.items():
        m = paras[idx]
        opening = re.match(r"<p(\s[^>]*)?>", m.group(0)).group(0)
        if "id=" in opening:
            sys.exit(f"ERROR: paragraph {idx} already carries an id")
        new_open = opening[:-1] + f' id="{anchor}">'
        edits.append((m.start(), m.start() + len(opening), new_open))

    edits.append((paras[toc_start].start(), paras[toc_end - 1].end(), nav))
    edits.sort(key=lambda e: e[0], reverse=True)

    for start, end, repl in edits:
        body = body[:start] + repl + body[end:]

    html = html[:div.start(2)] + body + html[div.end(2):]

    # --- add the contents styling next to the existing ocr-text rule
    rule = "    .ocr-text p { margin-bottom: 1rem; line-height: 1.75; }\n"
    if rule not in html:
        sys.exit("ERROR: could not find the .ocr-text style rule to extend")
    html = html.replace(rule, rule + TOC_CSS, 1)

    POST.write_text(html, encoding="utf-8")
    print(f"Wrote {POST.relative_to(ROOT)}: {len(SECTIONS)} contents links, {len(targets)} anchors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
