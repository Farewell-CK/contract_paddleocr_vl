"""
High-level helpers that orchestrate PaddleOCR-VL to analyse contract documents.

The functions in this module demonstrate a realistic end-to-end workflow that:

1. Collects input files (images or PDFs) that represent contract scans.
2. Runs PaddleOCR-VL to generate structured Markdown/JSON outputs.
3. Extracts key contract attributes using :mod:`contract_extraction`.
4. Optionally persists Markdown/JSON artefacts to disk for auditing.

The actual OCR step depends on the PaddleOCR runtime and therefore may require
GPU resources to run efficiently.  All heavy lifting is contained in the
``run_contract_ocr`` function so other modules (such as the Gradio demo) can
reuse it.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from paddleocr import PaddleOCRVL

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parent))
    from contract_extraction import extract_contract_fields  # type: ignore
else:
    from .contract_extraction import extract_contract_fields

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".pdf", ".tif", ".tiff"}

DEFAULT_PIPELINE_KWARGS = {
    "use_doc_orientation_classify": True,
    "use_doc_unwarping": True,
    "use_layout_detection": True,
    "use_chart_recognition": False,
    "format_block_content": True,
}


def _resolve_inputs(inputs: str | Path | Sequence[str | Path]) -> List[str]:
    """
    Normalise user-provided inputs to a list of filesystem paths.

    PaddleOCR-VL already accepts strings, lists, directories or URLs.  However,
    normalising upfront allows us to validate existence early and support
    glob-style directory expansion.
    """

    def _coerce_path(item: str | Path) -> Path:
        p = Path(item)
        if not p.exists():
            raise FileNotFoundError(f"Input path does not exist: {p}")
        return p

    if isinstance(inputs, (str, Path)):
        path = _coerce_path(inputs)
        if path.is_dir():
            return [
                str(child)
                for child in sorted(path.iterdir())
                if child.suffix.lower() in SUPPORTED_SUFFIXES
            ]
        return [str(path)]

    if isinstance(inputs, Sequence):
        return [str(_coerce_path(item)) for item in inputs]

    raise TypeError(f"Unsupported input specification: {type(inputs)!r}")


def _extract_markdown_from_result(result) -> Optional[str | Mapping[str, str]]:
    """
    Retrieve the Markdown payload from a PaddleOCR-VL result object.

    ``Result.markdown`` can be either a dictionary (containing ``markdown_text``
    and optional image assets) or a plain string.
    """

    if hasattr(result, "markdown"):
        markdown_payload = result.markdown
        if isinstance(markdown_payload, (str, Mapping)):
            return markdown_payload
    # Some versions expose the payload inside the JSON structure.
    if hasattr(result, "json"):
        json_payload = getattr(result, "json")
        if isinstance(json_payload, Mapping):
            markdown_info = json_payload.get("markdown")
            if isinstance(markdown_info, (str, Mapping)):
                return markdown_info
    return None


def _result_to_dict(result) -> Optional[Mapping]:
    if hasattr(result, "json"):
        payload = result.json
        if isinstance(payload, Mapping):
            return payload
    if hasattr(result, "res"):
        payload = getattr(result, "res")
        if isinstance(payload, Mapping):
            return payload
    return None


def _write_markdown_file(markdown_text: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(markdown_text, encoding="utf-8")


def _write_json_file(obj: Mapping, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as fp:
        json.dump(obj, fp, ensure_ascii=False, indent=2)


def run_contract_ocr(
    inputs: str | Path | Sequence[str | Path],
    *,
    output_dir: str | Path | None = None,
    pipeline_kwargs: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """
    Execute PaddleOCR-VL on the given inputs and extract key contract fields.

    Parameters
    ----------
    inputs:
        A path (or list of paths) pointing to image/PDF files that represent
        contracts.
    output_dir:
        When provided, Markdown and JSON artefacts for each page are saved under
        the directory.  The extracted field summary is also written to
        ``summary.json``.
    pipeline_kwargs:
        Optional overrides passed directly to :class:`PaddleOCRVL`.  Sensible
        defaults are enabled (orientation classification, unwarping, layout
        detection, Markdown formatting) but callers may override them to match
        their runtime needs.
    """

    pipeline_params = dict(DEFAULT_PIPELINE_KWARGS)
    if pipeline_kwargs:
        pipeline_params.update(pipeline_kwargs)

    input_paths = _resolve_inputs(inputs)
    logger.info("Running PaddleOCR-VL on %d file(s)", len(input_paths))

    pipeline = PaddleOCRVL(**pipeline_params)
    markdown_segments: List[str | Mapping[str, str]] = []
    raw_payloads: List[Mapping] = []

    try:
        results = pipeline.predict(input_paths)
        for res in results:
            markdown_payload = _extract_markdown_from_result(res)
            if markdown_payload:
                markdown_segments.append(markdown_payload)
            result_dict = _result_to_dict(res)
            if result_dict:
                raw_payloads.append(result_dict)
    finally:
        pipeline.close()

    if not markdown_segments:
        logger.warning("No markdown payloads were produced by PaddleOCR-VL.")

    extracted_fields = extract_contract_fields(markdown_segments)

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        summary_path = output_path / "summary.json"
        _write_json_file(
            {"inputs": input_paths, "fields": extracted_fields},
            summary_path,
        )
        for idx, payload in enumerate(raw_payloads):
            base_name = payload.get("input_path")
            page_index = payload.get("page_index")
            if base_name:
                stem = Path(base_name).stem
            else:
                stem = f"page_{idx:03d}"
            if page_index is not None:
                stem = f"{stem}_page{int(page_index):03d}"
            json_path = output_path / f"{stem}.json"
            _write_json_file(payload, json_path)

        for idx, markdown_payload in enumerate(markdown_segments):
            if isinstance(markdown_payload, Mapping):
                md_text = markdown_payload.get("markdown_text") or markdown_payload.get("markdown")
            else:
                md_text = markdown_payload
            if not md_text:
                continue
            md_path = output_path / f"page_{idx:03d}.md"
            _write_markdown_file(md_text, md_path)

    return {
        "inputs": input_paths,
        "fields": extracted_fields,
        "markdown": markdown_segments,
        "raw": raw_payloads,
    }


__all__ = ["run_contract_ocr", "DEFAULT_PIPELINE_KWARGS"]
