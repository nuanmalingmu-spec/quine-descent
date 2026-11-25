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

固定圧縮はすべて不成立でした。圧縮器のオーバーヘッドが削減量を上回るためです。一方、境界を動かすと P が劇的に痩せることが分かりました。31 B を破る短縮はまだ出ていません。

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

## ライセンス

MIT. 詳細は [LICENSE](LICENSE)。
