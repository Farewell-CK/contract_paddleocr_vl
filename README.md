# PaddleOCR-VL 多语言合同解析实践

本项目演示如何基于 **PaddleOCR-VL** 快速搭建一个“合同解析与关键信息抽取”小工具，包含以下内容：

- `generate_synthetic_contracts.py`：自动生成中英文合同 Markdown（可选渲染为 PNG），方便复现示例；
- `contract_ocr_pipeline.py`：封装 PaddleOCR-VL 推理流程，并将输出交给信息抽取模块；
- `contract_extraction.py`：针对合同 Markdown 进行正则 + 表格混合解析，输出甲乙方、金额、日期等关键字段；
- `contract_ocr_demo.ipynb`：Notebook 版实践项目，介绍背景架构、环境准备、测试与完整流程；
- `gradio_app.py`：提供一个简单的 Web Demo，上传合同即可返回 Markdown 与关键信息概览；
- `tests/test_contract_extraction.py`：对抽取逻辑进行快速单元测试，便于 CI 验证。

> **注意**：PaddleOCR-VL 默认模型体积较大，建议先阅读官方文档准备好运行环境，并优先使用 GPU/VLM 服务化部署以获得更快推理速度。

---

## 快速开始

1. **安装依赖**（建议放在独立虚拟环境）：

   ```bash
   # 以 GPU CUDA12.6 环境为例，其它平台请参考官方安装说明
   python -m pip install paddlepaddle-gpu==3.2.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
   python -m pip install -U "paddleocr[doc-parser]" gradio pillow pytest
   ```

   如需使用 vLLM/SGLang 后端，请参考官方文档执行 `paddleocr install_genai_server_deps vllm` 并启动 `paddleocr genai_server`。

2. **生成示例合同**（在仓库根目录执行）：

   ```bash
   python generate_synthetic_contracts.py --output-dir data/synthetic_contracts
   ```

3. **运行一次合同解析**（在仓库根目录执行）：

   ```bash
   python app.py --input data/synthetic_contracts/EN-002.md --output-dir ./ocr_outputs
   ```

   命令会调用 `PaddleOCRVL` 对输入进行解析，将 Markdown/JSON 结果保存到 `ocr_outputs` 并输出提取出来的关键信息。

4. **体验 Gradio Demo**（在仓库根目录执行）：

   ```bash
   python gradio_app.py
   ```

   浏览器会打开一个上传页面，选择合同文件即可快速查看解析结果。

---

## 项目结构

```
contract_paddleocr_vl/
├── __init__.py
├── README.md
├── app.py                     # 命令行封装
├── contract_extraction.py     # 关键信息抽取逻辑
├── contract_ocr_pipeline.py   # PaddleOCR-VL 推理封装
├── contract_ocr_demo.ipynb    # Notebook 实践流程
├── generate_synthetic_contracts.py
├── gradio_app.py
└── tests/
    └── test_contract_extraction.py
```

---

## 常见问题

- **合同样本从哪里来？**
  - 可使用脚本生成的 Markdown/PNG；
  - 亦可使用公开合同模板（如 GitHub “contracts” 仓库）或自行翻译调整。

- **如何提速？**
  - 启用 `vl_rec_backend="vllm-server"` 并配置 `vl_rec_server_url` 指向已经运行的 VLM 服务；
  - 调整 `vl_rec_max_concurrency`、`use_layout_detection` 等参数；
  - 参考官方文档中的性能调优章节。

- **抽取字段缺失怎么办？**
  - `contract_extraction.extract_contract_fields` 会对未命中的字段返回 `None`，可在结果界面提示用户人工补录；
  - 若有新的合同模板，可在 `_FIELD_PATTERNS` 或 `_TABLE_HEADERS` 中补充匹配规则。

---

欢迎将实践经验整理成文章投稿到百度飞桨星河社区，分享更多行业场景下的 PaddleOCR-VL 最佳实践。祝开发顺利！
