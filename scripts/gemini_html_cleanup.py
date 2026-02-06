#!/usr/bin/env python3
"""
Pass Gemini-processed post HTML through Gemini 3 Flash for cleanup.
Fixes extraneous newlines, removes paging artifacts, cleans up
unnecessary text while preserving the actual document content.
"""

import os
import re
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from google import genai

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"

CLEANUP_PROMPT = """You are cleaning up the HTML text of a historical speech, memo, or testimony by Admiral Hyman G. Rickover.

The text below is already extracted and wrapped in <p> tags. Your job is to clean it up:

1. Remove any page numbers, page headers/footers, or paging artifacts that slipped through
2. Remove any OCR artifacts, garbled text, or nonsense characters
3. Remove any copyright notices, boilerplate disclaimers, "check against delivery" notes, or "for official use only" headers
4. Remove any web browser artifacts (URLs, timestamps, "Open in Reader", social media buttons, etc.)
5. Remove any repeated headers that appear on every page
6. Fix extraneous line breaks — merge paragraphs that were incorrectly split mid-sentence
7. Fix obvious typos or OCR errors (like "tbe" → "the") but preserve Rickover's actual words and style
8. Ensure each <p> tag contains a complete, logical paragraph
9. Do NOT add any markdown formatting (no *, **, _, `, #, etc.)
10. Do NOT add any commentary, headers, or metadata — just output the cleaned <p> tags
11. Do NOT summarize or shorten — preserve ALL of the original text content
12. Output ONLY <p>...</p> tags, nothing else

Here is the HTML to clean up:

"""


def get_gemini_posts():
    """Get list of Gemini-processed posts from manifest.json."""
    import json
    manifest_path = ROOT / "manifest.json"
    with open(manifest_path) as f:
        data = json.load(f)
    return [entry for entry in data if entry.get("gemini")]


def extract_ocr_html(post_path: Path) -> str:
    """Extract the OCR text div content from a post HTML file."""
    content = post_path.read_text(encoding='utf-8')
    match = re.search(
        r'<div class="ocr-text text-gray-800">\s*(.*?)\s*</div>',
        content, re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return ""


def update_ocr_html(post_path: Path, new_html: str) -> bool:
    """Replace the OCR text div content in a post HTML file."""
    content = post_path.read_text(encoding='utf-8')
    pattern = r'(<div class="ocr-text text-gray-800">)\s*(.*?)\s*(</div>)'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return False

    new_content = (
        content[:match.start()]
        + match.group(1) + '\n        '
        + new_html + '\n      '
        + match.group(3)
        + content[match.end():]
    )
    post_path.write_text(new_content, encoding='utf-8')
    return True


def clean_with_gemini(client, ocr_html: str, title: str) -> str:
    """Send OCR HTML to Gemini for cleanup."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[CLEANUP_PROMPT + ocr_html],
                config=genai.types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=65536,
                ),
            )
            break
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait = 30 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise

    text = response.text.strip()
    # Strip markdown code block wrapper if present
    if text.startswith("```html"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your-key-here":
        print("ERROR: Set GEMINI_API_KEY in .env file")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    gemini_posts = get_gemini_posts()
    print(f"Found {len(gemini_posts)} Gemini-processed posts")

    # Allow passing specific indices
    if len(sys.argv) > 1:
        indices = [int(i) for i in sys.argv[1:]]
        gemini_posts = [gemini_posts[i] for i in indices if i < len(gemini_posts)]

    cleaned = 0
    for idx, entry in enumerate(gemini_posts):
        title = entry.get("Title", "Unknown")
        blog_page = entry.get("blog_page", "")
        if not blog_page:
            continue

        post_path = ROOT / blog_page.lstrip('/')
        if not post_path.exists():
            print(f"  SKIP: {blog_page} not found")
            continue

        print(f"\n[{idx+1}/{len(gemini_posts)}] {title}")

        # Extract current OCR HTML
        ocr_html = extract_ocr_html(post_path)
        if not ocr_html or len(ocr_html) < 100:
            print(f"  SKIP: No/minimal OCR content")
            continue

        # Send to Gemini for cleanup
        print(f"  Sending to Gemini for cleanup...")
        try:
            cleaned_html = clean_with_gemini(client, ocr_html, title)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        # Sanity check: cleaned version shouldn't be drastically shorter
        if len(cleaned_html) < len(ocr_html) * 0.5:
            print(f"  WARNING: Cleaned text is {len(cleaned_html)} chars vs original {len(ocr_html)} chars — skipping")
            continue

        # Update the post file
        if update_ocr_html(post_path, cleaned_html):
            cleaned += 1
            print(f"  Done! ({len(ocr_html)} → {len(cleaned_html)} chars)")
        else:
            print(f"  Failed to update HTML")

        # Brief pause between requests
        if idx < len(gemini_posts) - 1:
            time.sleep(2)

    print(f"\nAll done! Cleaned {cleaned}/{len(gemini_posts)} posts.")


if __name__ == "__main__":
    main()
