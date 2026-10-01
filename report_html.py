import csv
from html import escape
from pathlib import Path

COLUMNS = [
    "account", "symbol", "calculated_position",
    "reference_position", "difference", "status",
]
LABELS = [
    "账户", "股票", "计算持仓", "参考持仓", "差异", "状态",
]
STATUSES = {
    "MATCH", "MISMATCH", "MISSING_REFERENCE", "REFERENCE_ONLY",
}


def build_html(rows):
    rows = list(rows)
    if not rows:
        raise ValueError("Report contains no positions.")

    for row in rows:
        if any(key not in row or row[key] is None for key in COLUMNS):
            raise ValueError("Missing report fields.")
        if row["status"] not in STATUSES:
            raise ValueError("Unknown report status.")

    exceptions = sum(row["status"] != "MATCH" for row in rows)
    ordered = sorted(
        rows,
        key=lambda row: (
            row["status"] == "MATCH",
            row["account"],
            row["symbol"],
        ),
    )

    body = []
    for row in ordered:
        style = "match" if row["status"] == "MATCH" else "exception"
        cells = "".join(
            "<td>" + escape(str(row[key])) + "</td>"
            for key in COLUMNS
        )
        body.append(f'<tr class="{style}">{cells}</tr>')

    header = "".join(f"<th>{label}</th>" for label in LABELS)
    verdict = "存在核对异常" if exceptions else "全部一致"

    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>持仓核对报告</title>
<style>
body {
    font-family: system-ui, sans-serif;
    max-width: 1100px; margin: 40px auto;
    padding: 0 20px; color: #172033; background: #f5f7fb;
}
.summary {
    background: white; padding: 20px;
    border-radius: 12px; margin-bottom: 24px;
}
.table-wrap { overflow-x: auto; }
table {
    width: 100%; border-collapse: collapse; background: white;
}
th, td {
    padding: 14px; text-align: left;
    border-bottom: 1px solid #e5e7eb;
}
th { background: #e8edf5; }
.exception { background: #fff0f0; color: #9b1c1c; }
.match { color: #166534; }
.note { color: #586174; font-size: 14px; }
</style>
</head>
<body>
<h1>持仓核对报告</h1>
""" + (
        f'<section class="summary"><h2>{verdict}</h2>'
        f"<p>持仓：{len(rows)} ｜ 一致：{len(rows) - exceptions}"
        f" ｜ 异常：{exceptions}</p></section>"
        '<div class="table-wrap"><table>'
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
        '<p class="note">差异 = 计算持仓 − 参考持仓。'
        "单边缺失时差异留空；异常记录优先显示。"
        "此报告不代表输入数据完整性或交易日期已通过校验。</p>"
        "</body></html>"
    )


def write_html(csv_path):
    csv_path = Path(csv_path)
    with csv_path.open(newline="", encoding="utf-8") as file:
        document = build_html(csv.DictReader(file))

    output = csv_path.with_suffix(".html")
    staging = output.with_suffix(".html.tmp")
    staging.write_text(document, encoding="utf-8")
    staging.replace(output)
    return output
