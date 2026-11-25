"""v1 プロトタイプ: Environment-Dependent Self-Reproduction.

v0（自己完結型 Quine）とは別カテゴリ。ソースを実行環境から取得するため、
31B とは比較しない。ファイルとして実行して is_self_reproducing() を検証する。
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "env_results.json"

sys.path.insert(0, str(ROOT))
from classifier import classify  # noqa: E402

CANDIDATES = {
    "file-read": "print(open(__file__).read())",
    "inspect": "import inspect;print(inspect.getsource())",
    "inspect-frame": "import inspect,sys;print(inspect.getsource(sys._getframe()))",
    "frame-file": "import sys;print(open(sys._getframe().f_code.co_filename).read())",
}


def self_reproducing(code: str) -> bool:
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d, "candidate.py")
        p.write_text(code, encoding="utf-8")
        try:
            r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True, timeout=5, cwd=d)
        except Exception:
            return False
        return r.stdout.rstrip("\n") == p.read_text(encoding="utf-8").rstrip("\n")


def main() -> None:
    rows = []
    for name, code in CANDIDATES.items():
        cls = classify(code)
        rows.append({
            "id": name,
            "bytes": len(code.encode("utf-8")),
            "self_reproducing": self_reproducing(code),
            "category": cls["category"],
            "self_contained": cls["self_contained"],
            "reason": cls["reason"],
            "source": code,
        })
    rep = {
        "note": "環境依存型は v0 の 31B と別カテゴリ。同じランキングでは比較しない。",
        "rows": rows,
    }
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in rows:
        print(f"{r['id']:16s} {r['bytes']:3d}B self_reproducing={r['self_reproducing']} {r['category']}")
    b = json.dumps({"type": "log", "source": "env-reproduction", "text": "v1 プロトタイプ: 環境依存型自己再生を4候補検証"}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:8765/api/event", data=b, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=4)
    except Exception:
        pass


if __name__ == "__main__":
    main()
