# -*- coding: utf-8 -*-
"""
Extract Question + Answer pairs from a PDF using PyMuPDF (fitz).
Preserves Unicode (☑/☐/emoji/etc).
Identifies REAL questions (ending with '?') and nearest checkbox answers.
"""

import io
import re
import sys
import requests
import fitz  # PyMuPDF
from typing import Iterator, Optional, Tuple


# -----------------------------
# REGEXES
# -----------------------------

QUESTION_REGEX = re.compile(
    r"(?P<question>[^()\n].*?\?)",
    flags=re.DOTALL
)

CHECKBOX_REGEX = re.compile(
    r"^[ \t]*([☑☐✔✖✕✗□].+)$",
    flags=re.MULTILINE
)


# -----------------------------
# PDF LOADING USING PyMuPDF
# -----------------------------

def load_pdf_document(source: str) -> fitz.Document:
    """
    Load a PDF either from a URL or a local file.
    Returns a PyMuPDF Document.
    """
    if source.lower().startswith(("http://", "https://")):
        resp = requests.get(source, timeout=60)
        resp.raise_for_status()
        data = resp.content
        return fitz.open(stream=data, filetype="pdf")
    else:
        return fitz.open(source)


def iter_page_text(doc: fitz.Document) -> Iterator[Tuple[int, str]]:
    """
    Yield (page_number_1_based, extracted_text) for each page.
    PyMuPDF's get_text("text") preserves reading order and unicode well.
    """
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text") or ""
        yield i + 1, text


# -----------------------------
# QUESTION / ANSWER EXTRACTION
# -----------------------------

def extract_qas_from_page(page_text: str):
    """
    Extract REAL questions (ending with '?') and their nearest checkbox answer.
    Completely ignores headings and section markers.
    """
    text = page_text

    for match in QUESTION_REGEX.finditer(text):
        question = match.group("question").strip()

        # Look for answer after the question
        start = match.end()
        scope = text[start:]

        checkbox_match = CHECKBOX_REGEX.search(scope)
        answer = checkbox_match.group(1).strip() if checkbox_match else ""

        yield question, answer


# -----------------------------
# DRIVER (main)
# -----------------------------

def main():
    pdf_source = (
        "https://corporate.thermofisher.com/content/dam/tfcorpsite/documents/"
        "corporate-social-responsibility/Thermo-Fisher-Scientific-Inc-2024-FINAL-CDP-REPORT.pdf"
    )

    try:
        doc = load_pdf_document(pdf_source)
    except Exception as e:
        print(f"Error loading PDF: {e}", file=sys.stderr)
        sys.exit(1)

    results = {}  # { page_num: [ {question, answer}, ... ] }

    for page_num, page_text in iter_page_text(doc):
        if not page_text.strip():
            continue

        page_entries = []

        # Each item is (question, answer)
        for question, answer in extract_qas_from_page(page_text):
            page_entries.append({
                "question": question,
                "answer": answer
            })

        if page_entries:
            results[page_num] = page_entries

    # Save JSON
    import json
    with open("extracted_qas.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("Saved extracted_qas.json")


if __name__ == "__main__":
    main()