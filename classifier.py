"""v1 の前提: Quine と Quine-like を分ける分類器。

第5ラウンドの裁定:
- ChatGPT: カテゴリ名「Environment-Dependent Self-Reproduction」、v0 と別ランキング
- Qwen: 判定条件 source(P) ∈ Closure(P.internal_state)
        バイト列・定数プールから元のソース表記（コメント/空白/引用形式）は復元できない
        したがって inspect.getsource / sys._getframe / open(__file__) は外部依存

実装: 静的な使用者チェックで「自己完結型」か「環境依存型」かを classify する。
"""

from __future__ import annotations

import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "classifier_results.json"

# 環境からソースを取得する API（Quine-like 判定）
ENV_SOURCE_APIS = (
    "inspect.getsource",
    "_getframe",
    "co_filename",
    "linecache",
    "open(__file__",
    "__file__",
    "sys.argv",
    "input(",
)


def classify(code: str) -> dict:
    hits = [api for api in ENV_SOURCE_APIS if api in code]
    if hits:
        return {
            "category": "Environment-Dependent Self-Reproduction (Quine-like)",
            "self_contained": False,
            "reason": "source(P) の構成に実行環境 E を利用: " + ", ".join(hits),
            "same_ranking_as_v0": False,
        }
    return {
        "category": "Self-contained Quine",
        "self_contained": True,
        "reason": "外部のソース取得 API を使用せず、内部データのみで自己を構成",
        "same_ranking_as_v0": True,
    }


def samples() -> list[tuple[str, str]]:
    return [
        ("v0-best", "s='s=%r;print(s%%s)';print(s%s)"),
        ("exec-walrus", "exec(s:='print(\"exec(s:=%r)\"%s)')"),
        ("frame-hack-inspect", "import inspect;print(inspect.getsource())"),
        ("frame-hack-getframe", "import sys;print(open(sys._getframe().f_code.co_filename).read())"),
        ("file-read", "print(open(__file__).read())"),
    ]


def main() -> None:
    rows = []
    for name, code in samples():
        r = classify(code)
        r.update({"id": name, "bytes": len(code.encode("utf-8"))})
        rows.append(r)
    report = {
        "rule": "source(P) in Closure(P.internal_state) -> Quine / otherwise -> Quine-like",
        "note": "Frame Hack は v0 の 31B と同一ランキングに載せない（ChatGPT 裁定）",
        "rows": rows,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in rows:
        print(f"{r['id']:22s} {r['bytes']:3d}B {r['category']}")
        print(f"  {r['reason']}")
    b = json.dumps({"type": "log", "source": "classifier", "text": "Quine/Quine-like 分類器を実装・検証しました"}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:8765/api/event", data=b, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=4)
    except Exception:
        pass


if __name__ == "__main__":
    main()
