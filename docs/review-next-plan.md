# review and next plan

## 現状評価

- 共通基盤の最小骨組みは実装済み
- 紙上実行 Bot は動作する
- Recorder / Metrics / Risk / RunLock の責務分離はできている
- EC2 常駐、Prometheus、Grafana までの配備素材はある
- BitFlyer 実データ adapter、実注文 adapter、Secrets Manager、Discord 通知、Bot テンプレート、分析ジョブ最小版まで入った
- 量産可能な基盤にかなり近づいたが、運用ログと戦略面はまだ薄い

現時点の到達点は、`共通基盤 + CEX 最小実装 + 通知 + secrets + 分析` が通った段階です。

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

### 3. 運用ログの集約が未整備

- Prometheus ルールはある
- Grafana も compose に入っている
- Alertmanager と Discord relay も入り、Webhook / Bot Token の両経路で通知できる
- ただし永続ログの集約先がなく、障害解析の導線はまだ弱い

対応方針:

- CloudWatch Logs か Loki を追加する
- コンテナログと Bot の運用ログをまとめて拾う
- 通知とログをひもづけて原因追跡しやすくする

### 4. 戦略ロジックと検証導線が弱い

- Recorder を読む分析ジョブ最小版は入った
- ただし売買ロジック自体はまだ薄く、backtest / replay もない
- 実データを取れても戦略改善の回転数はまだ低い

対応方針:

- `research/` に戦略別特徴量と評価を追加する
- replay / backtest の最小版を後続で作る
- summary CLI を戦略改善に使える粒度へ拡張する

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

### Phase 2: 運用ログの整備

目的:
常駐運用時の障害解析をしやすくする

作業:

- CloudWatch Logs か Loki を追加する
- コンテナログの転送設定を入れる
- Bot の runtime / risk / execution エラーを検索しやすくする

完了条件:

- 常駐中の例外と運用ログを横断検索できる
- 通知発火時の前後ログを追える

### Phase 3: 戦略ロジック

目的:
実データを売買判断へつなげる

作業:

- エントリー/イグジット条件を定義する
- signal の説明変数を `research/` に切り出す
- リスク制御との境界を明確化する

完了条件:

- synthetic ではなく実データ前提で判断が回る
- 取引理由を recorder と summary で追える

### Phase 4: 検証ループ強化

目的:
改善速度を上げる

作業:

- backtest / replay の最小版を追加する
- summary CLI に戦略比較軸を増やす
- 主要指標をダッシュボードへ反映する

完了条件:

- 改善案をオフラインで比較できる
- 実運用前の検証回数を増やせる

### Phase 5: 量産フェーズ

目的:
Bot を増やしやすくする

作業:

- Bot テンプレートの差分をさらに減らす
- venue ごとの差し替え点を整理する
- ダッシュボードや通知ルールを Bot ごとに増やしやすくする

完了条件:

- 新規 Bot を短時間で増やせる
- 監視と分析も一緒に複製できる

## 直近 3 スプリントの着手単位

### Sprint A

- テスト経路固定
- config 再設計
- paper bot 移行
- README / docs 更新

### Sprint B

- CloudWatch Logs / Loki
- ログ転送設定
- 運用ログ確認手順の整備

### Sprint C

- 戦略ロジック最小版
- replay / backtest 方針
- summary 拡張

## 着手前に決めるべきこと

- CloudWatch Logs と Loki のどちらを優先するか
- live 初号機の対象 venue をどこにするか
- テストは `unittest` 継続か `pytest` へ寄せるか
- 戦略検証を replay と backtest のどちらから始めるか

## すぐ着手してよい実装候補

次に着手するなら、順番はこれです。

1. CloudWatch Logs / Loki 方針決定
2. 戦略ロジック最小版
3. replay / backtest 最小版
4. summary CLI 拡張

この 4 点まで終わると、実運用と改善ループの密度がかなり上がります。
