#!/usr/bin/env python3
"""
Add theme tags to Gemini-processed posts.
Removes Source and Type tags, replaces with thematic tags.
Updates manifest.json, post HTML files, and blog.html.
"""

import json
import re
import html as html_lib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.json"
POSTS_DIR = ROOT / "posts"

# Theme assignments by title keyword matching
THEME_MAP = {
    "1979 management magazine": ["Management", "Leadership"],
    "purpose of education": ["Education"],
    "some thoughts on the future": ["Government"],
    "accounting practices": ["Accountability", "Government"],
    "paper reactor memo": ["Navy", "Engineering"],
    "meaning of nautilus polar voyage": ["Navy"],
    "memo of conversation with jimmy carter": ["Government", "Navy"],
    "personal accountability in financial management": ["Accountability", "Government"],
    "humanistic technology": ["Technology", "Society"],
    "role of the critic": ["Society", "Education"],
    "lawyers versus society": ["Society", "Law"],
    "role of professional man": ["Society", "Work"],
    "energy speech at athens": ["Energy"],
    "nuclear power and bremerton": ["Navy", "Energy"],
    "rickover and education": ["Education"],
    "democracy and competence": ["Government", "Education"],
    "doing a job": ["Management", "Leadership"],
    "mans purpose in life": ["Society"],
    "what are schools for": ["Education"],
    "talented mind": ["Education"],
    "in defense of truth": ["Society", "Education"],
    "environmental perspective": ["Energy", "Environment"],
    "significance of electricity": ["Energy", "Technology"],
    "meaning of a university": ["Education"],
    "intellect in a democracy": ["Education", "Government"],
    "who protects the public": ["Accountability", "Government"],
    "summary of president nixon": ["Government", "Navy"],
    "administering large projects": ["Management", "Navy"],
    "our naval revolution": ["Navy", "Technology"],
    "americas goals": ["Society", "Education"],
    "never ending challenge": ["Navy", "Management"],
    "fact and fiction in american education": ["Education"],
    "technology and the citizen": ["Technology", "Society"],
    "nationsal scholastic standard": ["Education"],
    "freedom and the knowledge gap": ["Education", "Society"],
    "liberty, science, and law": ["Society", "Law"],
    "role of engineering in the navy": ["Navy", "Engineering"],
    "decline of the individual": ["Society"],
    "illusions cost too much": ["Navy", "Accountability"],
    "energy - a diminishing": ["Energy"],
    "business and freedom": ["Society", "Work"],
    "education and patriotism": ["Education"],
}

THEME_COLORS = {
    "Energy": "bg-yellow-100 text-yellow-800",
    "Navy": "bg-blue-100 text-blue-800",
    "Education": "bg-green-100 text-green-800",
    "Management": "bg-purple-100 text-purple-800",
    "Leadership": "bg-purple-100 text-purple-800",
    "Government": "bg-red-100 text-red-800",
    "Technology": "bg-indigo-100 text-indigo-800",
    "Society": "bg-pink-100 text-pink-800",
    "Accountability": "bg-orange-100 text-orange-800",
    "Engineering": "bg-blue-100 text-blue-800",
    "Law": "bg-gray-100 text-gray-800",
    "Environment": "bg-green-100 text-green-800",
    "Work": "bg-purple-100 text-purple-800",
}


def get_themes(title):
    """Get themes for a post title."""
    lower = title.lower()
    for key, themes in THEME_MAP.items():
        if key in lower:
            return themes
    return []


def update_post_html(post_path, year, themes):
    """Update a post HTML file: remove Source/Type, add theme tags."""
    content = post_path.read_text(encoding='utf-8')
    original = content

    # Replace the metadata div: year + type + source → year + themes
    meta_match = re.search(
        r'(<div class="flex flex-wrap gap-3 text-sm text-gray-600 mb-4">)\s*(.*?)\s*(</div>)',
        content, re.DOTALL
    )
    if meta_match:
        theme_spans = [f'<span class="bg-gray-200 px-2 py-1 rounded">{year}</span>']
        for theme in themes:
            color = THEME_COLORS.get(theme, "bg-gray-100 text-gray-800")
            theme_spans.append(f'<span class="{color} px-2 py-1 rounded">{theme}</span>')

        new_meta = meta_match.group(1) + '\n        ' + '\n        '.join(theme_spans) + '\n      ' + meta_match.group(3)
        content = content[:meta_match.start()] + new_meta + content[meta_match.end():]

    # Also remove View Original TXT link, keep only PDF
    content = re.sub(
        r'\s*<a href="https://rickover-corpus\.s3\.us-east-1\.amazonaws\.com/[^"]+\.txt"[^>]*>View Original TXT</a>',
        '', content
    )

    if content != original:
        post_path.write_text(content, encoding='utf-8')
        return True
    return False


def regenerate_blog_html(data):
    """Regenerate blog.html with theme tags instead of type tags."""
    gemini_posts = [e for e in data if e.get("gemini") and e.get("blog_page")]
    gemini_posts.sort(key=lambda e: e.get("Year", ""), reverse=True)

    cards_html = []
    for entry in gemini_posts:
        title = entry.get("Title", "")
        year = entry.get("Year", "")
        summary = entry.get("Summary", "")
        blog_page = entry.get("blog_page", "")
        themes = entry.get("themes", [])

        title_escaped = html_lib.escape(title, quote=True)
        summary_escaped = html_lib.escape(summary, quote=True)
        summary_preview = html_lib.escape(summary[:280], quote=True)
        if len(summary) > 280:
            summary_preview += "..."

        theme_spans = [f'<span class="bg-gray-200 px-2 py-0.5 rounded text-gray-700">{year}</span>']
        for theme in themes:
            color = THEME_COLORS.get(theme, "bg-gray-100 text-gray-800")
            theme_spans.append(f'<span class="{color} px-2 py-0.5 rounded">{theme}</span>')

        card = f'''      <a href="{blog_page}" class="block bg-white border border-gray-200 rounded-lg p-5 shadow-sm hover:shadow-md transition-shadow no-underline" data-title="{title_escaped}" data-summary="{summary_escaped}" data-year="{year}" data-themes="{','.join(themes)}">
        <div class="flex items-start justify-between mb-2">
          <h2 class="text-lg font-semibold text-gray-900" style="text-decoration:none">{title_escaped}</h2>
        </div>
        <div class="flex flex-wrap gap-2 mb-3 text-sm">
          {' '.join(theme_spans)}
        </div>
        <p class="text-sm text-gray-600 leading-relaxed" style="text-decoration:none">{summary_preview}</p>
      </a>'''
        cards_html.append(card)

    blog_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Full Text — The Rickover Corpus</title>
  <meta name="description" content="Full-text blog posts from Admiral Hyman G. Rickover's speeches, testimonies, and writings.">
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
  <link rel="icon" type="image/png" href="/assets/rickover_favicon.png" sizes="256x256">
  <style>
    a {{ color: #1d4ed8; text-decoration: underline; }}
    a:hover {{ color: #1e40af; }}
  </style>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-M0H8BLJN0S"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());gtag('config', 'G-M0H8BLJN0S');
  </script>
</head>
<body class="bg-gray-50 text-gray-900 font-sans">
  <header class="max-w-3xl mx-auto px-4 pt-10 pb-6">
    <nav class="text-sm mb-4">
      <a href="/index.html">&larr; Back to Full Archive (143 documents)</a>
    </nav>
    <h1 class="text-3xl font-bold tracking-tight mb-2">The Rickover Corpus — Full Text</h1>
    <p class="text-gray-600 mb-4">Over 40 of Admiral Rickover's speeches, testimonies, and writings — transcribed and searchable.</p>
    <input id="searchInput" type="text" placeholder="Search by title, theme, or keyword..." class="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
  </header>
  <main class="max-w-3xl mx-auto px-4 pb-12">
    <div id="blogCards" class="space-y-4">
{chr(10).join(cards_html)}
    </div>
  </main>
  <footer class="mt-12 border-t border-gray-300 pt-6 pb-8 text-sm max-w-3xl mx-auto px-4 text-center text-gray-600">
    <p>Compiled by <a href="https://charlesyang.io" target="_blank">Charles Yang</a> under the <a href="https://industrialstrategy.org" target="_blank">Center for Industrial Strategy</a>.</p>
    <a href="https://www.industrialstrategy.org" target="_blank" class="mt-4 inline-block">
      <img src="/assets/CIS_logo.png" alt="CIS Logo" class="h-10 w-auto mx-auto" style="clip-path: inset(1px 1px 1px 1px);">
    </a>
  </footer>
  <script src="https://cdn.jsdelivr.net/npm/fuse.js@6.6.2/dist/fuse.min.js"></script>
  <script>
    document.addEventListener('DOMContentLoaded', () => {{
      const cards = document.querySelectorAll('#blogCards > a');
      const data = Array.from(cards).map(card => ({{
        title: card.dataset.title,
        summary: card.dataset.summary,
        year: card.dataset.year,
        themes: card.dataset.themes,
        el: card
      }}));
      const fuse = new Fuse(data, {{
        keys: ['title', 'summary', 'themes'],
        threshold: 0.4,
        minMatchCharLength: 2,
      }});
      document.getElementById('searchInput').addEventListener('input', (e) => {{
        const query = e.target.value.trim();
        if (!query) {{
          data.forEach(d => d.el.style.display = '');
          return;
        }}
        const results = fuse.search(query);
        const matched = new Set(results.map(r => r.item.el));
        data.forEach(d => {{
          d.el.style.display = matched.has(d.el) ? '' : 'none';
        }});
      }});
    }});
  </script>
</body>
</html>
'''
    return blog_content


def main():
    with open(MANIFEST, encoding='utf-8') as f:
        data = json.load(f)

    updated_posts = 0
    for entry in data:
        if not entry.get("gemini"):
            continue

        title = entry.get("Title", "")
        themes = get_themes(title)
        if not themes:
            print(f"  NO THEMES: {title}")
            continue

        entry["themes"] = themes

        blog_page = entry.get("blog_page", "")
        if blog_page:
            post_path = ROOT / blog_page.lstrip("/")
            if post_path.exists():
                year = entry.get("Year", "")
                if update_post_html(post_path, year, themes):
                    updated_posts += 1
                    print(f"  Updated: {post_path.name} → {', '.join(themes)}")

    # Save manifest
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Regenerate blog.html
    blog_html = regenerate_blog_html(data)
    (ROOT / "blog.html").write_text(blog_html, encoding='utf-8')
    print(f"\nRegenerated blog.html")

    print(f"Done: {updated_posts} post files updated")


if __name__ == "__main__":
    main()
