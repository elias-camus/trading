# TODO

## 基盤の現在地

すでにできていること:

- 共通ランタイムの骨組み
  - 設定読み込み
  - メトリクス registry
  - `/metrics` と `/healthz`
  - NDJSON レコーダー
  - リスクガード
  - 単一起動ロック
- 紙上実行のサンプルBot
  - 疑似シグナル生成
  - 判定
  - 紙上約定
  - レポート出力
- AWS 常駐の骨組み
  - Dockerfile
  - EC2 配備メモ
  - cloud-init
  - systemd
  - deploy script
- BitFlyer adapter
  - HTTP Public API の market data
  - Private API の実注文 dry-run / live
- 監視の骨組み
  - Prometheus
  - Grafana
  - 基本アラート

まだ足りないこと:

- 日本居住者向けの取引所選定
- 実取引所データ adapter
- Secrets Manager 連携
- ログ集約
- バックテスト/分析ジョブ
- Bot テンプレート化
- Discord 通知

## 基盤完成までの残タスク

### 優先度A: まずこれがないと量産しにくい

- 日本居住者前提の venue 方針を固める
  - 現物の初期対象を国内登録業者から選ぶ
  - レバレッジの初期対象も国内 API 対応可否で絞る
  - 海外取引所は research 用と live 用を分ける
- CEX 実データ adapter を作る
  - WebSocket で ticker / trades / orderbook を取る
  - recorder にそのまま保存する
- config を戦略共通と取引所共通に分ける
  - symbol
  - venue
  - credentials 参照先
  - 実行モード
- Bot テンプレートを作る
  - 新規Botを 1 ディレクトリ追加すれば作り始められる状態にする
- 分析ジョブの最小版を作る
  - 日次集計
  - 勝率
  - 損益
  - slippage
  - 理由別ブロック数

### 優先度B: 実運用に近づける

- [x] 実注文 adapter を作る
  - paper
  - dry-run
  - live の 3 モード
- Secrets Manager から API キーを読む
- CloudWatch Logs か Loki にログ転送する
- Alertmanager と Discord 通知をつなぐ
  - Discord を標準通知先にする
  - Webhook URL は Secrets Manager で管理する

### 優先度C: 量産フェーズで効く

- CEX/DEX 裁定向け adapter を追加
- DeFi イベント検知 adapter を追加
- backtest / replay 基盤を作る
- Parquet 出力を追加する
- Grafana ダッシュボードをコード管理する

## 最短ルート

基盤を「Bot を量産できる状態」とみなす条件は次の 5 点。

1. 実データを安定取得できる
2. 紙上実行と実発注を切り替えられる
3. 監視とアラートがある
4. API キーを安全に扱える
5. 新規Botをテンプレートから最小差分で増やせる

この状態までの最短順序:

1. CEX 実データ adapter
2. 分析ジョブ最小版
3. 実注文 adapter
4. Secrets Manager
5. 通知付き監視
6. Bot テンプレート化

## 直近の実装候補

- 国内登録業者を優先して market data adapter を 1 本作る
- `research/` に recorder から読む集計スクリプトを置く
- `bots/cex_swing/` をサンプル設定置き場から Bot 雛形へ格上げする
- Grafana ダッシュボード JSON を追加する
- Alertmanager + Discord Webhook の通知経路を追加する
