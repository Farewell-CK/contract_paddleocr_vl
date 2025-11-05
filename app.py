"""
Command line interface for the PaddleOCR-VL contract parsing demo.

Example usage:

    python -m applications.contract_ocr_vl.app \
        --input ./data/contract.pdf \
        --output-dir ./outputs \
        --vl-rec-backend vllm-server \
        --vl-rec-server-url http://localhost:8118/v1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parent))
    from contract_ocr_pipeline import DEFAULT_PIPELINE_KWARGS, run_contract_ocr  # type: ignore
else:
    from .contract_ocr_pipeline import DEFAULT_PIPELINE_KWARGS, run_contract_ocr


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PaddleOCR-VL contract parsing on images or PDFs.")
    parser.add_argument(
        "--input",
        required=True,
        nargs="+",
        help="One or more image/PDF paths (directories will be expanded).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to store Markdown/JSON artefacts and summary.json.",
    )
    parser.add_argument(
        "--vl-rec-backend",
        choices=["native", "vllm-server", "sglang-server", "fastdeploy-server"],
        default=None,
        help="Override the backend used by PaddleOCR-VL's recognition component.",
    )
    parser.add_argument(
        "--vl-rec-server-url",
        default=None,
        help="URL of the GenAI server when using vLLM/SGLang/FastDeploy backends.",
    )
    parser.add_argument(
        "--vl-rec-max-concurrency",
        type=int,
        default=None,
        help="Optional concurrency hint forwarded to the backend.",
    )
    parser.add_argument(
        "--disable-layout-detection",
        action="store_true",
        help="Skip layout detection to reduce latency (may impact accuracy).",
    )
    parser.add_argument(
        "--disable-orientation",
        action="store_true",
        help="Disable document orientation classification.",
    )
    parser.add_argument(
        "--disable-unwarping",
        action="store_true",
        help="Disable document unwarping.",
    )
    parser.add_argument(
        "--enable-chart-recognition",
        action="store_true",
        help="Enable chart recognition (disabled by default to save resources).",
    )
    return parser


def _collect_pipeline_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    if args.disable_layout_detection:
        overrides["use_layout_detection"] = False
    if args.disable_orientation:
        overrides["use_doc_orientation_classify"] = False
    if args.disable_unwarping:
        overrides["use_doc_unwarping"] = False
    if args.enable_chart_recognition:
        overrides["use_chart_recognition"] = True
    if args.vl_rec_backend:
        overrides["vl_rec_backend"] = args.vl_rec_backend
    if args.vl_rec_server_url:
        overrides["vl_rec_server_url"] = args.vl_rec_server_url
    if args.vl_rec_max_concurrency is not None:
        overrides["vl_rec_max_concurrency"] = args.vl_rec_max_concurrency
    return overrides


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pipeline_kwargs = dict(DEFAULT_PIPELINE_KWARGS)
    pipeline_kwargs.update(_collect_pipeline_overrides(args))

    result = run_contract_ocr(
        inputs=args.input,
        output_dir=args.output_dir,
        pipeline_kwargs=pipeline_kwargs,
    )

    print("==== Contract parsing summary ====")
    print(json.dumps(result["fields"], ensure_ascii=False, indent=2))
    if args.output_dir:
        print(f"\nDetailed artefacts written to: {Path(args.output_dir).resolve()}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
