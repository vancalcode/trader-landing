#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 App 仓库的 git log 生成 changelog.js —— 落地页的「更新日志」直接读它。

用法：
    python3 tools/gen_changelog.py --out changelog.js
    python3 tools/gen_changelog.py --repo ../../trader-android --limit 30 --print

为什么从 commit 生成而不是手写：手写的更新日志必然和代码脱节 ——
改完东西忘了补，过两个月页面上还停在上个版本。从 git log 出来，
只要提交信息写得像人话，页面就是真的。

提交信息怎么被读：
  · 「范围：具体改动」→ 范围拆成小标签，具体改动当正文
  · 「repo: 具体改动」→ 前缀直接丢掉（那是仓库名，不是功能）
  · 其余原样展示

SKIP 里是纯内部提交（README / 图标微调 / 测试基建），对下载页读者没有意义。
只排除这一类，不做任何改写 —— 页面上看到的就是提交原文。
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

DEFAULT_REPO = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "trader-android"))

# 纯内部提交，不进更新日志
SKIP = re.compile(r"^(README|Icons|docs|chore|build|ci)\b|冒烟测试")

# 「范围：改动」里的范围，太长就不是范围而是一句话了
TAG = re.compile(r"^([^：:]{2,10})：\s*(.+)$")
# 「trader-android: xxx」这种仓库名前缀
REPO_PREFIX = re.compile(r"^[a-z0-9][a-z0-9-]*:\s+")


def read_log(repo, limit):
    fmt = "%ad\x1f%s"
    cmd = ["git", "-C", repo, "log", "--no-merges",
           "--date=short", "--pretty=format:" + fmt]
    if limit:
        cmd += ["-n", str(limit)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        sys.exit("找不到 git")
    except subprocess.CalledProcessError as e:
        sys.exit("读 %s 的 git log 失败：%s" % (repo, e.stderr.strip()))

    rows = []
    for line in out.splitlines():
        if "\x1f" not in line:
            continue
        date, subject = line.split("\x1f", 1)
        subject = subject.strip()
        if not subject or SKIP.search(subject):
            continue
        subject = REPO_PREFIX.sub("", subject)
        m = TAG.match(subject)
        if m:
            rows.append((date, m.group(1).strip(), m.group(2).strip()))
        else:
            rows.append((date, "", subject))
    return rows


def group(rows):
    """按日期分组，保持 git log 的顺序（新 → 旧）。"""
    out = []
    for date, tag, text in rows:
        if not out or out[-1]["date"] != date:
            out.append({"date": date, "items": []})
        out[-1]["items"].append({"tag": tag, "text": text})
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=DEFAULT_REPO, help="App 的 git 仓库")
    p.add_argument("--limit", type=int, default=0, help="最多读多少条（0 = 全部）")
    p.add_argument("--out", default="changelog.js")
    p.add_argument("--print", action="store_true", help="只打印，不写文件")
    args = p.parse_args()

    rows = read_log(args.repo, args.limit)
    days = group(rows)

    payload = {
        "source": os.path.basename(os.path.normpath(args.repo)),
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "entries": days,
    }

    if args.print:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("// 由 tools/gen_changelog.py 生成，请勿手改。\n")
        f.write("// 源：%s 的 git log。重新生成：python3 tools/gen_changelog.py\n"
                % payload["source"])
        f.write("window.CHANGELOG = ")
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write(";\n")

    n = sum(len(d["items"]) for d in days)
    print("已写出 %s" % args.out)
    print("  %d 条更新，跨 %d 天（%s → %s）"
          % (n, len(days), days[-1]["date"] if days else "-",
             days[0]["date"] if days else "-"))


if __name__ == "__main__":
    main()
