# review and next plan

## 現状: 基盤完成

Bot を開発・テスト・監視して改善できる基盤はすべて揃った。

### 達成済み

- 共通基盤 (config, metrics, recorder, risk, runtime, logging)
- Market Data adapter (BitFlyer HTTP ticker / Synthetic)
- Execution adapter (paper / dry-run / BitFlyer live)
- Strategy 抽象化 (Strategy ABC + factory + passthrough + momentum)
- Graceful shutdown (SIGTERM/SIGINT handler)
- 構造化ログ (JSON-line, CloudWatch/Loki 互換)
- BitFlyer fill confirmation (getexecutions polling, fill_status metadata)
- AWS Secrets Manager 連携
- Discord 通知 (Webhook / Bot Token)
- Bot テンプレート化
- 分析ジョブ (勝率, 損益, slippage)
- AWS Lightsail デプロイ (Docker Compose + systemd)
- Prometheus / Grafana / Alertmanager 監視

### テスト: 50 件パス

- 共通基盤テスト (config, metrics, recorder, risk, runtime)
- Strategy テスト (passthrough, momentum, factory)
- Graceful shutdown テスト
- BitFlyer execution テスト (fill_status 含む)

## 次のフェーズ: 戦略開発

基盤が完成したので、メインの作業は戦略ロジックの開発とテスト。

### 戦略開発の流れ

1. `src/trading_bot/strategy/` に Strategy クラスを書く
2. `strategy/factory.py` に登録する
3. config.json を作る
4. テストを書く
5. paper bot で検証する
6. 結果を分析して改善する

### 戦略候補

- Mean reversion (移動平均からの乖離)
- Spread-based (bid/ask スプレッドの変動)
- VWAP (出来高加重)
- Multi-timeframe momentum
- Volatility breakout

## 運用改善 (優先度順)

### 1. CloudWatch Logs / Loki

構造化ログは出力済み。転送先を決めて接続するだけ。

### 2. CI/CD

GitHub Actions でテスト自動実行 + デプロイ自動化。

### 3. Grafana ダッシュボード

JSON provisioning でコード管理する。

### 4. backtest / replay

recorder のログを再生して戦略をオフラインで比較する。

## 量産フェーズ

- 他の国内取引所 adapter (GMO コイン, bitbank)
- CEX/DEX 裁定向け adapter
- DeFi イベント検知 adapter
- Parquet 出力 (分析効率向上)
- 複数 Bot の並列運用と比較ダッシュボード
