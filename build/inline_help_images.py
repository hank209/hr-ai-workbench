# -*- coding: utf-8 -*-
"""把 使用说明-专员版.html 里的截图内联为 base64 data URI，使文件完全自包含。

这样说明文件无论通过 file:// 双击打开、还是通过工作台 /help 路由访问、或者单独发给别人，
图片都不会丢失。
"""
import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "使用说明-专员版.html"

PAT = re.compile(r'src="(docs/ui_shots/([^"]+\.png))"')


def main():
    text = HTML.read_text(encoding="utf-8")
    cache = {}

    def repl(m):
        rel, name = m.group(1), m.group(2)
        if name not in cache:
            p = ROOT / rel
            if not p.exists():
                print("  跳过（文件不存在）:", rel)
                return m.group(0)
            b64 = base64.b64encode(p.read_bytes()).decode("ascii")
            cache[name] = "data:image/png;base64," + b64
            print("  内联 %-28s %6.0f KB" % (name, len(b64) / 1024))
        return 'src="%s"' % cache[name]

    new = PAT.sub(repl, text)
    HTML.write_text(new, encoding="utf-8")
    print("完成：%s  (%.0f KB)" % (HTML.name, HTML.stat().st_size / 1024))


if __name__ == "__main__":
    main()
