"""Joint Quine Optimizer v0 - D/P 境界を探索変数として扱う実験。

Quine を「データ部 D（自己参照文字列）」と「復元コード P」に分解し、
境界（D と P の分担）を変えた候補を生成して、完成ソース全体の
UTF-8 バイト数と Quine 性を測定する。

判定は圧縮率ではなく |D| + |P| の合計。大域最小性は主張しない。
"""

from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.request
import zlib

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "boundary_results.json"


def run(code: str) -> str:
    try:
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=5)
        return p.stdout.rstrip("\n")
    except Exception:
        return ""


def is_quine(code: str) -> bool:
    return run(code) == code


def split_dp(code: str) -> tuple[str, str]:
    """D = 最初の引用符から最後の引用符まで。P = 残り。"""
    try:
        a = code.index("'")
        b = code.rindex("'")
        d = code[a : b + 1]
    except ValueError:
        d = ""
    return d, code.replace(d, "", 1)


def candidates() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    # %r ファミリ：変数名と括弧の有無を変える（境界自体は同じでも D/P 比が変わる）
    for var in ("s", "a", "_"):
        for parens in (False, True):
            inner = f"print(({var}%%{var}))" if parens else f"print({var}%%{var})"
            call = f"print(({var}%{var}))" if parens else f"print({var}%{var})"
            tmpl = f"{var}=%r;{inner}"
            code = f"{var}='{tmpl}';{call}"
            out.append((f"repr/{var}/{'paren' if parens else 'plain'}", code))
    # exec + walrus：D が大きく P が小さい境界
    out.append(("exec/walrus", "exec(s:='print(\"exec(s:=%r)\"%s)')"))
    out.append(("exec/simple", "s='print(\"s=%r;exec(s)\"%s)';exec(s)"))
    # データ部を zlib+base85 で圧縮し、P に展開器を入れる試み（境界を意図的に動かす）
    tmpl = "s=%r;print(s%%s)"
    z = base64.b85encode(zlib.compress(tmpl.encode(), 9)).decode()
    out.append(("data/zlib-b85", f"import zlib,base64;s='{z}';print((s%s)%eval(compile('s=%r;print(s%%s)','','exec')))"))
    return out


def evaluate() -> dict:
    rows = []
    for name, code in candidates():
        ok = is_quine(code)
        d, p = split_dp(code)
        rows.append({
            "id": name,
            "bytes": len(code.encode("utf-8")),
            "d_bytes": len(d.encode("utf-8")),
            "p_bytes": len(p.encode("utf-8")),
            "quine": ok,
            "sha256": hashlib.sha256(code.encode("utf-8")).hexdigest()[:12],
            "source": code,
        })
    accepted = [r for r in rows if r["quine"]]
    best = min(accepted, key=lambda r: r["bytes"]) if accepted else None
    return {
        "note": "D=自己参照文字列, P=残りのコード。判定は |D|+|P| の合計バイト。大域最小性は主張しない。",
        "best": best["id"] if best else None,
        "best_bytes": best["bytes"] if best else None,
        "accepted": len(accepted),
        "total": len(rows),
        "rows": rows,
    }


def notify(text: str) -> None:
    b = json.dumps({"type": "log", "source": "boundary-search", "text": text}, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request("http://127.0.0.1:8765/api/event", data=b, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(r, timeout=4)
    except Exception:
        pass


def main() -> None:
    rep = evaluate()
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"best={rep['best']} {rep['best_bytes']}B accepted={rep['accepted']}/{rep['total']}")
    for r in rep["rows"]:
        print(f"{r['id']:24s} {r['bytes']:3d}B D={r['d_bytes']:2d}B P={r['p_bytes']:2d}B quine={r['quine']}")
    notify(f"境界探索完了: best={rep['best']} {rep['best_bytes']}B accepted={rep['accepted']}/{rep['total']}")


if __name__ == "__main__":
    main()
