"""収束の軌跡を SVG 1枚に出力する（GIF の代わりに README へ貼れる）。

    python demo.py > demo.svg
"""

from __future__ import annotations

import hashlib

STEPS = [
    ("gen0", 51, "print((lambda s:s%s)('print((lambda s:s%%s)(%r))'))"),
    ("MODE MUTATION", 31, "s='s=%r;print(s%%s)';print(s%s)"),
    ("gen1", 31, "s='s=%r;print(s%%s)';print(s%s)"),
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    h = 120 + len(STEPS) * 80
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{h}" viewBox="0 0 900 {h}">',
        '<rect width="900" height="100%" fill="#0e1116"/>',
        '<text x="30" y="50" fill="#dfe7ef" font-family="monospace" font-size="24">Quine Descent</text>',
        '<text x="30" y="78" fill="#8b98a8" font-family="monospace" font-size="13">31 bytes. Break it.</text>',
    ]
    for i, (label, size, code) in enumerate(STEPS):
        y = 120 + i * 80
        color = "#ff9f43" if "MUTATION" in label else "#7ee787"
        out.append(f'<text x="30" y="{y}" fill="{color}" font-family="monospace" font-size="14">{esc(label)} - {size}B - sha256:{hashlib.sha256(code.encode()).hexdigest()[:12]}</text>')
        out.append(f'<text x="30" y="{y+22}" fill="#79c0ff" font-family="monospace" font-size="13">{esc(code[:95])}</text>')
    out.append("</svg>")
    print("\n".join(out))


if __name__ == "__main__":
    main()
