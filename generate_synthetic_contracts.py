"""
Utilities to fabricate lightweight contract samples for demos and tests.

The script generates Markdown files that resemble bilingual contracts.  The
synthetic data is intentionally simple—its goal is to provide deterministic
fixtures for the extraction heuristics without relying on proprietary
documents.  Optionally, the script can render the Markdown text into images to
simulate scanned contracts.
"""

from __future__ import annotations

import argparse
import random
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - Pillow is optional
    Image = None
    ImageDraw = None
    ImageFont = None


ZH_TEMPLATE = textwrap.dedent(
    """
    # 服务合同

    **合同编号**: {contract_id}

    | 项目        | 说明 |
    | ----------- | ---- |
    | 甲方        | {party_a} |
    | 乙方        | {party_b} |
    | 合同金额    | {amount} |
    | 签署日期    | {sign_date} |
    | 生效日期    | {effective_date} |
    | 到期日期    | {termination_date} |

    ## 第一条 服务内容

    乙方应按照甲方要求提供专业化服务，并确保交付成果满足双方约定的质量标准。

    ## 第二条 费用及支付方式

    甲方应在合同生效后五个工作日内支付合同总金额的 50%，剩余款项于项目验收后七日内付清。

    ## 第三条 保密义务

    双方对在合同履行过程中获知的任何商业信息负有严格的保密义务。
    """
).strip()


EN_TEMPLATE = textwrap.dedent(
    """
    # Professional Services Agreement

    **Contract ID**: {contract_id}

    | Item            | Details |
    | --------------- | ------- |
    | Party A         | {party_a} |
    | Party B         | {party_b} |
    | Total Amount    | {amount} |
    | Date of Signature | {sign_date} |
    | Effective Date  | {effective_date} |
    | Expiry Date     | {termination_date} |

    ## Article 1 – Scope

    Party B shall deliver the agreed scope of work to Party A in accordance with
    the milestones defined in Annex A.

    ## Article 2 – Payment

    Party A shall remit 50% of the total amount within five business days after
    the contract becomes effective. The remaining balance is due within seven
    days after final acceptance.

    ## Article 3 – Confidentiality

    Both parties commit to keeping all trade secrets confidential.
    """
).strip()


@dataclass
class ContractSample:
    language: str
    contract_id: str
    party_a: str
    party_b: str
    amount: str
    sign_date: str
    effective_date: str
    termination_date: str

    def render_markdown(self) -> str:
        template = ZH_TEMPLATE if self.language == "zh" else EN_TEMPLATE
        return template.format(
            contract_id=self.contract_id,
            party_a=self.party_a,
            party_b=self.party_b,
            amount=self.amount,
            sign_date=self.sign_date,
            effective_date=self.effective_date,
            termination_date=self.termination_date,
        )


def _random_date() -> str:
    year = random.randint(2020, 2025)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


def _random_date_cn() -> str:
    year = random.randint(2020, 2025)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year}年{month}月{day}日"


def _random_amount(currency: str) -> str:
    value = random.randint(10, 500) * 1000
    if currency == "CNY":
        return f"人民币 {value:,} 元"
    return f"USD {value:,.2f}"


def _ensure_font(size: int = 32):
    if ImageFont is None:  # pragma: no cover - optional branch
        return None
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except (OSError, AttributeError):
        return ImageFont.load_default()


def render_markdown_to_image(markdown_text: str, destination: Path) -> None:
    """Render markdown text onto a white canvas for quick OCR experiments."""

    if Image is None or ImageDraw is None:  # pragma: no cover - Pillow optional
        raise RuntimeError("Pillow is required to render images.")

    lines = markdown_text.splitlines()
    font = _ensure_font()
    line_height = font.getbbox("Ag")[3] + 10
    width = 1500
    height = max(1200, line_height * len(lines) + 100)

    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    y = 40
    for line in lines:
        draw.text((40, y), line, fill="black", font=font, spacing=4)
        y += line_height

    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def create_samples(output_dir: Path, *, create_images: bool = False, count: int = 4) -> List[ContractSample]:
    random.seed(2024)
    output_dir.mkdir(parents=True, exist_ok=True)

    parties_cn = [
        ("北京星河科技有限公司", "上海明远数字有限公司"),
        ("杭州未来医疗科技公司", "深圳云帆信息科技有限公司"),
    ]
    parties_en = [
        ("Aurora Analytics LLC", "Blue Harbor Consulting Ltd."),
        ("Nebula Labs Inc.", "Southwind Solutions Co."),
    ]

    samples: List[ContractSample] = []
    for idx in range(count):
        language = "zh" if idx % 2 == 0 else "en"
        if language == "zh":
            party_a, party_b = parties_cn[idx % len(parties_cn)]
            sample = ContractSample(
                language=language,
                contract_id=f"CN-{idx+1:03d}",
                party_a=party_a,
                party_b=party_b,
                amount=_random_amount("CNY"),
                sign_date=_random_date_cn(),
                effective_date=_random_date_cn(),
                termination_date=_random_date_cn(),
            )
        else:
            party_a, party_b = parties_en[idx % len(parties_en)]
            sample = ContractSample(
                language=language,
                contract_id=f"EN-{idx+1:03d}",
                party_a=party_a,
                party_b=party_b,
                amount=_random_amount("USD"),
                sign_date=_random_date(),
                effective_date=_random_date(),
                termination_date=_random_date(),
            )
        samples.append(sample)

        markdown_text = sample.render_markdown()
        md_path = output_dir / f"{sample.contract_id}.md"
        md_path.write_text(markdown_text, encoding="utf-8")

        if create_images:
            try:
                img_path = output_dir / f"{sample.contract_id}.png"
                render_markdown_to_image(markdown_text, img_path)
            except RuntimeError as exc:  # pragma: no cover - optional branch
                print(f"[WARN] Could not render image for {sample.contract_id}: {exc}")

    return samples


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic contract samples for PaddleOCR-VL demos.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "synthetic_contracts",
        help="Directory where Markdown (and optional image) files will be written.",
    )
    parser.add_argument(
        "--images",
        action="store_true",
        help="Render the generated Markdown into PNG images (requires Pillow).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=4,
        help="Number of contract samples to create.",
    )
    args = parser.parse_args(argv)

    create_samples(args.output_dir, create_images=args.images, count=args.count)
    print(f"Synthetic contracts written to: {args.output_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

