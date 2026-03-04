# -*- coding: utf-8 -*-
"""
Extract Section, Question, Answer from a PDF page-by-page while preserving Unicode.
- Works with a URL or a local file path for the PDF.
- Pattern example it targets:
  C1. Introduction
  (1.1) In which language are you submitting your response?
  Select from:
  ☑ English
"""

import io
import re
import os
import mimetypes
from pathlib import Path
from typing import Iterator, Optional, Tuple,Union, IO
from typing import Union, IO, Optional

# If running locally, ensure these are installed:
# pip install PyPDF2 requests

import requests
from PyPDF2 import PdfReader


# SECTION_QUESTION_REGEX = re.compile(
#     r"\((?P<section>\d+(?:\.\d+)*)\)\s*(?P<question>.*?\?)",
#     flags=re.DOTALL
# )

SECTION_QUESTION_REGEX = re.compile(
    r"^[ \t]*\((?P<section>\d+(?:\.\d+)*)\)\s*(?P<question>.*?\?)",
    flags=re.MULTILINE | re.DOTALL
)


CHECKBOX_LINE_REGEX = re.compile(
    r"^[ \t]*([□☐☑✅✔✖☒].+)$",
    flags=re.MULTILINE
)

# NEXT_SECTION_TOKEN = re.compile(r"\(\d+(?:\.\d+)*\)")

NEXT_SECTION_TOKEN = re.compile(
    r"^[ \t]*\(\d+(?:\.\d+)*\)",
    flags=re.MULTILINE
)



def _is_url(s: str) -> bool:
    """Return True if string looks like an http(s) URL."""
    if not isinstance(s, str):
        return False
    s_lower = s.strip().lower()
    return s_lower.startswith("http://") or s_lower.startswith("https://")


def _assert_pdf_bytes(buf: bytes, hint_name: Optional[str] = None) -> None:
    """
    Light validation that we fetched/received a PDF.
    (Magic header: %PDF)
    """
    if not buf or not buf.lstrip().startswith(b"%PDF"):
        name_info = f" ({hint_name})" if hint_name else ""
        raise ValueError(f"Input does not appear to be a valid PDF{name_info}.")


def _try_decrypt(reader: PdfReader) -> None:
    """
    Best-effort: if encrypted, try to decrypt with an empty password.
    Raise a clear error if still locked.
    """
    try:
        if reader.is_encrypted:
            # Try common case: empty password
            ok = reader.decrypt("")  # returns 0/1/2 depending on algorithm
            if ok == 0:
                raise ValueError("PDF is encrypted and could not be opened without a password.")
    except Exception as e:
        raise ValueError(f"Failed to open encrypted PDF: {e}") from e


# def load_pdf_reader(source: Union[str, Path, IO[bytes]]) -> PdfReader:
#     """
#     Return a PyPDF2 PdfReader from:
#       • URL (http/https)
#       • Local filesystem path (str | Path)
#       • File-like binary object (e.g., open(file, "rb") or Flask's FileStorage.stream)

#     Raises ValueError with a clear message on failure.
#     """
#     # -------- Case 1: File-like object (already in memory or open handle) --------
#     if hasattr(source, "read"):  # duck-typing file-like
#         try:
#             data = source.read()
#             if isinstance(data, str):
#                 raise ValueError("File-like object returned text; expected binary bytes.")
#             _assert_pdf_bytes(data)
#             reader = PdfReader(io.BytesIO(data))
#             _try_decrypt(reader)
#             return reader
#         except Exception as e:
#             raise ValueError(f"Failed reading PDF from file-like object: {e}") from e

#     # Normalize strings/paths
#     if isinstance(source, Path):
#         source = str(source)

#     if not isinstance(source, str) or not source.strip():
#         raise ValueError("Invalid 'source'; expected URL, local path, or file-like object.")

#     # -------- Case 2: URL --------
#     if _is_url(source):
#         try:
#             resp = requests.get(source, timeout=60)
#             resp.raise_for_status()

#             # Optional: sanity-check type/extension to help catch HTML responses
#             content_type = resp.headers.get("Content-Type", "").lower()
#             # Allow 'application/pdf' or unknown but let magic header validation decide
#             if "pdf" not in content_type and not source.lower().endswith(".pdf"):
#                 # Not necessarily an error (some servers mislabel), but be cautious
#                 pass

#             data = resp.content
#             _assert_pdf_bytes(data, hint_name=source)
#             reader = PdfReader(io.BytesIO(data))
#             _try_decrypt(reader)
#             return reader

#         except requests.RequestException as e:
#             raise ValueError(f"Network error while fetching PDF: {e}") from e
#         except pypdf_errors.PdfReadError as e:
#             raise ValueError(f"Downloaded file is not a readable PDF: {e}") from e
#         except Exception as e:
#             raise ValueError(f"Failed to open remote PDF: {e}") from e

#     # -------- Case 3: Local file path --------
#     path = os.path.expanduser(source)
#     if not os.path.isabs(path):
#         # Optional: make relative paths explicit (e.g., relative to current working directory)
#         path = os.path.abspath(path)

#     if not os.path.exists(path):
#         raise ValueError(f"Local file not found: {path}")
#     if not os.path.isfile(path):
#         raise ValueError(f"Path is not a file: {path}")

#     # Small hint check: extension or mimetype
#     guessed_type, _enc = mimetypes.guess_type(path)
#     if guessed_type and "pdf" not in guessed_type.lower():
#         # Not fatal—use magic header check, but warn with a clear error if bad
#         pass

#     try:
#         with open(path, "rb") as f:
#             data = f.read()
#         _assert_pdf_bytes(data, hint_name=os.path.basename(path))
#         reader = PdfReader(io.BytesIO(data))
#         _try_decrypt(reader)
#         return reader
#     except pypdf_errors.PdfReadError as e:
#         raise ValueError(f"Local file is not a readable PDF: {e}") from e
#     except Exception as e:
#         raise ValueError(f"Failed to open local PDF '{path}': {e}") from e



def load_pdf_reader(source: str) -> PdfReader:
    """Return a PdfReader from a URL or local path."""
    if source.lower().startswith(("http://", "https://")):
        resp = requests.get(source, timeout=60)
        resp.raise_for_status()
        return PdfReader(io.BytesIO(resp.content))
    else:
        return PdfReader(source)


def iter_page_text(reader: PdfReader) -> Iterator[Tuple[int, str]]:
    """Yield (page_index_1_based, page_text) for each page."""
    for i, page in enumerate(reader.pages, start=1):
        # extract_text() returns unicode str
        text = page.extract_text() or ""
        yield i, text


# def find_first_checkbox_line(text_slice: str) -> Optional[str]:
#     """Return the first checkbox line (e.g., '☑ English') from a given text slice."""
#     m = CHECKBOX_LINE_REGEX.search(text_slice)
#     if m:
#         return m.group(1).strip()
#     return None


# def extract_qas_from_page(page_text: str) -> Iterator[Tuple[str, str, Optional[str]]]:
#     """
#     From a single page of text, yield tuples: (section, question, answer).
#     - section: like '1.1'
#     - question: full question text ending with '?'
#     - answer: first checkbox line found after question (e.g., '☑ English'), or None if not found
#     """
#     # Work on a normalized view of whitespace to avoid layout noise,
#     # but keep newlines (important for the checkbox line match).
#     text = page_text

#     for match in SECTION_QUESTION_REGEX.finditer(text):
#         section = match.group("section").strip()
#         question = match.group("question").strip()

#         # Search for answer between end of question and the next section token
#         start = match.end()
#         next_section_match = NEXT_SECTION_TOKEN.search(text, pos=start)
#         end = next_section_match.start() if next_section_match else len(text)
#         scope = text[start:end]

#         answer = find_first_checkbox_line(scope)

#         yield section, question, answer

# QUESTION_REGEX = re.compile(
#     r"(?P<question>[^()\n].*?\?)",
#     flags=re.DOTALL
# )

# CHECKBOX_REGEX = re.compile(
#     r"^[ \t]*([☑☐✔✖✕✗□].+)$",
#     flags=re.MULTILINE
# )

# def extract_qas_from_page(page_text: str):
#     """
#     Extract only REAL questions (text ending with '?') 
#     and their nearest checkbox answers.
#     Ignores headings, section numbers, and sub-headings.
#     """
#     text = page_text

#     for match in QUESTION_REGEX.finditer(text):
#         question = match.group("question").strip()

#         # Find answer immediately after the question
#         start = match.end()
#         scope = text[start:]

#         checkbox_match = CHECKBOX_REGEX.search(scope)
#         answer = checkbox_match.group(1).strip() if checkbox_match else ""

#         yield question, answer

# -*- coding: utf-8 -*-
import re
from typing import Iterator, Optional, Tuple

# -------------------------------
# New/updated regex definitions
# -------------------------------

# Leaf question lines, e.g., "(1.3.2) Organization type"
# Requires at least TWO dots in the number (=> leaf-like items)

LEAF_QUESTION_REGEX = re.compile(
    r"(?m)^\s*\((?P<qno>\d+(?:\.\d+){2,})\)\s*(?P<qtext>.+?)\s*$"
)


# Any question token (parent or leaf), used as a boundary
ANY_QUESTION_TOKEN = re.compile(
    r"(?m)^\s*\(\d+(?:\.\d+)+\)"
)

# Section header token (e.g., "C1. Introduction"), also a boundary
SECTION_HEADER_TOKEN = re.compile(
    r"(?m)^\s*C\d+\.\s+"
)

# "Select from:" line that precedes options
SELECT_FROM_LINE = re.compile(
    r"(?im)^\s*Select from:\s*$"
)

# A "selected" option line (keep only checked/selected marks)
# Covers: ☑, ✅, ✔, ✓, ☒, ✖, X / [x] / [X] / [✓] / [✔]
SELECTED_OPTION_LINE = re.compile(
    r"(?m)^\s*(?:[\u2611\u2705\u2714\u2716\u2612]|(?:\[[xX✓✔]\]))\s+.+$"
)

def _first_boundary_pos(text: str, start: int) -> int:
    """
    Returns the earliest boundary position after 'start':
    - next ANY_QUESTION_TOKEN
    - next SECTION_HEADER_TOKEN
    If none found, returns len(text).
    """
    end = len(text)
    m1 = ANY_QUESTION_TOKEN.search(text, pos=start)
    if m1:
        end = min(end, m1.start())
    m2 = SECTION_HEADER_TOKEN.search(text, pos=start)
    if m2:
        end = min(end, m2.start())
    return end

def _extract_checkbox_answer(scope: str) -> Optional[str]:
    """
    From a scope after a question, if a 'Select from:' block exists,
    keep 'Select from:' + all immediately-following SELECTED_OPTION_LINE lines.
    Stops on first blank line or when lines stop looking like options.
    """
    sf = SELECT_FROM_LINE.search(scope)
    if not sf:
        return None

    after = scope[sf.end():]
    selected = []
    for line in after.splitlines():
        # Stop if we hit another question or section header accidentally (safety)
        if ANY_QUESTION_TOKEN.match(line) or SECTION_HEADER_TOKEN.match(line):
            break

        # stop on first blank line IF we already collected something
        if not line.strip():
            if selected:
                break
            else:
                continue

        # collect only selected options
        if SELECTED_OPTION_LINE.match(line):
            selected.append(line.strip())
        else:
            # If we already started collecting selected lines and now hit a non-option, stop
            if selected:
                break
            # Otherwise continue scanning (there can be formatting noise)
            continue

    if selected:
        return "Select from:\n" + "\n".join(selected)
    return None

def _extract_text_answer(scope: str) -> str:
    """
    Take the first non-empty paragraph after the question as the answer,
    until a blank line or boundary. Skip a stray 'Select from:' if present
    without selected options.
    """
    lines = [ln.rstrip() for ln in scope.splitlines()]
    buf = []
    started = False

    for line in lines:
        if ANY_QUESTION_TOKEN.match(line) or SECTION_HEADER_TOKEN.match(line):
            break
        if SELECT_FROM_LINE.match(line):
            # This question uses checkboxes; textual answer not applicable.
            break

        if line.strip():
            buf.append(line.strip())
            started = True
        elif started:
            # stop at first blank line after we started capturing
            break

    return "\n".join(buf).strip()

def extract_qas_from_page(page_text: str):
    """
    Extract ONLY leaf question–answer pairs from a single page of text.
    Yields tuples: (question_no, question_content, answer_content)

    - Keeps questions like (1.3.2), (1.3.3), (1.4.1)
    - Drops section headers (e.g., "C1. Introduction") and parent prompts like (1.3)
    - For checkbox answers: keeps "Select from:\n<selected options>"
    - For textual answers: captures the first paragraph after the question
    """
    text = page_text or ""

    for m in LEAF_QUESTION_REGEX.finditer(text):
        qno = m.group("qno").strip()
        qtext = m.group("qtext").strip()

        # find answer scope (from end of this match to the next boundary)
        start = m.end()
        end = _first_boundary_pos(text, start)
        scope = text[start:end]

        answer = _extract_checkbox_answer(scope)
        if answer is None:
            answer = _extract_text_answer(scope)

        yield qno, qtext, (answer or "")

        