# 設計メモ

## 目的

- 戦略コードを薄く保ち、差し替えやすくする
- Recorder、Metrics、Risk を共通化する
- 実弾の前に紙上実行を標準経路にする
- 後から検証できるだけのイベント記録を必ず残す

## 現在の共通モジュール

- `trading_bot.core.config`
  - JSON 設定を dataclass に読み込む
- `trading_bot.core.metrics`
  - インメモリのメトリクスレジストリ
  - 必要に応じて HTTP で `/metrics` を公開
- `trading_bot.core.recorder`
  - NDJSON でイベントを日付単位に保存
- `trading_bot.core.risk`
  - 連敗数、日次損失、ポジション量、最小発注間隔を管理
- `trading_bot.core.runtime`
  - 単一起動ロックと設定フィンガープリント
- `trading_bot.bots.paper_cex_swing`
  - 共通モジュールを使うサンプルの紙上実行Bot
  - `max_iterations=0` のときは常駐実行する

## 実行フロー

1. Bot 設定を読み込む
2. 単一起動ロックを取得する
3. メトリクス公開を試みる
4. market snapshot を生成する
5. シグナル判定とリスク判定を行う
6. 紙上約定を記録する
7. 最後に日次サマリを出力する

`max_iterations=0` の場合は停止指示が入るまでループを継続する。

## 生成される記録

- `runtime`
  - 起動時の設定情報、実行フラグ、メトリクス公開可否
- `market_snapshots`
  - 入力として扱った価格とシグナル
- `decisions`
  - 見送り判断の理由
- `paper_fills`
  - 紙上約定の結果
- `risk_events`
  - リスク制限で止めた理由
- `reports`
  - 実行後の集計

## 直近の拡張候補

- 疑似 feed を取引所アダプタへ置き換える
- Parquet 出力と分析ジョブを追加する
- `research/` に戦略別の特徴量生成を切り出す
- CEX 実行アダプタと DeFi 実行アダプタを分離する
- Recorder と分析基盤を使って shadow execution を強化する

## 基盤完成の定義

このリポジトリで「基盤ができた」と言える状態は次の通り。

- 実データを安定取得できる
- paper / dry-run / live を切り替えられる
- recorder と metrics の両方が揃っている
- Secrets Manager などで秘密情報を安全に扱える
- 監視と通知がある
- 新規Botをテンプレートから増やせる

現状は、このうち `paper / recorder / metrics / 常駐配備` までが入っている。

## 取引所選定の前提

日本居住者向けに live Bot を組む場合は、取引所の選定自体を基盤要件として扱う。

- live の初期対象は国内登録業者を優先する
- 海外取引所は research と比較用途を優先する
- レバレッジやデリバティブは、商品提供可否と API 提供可否の両方を確認してから対応する

そのため adapter 層は、最初から `research venue` と `live venue` を分けて扱える形に寄せる。
