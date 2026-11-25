# 公開手順（承認待ち）

このリポジトリは**まだ GitHub に公開していません**。公開はユーザーの承認が必要な重大操作です。

## 現在の状態

- `python quine_descent.py` / `--demo` / `experiment.py` / `demo.py` すべてローカルで動作確認済み
- README / LICENSE / 実験結果 / SVG デモを用意済み
- `gh` CLI はこの環境に未インストール（公開には CLI または認証情報が必要）

## 公開するときの手順

```sh
cd quine-descent
git init
git add README.md LICENSE quine_descent.py experiment.py demo.py demo.svg results/experiment_results.json
git commit -m "Initial release: Quine Descent"
gh repo create quine-descent --public --source=. --push
```

または Web でリポジトリを作ってから:

```sh
git remote add origin https://github.com/<user>/quine-descent.git
git push -u origin main
```

## 公開前に確認すること（Notion ルール）

- [ ] 個人情報・API キーが含まれていないか
- [ ] ライセンス（MIT）と著作権表記が正しいか
- [ ] 「世界初」「新規性10」と書いていないか（README は 4/10 と正直に記載）
- [ ] 実測値捏造がないか（`results/experiment_results.json` と README が一致）
- [ ] 公開後、利用者の反応を測る導線があるか（Issue / Star / README の次の一手）
