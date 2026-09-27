#!/usr/bin/env python3
"""Убирает из змейки Platane/snk полосу «съеденного» под сеткой и обрезает высоту.

Запуск: python3 scripts/snake-trim.py dist/*.svg
"""
import re
import sys

for path in sys.argv[1:]:
    svg = open(path).read()
    svg = re.sub(r'<rect class="u [^>]*/>', "", svg)
    m = re.search(r'viewBox="(-?[\d.]+) (-?[\d.]+) ([\d.]+) ([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg)
    if m:
        x, y, w, h, W, H = map(float, m.groups())
        cut = 32  # полоса и отступ до неё
        svg = svg.replace(m.group(0),
                          f'viewBox="{x:g} {y:g} {w:g} {h - cut:g}" width="{W:g}" height="{H - cut:g}"', 1)
    open(path, "w").write(svg)
