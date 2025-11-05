"""
Contract-specific parsing helpers for PaddleOCR-VL outputs.

The PaddleOCR-VL pipeline is capable of exporting structured Markdown that
contains paragraphs and Markdown tables.  This module provides lightweight
regular-expression based heuristics to recover the key facts that通常在合同中会
出现，例如甲乙双方、签署日期、合同金额以及有效期。

The functions are written so they can be unit-tested without requiring access to
the full OCR stack.  They operate purely on Markdown strings that are produced
by PaddleOCR-VL's ``Result.markdown`` payload.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence


def _normalise_markdown_segments(markdown_segments: Sequence[str | Mapping[str, str]]) -> List[str]:
    """
    Flatten PaddleOCR-VL markdown payloads into plain text strings.

    ``Result.markdown`` can be either a plain string or a dictionary with the
    ``"markdown_text"`` key.  This helper hides those differences so downstream
    code always deals with a list of strings.
    """

    texts: List[str] = []
    for segment in markdown_segments:
        if isinstance(segment, str):
            texts.append(segment)
        elif isinstance(segment, Mapping):
            if "markdown_text" in segment and isinstance(segment["markdown_text"], str):
                texts.append(segment["markdown_text"])
            elif "markdown" in segment and isinstance(segment["markdown"], str):
                texts.append(segment["markdown"])
        else:
            raise TypeError(f"Unsupported markdown segment type: {type(segment)!r}")
    return texts


_FIELD_PATTERNS: Dict[str, List[str]] = {
    # Party names
    "party_a": [
        r"(?:甲方|Party\s*A)\s*[:：]\s*([^\n，。,;；]+)",
        r"Party\s*A\s*[-–]\s*([^\n]+)",
    ],
    "party_b": [
        r"(?:乙方|Party\s*B)\s*[:：]\s*([^\n，。,;；]+)",
        r"Party\s*B\s*[-–]\s*([^\n]+)",
    ],
    # Amount / value
    "contract_amount": [
        r"(?:合同金额|Total\s*Amount|Amount\s*Due)\s*[:：]\s*([^\n]+)",
        r"(?:金额|payment)\s*(?:为|is)\s*([^\n]+)",
    ],
    # Dates
    "sign_date": [
        r"(?:签署日期|Date\s*of\s*Signature)\s*[:：]\s*([0-9]{4}[年\-/][0-9]{1,2}[月\-/][0-9]{1,2}日?)",
        r"(?:Signed\s*on)\s*[:：]?\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
        r"(?:Date\s*of\s*Signature)\s*[:：]\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
    ],
    "effective_date": [
        r"(?:生效日期|Effective\s*Date)\s*[:：]\s*([0-9]{4}[年\-/][0-9]{1,2}[月\-/][0-9]{1,2}日?)",
        r"(?:effective\s+as\s+of)\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
        r"(?:Effective\s*Date)\s*[:：]\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
    ],
    "termination_date": [
        r"(?:终止日期|Expiry\s*Date)\s*[:：]\s*([0-9]{4}[年\-/][0-9]{1,2}[月\-/][0-9]{1,2}日?)",
        r"(?:valid\s+until)\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
        r"(?:Expiry\s*Date|Termination\s*Date)\s*[:：]\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
    ],
}

_TABLE_HEADERS = {
    "party_a": {"甲方", "party a"},
    "party_b": {"乙方", "party b"},
    "contract_amount": {"合同金额", "total amount", "amount"},
    "sign_date": {"签署日期", "signature date"},
    "effective_date": {"生效日期", "effective date"},
    "termination_date": {"到期日期", "有效期至", "expiry date", "termination date"},
}


@dataclass
class ExtractionResult:
    """Container for key-value pairs extracted from contract markdown."""

    fields: MutableMapping[str, Optional[str]] = field(
        default_factory=lambda: {
            "party_a": None,
            "party_b": None,
            "contract_amount": None,
            "sign_date": None,
            "effective_date": None,
            "termination_date": None,
        }
    )
    matched_sources: MutableMapping[str, str] = field(default_factory=dict)

    def update(self, key: str, value: str, source: str) -> None:
        if value:
            cleaned = value.strip()
            if cleaned:
                self.fields[key] = cleaned
                self.matched_sources[key] = source.strip()

    def to_dict(self) -> Dict[str, Optional[str]]:
        return dict(self.fields)


def _search_patterns(text: str, key: str, patterns: Iterable[str], result: ExtractionResult) -> None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            result.update(key, match.group(1), match.group(0))
            break


def _parse_markdown_table(line: str) -> Optional[List[str]]:
    if "|" not in line:
        return None
    parts = [cell.strip() for cell in line.strip().split("|")]
    if len(parts) < 3:  # minimal table row: | header | value |
        return None
    return [cell for cell in parts if cell]


def _extract_from_tables(markdown_text: str, result: ExtractionResult) -> None:
    lines = markdown_text.splitlines()
    for idx, line in enumerate(lines):
        row = _parse_markdown_table(line)
        if not row:
            continue
        lowered = [cell.lower() for cell in row]
        for key, expected_headers in _TABLE_HEADERS.items():
            for header in expected_headers:
                if header.lower() in lowered[0]:
                    if len(row) > 1:
                        result.update(key, row[1], line)
                    break
        # Also support two-column tables where headers occupy first row and data row follows
        if idx == 0 and set(lowered) & {h.lower() for hs in _TABLE_HEADERS.values() for h in hs}:
            header_positions = {header.lower(): pos for pos, header in enumerate(lowered)}
            for key, headers in _TABLE_HEADERS.items():
                for header in headers:
                    pos = header_positions.get(header.lower())
                    if pos is not None and idx + 1 < len(lines):
                        next_row = _parse_markdown_table(lines[idx + 1])
                        if next_row and len(next_row) > pos:
                            result.update(key, next_row[pos], lines[idx + 1])


def extract_contract_fields(markdown_segments: Sequence[str | Mapping[str, str]]) -> Dict[str, Optional[str]]:
    """
    Extract a handful of commonly required contract fields from PaddleOCR-VL Markdown.

    Parameters
    ----------
    markdown_segments:
        Iterable of Markdown strings or dictionaries returned by
        :attr:`Result.markdown`.  The function is resilient to both formats.

    Returns
    -------
    dict
        Mapping containing the recognised fields.  Keys that could not be
        extracted are set to ``None`` so downstream consumers can display which
        data needs manual verification.
    """

    texts = _normalise_markdown_segments(markdown_segments)
    combined = "\n".join(texts)

    result = ExtractionResult()

    # First try to leverage Markdown tables as they tend to be highly structured.
    for text in texts:
        _extract_from_tables(text, result)

    # Fallback to line-level regular expressions.
    for key, patterns in _FIELD_PATTERNS.items():
        if result.fields.get(key):
            continue
        _search_patterns(combined, key, patterns, result)

    return result.to_dict()


__all__ = [
    "ExtractionResult",
    "extract_contract_fields",
]

