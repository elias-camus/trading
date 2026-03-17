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
- Secrets Manager 連携
  - 取引所 API キーを AWS Secrets Manager から解決できる
  - Discord Webhook URL を AWS Secrets Manager から解決できる
- 監視の骨組み
  - Prometheus
  - Grafana
  - 基本アラート
- Discord 通知
  - Webhook URL
  - Discord Bot Token + Channel ID
- Bot テンプレート化
  - 最小差分で新規 Bot を追加できる
- 分析ジョブ最小版
  - 勝率
  - 損益
  - slippage

まだ足りないこと:

- 日本居住者向けの取引所選定の具体化
- CloudWatch Logs か Loki へのログ集約
- 実運用向け戦略ロジック
- backtest / replay 基盤

## 基盤完成までの残タスク

### 優先度A: まずこれがないと量産しにくい

- 日本居住者前提の venue 方針を固める
  - 現物の初期対象を国内登録業者から選ぶ
  - レバレッジの初期対象も国内 API 対応可否で絞る
  - 海外取引所は research 用と live 用を分ける
- config を戦略共通と取引所共通に分ける
  - symbol
  - venue
  - credentials 参照先
  - 実行モード
- 戦略ロジックを作る
  - 実シグナル生成
  - エントリー/イグジット条件
  - 理由別ブロック数の分析改善

### 優先度B: 実運用に近づける

- [x] CEX 実データ adapter を作る
  - BitFlyer HTTP Public API の ticker
- [x] 実注文 adapter を作る
  - paper
  - dry-run
  - live の 3 モード
- [x] Secrets Manager から API キーを読む
- [x] Alertmanager と Discord 通知をつなぐ
  - Discord を標準通知先にする
  - Webhook URL / Bot Token の両方に対応する
- [x] Bot テンプレートを作る
  - 新規Botを 1 ディレクトリ追加すれば作り始められる状態にする
- [x] 分析ジョブの最小版を作る
  - 日次集計
  - 勝率
  - 損益
  - slippage
- CloudWatch Logs か Loki にログ転送する

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

1. 戦略ロジック実装
2. CloudWatch Logs / Loki
3. backtest / replay 基盤
4. Grafana ダッシュボードのコード管理

## 直近の実装候補

- 国内登録業者を優先して market data adapter を 1 本作る
- `research/` に recorder から読む集計スクリプトを置く
- Grafana ダッシュボード JSON を追加する
- CloudWatch Logs か Loki への出力経路を追加する
- 実シグナル生成ロジックを最小版で入れる
