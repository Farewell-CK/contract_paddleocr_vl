from ..contract_extraction import extract_contract_fields


def test_extract_contract_fields_from_markdown_table():
    markdown_cn = """
    | 项目        | 说明 |
    | ----------- | ---- |
    | 甲方        | 北京星河科技有限公司 |
    | 乙方        | 上海明远数字有限公司 |
    | 合同金额    | 人民币 120,000 元 |
    | 签署日期    | 2024年05月12日 |
    | 生效日期    | 2024年05月13日 |
    | 到期日期    | 2025年05月12日 |
    """

    result = extract_contract_fields([markdown_cn])

    assert result["party_a"] == "北京星河科技有限公司"
    assert result["party_b"] == "上海明远数字有限公司"
    assert result["contract_amount"] == "人民币 120,000 元"
    assert result["sign_date"] == "2024年05月12日"
    assert result["effective_date"] == "2024年05月13日"
    assert result["termination_date"] == "2025年05月12日"


def test_extract_contract_fields_with_english_text_and_headings():
    markdown_en = """
    # Professional Services Agreement

    Party A: Aurora Analytics LLC
    Party B: Blue Harbor Consulting Ltd.
    Total Amount: USD 250,000.00
    Date of Signature: March 18, 2024
    Effective Date: March 20, 2024
    Expiry Date: March 19, 2025
    """

    result = extract_contract_fields([markdown_en])

    assert result["party_a"] == "Aurora Analytics LLC"
    assert result["party_b"] == "Blue Harbor Consulting Ltd."
    assert result["contract_amount"] == "USD 250,000.00"
    assert result["sign_date"] == "March 18, 2024"
    assert result["effective_date"] == "March 20, 2024"
    assert result["termination_date"] == "March 19, 2025"

