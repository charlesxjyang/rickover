#!/usr/bin/env python3
"""
Rickover Corpus OCR + Blog Generation Pipeline

Downloads PDFs from S3, OCRs them with Tesseract, and generates
blog-style HTML pages for each document.

Prerequisites:
    brew install tesseract poppler
    pip install pytesseract pdf2image requests Pillow
"""

import argparse
import json
import os
import re
import sys
import logging
import html
import tempfile
from pathlib import Path
from urllib.parse import unquote_plus

import requests
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT_DIR / "manifest.json"
OCR_OUTPUT_DIR = ROOT_DIR / "ocr_output"
POSTS_DIR = ROOT_DIR / "posts"

LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("pipeline")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(title: str) -> str:
    """Convert a title into a URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:120]


def download_pdf(url: str, dest: Path) -> bool:
    """Download a PDF from a public URL. Returns True on success."""
    if dest.exists():
        log.info("  PDF already downloaded: %s", dest.name)
        return True
    try:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        log.info("  Downloaded PDF: %s", dest.name)
        return True
    except Exception as e:
        log.error("  Failed to download %s: %s", url, e)
        return False


def preprocess_image(img: Image.Image) -> Image.Image:
    """Preprocess a page image for better OCR quality."""
    # Convert to grayscale
    img = img.convert("L")
    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)
    # Slight sharpen
    img = img.filter(ImageFilter.SHARPEN)
    return img


def ocr_pdf(pdf_path: Path, output_txt: Path) -> str:
    """Convert PDF to images, OCR each page, return full text."""
    if output_txt.exists():
        log.info("  OCR already done: %s", output_txt.name)
        return output_txt.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            images = convert_from_path(str(pdf_path), dpi=300, output_folder=tmpdir)
        except Exception as e:
            log.error("  PDF-to-image failed for %s: %s", pdf_path.name, e)
            return ""

        pages = []
        for i, img in enumerate(images, 1):
            processed = preprocess_image(img)
            text = pytesseract.image_to_string(processed)
            pages.append(text)
            if i % 10 == 0:
                log.info("    OCR page %d/%d", i, len(images))

    full_text = "\n\n--- Page Break ---\n\n".join(pages)
    output_txt.write_text(full_text, encoding="utf-8")
    log.info("  OCR complete: %d pages -> %s", len(pages), output_txt.name)
    return full_text


def format_ocr_text(raw_text: str) -> str:
    """Convert raw OCR text into HTML paragraphs."""
    if not raw_text.strip():
        return "<p class='text-gray-500 italic'>OCR text not available.</p>"

    # Split on page breaks and double newlines
    raw_text = raw_text.replace("--- Page Break ---", "\n\n")
    paragraphs = re.split(r"\n\s*\n", raw_text)

    html_parts = []
    for p in paragraphs:
        text = p.strip()
        if not text:
            continue
        # Escape HTML entities
        text = html.escape(text)
        # Preserve single newlines within a paragraph
        text = text.replace("\n", "<br>")
        html_parts.append(f"<p>{text}</p>")

    return "\n".join(html_parts)


def generate_post_html(entry: dict, ocr_text: str, slug: str) -> str:
    """Generate a blog-style HTML page for a single document."""
    title = html.escape(entry.get("Title", "Untitled"))
    year = entry.get("Year", "Unknown")
    doc_type = html.escape(entry.get("Type", "Document"))
    summary = html.escape(entry.get("Summary", ""))
    pdf_url = entry.get("file_pdf", "")
    ocr_url = entry.get("file_OCR", "")
    source = entry.get("Source", "")

    # Truncate summary for meta description
    meta_desc = summary[:160].replace('"', "&quot;")

    formatted_text = format_ocr_text(ocr_text)

    # Source link: if it's a URL, make it clickable
    if source.startswith("http"):
        source_html = f'<a href="{html.escape(source)}" target="_blank" class="text-blue-600 underline">{html.escape(source)}</a>'
    else:
        source_html = html.escape(source) if source else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — The Rickover Corpus</title>
  <meta name="description" content="{meta_desc}">
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
  <link rel="icon" type="image/png" href="/assets/rickover_favicon.png" sizes="256x256">
  <style>
    a {{ color: #1d4ed8; text-decoration: underline; }}
    a:hover {{ color: #1e40af; }}
    .ocr-text p {{ margin-bottom: 1rem; line-height: 1.75; }}
  </style>
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-M0H8BLJN0S"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-M0H8BLJN0S');
  </script>
</head>
<body class="bg-gray-50 text-gray-900 font-sans">

  <nav class="max-w-3xl mx-auto px-4 py-6 flex space-x-4 text-sm">
    <a href="/index.html">&larr; Archive</a>
    <a href="/blog.html">&larr; Blog Index</a>
  </nav>

  <article class="max-w-3xl mx-auto px-4 pb-12">
    <header class="mb-8">
      <h1 class="text-3xl font-bold tracking-tight mb-3">{title}</h1>
      <div class="flex flex-wrap gap-3 text-sm text-gray-600 mb-4">
        <span class="bg-gray-200 px-2 py-1 rounded">{year}</span>
        <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded">{doc_type}</span>
        {f'<span>Source: {source_html}</span>' if source else ''}
      </div>
      <div class="flex space-x-4 text-sm">
        <a href="{html.escape(pdf_url)}" target="_blank">View Original PDF</a>
        {f'<a href="{html.escape(ocr_url)}" target="_blank">View Original TXT</a>' if ocr_url else ''}
      </div>
    </header>

    <section class="bg-white border border-gray-200 rounded-lg p-6 mb-8 shadow-sm">
      <h2 class="text-lg font-semibold mb-2">Summary</h2>
      <p class="text-gray-700 leading-relaxed">{summary}</p>
    </section>

    <section>
      <h2 class="text-lg font-semibold mb-4">Full Text (OCR)</h2>
      <div class="ocr-text text-gray-800">
        {formatted_text}
      </div>
    </section>
  </article>

  <footer class="mt-12 border-t border-gray-300 pt-6 pb-8 text-sm max-w-3xl mx-auto px-4 text-center text-gray-600">
    <p>
      This project was compiled and digitized by <a href="https://charlesyang.io" target="_blank">Charles Yang</a>
      under the <a href="https://industrialstrategy.org" target="_blank">Center for Industrial Strategy</a>.
    </p>
    <a href="https://www.industrialstrategy.org" target="_blank" class="mt-4 inline-block">
      <img src="/assets/CIS_logo.png" alt="CIS Logo" class="h-10 w-auto mx-auto"
           style="clip-path: inset(1px 1px 1px 1px);">
    </a>
  </footer>

</body>
</html>"""


def generate_blog_index(entries: list[dict]):
    """Generate blog.html — the blog index page listing all documents."""
    # Sort by year descending, then title
    sorted_entries = sorted(entries, key=lambda e: (-e.get("Year", 0), e.get("Title", "")))

    cards_html = []
    for entry in sorted_entries:
        title = html.escape(entry.get("Title", "Untitled"))
        year = entry.get("Year", "Unknown")
        doc_type = html.escape(entry.get("Type", "Document"))
        summary = entry.get("Summary", "")
        # Truncate summary for card preview
        preview = html.escape(summary[:200]) + ("..." if len(summary) > 200 else "")
        slug = slugify(entry.get("Title", "untitled"))
        post_url = f"posts/{slug}.html"

        cards_html.append(f"""
      <a href="{post_url}" class="block bg-white border border-gray-200 rounded-lg p-5 shadow-sm hover:shadow-md transition-shadow no-underline" data-title="{title}" data-summary="{html.escape(summary[:300])}" data-year="{year}" data-type="{doc_type}">
        <div class="flex items-start justify-between mb-2">
          <h2 class="text-lg font-semibold text-gray-900" style="text-decoration:none">{title}</h2>
        </div>
        <div class="flex gap-2 mb-3 text-sm">
          <span class="bg-gray-200 px-2 py-0.5 rounded text-gray-700">{year}</span>
          <span class="bg-blue-100 text-blue-800 px-2 py-0.5 rounded">{doc_type}</span>
        </div>
        <p class="text-sm text-gray-600 leading-relaxed" style="text-decoration:none">{preview}</p>
      </a>""")

    blog_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog — The Rickover Corpus</title>
  <meta name="description" content="Browse Admiral Hyman G. Rickover's speeches, congressional testimonies, and memos in full text.">
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
  <link rel="icon" type="image/png" href="/assets/rickover_favicon.png" sizes="256x256">
  <style>
    a {{ color: #1d4ed8; text-decoration: underline; }}
    a:hover {{ color: #1e40af; }}
    a.no-underline {{ text-decoration: none; }}
    a.no-underline:hover {{ text-decoration: none; }}
  </style>
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-M0H8BLJN0S"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
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
      {"".join(cards_html)}
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
    (function() {{
      const cards = document.querySelectorAll('#blogCards > a');
      const searchInput = document.getElementById('blogSearch');
      const noResults = document.getElementById('noResults');
      const resultCount = document.getElementById('resultCount');

      // Build search data from card data attributes
      const items = Array.from(cards).map((card, i) => ({{
        title: card.dataset.title,
        summary: card.dataset.summary,
        year: card.dataset.year,
        type: card.dataset.type,
        index: i,
        element: card
      }}));

      const fuse = new Fuse(items, {{
        keys: ['title', 'summary', 'type'],
        threshold: 0.4,
        minMatchCharLength: 2
      }});

      resultCount.textContent = items.length + ' documents';

      searchInput.addEventListener('input', function() {{
        const query = this.value.trim();

        if (!query) {{
          cards.forEach(c => c.style.display = '');
          noResults.classList.add('hidden');
          resultCount.textContent = items.length + ' documents';
          return;
        }}

        const results = fuse.search(query);
        const matchedIndices = new Set(results.map(r => r.item.index));

        cards.forEach((card, i) => {{
          card.style.display = matchedIndices.has(i) ? '' : 'none';
        }});

        noResults.classList.toggle('hidden', results.length > 0);
        resultCount.textContent = results.length + ' of ' + items.length + ' documents';
      }});
    }})();
  </script>

</body>
</html>"""

    blog_path = ROOT_DIR / "blog.html"
    blog_path.write_text(blog_html, encoding="utf-8")
    log.info("Generated blog index: %s", blog_path)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def get_page_count(pdf_path: Path) -> int:
    """Get the number of pages in a PDF without converting."""
    try:
        info = pdfinfo_from_path(str(pdf_path))
        return info.get("Pages", 0)
    except Exception:
        return 0


def main():
    parser = argparse.ArgumentParser(description="Rickover Corpus OCR pipeline")
    parser.add_argument("--max-pages", type=int, default=0,
                        help="Skip PDFs with more than this many pages (0 = no limit)")
    parser.add_argument("--types", nargs="*", default=None,
                        help="Only process these document types (e.g. Speech Memo Interview)")
    args = parser.parse_args()

    OCR_OUTPUT_DIR.mkdir(exist_ok=True)
    POSTS_DIR.mkdir(exist_ok=True)

    # Load manifest
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    log.info("Loaded manifest with %d entries", len(manifest))
    if args.max_pages:
        log.info("Skipping PDFs with more than %d pages", args.max_pages)
    if args.types:
        log.info("Filtering to types: %s", ", ".join(args.types))

    # Track slugs for manifest update
    updated_manifest = []
    processed = 0
    skipped_type = 0
    skipped_pages = 0

    for i, entry in enumerate(manifest, 1):
        title = entry.get("Title", "Untitled")
        pdf_url = entry.get("file_pdf", "")
        doc_type = entry.get("Type", "")

        # Filter by type
        if args.types and doc_type not in args.types:
            log.info("[%d/%d] Skipping (type %s): %s", i, len(manifest), doc_type, title)
            entry["blog_page"] = entry.get("blog_page", "")
            updated_manifest.append(entry)
            skipped_type += 1
            continue

        log.info("[%d/%d] Processing: %s", i, len(manifest), title)

        if not pdf_url:
            log.warning("  No PDF URL, skipping")
            entry["blog_page"] = entry.get("blog_page", "")
            updated_manifest.append(entry)
            continue

        slug = slugify(title)

        # Derive local filename from URL
        pdf_filename = unquote_plus(pdf_url.split("/")[-1])
        pdf_path = OCR_OUTPUT_DIR / pdf_filename
        txt_filename = Path(pdf_filename).stem + ".txt"
        txt_path = OCR_OUTPUT_DIR / txt_filename
        post_path = POSTS_DIR / f"{slug}.html"

        # Skip if post already exists and has OCR text
        if post_path.exists() and txt_path.exists():
            log.info("  Already processed, skipping")
            ocr_text = txt_path.read_text(encoding="utf-8")
        else:
            # Download PDF
            if not download_pdf(pdf_url, pdf_path):
                entry["blog_page"] = entry.get("blog_page", "")
                updated_manifest.append(entry)
                continue

            # Check page count before OCR
            if args.max_pages:
                pages = get_page_count(pdf_path)
                if pages > args.max_pages:
                    log.info("  Skipping: %d pages (limit %d)", pages, args.max_pages)
                    pdf_path.unlink(missing_ok=True)
                    entry["blog_page"] = entry.get("blog_page", "")
                    updated_manifest.append(entry)
                    skipped_pages += 1
                    continue

            # OCR the PDF
            ocr_text = ocr_pdf(pdf_path, txt_path)

        # Generate blog post HTML
        post_html = generate_post_html(entry, ocr_text, slug)
        post_path.write_text(post_html, encoding="utf-8")
        log.info("  Generated post: %s", post_path.name)

        entry["blog_page"] = f"posts/{slug}.html"
        updated_manifest.append(entry)
        processed += 1

    # Generate blog index
    generate_blog_index(updated_manifest)

    # Update manifest with blog_page fields
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_manifest, f, indent=2, ensure_ascii=False)
    log.info("Updated manifest.json with blog_page fields")

    # Clean up downloaded PDFs to save space (keep OCR text)
    for pdf_file in OCR_OUTPUT_DIR.glob("*.pdf"):
        pdf_file.unlink()
        log.info("Cleaned up PDF: %s", pdf_file.name)

    log.info("Pipeline complete!")
    log.info("  Processed: %d | Skipped (type): %d | Skipped (pages): %d",
             processed, skipped_type, skipped_pages)


if __name__ == "__main__":
    main()
