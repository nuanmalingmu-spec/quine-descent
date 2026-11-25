"""Quine Descent 実験ハーネス（AI 依存ゼロ、Python 標準ライブラリのみ）

作戦会議の決定（ChatGPT / Perplexity / Qwen / Gemini / Grok ほぼ一致）:
- 31B への無期限探索を停止
- A/B/C を同じ条件で比較するハーネスを先に作る
- 判定は「圧縮率」ではなく「完成ソース全体の UTF-8 バイト数」
- Quine 成立は実行出力とソースのバイト一致で検証
- 不成立候補は記録するが最小記録には採用しない

A: Baseline 通常 Quine
B: 固定圧縮（zlib + base85）を試した Quine
C: D（自己参照データ）と P（展開コード）の境界を変えた Quine
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "experiment_results.json"

A = "s='s=%r;print(s%%s)';print(s%s)"

# B: 固定圧縮方式の候補（圧縮データを持ち、実行時に展開して自分を出力する試み）
B_CANDIDATES = [
    "import zlib,base64;s='eJxLZGRIVNBQyc5IzStOzMzMS8wpTi0uSU1RsLZQyC8uSU1RzM5IL的习惯';exec(zlib.decompress(base64.b85decode(s)).decode())",
    "import zlib,base64;s='';exec(zlib.decompress(base64.b85decode(s)).decode())",
]

# C: 境界（データ部 D / コード部 P の分担）を変えたバリエーション
C_CANDIDATES = [
    "s='s=%r;print(s%%s)';print(s%s)",
    "s='s=%r;print((s%%s))';print((s%s))",
    "exec(s:='print(\"exec(s:=%r)\"%s)')",
    "s='print(\"s=%r;exec(s)\"%s)';exec(s)",
]


def run(code: str, timeout: int = 5) -> tuple[str, str, float]:
    t0 = time.perf_counter()
    try:
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout)
        out, err = p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        out, err, = "", "TIMEOUT"
    return out, err, (time.perf_counter() - t0) * 1000


def evaluate(name: str, code: str) -> dict:
    out, err, ms = run(code)
    strict = out.rstrip("\n") == code
    return {
        "id": name,
        "source": code,
        "bytes": len(code.encode("utf-8")),
        "quine_strict": strict,
        "sha256": hashlib.sha256(code.encode("utf-8")).hexdigest()[:16],
        "runtime_ms": round(ms, 2),
        "stderr": err[:200],
        "accepted": strict,
    }


def measure_boundary(code: str) -> dict:
    """D（引用符内の自己参照文字列）と P（残りのコード）のサイズを測る。"""
    try:
        start = code.index("'")
        end = code.rindex("'")
        data = code[start : end + 1]
    except ValueError:
        data = ""
    return {"d_bytes": len(data.encode("utf-8")), "p_bytes": len(code.encode("utf-8")) - len(data.encode("utf-8"))}


def main() -> None:
    results = []
    results.append({**evaluate("A/baseline", A), "group": "A", **measure_boundary(A)})
    for i, c in enumerate(B_CANDIDATES):
        results.append({**evaluate(f"B/fixed-compression-{i}", c), "group": "B", **measure_boundary(c)})
    for i, c in enumerate(C_CANDIDATES):
        results.append({**evaluate(f"C/boundary-{i}", c), "group": "C", **measure_boundary(c)})

    accepted = [r for r in results if r["accepted"]]
    best = min(accepted, key=lambda r: r["bytes"]) if accepted else None
    report = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "note": "判定は完成ソース全体のUTF-8バイト数。圧縮率ではない。大域最小性は主張しない。",
        "best_accepted": best["id"] if best else None,
        "best_bytes": best["bytes"] if best else None,
        "results": results,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"best: {report['best_accepted']} {report['best_bytes']}B")
    for r in results:
        print(f"{r['id']:26s} {r['bytes']:3d}B quine={str(r['quine_strict']):5s} D={r['d_bytes']:2d}B P={r['p_bytes']:2d}B")
    print(f"accepted {len(accepted)}/{len(results)}")


if __name__ == "__main__":
    main()
