# Quine Descent

> An experimental system that searches for smaller self-reproducing programs while validating their quine property across generations.
>
> 世代ごとに自己複製性を検証しながら、より小さな自己複製プログラムを探索する実験システム。

**31 bytes. Break it.**

これは「最短の Quine を披露する」リポジトリではありません。**どこで行き詰まり、どうやって表現を変えて再び短くしたか**を、再現可能な形で記録する実験室です。

## Quick start

```sh
# 通常の降下（括弧の削除 → Quine 性を検証）
python quine_descent.py

# 別の自己参照方式から始めて、自動切替（MODE MUTATION）を見る
python quine_descent.py --demo

# A/B/C の比較実験（標準出力と JSON に結果を出す）
python experiment.py
```

必要なものは Python 3 だけです。外部ライブラリ・API キー・ネットワーク接続は不要です（実験はローカルで完結します）。

## 今の記録

| 方式 | サイズ | Quine |
|---|---:|:---:|
| percent-r（現行） | **31 B** | ✅ |
| exec + walrus | 33 B | ✅ |
| exec + simple | 35 B | ✅ |
| eval | 42 B | ✅ |
| str.format | 48 B | ✅ |
| lambda | 51 B | ✅ |
| zlib + base85 固定圧縮 | 75〜137 B | ❌ |

すべて `python quine_descent.py --demo` で再現できます。各世代は実行出力とソースのバイト一致で検証され、SHA-256 で履歴を残します。

## なぜ「新規性10」と言わないのか

圧縮 Quine には先行事例があります:

- `rsc/quine` の qzip（DEFLATE による自己含有アーカイブ）
- `honno/gzip-quine`（展開すると自身の複製になる GZIP）
- `mame/quine-clique`（51言語が互いに出力し合う）

先行事例を認識しており、新規性は未検証です。したがって「世界初」や「新規性10」は主張しません。

差別化するところはひとつだけ:

> **自己参照データ D と、それを復元するコード P の境界を、明示的で検証可能な探索変数として扱うこと。**

固定された圧縮 Quine を見せるのではなく、`|D| + |P|` の合計バイト数を、Quine 性を壊さずに探索した経路そのものを成果にします。

## 実験 A/B/C

`experiment.py` は同じ条件で3方式を比較します。

| 実験 | 内容 | 検証すること |
|---|---|---|
| A | 現在の 31 B Quine | 比較基準の再現性 |
| B | 固定圧縮（zlib + base85） | 圧縮器込みでも短くなるか |
| C | D / P の境界を変えた Quine | 全体サイズの最小値を更新できるか |

判定は **圧縮率ではなく、完成ソース全体の UTF-8 バイト数** です。Quine 成立は実行時の標準出力とソースのバイト一致で確認します。

`experiment_results.json` に実測値があります。例:

```text
A/baseline       31B quine=True  D=18B P=13B
C/boundary-0     31B quine=True  D=18B P=13B
C/boundary-2     33B quine=True  D=24B P= 9B   <- P が 13B -> 9B に激変
B/fixed-compression-0 137B quine=False (弃却)
```

固定圧縮はすべて不成立でした。圧縮器のオーバーヘッドが削減量を上回るためです。

境界を動かすと P は 13 B → 9 B に痩せますが、D が 18 B → 24 B に増えるため、合計は 31 B → 33 B に悪化します。したがって「境界が最適化に有効な探索変数だ」とは言いません。言えるのは、境界を明示的な測定軸にしたことで、**P だけを短くしても全体は短くならない**という負の結果を再現可能に示したことです。31 B を破る候補はまだありません（`boundary_results.json`）。

## 「止まった」ときの挙動

`quine_descent.py` は変換候補が尽きると、自分でほかの自己参照方式を探索します（`[MODE MUTATION]`）。どこにも短い方式がなければ、はじめて「局所最小」と宣言します。

```text
gen0   51B  print((lambda s:s%s)('print((lambda s:s%%s)(%r))'))
[MODE MUTATION] 方式を切り替えました -> percent-r
gen1   31B  s='s=%r;print(s%%s)';print(s%s)
gen1 current -> percent-r (51B -> 31B, -20B)
```

これは**探索範囲内の局所最小**であり、大域最小性は証明していません。SHA-256 は履歴の改ざん検出にだけ使っています。

## デモの見せ方（GIF を作る人へ）

1. **停滞（0〜1.5秒）**: `31B [Plateau Reached]`。収束ループが空転する。
2. **境界シフト（1.5〜2.0秒）**: `Boundary Shift: D(18B) + P(13B) -> D(24B) + P(9B)`。コード全体がパチッと別構文へ変わる。
3. **再降下（2.0〜4.0秒）**: 新しい方式でサイズが下がり始める。`Output Hash: MATCH` は緑を維持。

> When code compression plateaus, you don't shrink the code further—you shift the boundary between data and decoder.

## v1 の前提：Quine と Quine-like を分ける

第5ラウンドの円卓裁定:

- Frame Hack（`sys._getframe()` / `inspect.getsource()` / `open(__file__)` で実行環境からソースを取得する方式）は**狭義の Quine ではない**
- 別カテゴリ **Environment-Dependent Self-Reproduction (Quine-like)** として扱う
- v0 の 31 B とは**同じバイト数ランキングに載せない**（前提が違うため）

Qwen の定式化:

- Quine: `source(P) ∈ Closure(P.internal_state)` — 内部情報のみで自己を構成
- Quine-like: 上記は満たすが、`source(P)` の構成に実行環境 E を利用
- バイト列にはコメント・空白・元の引用形式が残らないため、Frame Hack は条件を満たさない

`classifier.py` に静的な分類器を実装済み（`classifier_results.json` に検証結果）。

ChatGPT の一文:

> Quine Descent v1 explores environment-dependent self-reproduction, a separate category from self-contained quines, and does not compare its byte counts directly with v0.

### v1 の実測（`env_reproduction.py`）

ファイルとして実行し、出力とソースの一致を確認（`env_results.json`）:

| 候補 | バイト | 自己再生 | 分类 |
|---|---:|:---:|---|
| `print(open(__file__).read())` | **28 B** | ✅ | Environment-Dependent |
| `import inspect;print(inspect.getsource())` | 41 B | ❌ | Environment-Dependent |
| `inspect.getsource(sys._getframe())` | 60 B | ✅ | Environment-Dependent |
| `open(sys._getframe().f_code.co_filename).read()` | 65 B | ✅ | Environment-Dependent |

**28 B は 31 B を破ったことにはなりません。** 実行環境（`__file__` / ファイルシステム）からソースを取得しているため、v0 の自己完結型 Quine とは前提が異なります（Perplexity によれば既存では *Cheating Quine* と呼ばれる）。

記録は完全に分離します:

| カテゴリ | 最良観測値 |
|---|---:|
| v0 Self-contained Quine | 31 B |
| v1 Environment-Dependent Self-Reproduction | 28 B |

ChatGPT の一文:

> Quine Descent v1 achieved a 28-byte environment-dependent self-reproduction using file-read, demonstrating a shorter result under different execution assumptions without superseding the 31-byte self-contained quine from v0.

## Conclusion（v0 の締め）

Quine Descent v0 explored 45 structural templates, of which 25 produced valid quines.
The shortest verified result was 31 bytes, with an 18-byte data component and a 13-byte reconstruction component.
No candidate improved upon this result within the tested search space.

This establishes 31 bytes as the best observed result of this experiment, **not a theoretical lower bound** for Python quines.
The v0 experiment is complete. Further exploration of alternative self-reference principles is outside its scope.

## Final statement（第7ラウンド議長裁定）

> Quine Descent is complete: it documents a reproducible 31-byte best result within its tested self-contained search space and a separate 28-byte environment-dependent self-reproduction result, without claiming a theoretical lower bound or a universal minimum.

日本語: 45テンプレートを探索し25件が有効なQuineでした。最良は31バイト（D=18B, P=13B）。この探索空間では改善条件 `ΔL < 0` を満たす候補は0件でした。**31Bは実測記録であり、Python Quineの理論的下限ではありません。** v0はここで完了とします。

完了の意味は「これ以上改善できない」ではなく、「定義した探索空間で反証可能な負の結果を残し、Quine と Quine-like を分離して公開する水準に達した」ことです（Perplexity / ChatGPT）。将来の新原理は別プロジェクトとして扱います。

**31B。破れなかった壁を、残す。**（Grok）

次に進むなら v1 として、自己参照の方式そのものを変える（例: データ部を持たず実行コンテキストから自己を再構築する Frame Hack 的な方式）。ただしこれは Quine の定義（外部入力なし）との兼ね合いを先に議論する必要があります。

## ライセンス

MIT. 詳細は [LICENSE](LICENSE)。
