#!/usr/bin/env python3
"""
Clean markdown decorators from Summary fields in manifest.json
and in the corresponding post HTML files.

Removes: *italics*, **bold**, `code`, ## headings
"""

import json
import re
import html as html_lib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.json"
POSTS_DIR = ROOT / "posts"


def strip_markdown(text: str) -> str:
    """Remove markdown formatting from text, keeping the inner content."""
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Italic: *text* or _text_ (but not inside words like don't)
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'\1', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text)
    # Inline code: `text`
    text = re.sub(r'`(.+?)`', r'\1', text)
    # Headings: ## text -> text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Strikethrough: ~~text~~
    text = re.sub(r'~~(.+?)~~', r'\1', text)
    return text


def strip_markdown_html_escaped(text: str) -> str:
    """Strip markdown from HTML-escaped text (where * is literal, not &ast;)."""
    # In HTML attributes/content, markdown chars are usually literal
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'\1', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'~~(.+?)~~', r'\1', text)
    # Remove leftover unclosed markdown markers (from truncated text)
    text = re.sub(r'\*{1,2}(?=\w)', '', text)
    text = re.sub(r'(?<=\w)\*{1,2}', '', text)
    return text


def clean_post_file(post_path: Path) -> bool:
    """Clean markdown from summary section and meta description in a post HTML file."""
    content = post_path.read_text(encoding='utf-8')
    original = content

    # Clean meta description
    meta_match = re.search(r'(<meta\s+name="description"\s+content=")(.*?)(")', content, re.DOTALL)
    if meta_match:
        old_desc = meta_match.group(2)
        new_desc = strip_markdown_html_escaped(old_desc)
        if old_desc != new_desc:
            content = content[:meta_match.start(2)] + new_desc + content[meta_match.end(2):]

    # Clean summary <p> tag
    summary_match = re.search(
        r'(<h2 class="text-lg font-semibold mb-2">Summary</h2>\s*<p class="text-gray-700 leading-relaxed">)(.*?)(</p>)',
        content, re.DOTALL
    )
    if summary_match:
        old_summary = summary_match.group(2)
        new_summary = strip_markdown_html_escaped(old_summary)
        if old_summary != new_summary:
            content = content[:summary_match.start(2)] + new_summary + content[summary_match.end(2):]

    if content != original:
        post_path.write_text(content, encoding='utf-8')
        return True
    return False


def main():
    with open(MANIFEST, encoding='utf-8') as f:
        data = json.load(f)

    changed_manifest = 0
    changed_posts = 0

    for entry in data:
        summary = entry.get('Summary', '')
        if not summary:
            continue

        cleaned = strip_markdown(summary)
        if cleaned == summary:
            continue

        # Update manifest
        old_summary = summary
        entry['Summary'] = cleaned
        changed_manifest += 1

    # Write updated manifest
    if changed_manifest > 0:
        with open(MANIFEST, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Clean all post HTML files (meta descriptions + summary sections)
    posts = sorted(POSTS_DIR.glob("*.html"))
    for post in posts:
        if clean_post_file(post):
            changed_posts += 1
            print(f"  Updated: {post.name}")

    print(f"\nDone: {changed_manifest} summaries cleaned in manifest.json")
    print(f"      {changed_posts} post HTML files updated")


if __name__ == "__main__":
    main()
