# review and next plan

## 現状評価

- 共通基盤の最小骨組みは実装済み
- 紙上実行 Bot は動作する
- Recorder / Metrics / Risk / RunLock の責務分離はできている
- EC2 常駐、Prometheus、Grafana までの配備素材はある
- ただし「量産可能な基盤」にはまだ届いていない

現時点の到達点は、`paper execution の土台が通ったプロトタイプ` です。

## レビューで優先度が高かった論点

### 1. テスト実行経路が未整備

- `python3 -m unittest discover -s tests -v` は `ModuleNotFoundError: trading_bot` で失敗する
- `src/` レイアウトを前提にしているが、テスト実行方法が固定されていない
- CI を入れる前に `python -m unittest` か `pytest` の標準経路を 1 本に決める必要がある

対応方針:

- 開発用セットアップ手順に `pip install -e .[dev]` を入れる
- もしくは `PYTHONPATH=src` 前提のテストコマンドを `README.md` と Makefile に固定する
- 最初の実装フェーズでテスト実行を自動化する

### 2. 設定スキーマが拡張前提を満たしていない

- 現在の設定は `bot / risk / strategy` の 3 区分のみ
- TODO にある `venue`, `execution mode`, `credentials 参照先` をまだ表現できない
- adapter を追加する前に設定モデルを再設計しないと、すぐ作り直しになる

対応方針:

- `market_data`, `execution`, `credentials`, `venue` を独立セクション化する
- `paper / dry-run / live` を enum 的に扱えるようにする
- Bot 固有設定と基盤共通設定を分離する

### 3. 監視はあるが通知経路が未完成

- Prometheus ルールはある
- Grafana も compose に入っている
- しかし Alertmanager と Discord 通知経路は未実装
- `監視あり` ではなく `可視化のみ` の段階

対応方針:

- Alertmanager を compose に追加する
- `critical` のみ先に Discord 通知する
- Webhook URL は後続フェーズで Secrets Manager へ移す

### 4. 実データ adapter 着手前の分析導線が弱い

- Recorder はあるが、それを読む分析ジョブがまだない
- 実データを取り始めても品質を評価する導線が不足する
- TODO 上の順序より、adapter と分析を同じフェーズで進める方が安全

対応方針:

- `research/` を追加する
- recorder から日次集計を出す CLI を先に作る
- market snapshot 件数、hold 件数、risk block 件数、paper pnl を最低限集計する

## 次フェーズの実行順

### Phase 1: 土台の固定

目的:
実装を増やしても壊れにくい開発基盤にする

作業:

- テスト実行経路を固定する
- 設定スキーマを再設計する
- サンプル設定を新スキーマへ移行する
- README と docs を実際の起動方法に合わせて揃える

完了条件:

- ローカルで 1 コマンドでテスト実行できる
- `paper-cex-swing` が新設定で起動できる
- 設定追加時に既存コードの変更範囲が限定される

### Phase 2: 市場データの取り込み

目的:
疑似 feed から実データ feed へ移行する

作業:

- `MarketDataAdapter` の interface を定義する
- research 向け venue を 1 本選ぶ
- ticker / trades / orderbook のうち最初は ticker から始める
- adapter 取得データを recorder に保存する
- 切断時の再接続と失敗メトリクスを追加する

完了条件:

- 疑似 snapshot と実 snapshot を差し替え可能
- 取得イベントが NDJSON に保存される
- 接続失敗回数と最終受信時刻を metrics で見られる

### Phase 3: 分析ジョブ最小版

目的:
記録したイベントから継続改善できる状態にする

作業:

- `research/summary.py` などの集計 CLI を追加する
- 日次の trades / holds / risk blocks / pnl を集計する
- venue, symbol, bot name 単位で絞り込めるようにする
- 出力はまず JSON か CSV にする

完了条件:

- 1 日分の recorder データから集計が出せる
- 取引しなかった理由と損益の傾向を確認できる

### Phase 4: 実行モードの分離

目的:
paper と live の責務を分ける

作業:

- `ExecutionAdapter` interface を定義する
- `paper`, `dry-run`, `live` を明示的に分岐する
- 現在の紙上約定ロジックを `paper adapter` に移す
- live 未実装でも interface ベースで起動可能にする

完了条件:

- strategy 層が execution 実装詳細を知らない
- mode 切り替えが config だけで済む

### Phase 5: 通知と secrets

目的:
常駐運用に必要な最低限の運用安全性を作る

作業:

- Alertmanager を compose に追加する
- critical アラートの Discord 通知をつなぐ
- credentials / webhook の参照先 abstraction を作る
- AWS Secrets Manager 実装を追加する

完了条件:

- metrics 停止や損失閾値超えを通知できる
- 秘密情報をコードや JSON に直書きしない

## 直近 3 スプリントの着手単位

### Sprint A

- テスト経路固定
- config 再設計
- paper bot 移行
- README / docs 更新

### Sprint B

- market data interface
- venue 1 本の ticker adapter
- recorder 保存
- reconnect metrics

### Sprint C

- research 集計 CLI
- 日次サマリ
- execution interface
- paper adapter 抽出

## 着手前に決めるべきこと

- live 初号機の対象 venue をどこにするか
- research venue と live venue を分けるか
- テストは `unittest` 継続か `pytest` へ寄せるか
- 実行モード名を `paper / dry-run / live` に固定するか

## すぐ着手してよい実装候補

次に着手するなら、順番はこれです。

1. テスト実行経路の固定
2. config スキーマ再設計
3. `MarketDataAdapter` interface 追加
4. research 集計 CLI の最小版追加

この 4 点まで終わると、その後の adapter 実装がかなり進めやすくなります。
