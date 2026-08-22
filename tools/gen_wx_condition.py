#!/usr/bin/env python3
"""Emit a WFF <Condition> block mapping a weather condition source to wx_* icons.

Usage: gen_wx_condition.py <cond_source> <isday_source> <x> <y> <size> <name_suffix>
Prints the XML block on stdout (indented for Scene level).
"""
import sys

BUCKETS = [
    ("clearD", "({c} == 1 || {c} == 8) && {d}", "wx_clear"),
    ("clearN", "({c} == 1 || {c} == 8) && !{d}", "wx_night"),
    ("partlyD", "({c} == 14 || {c} == 15) && {d}", "wx_partly"),
    ("partlyN", "({c} == 14 || {c} == 15) && !{d}", "wx_night_cloud"),
    ("rain", "{c} == 4 || {c} == 6 || {c} == 12", "wx_rain"),
    ("snow", "{c} == 5 || {c} == 7 || {c} == 10 || {c} == 11", "wx_snow"),
    ("thunder", "{c} == 9", "wx_thunder"),
]


def block(cond_src, day_src, x, y, size, suffix, indent=8):
    pad = " " * indent
    exprs, compares = [], []
    img = (f'{pad}        <PartImage x="{x}" y="{y}" width="{size}" height="{size}">\n'
           f'{pad}            <Image resource="@drawable/%s" />\n'
           f'{pad}        </PartImage>')
    for name, tmpl, icon in BUCKETS:
        ename = f"{name}{suffix}"
        expr = tmpl.format(c=f"[{cond_src}]", d=f"[{day_src}]")
        exprs.append(f'{pad}    <Expression name="{ename}"><![CDATA[{expr}]]></Expression>')
        compares.append(f'{pad}    <Compare expression="{ename}">\n' + (img % icon).replace(pad + "        ", pad + "        ") + f'\n{pad}    </Compare>')
    body = (f'{pad}<Condition>\n'
            f'{pad}    <Expressions>\n' + "\n".join(exprs) + f'\n{pad}    </Expressions>\n'
            + "\n".join(compares) + "\n"
            f'{pad}    <Default>\n' + (img % "wx_cloudy") + f'\n{pad}    </Default>\n'
            f'{pad}</Condition>')
    return body


if __name__ == "__main__":
    cond_src, day_src, x, y, size, suffix = sys.argv[1:7]
    print(block(cond_src, day_src, int(x), int(y), int(size), suffix))
