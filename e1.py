# -*- coding: utf-8 -*-
"""
Fully rewritten CDP PDF extractor with:
- Multi-level hierarchy detection
- Flat fields (parent_section, grandparent_section, etc.)
- Leaf question extraction (2+ dots)
- Robust broken-line PDF parsing
- Checkbox + text answer extraction
"""

import re
from typing import Iterator, Tuple, Optional

# ---------------------------
# Regex definitions
# ---------------------------

QUESTION_TOKEN = re.compile(r"^\s*\((\d+(?:\.\d+)+)\)\s*$")
INLINE_QUESTION = re.compile(r"^\s*\((\d+(?:\.\d+)+)\)\s*(.+)$")

CHECKBOX_SELECTED = re.compile(
    r"^\s*(?:[\u2611\u2705\u2714\u2612]|x|\[x\]|\[X\]).+$",
    re.IGNORECASE
)

SELECT_FROM = re.compile(r"^\s*Select from:\s*$", re.IGNORECASE)

# ---------------------------
# Helpers
# ---------------------------

def normalize_lines(text: str) -> list:
    """Normalize PDF text into usable lines."""
    lines = []
    for ln in text.splitlines():
        ln = ln.replace("\u00a0", " ").strip()
        if ln:
            lines.append(ln)
    return lines


def extract_answer(lines: list, idx: int) -> str:
    """
    Extract answer block beginning just after a leaf question.
    Stops on encountering the next question token or blank line.
    """
    collected = []
    i = idx

    # Detect checkbox block
    if i < len(lines) and SELECT_FROM.match(lines[i]):
        collected.append("Select from:")
        i += 1
        while i < len(lines):
            if QUESTION_TOKEN.match(lines[i]) or INLINE_QUESTION.match(lines[i]):
                break
            if CHECKBOX_SELECTED.match(lines[i]):
                collected.append(lines[i])
            else:
                break
            i += 1
        return "\n".join(collected).strip()

    # Text block
    started = False
    while i < len(lines):
        if QUESTION_TOKEN.match(lines[i]) or INLINE_QUESTION.match(lines[i]):
            break
        if not lines[i].strip():
            if started:
                break
        else:
            collected.append(lines[i].strip())
            started = True
        i += 1

    return "\n".join(collected).strip()


# ---------------------------
# Main extractor
# ---------------------------

def extract_qas_from_page(page_text: str) -> Iterator[Tuple]:
    """
    Yields:
      (section, question, answer, parent_section, parent_question,
       grandparent_section, grandparent_question)

    Only leaf questions (2+ dots) become Q&A entries.
    """
    lines = normalize_lines(page_text)
    hierarchy = []  # Stack of (section, question)
    i = 0

    while i < len(lines):
        ln = lines[i]

        # Case 1: (2.4) where text is on next lines
        m1 = QUESTION_TOKEN.match(ln)
        if m1:
            sec = m1.group(1)
            qtext = ""

            # Try next lines for the question text
            if i + 1 < len(lines):
                if not QUESTION_TOKEN.match(lines[i+1]):
                    qtext = lines[i+1].strip()

            # Update hierarchy
            parts = sec.split(".")
            depth = len(parts)

            while len(hierarchy) >= depth:
                hierarchy.pop()
            hierarchy.append((sec, qtext))
            i += 1
            continue

        # Case 2: inline question "(2.4) Text"
        m2 = INLINE_QUESTION.match(ln)
        if m2:
            sec = m2.group(1)
            qtext = m2.group(2).strip()

            parts = sec.split(".")
            depth = len(parts)

            while len(hierarchy) >= depth:
                hierarchy.pop()
            hierarchy.append((sec, qtext))
            i += 1
            continue

        # Check if current top of hierarchy is a leaf (2.4.7 etc.)
        if hierarchy:
            sec, qtext = hierarchy[-1]
            if sec.count(".") >= 2:  # leaf-level question
                answer = extract_answer(lines, i)
                # Pull parents
                parent_section = parent_question = ""
                grand_section = grand_question = ""

                if len(hierarchy) >= 2:
                    parent_section, parent_question = hierarchy[-2]
                if len(hierarchy) >= 3:
                    grand_section, grand_question = hierarchy[-3]

                yield (
                    sec,
                    qtext,
                    answer,
                    parent_section,
                    parent_question,
                    grand_section,
                    grand_question
                )

                # Reset leaf to avoid double output
                hierarchy.pop()

        i += 1