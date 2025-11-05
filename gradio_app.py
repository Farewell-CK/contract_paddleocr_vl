"""
Simple Gradio demo for the PaddleOCR-VL contract parsing workflow.

The UI allows users to upload a contract (image/PDF), select whether to enable
layout detection / orientation / unwarping, and optionally configure a remote
VLM backend such as vLLM.  Results include the extracted key fields and the
full Markdown reconstruction.
"""

from __future__ import annotations

from typing import List, Mapping, Optional

import gradio as gr

from .contract_ocr_pipeline import DEFAULT_PIPELINE_KWARGS, run_contract_ocr


def _flatten_markdown(markdown_segments: List[str | Mapping[str, str]]) -> str:
    pieces: List[str] = []
    for item in markdown_segments:
        if isinstance(item, Mapping):
            text = item.get("markdown_text") or item.get("markdown")
        else:
            text = item
        if text:
            pieces.append(text.strip())
    return "\n\n---\n\n".join(pieces)


def process_document(
    file: Optional[gr.File],
    use_layout_detection: bool,
    use_orientation: bool,
    use_unwarping: bool,
    use_chart_recognition: bool,
    vl_rec_backend: str,
    vl_rec_server_url: str,
    vl_rec_max_concurrency: Optional[int],
):
    if file is None:
        return "请上传合同文件。", {}

    pipeline_kwargs = dict(DEFAULT_PIPELINE_KWARGS)
    pipeline_kwargs["use_layout_detection"] = use_layout_detection
    pipeline_kwargs["use_doc_orientation_classify"] = use_orientation
    pipeline_kwargs["use_doc_unwarping"] = use_unwarping
    pipeline_kwargs["use_chart_recognition"] = use_chart_recognition

    if vl_rec_backend != "native":
        pipeline_kwargs["vl_rec_backend"] = vl_rec_backend
    if vl_rec_server_url:
        pipeline_kwargs["vl_rec_server_url"] = vl_rec_server_url
    if vl_rec_max_concurrency:
        pipeline_kwargs["vl_rec_max_concurrency"] = int(vl_rec_max_concurrency)

    try:
        result = run_contract_ocr(
            inputs=file.name,
            output_dir=None,
            pipeline_kwargs=pipeline_kwargs,
        )
    except Exception as exc:  # pragma: no cover - runtime errors shown in UI
        return f"解析失败：{exc}", {}

    markdown_combined = _flatten_markdown(result.get("markdown", []))
    if not markdown_combined:
        markdown_combined = "未获取到 Markdown 结果，请检查 OCR 配置或输入文件。"

    fields = result.get("fields") or {}
    return markdown_combined, fields


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="PaddleOCR-VL Contract Parser") as demo:
        gr.Markdown(
            """
            # PaddleOCR-VL 多语言合同解析 Demo

            上传合同（图片或 PDF），即可调用 PaddleOCR-VL 完成结构化解析，
            并从生成的 Markdown 中抽取甲乙方、金额、日期等关键字段。若使用远程
            vLLM/SGLang 服务，请在下方填写连接信息。
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(label="上传合同文件")
                use_layout_detection = gr.Checkbox(
                    value=True, label="使用版面分析", info="对复杂排版更友好，但略增耗时。"
                )
                use_orientation = gr.Checkbox(
                    value=True, label="启用方向分类", info="自动纠正翻转页面。"
                )
                use_unwarping = gr.Checkbox(
                    value=True, label="启用去畸变", info="适合弯曲/拍照场景。"
                )
                use_chart = gr.Checkbox(
                    value=False,
                    label="开启图表识别",
                    info="若合同包含图表，可打开此选项（需更多算力）。",
                )

                backend = gr.Dropdown(
                    choices=["native", "vllm-server", "sglang-server", "fastdeploy-server"],
                    value="native",
                    label="识别后端",
                )
                server_url = gr.Textbox(
                    label="服务器地址",
                    placeholder="http://127.0.0.1:8118/v1",
                )
                concurrency = gr.Number(
                    label="最大并发数（可选）",
                    value=None,
                    precision=0,
                )
                run_button = gr.Button("解析合同", variant="primary")

            with gr.Column(scale=1):
                markdown_output = gr.Markdown(label="Markdown 解析结果")
                fields_output = gr.JSON(label="关键信息")

        run_button.click(
            fn=process_document,
            inputs=[
                file_input,
                use_layout_detection,
                use_orientation,
                use_unwarping,
                use_chart,
                backend,
                server_url,
                concurrency,
            ],
            outputs=[markdown_output, fields_output],
        )

    return demo


def main() -> None:
    demo = build_demo()
    demo.queue(concurrency_count=1)
    demo.launch()


if __name__ == "__main__":  # pragma: no cover
    main()

