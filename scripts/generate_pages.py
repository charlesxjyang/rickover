#!/usr/bin/env python3
"""Generate blog.html index and individual post pages from manifest.json."""

import json
import html
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT_DIR / "manifest.json"
POSTS_DIR = ROOT_DIR / "posts"


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:120]


def generate_post(entry: dict) -> str:
    title = html.escape(entry.get("Title", "Untitled"))
    year = entry.get("Year", "Unknown")
    doc_type = html.escape(entry.get("Type", "Document"))
    summary = html.escape(entry.get("Summary", ""))
    pdf_url = entry.get("file_pdf", "")
    ocr_url = entry.get("file_OCR", "")
    source = entry.get("Source", "")
    meta_desc = summary[:160].replace('"', "&quot;")

    if source.startswith("http"):
        source_html = '<a href="' + html.escape(source) + '" target="_blank" class="text-blue-600 underline">' + html.escape(source) + '</a>'
    else:
        source_html = html.escape(source) if source else ""

    source_line = "<span>Source: " + source_html + "</span>" if source else ""

    ocr_link = ""
    if ocr_url:
        ocr_link = '<a href="' + html.escape(ocr_url) + '" target="_blank">View Original TXT</a>'

    ocr_placeholder = (
        '<p class="text-gray-500 italic">Full OCR text will be available after running the pipeline. '
        'In the meantime, you can <a href="' + html.escape(ocr_url) + '" target="_blank">view the existing TXT file</a> '
        'or <a href="' + html.escape(pdf_url) + '" target="_blank">view the original PDF</a>.</p>'
    )

    parts = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '  <title>' + title + ' — The Rickover Corpus</title>',
        '  <meta name="description" content="' + meta_desc + '">',
        '  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">',
        '  <link rel="icon" type="image/png" href="/assets/rickover_favicon.png" sizes="256x256">',
        '  <style>',
        '    a { color: #1d4ed8; text-decoration: underline; }',
        '    a:hover { color: #1e40af; }',
        '    .ocr-text p { margin-bottom: 1rem; line-height: 1.75; }',
        '  </style>',
        '  <!-- Google tag (gtag.js) -->',
        '  <script async src="https://www.googletagmanager.com/gtag/js?id=G-M0H8BLJN0S"></script>',
        '  <script>',
        '    window.dataLayer = window.dataLayer || [];',
        '    function gtag(){dataLayer.push(arguments);}',
        "    gtag('js', new Date());",
        "    gtag('config', 'G-M0H8BLJN0S');",
        '  </script>',
        '</head>',
        '<body class="bg-gray-50 text-gray-900 font-sans">',
        '',
        '  <nav class="max-w-3xl mx-auto px-4 py-6 flex space-x-4 text-sm">',
        '    <a href="/index.html">&larr; Archive</a>',
        '    <a href="/blog.html">&larr; Blog Index</a>',
        '  </nav>',
        '',
        '  <article class="max-w-3xl mx-auto px-4 pb-12">',
        '    <header class="mb-8">',
        '      <h1 class="text-3xl font-bold tracking-tight mb-3">' + title + '</h1>',
        '      <div class="flex flex-wrap gap-3 text-sm text-gray-600 mb-4">',
        '        <span class="bg-gray-200 px-2 py-1 rounded">' + str(year) + '</span>',
        '        <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded">' + doc_type + '</span>',
        '        ' + source_line,
        '      </div>',
        '      <div class="flex space-x-4 text-sm">',
        '        <a href="' + html.escape(pdf_url) + '" target="_blank">View Original PDF</a>',
        '        ' + ocr_link,
        '      </div>',
        '    </header>',
        '',
        '    <section class="bg-white border border-gray-200 rounded-lg p-6 mb-8 shadow-sm">',
        '      <h2 class="text-lg font-semibold mb-2">Summary</h2>',
        '      <p class="text-gray-700 leading-relaxed">' + summary + '</p>',
        '    </section>',
        '',
        '    <section>',
        '      <h2 class="text-lg font-semibold mb-4">Full Text (OCR)</h2>',
        '      <div class="ocr-text text-gray-800">',
        '        ' + ocr_placeholder,
        '      </div>',
        '    </section>',
        '  </article>',
        '',
        '  <footer class="mt-12 border-t border-gray-300 pt-6 pb-8 text-sm max-w-3xl mx-auto px-4 text-center text-gray-600">',
        '    <p>',
        '      This project was compiled and digitized by <a href="https://charlesyang.io" target="_blank">Charles Yang</a>',
        '      under the <a href="https://industrialstrategy.org" target="_blank">Center for Industrial Strategy</a>.',
        '    </p>',
        '    <a href="https://www.industrialstrategy.org" target="_blank" class="mt-4 inline-block">',
        '      <img src="/assets/CIS_logo.png" alt="CIS Logo" class="h-10 w-auto mx-auto"',
        '           style="clip-path: inset(1px 1px 1px 1px);">',
        '    </a>',
        '  </footer>',
        '',
        '</body>',
        '</html>',
    ]
    return "\n".join(parts)


def generate_blog_index(entries: list) -> str:
    sorted_entries = sorted(entries, key=lambda e: (-e.get("Year", 0), e.get("Title", "")))

    cards = []
    for entry in sorted_entries:
        title = html.escape(entry.get("Title", "Untitled"))
        year = entry.get("Year", "Unknown")
        doc_type = html.escape(entry.get("Type", "Document"))
        summary = entry.get("Summary", "")
        preview = html.escape(summary[:200]) + ("..." if len(summary) > 200 else "")
        slug = slugify(entry.get("Title", "untitled"))
        post_url = "posts/" + slug + ".html"

        card = (
            '      <a href="' + post_url + '" class="block bg-white border border-gray-200 rounded-lg p-5 shadow-sm hover:shadow-md transition-shadow no-underline"'
            ' data-title="' + title + '"'
            ' data-summary="' + html.escape(summary[:300]) + '"'
            ' data-year="' + str(year) + '"'
            ' data-type="' + doc_type + '">\n'
            '        <div class="flex items-start justify-between mb-2">\n'
            '          <h2 class="text-lg font-semibold text-gray-900" style="text-decoration:none">' + title + '</h2>\n'
            '        </div>\n'
            '        <div class="flex gap-2 mb-3 text-sm">\n'
            '          <span class="bg-gray-200 px-2 py-0.5 rounded text-gray-700">' + str(year) + '</span>\n'
            '          <span class="bg-blue-100 text-blue-800 px-2 py-0.5 rounded">' + doc_type + '</span>\n'
            '        </div>\n'
            '        <p class="text-sm text-gray-600 leading-relaxed" style="text-decoration:none">' + preview + '</p>\n'
            '      </a>'
        )
        cards.append(card)

    cards_html = "\n".join(cards)

    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog — The Rickover Corpus</title>
  <meta name="description" content="Browse Admiral Hyman G. Rickover's speeches, congressional testimonies, and memos in full text.">
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
  <link rel="icon" type="image/png" href="/assets/rickover_favicon.png" sizes="256x256">
  <style>
    a { color: #1d4ed8; text-decoration: underline; }
    a:hover { color: #1e40af; }
    a.no-underline { text-decoration: none; }
    a.no-underline:hover { text-decoration: none; }
  </style>
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-M0H8BLJN0S"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-M0H8BLJN0S');
  </script>
</head>
<body class="bg-gray-50 text-gray-900 font-sans">

  <header class="py-8 bg-gray-50">
    <div class="max-w-5xl mx-auto px-4 text-center">
      <img src="assets/rickover.jpg" alt="Rickover"
           class="w-28 h-28 rounded-full border border-gray-300 object-cover shadow-sm mx-auto mb-4">
      <h1 class="text-3xl font-bold tracking-tight">The Rickover Corpus</h1>
      <p class="text-sm text-gray-600 italic mb-4">Full-text archive of Admiral Rickover's documents</p>
      <nav class="text-sm space-x-4">
        <a href="index.html">&larr; Back to Archive</a>
      </nav>
    </div>
  </header>

  <main class="max-w-4xl mx-auto px-4 pb-12">
    <input id="blogSearch" type="text" placeholder="Search documents..."
           class="w-full px-4 py-2 border border-gray-300 rounded mb-6">

    <p id="resultCount" class="text-sm text-gray-500 mb-4"></p>

    <div id="blogCards" class="space-y-4">
""" + cards_html + """
    </div>

    <p id="noResults" class="hidden text-center text-gray-500 mt-8">No documents match your search.</p>
  </main>

  <footer class="mt-12 border-t border-gray-300 pt-6 pb-8 text-sm max-w-5xl mx-auto px-4 text-center text-gray-600">
    <p>
      This project was compiled and digitized by <a href="https://charlesyang.io" target="_blank">Charles Yang</a>
      under the <a href="https://industrialstrategy.org" target="_blank">Center for Industrial Strategy</a>.
    </p>
    <a href="https://www.industrialstrategy.org" target="_blank" class="mt-4 inline-block">
      <img src="assets/CIS_logo.png" alt="CIS Logo" class="h-10 w-auto mx-auto"
           style="clip-path: inset(1px 1px 1px 1px);">
    </a>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/fuse.js@6.6.2"></script>
  <script>
    (function() {
      const cards = document.querySelectorAll('#blogCards > a');
      const searchInput = document.getElementById('blogSearch');
      const noResults = document.getElementById('noResults');
      const resultCount = document.getElementById('resultCount');

      const items = Array.from(cards).map((card, i) => ({
        title: card.dataset.title,
        summary: card.dataset.summary,
        year: card.dataset.year,
        type: card.dataset.type,
        index: i,
        element: card
      }));

      const fuse = new Fuse(items, {
        keys: ['title', 'summary', 'type'],
        threshold: 0.4,
        minMatchCharLength: 2
      });

      resultCount.textContent = items.length + ' documents';

      searchInput.addEventListener('input', function() {
        const query = this.value.trim();

        if (!query) {
          cards.forEach(c => c.style.display = '');
          noResults.classList.add('hidden');
          resultCount.textContent = items.length + ' documents';
          return;
        }

        const results = fuse.search(query);
        const matchedIndices = new Set(results.map(r => r.item.index));

        cards.forEach((card, i) => {
          card.style.display = matchedIndices.has(i) ? '' : 'none';
        });

        noResults.classList.toggle('hidden', results.length > 0);
        resultCount.textContent = results.length + ' of ' + items.length + ' documents';
      });
    })();
  </script>

</body>
</html>"""


def main():
    POSTS_DIR.mkdir(exist_ok=True)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"Loaded {len(manifest)} entries from manifest.json")

    # Generate individual post pages
    count = 0
    for entry in manifest:
        title = entry.get("Title", "Untitled")
        slug = slugify(title)
        post_path = POSTS_DIR / (slug + ".html")
        post_html = generate_post(entry)
        post_path.write_text(post_html, encoding="utf-8")
        count += 1

    print(f"Generated {count} post pages in posts/")

    # Generate blog index
    blog_html = generate_blog_index(manifest)
    blog_path = ROOT_DIR / "blog.html"
    blog_path.write_text(blog_html, encoding="utf-8")
    print("Generated blog.html")

    # Update manifest with blog_page fields
    for entry in manifest:
        slug = slugify(entry.get("Title", "untitled"))
        entry["blog_page"] = "posts/" + slug + ".html"

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print("Updated manifest.json with blog_page fields")


if __name__ == "__main__":
    main()
