"""Joint Quine Optimizer v1 - D/P 合計長を目的関数にしたテンプレート探索。

第3ラウンドの指摘を反映:
- 「境界」は測定軸。改善の是非は ΔL = (|P'|-|P|) - (|D|-|D'|) < 0 で判定する
- 探索対象: 変数名 / 引用符 / print 形式 / 区切り / exec 方式
- 31B (D=18, P=13) をベースラインにする
- 大域最小性は主張しない。31B未満が出なければ「この探索空間では改善なし」と記録する
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "template_results.json"
BASE_D, BASE_P = 18, 13


def run(code: str) -> str:
    try:
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=5)
        return p.stdout.rstrip("\n")
    except Exception:
        return ""


def split_dp(code: str) -> tuple[str, str]:
    try:
        a, b = code.index("'"), code.rindex("'")
        d = code[a : b + 1]
    except ValueError:
        try:
            a, b = code.index('"'), code.rindex('"')
            d = code[a : b + 1]
        except ValueError:
            d = ""
    return d, code.replace(d, "", 1)


def templates() -> list[tuple[str, str]]:
    out = []
    for var in ("s", "a", "_", "q", "z"):
        for sep in (";", ";"):
            for parens in (False, True):
                inner = f"print(({var}%%{var}))" if parens else f"print({var}%%{var})"
                call = f"print(({var}%{var}))" if parens else f"print({var}%{var})"
                tmpl = f"{var}=%r{sep}{inner}"
                out.append((f"repr/{var}/{'paren' if parens else 'plain'}", f"{var}='{tmpl}'{sep}{call}"))
                # 二重引用符版（Quine になるものだけ残る）
                out.append((f"repr/{var}/dq", f'{var}="{tmpl}"{sep}{call}'))
    out.append(("exec/walrus", "exec(s:='print(\"exec(s:=%r)\"%s)')"))
    out.append(("exec/simple", "s='print(\"s=%r;exec(s)\"%s)';exec(s)"))
    out.append(("eval", "s=\"print('s='+repr(s)+';eval(s)')\";eval(s)"))
    out.append(("format", "s='s={!r};print(s.format(s))';print(s.format(s))"))
    out.append(("lambda", "print((lambda s:s%s)('print((lambda s:s%%s)(%r))'))"))
    return out


def evaluate() -> dict:
    rows = []
    for name, code in templates():
        ok = run(code) == code
        d, p = split_dp(code)
        dlen, plen = len(d.encode()), len(p.encode())
        total = len(code.encode())
        delta_l = (plen - BASE_P) - (BASE_D - dlen)
        rows.append({
            "id": name, "bytes": total, "d_bytes": dlen, "p_bytes": plen,
            "quine": ok, "delta_l": delta_l, "improved": ok and delta_l < 0,
            "sha256": hashlib.sha256(code.encode()).hexdigest()[:12],
            "source": code,
        })
    accepted = [r for r in rows if r["quine"]]
    best = min(accepted, key=lambda r: r["bytes"]) if accepted else None
    improved = [r for r in rows if r["improved"]]
    return {
        "objective": "min len(bytes(P)) + len(bytes(D))  s.t. quine",
        "baseline": {"bytes": 31, "d": BASE_D, "p": BASE_P},
        "delta_formula": "(|P'|-|P|) - (|D|-|D'|) < 0",
        "best": best["id"] if best else None,
        "best_bytes": best["bytes"] if best else None,
        "improved_count": len(improved),
        "accepted": len(accepted), "total": len(rows),
        "note": "31B未満・ΔL<0 の候補がなければ、この探索空間では改善なしと記録する。大域最小性は主張しない。",
        "rows": rows,
    }


def notify(text: str) -> None:
    b = json.dumps({"type": "log", "source": "template-search", "text": text}, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request("http://127.0.0.1:8765/api/event", data=b, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(r, timeout=4)
    except Exception:
        pass


def main() -> None:
    rep = evaluate()
    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"best={rep['best']} {rep['best_bytes']}B improved={rep['improved_count']} accepted={rep['accepted']}/{rep['total']}")
    for r in rep["rows"]:
        if r["quine"]:
            print(f"{r['id']:22s} {r['bytes']:3d}B D={r['d_bytes']:2d}B P={r['p_bytes']:2d}B dL={r['delta_l']:+d}")
    notify(f"テンプレート探索完了: best={rep['best']} {rep['best_bytes']}B improved={rep['improved_count']}")


if __name__ == "__main__":
    main()
