import argparse
import json
import tempfile
import webbrowser
from html import escape
from pathlib import Path

BASE = Path(__file__).resolve().parent
LABELS = {
    "MATCH": "全部一致",
    "EXCEPTIONS": "存在差异",
    "FAILED": "运行失败",
    "UNREADABLE": "清单损坏或缺失",
}


def text(value):
    return escape(str(value), quote=True)


def report_link(batch, manifest):
    if manifest.get("status") not in ("MATCH", "EXCEPTIONS"):
        return "—"

    raw = manifest.get("report_html")
    if not isinstance(raw, str) or not raw:
        return "报告不可用"

    try:
        relative = Path(raw)
        if relative.is_absolute():
            return "报告路径被拒绝"
        target = (batch / relative).resolve()
        target.relative_to(batch.resolve())
        if target.suffix != ".html" or not target.is_file():
            return "报告不可用"
        return f'<a href="{text(target.as_uri())}">打开报告</a>'
    except (OSError, ValueError, RuntimeError):
        return "报告路径被拒绝"


def build_history(root):
    entries = []
    for batch in root.glob("workflow_*"):
        if not batch.is_dir():
            continue
        try:
            manifest = json.loads(
                (batch / "manifest.json").read_text(encoding="utf-8")
            )
            if not isinstance(manifest, dict):
                raise ValueError("manifest must be an object")
            status = manifest.get("status")
            if not isinstance(status, str) or status not in LABELS:
                raise ValueError("missing or unknown status")
        except (OSError, ValueError, UnicodeError) as error:
            manifest = {
                "status": "UNREADABLE",
                "error": str(error),
            }
        entries.append((batch, manifest))

    entries.sort(
        key=lambda item: (
            str(item[1].get("started_at", "")),
            item[0].name,
        ),
        reverse=True,
    )

    rows = []
    counts = {status: 0 for status in LABELS}
    for batch, manifest in entries:
        status = manifest["status"]
        counts[status] += 1
        cells = [
            text(manifest.get("started_at", "时间未知")),
            text(batch.name),
            text(LABELS[status]),
            text(manifest.get("exit_code", "—")),
            report_link(batch, manifest),
            text(manifest.get("error", "")),
        ]
        rows.append(
            f'<tr class="{status}">'
            + "".join(f"<td>{cell}</td>" for cell in cells)
            + "</tr>"
        )

    summary = " ｜ ".join(
        f"{LABELS[status]}：{count}"
        for status, count in counts.items()
    )
    body = "".join(rows) or '<tr><td colspan="6">暂无运行记录</td></tr>'

    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>核对历史</title>
<style>
body {font-family:system-ui,sans-serif;margin:30px;color:#172033}
.summary {padding:18px;background:#eef2f7;border-radius:10px}
.scroll {overflow-x:auto}
table {width:100%;border-collapse:collapse;margin-top:20px}
th,td {padding:12px;text-align:left;border-bottom:1px solid #ddd}
td {overflow-wrap:anywhere}
th {background:#eef2f7}
.MATCH {color:#166534}
.EXCEPTIONS {background:#fff4dd}
.FAILED,.UNREADABLE {background:#fff0f0;color:#991b1b}
.note {color:#586174}
</style>
</head>
<body>
<h1>核对历史</h1>
""" + (
        f'<p class="summary">运行记录：{len(entries)} ｜ {summary}</p>'
        '<p class="note">按清单开始时间倒序排列；时间未知的记录放在末尾。'
        '缺失清单也可能表示运行尚未结束，请稍后重新生成本页。'
        '此页是历史索引，不代表已执行新的核对，也不验证文件是否被修改。</p>'
        '<div class="scroll"><table><thead><tr>'
        '<th>开始时间（UTC）</th><th>运行目录</th><th>结果</th>'
        '<th>退出码</th><th>报告</th><th>失败原因</th>'
        f'</tr></thead><tbody>{body}</tbody></table></div>'
        '</body></html>'
    )


def write_history(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    document = build_history(root)
    output = root / "index.html"

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".tmp",
        dir=root, delete=False,
    ) as file:
        staging = Path(file.name)
        try:
            file.write(document)
        except BaseException:
            file.close()
            staging.unlink(missing_ok=True)
            raise

    try:
        staging.replace(output)
    finally:
        staging.unlink(missing_ok=True)
    return output


def main():
    parser = argparse.ArgumentParser(description="Build run history page.")
    parser.add_argument(
        "--output-dir", type=Path, default=BASE / "outputs"
    )
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    try:
        output = write_history(args.output_dir)
    except (OSError, ValueError) as error:
        print(f"History generation failed: {error}")
        return 2

    print(f"History: {output}", flush=True)
    if args.open:
        try:
            if not webbrowser.open(output.as_uri()):
                print("Open the HTML file manually.")
        except Exception as error:
            print(f"Browser unavailable: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
