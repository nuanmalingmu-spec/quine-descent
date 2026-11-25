"""Quine Descent - MVP (Python 標準ライブラリのみ)

自己複製プログラムに対して Quine 専用の構造変換を試し、
自己複製性を維持できた場合だけ次の世代として採用する。
SHA-256 は履歴の改ざん検出にのみ使い、最小性は主張しない。

v2: 不要な空白の削除を追加。各候補を is_quine() で検証し、
    不合格候補は弃却ログとして残す。
"""

from __future__ import annotations

import ast
import hashlib
import io
import subprocess
import sys
import tokenize


INITIAL = "s='s=%r;print((s%%s))';print((s%s))"

# 自己参照方式のカタログ（すべて is_quine で検証済み）
SCHEMES = {
    "percent-r": "s='s=%r;print(s%%s)';print(s%s)",          # 31B
    "exec-walrus": "exec(s:='print(\"exec(s:=%r)\"%s)')",      # 33B
    "exec-simple": "s='print(\"s=%r;exec(s)\"%s)';exec(s)",    # 35B
    "eval": "s=\"print('s='+repr(s)+';eval(s)')\";eval(s)",   # 42B
    "format": "s='s={!r};print(s.format(s))';print(s.format(s))",  # 48B
    "lambda": "print((lambda s:s%s)('print((lambda s:s%%s)(%r))'))",  # 51B
}

# 弃却ログ: (gen, 変換名, 候補, 理由)
REJECTS: list[tuple[int, str, str, str]] = []

# 方式切替ログ: (gen, 旧方式, 新方式, 旧B, 新B)
MUTATIONS: list[tuple[int, str, str, int, int]] = []


def run(code: str) -> str:
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=5,
    )
    return proc.stdout


def diagnose(code: str) -> str:
    """is_quine 不合格の理由を分類する"""
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg}"
    out = run(code).rstrip("\n")
    if out != code:
        return f"output mismatch ({len(out)}B != {len(code)}B)"
    return "valid quine"


def is_quine(code: str) -> bool:
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    out = run(code).rstrip("\n")
    return out == code


def strip_spaces_outside_strings(code: str) -> str:
    """文字列リテラル内の空白は保持し、コード部分の空白だけを削除する。

    Quine では文字列内の空白が自己参照テンプレートとして意味を持つため、
    外側だけを削除すると output mismatch になることがある（弃却ログに残る）。
    """
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError):
        return code
    parts = []
    for tok in toks:
        if tok.type in (tokenize.ENDMARKER, tokenize.NEWLINE, tokenize.NL):
            continue
        parts.append(tok.string)
    return "".join(parts)


def whitespace_candidates(code: str) -> list[tuple[str, str]]:
    """不要な空白の削除（Quine 対応）。"""
    cands: list[tuple[str, str]] = []
    # 1) 全空白を削除（Quine のテンプレート内の空白も同時に更新される）
    naive = code.replace(" ", "")
    if naive != code:
        cands.append(("whitespace/all", naive))
    # 2) 文字列外の空白だけを削除（テンプレートは保持）
    outside = strip_spaces_outside_strings(code)
    if outside != code and outside not in [c for _, c in cands]:
        cands.append(("whitespace/outside-strings", outside))
    return cands


def transforms(code: str, gen: int = 0) -> list[tuple[str, str]]:
    """Quine 構造を理解した専用変換（汎用 AST 最適化ではない）。"""
    named: list[tuple[str, str]] = []
    # 冗長な括弧: テンプレート内と実行部分の両方を対応させて消す
    named.append(("parens/both",
                  code.replace("print((s%%s))", "print(s%%s)").replace("print((s%s))", "print(s%s)")))
    named.append(("parens/template", code.replace("print((s%%s))", "print(s%%s)")))
    named.append(("parens/call", code.replace("print((s%s))", "print(s%s)")))
    # 不要な空白の削除（追加）
    named.extend(whitespace_candidates(code))

    unique: dict[str, str] = {}
    for name, cand in named:
        if cand == code:
            continue
        reason = diagnose(cand)
        if not reason.startswith("valid"):
            REJECTS.append((gen, name, cand, reason))
            continue
        unique.setdefault(cand, name)
    return [(name, cand) for cand, name in unique.items()]


def sha(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]


def pivot(current: str, gen: int) -> tuple[str, str] | None:
    """変換が止まったとき、自分で別の自己参照方式を探す（MODE MUTATION）。

    現在より短く、かつ is_quine が成立する方式があれば採用する。
    既定ではカタログ照合であり、大域最小性は主張しない。
    """
    size = len(current.encode())
    best_name, best_code = None, None
    for name, code in SCHEMES.items():
        if len(code.encode()) >= size:
            continue
        if not is_quine(code):
            REJECTS.append((gen, f"scheme/{name}", code, "output mismatch"))
            continue
        if best_code is None or len(code) < len(best_code):
            best_name, best_code = name, code
    if best_code is None:
        return None
    MUTATIONS.append((gen, "current", best_name, size, len(best_code.encode())))
    return best_name, best_code


def main() -> None:
    current = INITIAL
    history = []
    if not is_quine(current):
        print("初期 Quine が成立していません")
        return
    print(f"gen0  {len(current.encode()):3d}B  {sha(current)}  {current}")
    history.append(current)

    for gen in range(1, 12):
        best = None
        best_name = ""
        for name, cand in transforms(current, gen):
            if is_quine(cand) and len(cand.encode()) < len(current.encode()):
                if best is None or len(cand) < len(best):
                    best = cand
                    best_name = name
        if best is None:
            mutated = pivot(current, gen)
            if mutated:
                best_name, best = mutated
                print(f"[MODE MUTATION] 方式を切り替えました -> {best_name}")
            else:
                print(f"全方式を探索したが短縮候補なし → gen{gen-1} を採用（局所最小）")
                break
        current = best
        history.append(current)
        print(f"gen{gen}  {len(current.encode()):3d}B  {sha(current)}  [{best_name}]  {current}")

    print("\n--- history ---")
    for i, code in enumerate(history):
        print(f"gen{i} {len(code.encode()):3d}B sha256:{sha(code)}")

    print("\n--- mode mutations ---")
    if MUTATIONS:
        for gen, old, new, old_b, new_b in MUTATIONS:
            print(f"gen{gen} {old} -> {new} ({old_b}B -> {new_b}B, -{old_b-new_b}B)")
    else:
        print("(none)")

    print("\n--- rejected candidates ---")
    if REJECTS:
        for gen, name, cand, reason in REJECTS:
            print(f"gen{gen} {name}: {reason} :: {cand[:70]}")
    else:
        print("(none)")

    print(f"\n初期 {len(INITIAL.encode())}B -> 最終 {len(current.encode())}B "
          f"({len(INITIAL.encode()) - len(current.encode())}B 削減)")
    print("※ これは探索範囲内の局所最小であり、大域的最小性は主張しません。")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        # verbose な方式から始めて、自律的な MODE MUTATION を実証する
        INITIAL = SCHEMES["lambda"]
    main()
