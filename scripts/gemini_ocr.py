#!/usr/bin/env python3
"""
OCR pipeline using Google Gemini API (google-genai SDK).
Downloads PDFs from S3, sends to Gemini for text extraction,
and updates the post HTML files with clean extracted text.
"""

import os
import re
import sys
import time
import tempfile
import requests
from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader, PdfWriter

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from google import genai

POSTS_DIR = Path(__file__).resolve().parent.parent / "posts"

GEMINI_PROMPT = """Extract all the text from this PDF document. This is a historical speech, memo, or testimony by Admiral Hyman G. Rickover (1950s-1980s).

Rules:
- Extract the FULL text faithfully — do not summarize or skip anything
- Clean up OCR artifacts, page numbers, headers/footers, and repeated page titles
- Remove any copyright notices, boilerplate disclaimers, or "check against delivery" notes
- Remove any web browser artifacts (URLs, timestamps, "Open in Reader", etc.)
- Fix obvious OCR errors (like "tbe" → "the", "witb" → "with") but preserve Rickover's actual words
- Output ONLY the document text as clean HTML paragraphs using <p> tags
- Use <p> tags for each paragraph — do not use <br> tags
- Preserve paragraph breaks as they appear in the original
- Do not wrap output in ```html``` code blocks — just output the raw <p> tags
- Do not add any commentary, headers, or metadata — just the document text"""

# The 28 posts to process
POSTS = [
    {
        "title": "1979 Management Magazine - Rickover on Management",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/1979+Management+Magazine+-+Rickover+on+Management.pdf",
        "blog_page": "posts/1979-management-magazine-rickover-on-management.html"
    },
    {
        "title": "The Purpose of Education",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/The+Purpose+of+Education.pdf",
        "blog_page": "posts/the-purpose-of-education.html"
    },
    {
        "title": "Some Thoughts on the Future of the United States Government by Admiral H. G. Rickover, USN",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Some+Thoughts+on+the+Future+of+the+United+States+Government+by+Admiral+H.+G.+Rickover,+USN.pdf",
        "blog_page": "posts/some-thoughts-on-the-future-of-the-united-states-government-by-admiral-h-g-rickover-usn.html"
    },
    {
        "title": "Accounting Practices - Do They Protect the Public",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Accounting+Practices+-+Do+They+Protect+the+Public.pdf",
        "blog_page": "posts/accounting-practices-do-they-protect-the-public.html"
    },
    {
        "title": "Paper Reactor Memo",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Paper+Reactor+Memo.pdf",
        "blog_page": "posts/paper-reactor-memo.html"
    },
    {
        "title": "Meaning of Nautilus Polar Voyage",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Meaning+of+Nautilus+Polar+Voyage.pdf",
        "blog_page": "posts/meaning-of-nautilus-polar-voyage.html"
    },
    {
        "title": "Memo of Conversation with Jimmy Carter",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Memo+of+Conversation+with+Jimmy+Carter.pdf",
        "blog_page": "posts/memo-of-conversation-with-jimmy-carter.html"
    },
    {
        "title": "Personal Accountability in Financial Management",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Personal+Accountability+in+Financial+Management.pdf",
        "blog_page": "posts/personal-accountability-in-financial-management.html"
    },
    {
        "title": "Humanistic Technology",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Humanistic+Technology.pdf",
        "blog_page": "posts/humanistic-technology.html"
    },
    {
        "title": "Role of the Critic",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Role+of+the+Critic.pdf",
        "blog_page": "posts/role-of-the-critic.html"
    },
    {
        "title": "Lawyers versus Society",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Lawyers+versus+Society.pdf",
        "blog_page": "posts/lawyers-versus-society.html"
    },
    {
        "title": "Role of Professional Man",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Role+of+Professional+Man.pdf",
        "blog_page": "posts/role-of-professional-man.html"
    },
    {
        "title": "Energy Speech at Athens Propeller Club",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Energy+Speech+at+Athens+Propeller+Club.pdf",
        "blog_page": "posts/energy-speech-at-athens-propeller-club.html"
    },
    {
        "title": "Nuclear Power and Bremerton",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Nuclear+Power+and+Bremerton.pdf",
        "blog_page": "posts/nuclear-power-and-bremerton.html"
    },
    {
        "title": "Rickover and Education",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Rickover+and+Education.pdf",
        "blog_page": "posts/rickover-and-education.html"
    },
    {
        "title": "Democracy and Competence",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Democracy+and+Competence.pdf",
        "blog_page": "posts/democracy-and-competence.html"
    },
    {
        "title": "Doing a Job",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Doing+a+Job.pdf",
        "blog_page": "posts/doing-a-job.html"
    },
    {
        "title": "Mans Purpose in Life",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Mans+Purpose+in+Life.pdf",
        "blog_page": "posts/mans-purpose-in-life.html"
    },
    {
        "title": "What Are Schools For",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/What+Are+Schools+For.pdf",
        "blog_page": "posts/what-are-schools-for.html"
    },
    {
        "title": "The Talented Mind",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/The+Talented+Mind.pdf",
        "blog_page": "posts/the-talented-mind.html"
    },
    {
        "title": "In Defense of Truth",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/In+Defense+of+Truth.pdf",
        "blog_page": "posts/in-defense-of-truth.html"
    },
    {
        "title": "Environmental Perspective",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Environmental+Perspective.pdf",
        "blog_page": "posts/environmental-perspective.html"
    },
    {
        "title": "Significance of Electricity",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Significance+of+Electricity.pdf",
        "blog_page": "posts/significance-of-electricity.html"
    },
    {
        "title": "Meaning of a University",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Meaning+of+a+University.pdf",
        "blog_page": "posts/meaning-of-a-university.html"
    },
    {
        "title": "Intellect in a Democracy",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Intellect+in+a+Democracy.pdf",
        "blog_page": "posts/intellect-in-a-democracy.html"
    },
    {
        "title": "Who Protects the Public",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Who+Protects+the+Public.pdf",
        "blog_page": "posts/who-protects-the-public.html"
    },
    {
        "title": "Rickover Final Testimony to Congress",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Rickover+Final+Testimony+to+Congress.pdf",
        "blog_page": "posts/rickover-final-testimony-to-congress.html"
    },
    {
        "title": "Summary of President Nixon Dinner Conversation",
        "file_pdf": "https://rickover-corpus.s3.us-east-1.amazonaws.com/Summary+of+President+Nixon+Dinner+Conversation.pdf",
        "blog_page": "posts/summary-of-president-nixon-dinner-conversation.html"
    },
]


def download_pdf(url: str, dest: str) -> bool:
    """Download a PDF from S3."""
    resp = requests.get(url, timeout=120)
    if resp.status_code == 200:
        with open(dest, 'wb') as f:
            f.write(resp.content)
        return True
    print(f"  ERROR: HTTP {resp.status_code} downloading {url}")
    return False


CHUNK_SIZE = 10  # Max pages per chunk


def split_pdf(pdf_path: str, chunk_size: int = CHUNK_SIZE) -> list:
    """Split a PDF into chunks, returning list of (chunk_path, start_page, end_page)."""
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    if total_pages <= chunk_size:
        return [(pdf_path, 1, total_pages)]

    chunks = []
    tmpdir = tempfile.mkdtemp()
    for start in range(0, total_pages, chunk_size):
        end = min(start + chunk_size, total_pages)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])
        chunk_path = os.path.join(tmpdir, f"chunk_{start+1}_{end}.pdf")
        with open(chunk_path, 'wb') as f:
            writer.write(f)
        chunks.append((chunk_path, start + 1, end))

    return chunks


def extract_chunk_with_gemini(client, pdf_path: str, title: str, page_info: str = "") -> str:
    """Upload a PDF (or chunk) to Gemini and extract clean HTML text."""
    uploaded = client.files.upload(file=pdf_path)

    # Wait for file to be processed
    while uploaded.state.name == "PROCESSING":
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name == "FAILED":
        raise RuntimeError(f"Gemini file upload failed for {title}")

    prompt = GEMINI_PROMPT
    if page_info:
        prompt += "\n\nNote: This is " + page_info + " of the document. Continue extracting faithfully."

    # Generate content with retry on rate limits
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[
                    genai.types.Part.from_uri(file_uri=uploaded.uri, mime_type="application/pdf"),
                    prompt,
                ],
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

    # Clean up uploaded file
    try:
        client.files.delete(name=uploaded.name)
    except Exception:
        pass

    text = response.text.strip() if response.text else ""
    # Strip markdown code block wrapper if present
    if text.startswith("```html"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def extract_text_with_gemini(client, pdf_path: str, title: str) -> str:
    """Extract text from PDF, chunking if over CHUNK_SIZE pages."""
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    if total_pages <= CHUNK_SIZE:
        print(f"  {total_pages} pages — single pass")
        return extract_chunk_with_gemini(client, pdf_path, title)

    # Split into chunks
    print(f"  {total_pages} pages — chunking into {CHUNK_SIZE}-page segments")
    chunks = split_pdf(pdf_path)
    all_text = []

    for chunk_path, start, end in chunks:
        page_info = f"pages {start}-{end} of {total_pages}"
        print(f"  Processing {page_info}...")
        chunk_text = extract_chunk_with_gemini(client, chunk_path, title, page_info)
        all_text.append(chunk_text)
        # Clean up chunk file if it's not the original
        if chunk_path != pdf_path:
            os.remove(chunk_path)
        time.sleep(2)  # Brief pause between chunks

    return "\n\n".join(all_text)


def update_post_html(blog_page: str, new_ocr_html: str) -> bool:
    """Replace the OCR text div content in a post HTML file."""
    filepath = Path(__file__).resolve().parent.parent / blog_page
    if not filepath.exists():
        print(f"  WARNING: {filepath} does not exist")
        return False

    content = filepath.read_text(encoding='utf-8')

    # Find the OCR text div
    pattern = r'(<div class="ocr-text text-gray-800">)\s*(.*?)\s*(</div>)'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"  WARNING: No ocr-text div found in {blog_page}")
        return False

    # Replace content
    new_content = (
        content[:match.start()]
        + match.group(1) + '\n        '
        + new_ocr_html + '\n      '
        + match.group(3)
        + content[match.end():]
    )

    filepath.write_text(new_content, encoding='utf-8')
    return True


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your-key-here":
        print("ERROR: Set GEMINI_API_KEY in .env file")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Allow passing specific indices to process (e.g., "python gemini_ocr.py 0 5 10")
    if len(sys.argv) > 1:
        indices = [int(i) for i in sys.argv[1:]]
        posts_to_process = [(i, POSTS[i]) for i in indices if i < len(POSTS)]
    else:
        posts_to_process = list(enumerate(POSTS))

    print(f"Processing {len(posts_to_process)} posts with Gemini...")

    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, (i, post) in enumerate(posts_to_process):
            title = post["title"]
            print(f"\n[{idx+1}/{len(posts_to_process)}] {title}")

            # Download PDF
            pdf_path = os.path.join(tmpdir, f"doc_{i}.pdf")
            print(f"  Downloading PDF...")
            if not download_pdf(post["file_pdf"], pdf_path):
                continue

            # Extract text with Gemini
            print(f"  Sending to Gemini...")
            try:
                ocr_html = extract_text_with_gemini(client, pdf_path, title)
            except Exception as e:
                print(f"  ERROR: Gemini extraction failed: {e}")
                continue

            # Update post HTML
            print(f"  Updating {post['blog_page']}...")
            if update_post_html(post["blog_page"], ocr_html):
                print(f"  Done!")
            else:
                print(f"  Failed to update HTML")

            # Clean up PDF
            os.remove(pdf_path)

            # Rate limit: brief pause between requests
            if idx < len(posts_to_process) - 1:
                time.sleep(2)

    print(f"\nAll done! Processed {len(posts_to_process)} posts.")


if __name__ == "__main__":
    main()
