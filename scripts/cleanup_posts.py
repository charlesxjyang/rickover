#!/usr/bin/env python3
"""
Clean up generated blog post HTML files:
- Convert ALL CAPS OCR text to sentence case
- Remove standalone page number paragraphs
- Remove OCR noise/artifacts
- Fix excessive <br> tags and redundant newlines
- Fix ALL CAPS titles in <h1> and <title> tags
"""

import re
import html
from pathlib import Path

POSTS_DIR = Path(__file__).resolve().parent.parent / "posts"

# Words/acronyms that should stay uppercase
KEEP_UPPER = {
    "USS", "USN", "U.S.", "U.S", "USA", "UK", "NATO", "AEC", "CIA", "FBI",
    "DOD", "DOE", "NASA", "MIT", "NRC", "USNA", "SSN", "CGN", "CVN",
    "FY", "AEGIS", "ASW", "ICBM", "SLBM", "MX", "TV", "CBS", "NBC",
    "ABC", "DC", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX",
    "X", "XI", "XII", "XIII", "XIV", "XV", "ROTC", "GNP", "GDP", "PhD",
    "D.C.", "N.Y.", "H.G.", "H.R.", "S.", "R&D", "PWR", "BWR", "TMI",
    "GPU", "NIMITZ", "OHIO", "TRIDENT", "POLARIS", "POSEIDON",
    "NAUTILUS", "DNA", "RNA", "IBM", "AT&T", "GE", "LBJ", "FDR", "TR",
    "AM", "PM", "AD", "BC", "OPEC",
}

# Common title words that should stay lowercase (in title case)
TITLE_LOWER = {"a", "an", "the", "and", "but", "or", "for", "nor", "on",
               "at", "to", "from", "by", "in", "of", "with", "as", "is"}


def is_all_caps(text: str) -> bool:
    """Check if text is predominantly ALL CAPS."""
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 4:
        return False
    upper_count = sum(1 for c in letters if c.isupper())
    return upper_count / len(letters) > 0.7


def sentence_case(text: str) -> str:
    """Convert ALL CAPS text to sentence case, preserving known acronyms."""
    if not is_all_caps(text):
        return text

    words = text.split()
    result = []
    after_period = True  # Start of text = capitalize first word

    for i, word in enumerate(words):
        # Strip HTML entities and punctuation for checking
        clean = re.sub(r'&[a-z]+;', '', word)
        clean_alpha = re.sub(r'[^A-Za-z]', '', clean)

        # Check if this word (or its base) should stay uppercase
        word_upper = clean_alpha.upper()
        keep = False
        for acronym in KEEP_UPPER:
            if word_upper == acronym.replace(".", "").upper():
                keep = True
                break

        # Check for words with periods that are acronyms (H.G., U.S., etc.)
        if re.match(r'^[A-Z]\.[A-Z]\.?', word):
            keep = True

        if keep:
            result.append(word)
            # Only treat as sentence end if the period is truly sentence-ending
            stripped = word.rstrip(',').rstrip('"').rstrip("'")
            if stripped.endswith(('.', '?', '!')) and not re.match(r'^[A-Z]\.[A-Z]', stripped):
                after_period = True
            else:
                after_period = False
            continue

        # Convert to lowercase then capitalize as needed
        lower_word = word.lower()

        if after_period or i == 0:
            # Capitalize first letter after sentence boundary
            lower_word = capitalize_first(lower_word)
            after_period = False

        result.append(lower_word)

        # Check if this word ends a sentence (period, question mark, exclamation, colon)
        stripped = word.rstrip(',').rstrip('"').rstrip("'")
        if stripped.endswith(('.', '?', '!')) and not re.match(r'^[A-Z]\.[A-Z]', stripped):
            after_period = True

    return ' '.join(result)


def capitalize_first(word: str) -> str:
    """Capitalize the first alphabetic character in a word."""
    for i, c in enumerate(word):
        if c.isalpha():
            return word[:i] + c.upper() + word[i+1:]
    return word


def title_case_smart(text: str) -> str:
    """Convert ALL CAPS title to smart title case."""
    if not is_all_caps(text):
        return text

    words = text.split()
    result = []

    for i, word in enumerate(words):
        clean_alpha = re.sub(r'[^A-Za-z]', '', word)
        word_upper = clean_alpha.upper()

        # Keep known acronyms
        keep = False
        for acronym in KEEP_UPPER:
            if word_upper == acronym.replace(".", "").upper():
                keep = True
                break

        if re.match(r'^[A-Z]\.[A-Z]\.?', word):
            keep = True

        if keep:
            result.append(word)
        elif i == 0 or word.lower() not in TITLE_LOWER:
            result.append(capitalize_first(word.lower()))
        else:
            result.append(word.lower())

    return ' '.join(result)


def is_page_number(text: str) -> bool:
    """Check if a paragraph is just a page number or OCR noise."""
    stripped = text.strip()
    # Pure page numbers
    if re.match(r'^\d{1,3}$', stripped):
        return True
    # OCR noise: very short, mostly non-alpha
    if len(stripped) <= 4:
        alpha = sum(1 for c in stripped if c.isalpha())
        if alpha <= 1:
            return True
    return False


def is_ocr_noise(text: str) -> bool:
    """Check if text is OCR noise/artifacts."""
    stripped = text.strip()
    # Very short nonsense
    if len(stripped) <= 3 and not stripped.isalpha():
        return True
    # Common OCR artifacts
    noise_patterns = [
        r'^[;:.,\-=\+\*\|]+$',           # Just punctuation
        r'^[oeao0O\s\-=]+$',              # Common OCR garbage
        r'^\d{1,3}$',                      # Page numbers
        r'^[\s]*$',                         # Whitespace only
        r'^[a-z\d\s\-=\+\.\,]{2,8}$',    # Short garbled text (like "oo 85 oy", "a = oe")
        # Timestamps from web page saves (e.g. "6/12/2025, 10:48 PM" or "1 of 12 6/12/2025, 10:49 PM")
        r'^\d{1,2}/\d{1,2}/\d{4},?\s*\d{1,2}:\d{2}\s*(AM|PM)?$',
        r'^\d{1,2}\s+of\s+\d{1,3}\s+\d{1,2}/\d{1,2}/\d{4}',
        # Browser UI / reader mode artifacts
        r'.*Open\s*in\s*Reader.*',
        r'.*Auto highlighting.*',
        r'^R\|.*Q[\-\+].*',
        # URL-only lines (repeated page headers from web saves)
        r'^.*https?://\S+\.(htm|html|org|com|gov|pdf)\s*$',
        r'^.*https?:/[A-Za-z]\S+\.(htm|html|org|com|gov)\S*\s*$',
        # Garbled caps runs (corrupted OCR, 4+ consecutive all-caps words of 5+ chars)
        r'^[A-Z\s,.\-;:©®@>\d\(\)]+$',
        # Website names/headers
        r'^.*[Ll][ée]aders\.org.*$',
        r'^Growing Leaders for the Public Service$',
        # Social media / Substack artifacts
        r'^@\s*\d+\s*O\s*\d+.*Share',
        r'^\.\s*\d\)\s*ae\s+ise\s+gettyimages',
        r'^G\d+\s+claude\s+berube',
    ]
    for pattern in noise_patterns:
        if re.match(pattern, stripped):
            return True
    return False


def is_repeated_header(text: str) -> bool:
    """Check if paragraph is a repeated page header from web-saved PDFs."""
    stripped = text.strip()
    # Lines that are title + URL (repeated on each page of web-saved PDFs)
    if re.search(r'https?://?[A-Za-z]?\S+\.(htm|html|org|com|gov)', stripped):
        # If the line is mostly a URL or title+URL, it's a header
        url_match = re.search(r'https?://\S+', stripped)
        if url_match:
            non_url = stripped[:url_match.start()].strip() + stripped[url_match.end():].strip()
            # If what's left is short (just a title), it's a repeated header
            if len(non_url) < 100:
                return True
    return False


def is_boilerplate(text: str) -> bool:
    """Check if text is a boilerplate disclaimer/copyright/header from speech PDFs."""
    lower = text.lower().strip()
    patterns = [
        r'this speech reflects the views',
        r'does not\s+.*necessarily reflect the views',
        r'copyright\s+\d{4}',
        r'copyricht\s+\d{4}',  # OCR misspelling
        r'no permission needed for newspaper',
        r'above copyright notice',
        r'if most of speech reprinted',
        r'department of the navy',
        r'department of energy',
        r'for official use only',
        r'not for publication',
        r'embargoed.*until',
        r'advance\s+text',
        r'delivery\s*copy',
        r'check\s+against\s+delivery',
        r'as\s+prepared\s+for\s+delivery',
    ]
    for pattern in patterns:
        if re.search(pattern, lower):
            return True
    return False


def has_garbled_caps(text: str) -> bool:
    """Check if text contains garbled ALL CAPS runs (corrupted OCR from web saves)."""
    # Look for runs of 4+ consecutive ALL-CAPS words of 4+ chars each
    words = text.split()
    caps_run = 0
    for w in words:
        clean = re.sub(r'[^A-Za-z]', '', w)
        if len(clean) >= 4 and clean.isupper():
            caps_run += 1
            if caps_run >= 4:
                return True
        else:
            caps_run = 0
    return False


def clean_br_tags(html_text: str) -> str:
    """Clean up excessive <br> tags."""
    # Remove <br> at end of paragraphs (before </p>)
    html_text = re.sub(r'(<br>\s*)+</p>', '</p>', html_text)
    # Remove <br> at start of paragraphs (after <p>)
    html_text = re.sub(r'<p>\s*(<br>\s*)+', '<p>', html_text)
    # Collapse multiple <br> into one
    html_text = re.sub(r'(<br>\s*){3,}', '<br><br>', html_text)
    return html_text


def clean_ocr_div(ocr_html: str) -> str:
    """Clean up the OCR text content within the div."""
    # Extract paragraphs
    paragraphs = re.findall(r'<p>(.*?)</p>', ocr_html, re.DOTALL)

    cleaned = []
    for p in paragraphs:
        # Decode HTML entities for processing, then re-encode
        text = p.strip()

        if not text:
            continue

        # Get plain text version for checks
        plain = re.sub(r'<[^>]+>', ' ', text)
        plain = html.unescape(plain).strip()

        # Skip page numbers and OCR noise
        if is_page_number(plain) or is_ocr_noise(plain):
            continue

        # Skip repeated web-page headers (title + URL combos)
        if is_repeated_header(plain):
            continue

        # Skip boilerplate disclaimers and copyright notices
        if is_boilerplate(plain):
            continue

        # Skip paragraphs that are entirely garbled caps (corrupted OCR)
        if has_garbled_caps(plain) and len(plain) < 200:
            # Only skip if the paragraph is short-ish (long ones might have real content mixed in)
            alpha_chars = [c for c in plain if c.isalpha()]
            if alpha_chars:
                upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
                if upper_ratio > 0.8:
                    continue

        # Strip leading page numbers embedded in paragraphs (e.g. "4\nOur people...")
        text = re.sub(r'^\d{1,3}\s*<br>\s*', '', text)
        text = re.sub(r'<br>\s*\d{1,3}\s*<br>', '<br>', text)

        # Convert ALL CAPS to sentence case
        # Join <br> text into single string so sentence boundaries work across lines
        merged = text.replace('<br>', ' ')
        unescaped = html.unescape(merged)
        converted = sentence_case(unescaped)
        # Re-escape special chars
        converted = converted.replace('&', '&amp;')
        converted = converted.replace('<', '&lt;')
        converted = converted.replace('>', '&gt;')
        converted = converted.replace('"', '&quot;')
        text = converted
        cleaned.append('<p>' + text + '</p>')

    return '\n'.join(cleaned)


def clean_post_file(filepath: Path) -> bool:
    """Clean up a single post HTML file. Returns True if changes were made."""
    content = filepath.read_text(encoding='utf-8')
    original = content

    # Fix ALL CAPS in <title> tag
    title_match = re.search(r'<title>(.*?) — The Rickover Corpus</title>', content)
    if title_match:
        old_title = title_match.group(1)
        new_title = title_case_smart(html.unescape(old_title))
        new_title = new_title.replace('&', '&amp;')
        if old_title != new_title:
            content = content.replace(
                '<title>' + old_title + ' — The Rickover Corpus</title>',
                '<title>' + new_title + ' — The Rickover Corpus</title>'
            )

    # Fix ALL CAPS in <h1> tag
    h1_match = re.search(r'<h1 class="text-3xl font-bold tracking-tight mb-3">(.*?)</h1>', content)
    if h1_match:
        old_h1 = h1_match.group(1)
        new_h1 = title_case_smart(html.unescape(old_h1))
        new_h1 = new_h1.replace('&', '&amp;')
        if old_h1 != new_h1:
            content = content.replace(
                '>' + old_h1 + '</h1>',
                '>' + new_h1 + '</h1>'
            )

    # Clean OCR text div
    ocr_match = re.search(
        r'(<div class="ocr-text text-gray-800">\s*)(.*?)(</div>)',
        content, re.DOTALL
    )
    if ocr_match:
        prefix = ocr_match.group(1)
        ocr_content = ocr_match.group(2).strip()
        suffix = ocr_match.group(3)

        # Only clean if it has actual OCR content (not placeholder)
        if '<p>' in ocr_content and 'Full OCR text will be available' not in ocr_content:
            cleaned_ocr = clean_ocr_div(ocr_content)
            cleaned_ocr = clean_br_tags(cleaned_ocr)
            content = content[:ocr_match.start()] + prefix + '\n        ' + cleaned_ocr + '\n      ' + suffix + content[ocr_match.end():]

    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return True
    return False


def main():
    posts = sorted(POSTS_DIR.glob("*.html"))
    print(f"Found {len(posts)} post files")

    changed = 0
    for i, post in enumerate(posts, 1):
        if clean_post_file(post):
            changed += 1
            if changed <= 10 or changed % 20 == 0:
                print(f"  [{i}/{len(posts)}] Cleaned: {post.name}")

    print(f"\nDone: {changed}/{len(posts)} files cleaned")


if __name__ == "__main__":
    main()
