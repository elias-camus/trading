# TODO

## 基盤の状態: 完成

Bot を開発・テスト・監視して改善できる基盤はすべて揃った。
以下の完成条件を全て達成済み:

- [x] 実データを安定取得できる (BitFlyer ticker)
- [x] paper / dry-run / live を切り替えられる
- [x] recorder と metrics が揃っている
- [x] Secrets Manager で秘密情報を安全に扱える
- [x] 監視と通知がある (Prometheus / Grafana / Alertmanager / Discord)
- [x] 新規 Bot をテンプレートから最小差分で増やせる
- [x] 戦略ロジック層がある (Strategy ABC + factory)
- [x] Graceful shutdown (SIGTERM/SIGINT)
- [x] 構造化ログ (JSON-line, CloudWatch/Loki 互換)
- [x] BitFlyer fill confirmation (getexecutions polling)
- [x] AWS Lightsail にデプロイ済み (Docker Compose + systemd)

## 今後やること

### 戦略開発 (メインの作業)

ここが本業。CLAUDE.md に開発手順を書いてある。

- [ ] より高度な戦略の開発とテスト
  - mean reversion, VWAP, spread-based, etc.
- [ ] backtest / replay 基盤
  - recorder のログを再生して戦略を比較する
- [ ] 戦略パラメータの最適化ツール
- [ ] 複数戦略の並列実行と比較

### 運用改善

- [ ] CloudWatch Logs か Loki へのログ集約
  - 構造化ログは出力済み。転送先を決めて接続するだけ
- [ ] Grafana ダッシュボードのコード管理 (JSON provisioning)
- [ ] Grafana の admin パスワード変更 (デフォルトのまま)
- [ ] Discord Webhook URL を Secrets Manager に登録
  - alertmanager.yml に直書きしている
- [ ] CI/CD パイプライン (GitHub Actions)
  - テスト自動実行 + デプロイ自動化
- [ ] Parquet 出力 (分析効率向上)

### 取引所拡張

- [ ] 他の国内登録業者の adapter (GMO コイン, bitbank, etc.)
- [ ] CEX/DEX 裁定向け adapter
- [ ] DeFi イベント検知 adapter

## ファイル構成 (戦略開発者向け)

触るファイル:
- `src/trading_bot/strategy/` — 戦略を書く場所
- `src/trading_bot/strategy/factory.py` — 新しい戦略を登録する
- `bots/*/config.json` — Bot の設定
- `tests/test_strategy.py` — 戦略のテスト

触らなくていいファイル:
- `src/trading_bot/core/` — 設定、メトリクス、記録、リスク管理
- `src/trading_bot/execution/` — 注文実行アダプタ
- `src/trading_bot/market_data/` — 市場データ取得
- `src/trading_bot/alerting/` — Discord 通知
- `src/trading_bot/bots/base.py` — Bot 共通ループ
- `deploy/` — デプロイ設定
