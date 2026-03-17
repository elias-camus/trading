# Bot Template

このディレクトリを丸ごとコピーして bot 名を変えるだけで、新規 Bot の着手を始められる最小テンプレートです。

## 使い方

1. `bots/template_bot/` を新しいディレクトリ名へコピーします。
2. `config.example.json` の `bot.name` を新しい Bot 名へ変更します。
3. 必要に応じて `strategy` / `risk` / `market_data` / `execution` を調整します。
4. 実行時はコピー先の設定ファイルを `--config` に渡します。

例:

```bash
cp -R bots/template_bot bots/my_new_bot
PYTHONPATH=src python3 -m trading_bot run-paper-bot --config bots/my_new_bot/config.example.json
```

## 設定キー

- `bot.name`: recorder 配下や lock 名に使われる Bot の識別子です。
- `risk.*`: ポジション上限、日次損失上限、連敗上限、注文間隔を制御します。
- `strategy.*`: シンボル、基準価格、エントリー閾値など戦略固有のパラメータです。
- `market_data.source`: 後方互換キーです。新規設定では `market_data.adapter` を優先し、必要なら同じ値を併記します。
- `execution.adapter`: 約定送信先の実装を選びます。`paper`、`dry-run`、`bitflyer-dry-run`、`bitflyer-live` などを指定します。

## 補足

- JSON にはコメントを書けないため、設定の意味はこの README に寄せています。
- このテンプレートは `synthetic + paper` の最小構成です。Bot ロジックの実装は `src/trading_bot/bots/` 側で追加してください。
