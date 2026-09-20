#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 App 的真实行情里截一段，画成与 App 图表同款的 K 线 SVG。

用法：
    python3 tools/gen_chart.py --preset desktop --out chart.svg
    python3 tools/gen_chart.py --preset mobile  --out chart-mobile.svg
    python3 tools/gen_chart.py --preset mobile --code 518880 --bars 40 --out /tmp/probe.svg

为什么要脚本而不是手画一张插画：落地页上那张图不是装饰，是 App 里真实会看到的
那一张 —— 同一套配色（ui/Palette.kt）、同一批元素（蜡烛 / MA5 / MA20 / 右轴
价签 / 持仓区间水洗）。数据也是真的，从 App 的 assets/data.json 现取。

为什么出两个尺寸：SVG 等比缩放到 390px 宽时，13px 的轴标签会变成 4px 的蚂蚁。
所以窄屏不缩，换一张**元素更少、字更大**的 mobile 版，由 <picture> 切换。
"""

import argparse
import json
import math
import os
import sys

# 两套尺寸。窄屏不是把大图缩小，是重新排版：根数减半、字号放大。
PRESETS = {
    "desktop": dict(w=1200, h=460, pad_l=10, pad_r=78, pad_t=24, pad_b=30,
                    bars=72, font=13, wash="0.42,0.88"),
    "mobile":  dict(w=560,  h=320, pad_l=6,  pad_r=62, pad_t=18, pad_b=22,
                    bars=34, font=16, wash="0.34,0.86"),
}

# ── 配色：逐条对齐 App 的 ui/Palette.kt ──────────────────────────────────
C_UP = "#2ED3A0"
C_DOWN = "#FF6B81"
C_MA_FAST = "#E3B25C"      # Palette.maFast（金色）
C_MA_SLOW = "#6EA8FE"      # Palette.maSlow（蓝色）
C_AXIS_TEXT = "#5F6B81"    # Palette.axisText
C_TAG_BG = "#2B3444"       # Palette.tagBg（右轴现价标签底）
C_TAG_TEXT = "#E9EEF6"
C_GRID = "rgba(255,255,255,0.045)"   # Palette.grid = 白 4.3%
C_WASH = "rgba(46,211,160,0.09)"     # Palette.upWash = 9% 不透明度
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"

DEFAULT_DATA = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "trader-android", "app", "src", "main", "assets", "data.json"))


def load_series(path, code):
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    for s in doc["series"]:
        if s["code"] == code:
            return s
    have = ", ".join(s["code"] for s in doc["series"])
    sys.exit("data.json 里没有 %s，只有：%s" % (code, have))


def sma(vals, n):
    """简单均线。**在整条序列上算完再切片** —— 否则窗口最左边几根算不出来，
    图开头会缺一截均线，跟 App 里看到的不一样。"""
    out, acc = [], 0.0
    for i, v in enumerate(vals):
        acc += v
        if i >= n:
            acc -= vals[i - n]
        out.append(acc / n if i >= n - 1 else None)
    return out


def nice_step(span, target=7):
    """把价格区间切成 ~target 段，步长取 1/2/2.5/5/10 × 10^k 里最接近的。"""
    raw = span / target
    if raw <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= mag * m:
            return mag * m
    return mag * 10


def fmt_price(v, step):
    if step >= 1:
        return "%.0f" % v
    if step >= 0.1:
        return "%.1f" % v
    if step >= 0.01:
        return "%.2f" % v
    return "%.3f" % v


def build(s, cfg):
    W, H = cfg["w"], cfg["h"]
    PL, PR, PT, PB = cfg["pad_l"], cfg["pad_r"], cfg["pad_t"], cfg["pad_b"]
    F = cfg["font"]
    bars = cfg["bars"]
    wash = tuple(float(x) for x in cfg["wash"].split(","))

    n_all = len(s["c"])
    i0 = max(0, n_all - bars)
    rng = range(i0, n_all)

    o = [s["o"][i] for i in rng]
    h = [s["h"][i] for i in rng]
    l = [s["l"][i] for i in rng]
    c = [s["c"][i] for i in rng]
    d = [s["d"][i] for i in rng]
    n = len(c)

    ma5 = sma(s["c"], 5)[i0:n_all]
    ma20 = sma(s["c"], 20)[i0:n_all]

    vals = h + l + [v for v in ma20 if v is not None]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.08 or 0.01
    lo, hi = lo - pad, hi + pad

    plot_w = W - PL - PR
    plot_h = H - PT - PB

    def X(i):
        return PL + (i + 0.5) * plot_w / n

    def Y(p):
        return PT + (hi - p) / (hi - lo) * plot_h

    body = max(2.0, plot_w / n * 0.62)

    # 右轴槽：价签和现价胶囊共用这一列，现价胶囊盖住谁就跳过谁
    axis_x = W - 6
    tag_x = W - PR + 2
    tag_w = PR - 8
    tag_h = round(F * 1.85)

    out = []
    a = out.append

    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
      'width="%d" height="%d" role="img" '
      'aria-label="%s 日线，%s 至 %s">'
      % (W, H, W, H, s["name"], d[0], d[-1]))

    # 网格：横线 + 右轴价签
    step = nice_step(hi - lo, 7)
    tag_y = Y(c[-1])
    g = math.ceil(lo / step) * step
    while g <= hi:
        y = Y(g)
        a('<line x1="%g" y1="%.1f" x2="%g" y2="%.1f" stroke="%s" stroke-width="1"/>'
          % (PL, y, W - PR, y, C_GRID))
        if abs(y - tag_y) > tag_h * 0.62:
            a('<text x="%d" y="%.1f" text-anchor="end" dominant-baseline="central" '
              'font-family="%s" font-size="%d" fill="%s">%s</text>'
              % (axis_x, y, MONO, F, C_AXIS_TEXT, fmt_price(g, step)))
        g += step

    # 持仓区间水洗（App 里盖住持仓那一段，9% 不透明度）
    w0, w1 = int(n * wash[0]), int(n * wash[1])
    a('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s"/>'
      % (X(w0) - body / 2, PT, X(w1) - X(w0) + body, plot_h, C_WASH))

    # 均线先画，压在蜡烛下面
    for series, color in ((ma20, C_MA_SLOW), (ma5, C_MA_FAST)):
        pts = ["%.1f,%.1f" % (X(i), Y(v)) for i, v in enumerate(series) if v is not None]
        if len(pts) > 1:
            a('<polyline points="%s" fill="none" stroke="%s" stroke-width="%.1f" '
              'stroke-linejoin="round" stroke-linecap="round"/>'
              % (" ".join(pts), color, F / 6.5))

    # 蜡烛
    for i in range(n):
        col = C_UP if c[i] >= o[i] else C_DOWN
        x = X(i)
        a('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f"/>'
          % (x, Y(h[i]), x, Y(l[i]), col, F / 8))
        top, bot = Y(max(o[i], c[i])), Y(min(o[i], c[i]))
        a('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
          % (x - body / 2, top, body, max(1.5, bot - top), col))

    # 现价胶囊（占满整条右轴槽，像 App 那样）
    label = fmt_price(c[-1], step)
    a('<rect x="%d" y="%.1f" width="%d" height="%d" rx="%d" fill="%s"/>'
      % (tag_x, tag_y - tag_h / 2, tag_w, tag_h, round(F / 2.6), C_TAG_BG))
    a('<text x="%.1f" y="%.1f" text-anchor="middle" dominant-baseline="central" '
      'font-family="%s" font-size="%d" font-weight="500" fill="%s">%s</text>'
      % (tag_x + tag_w / 2, tag_y, MONO, F, C_TAG_TEXT, label))

    a('</svg>')
    return "\n".join(out), d[0], d[-1], n


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--preset", choices=sorted(PRESETS), default="desktop")
    p.add_argument("--data", default=DEFAULT_DATA, help="App 的 assets/data.json")
    p.add_argument("--code", default="510300", help="品种代码")
    p.add_argument("--bars", type=int, help="覆盖 preset 的画多少根")
    p.add_argument("--out", default=None)
    args = p.parse_args()

    cfg = dict(PRESETS[args.preset])
    if args.bars:
        cfg["bars"] = args.bars
    out_path = args.out or ("chart.svg" if args.preset == "desktop" else "chart-mobile.svg")

    s = load_series(args.data, args.code)
    svg, d0, d1, n = build(s, cfg)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg + "\n")

    print("已写出 %-22s %s %s · %d 根 · %s → %s · %dx%d"
          % (out_path, s["code"], s["name"], n, d0, d1, cfg["w"], cfg["h"]))


if __name__ == "__main__":
    main()
