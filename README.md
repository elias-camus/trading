# trading

仮想通貨Bot、共有ランタイム、検証ワークフローを育てていくための Python ベースの土台です。

## 概要

現在は次のものが入っています。

- 共通基盤
  - 設定読み込み
  - market data / execution adapter の interface
  - メトリクス管理
  - NDJSON レコーダー
  - リスクガード
  - 単一起動ロック
  - credential resolver
- サンプルBot
  - CEX 向けの紙上実行Bot
  - 疑似シグナルを使って記録・判定・紙上約定まで流す
  - recorder を読む集計 CLI

## 現在地

いまは「基盤の骨組みがあり、BitFlyer の実データ adapter と実注文 adapter が入った段階」です。

- できていること
  - 紙上実行Botを動かす
  - BitFlyer HTTP Public API から ticker を取得する
  - BitFlyer Private API へ dry-run / live で注文を組み立てて送る
  - recorder に記録する
  - recorder の日次集計を出す
  - `/metrics` を出す
  - EC2 へ常駐配備する
  - Prometheus / Grafana で監視する
- これから必要なこと
  - 秘密情報の安全な取り扱い
  - 新規Botを量産するためのテンプレート化

残タスクの要約は [TODO.md](/Users/toshikikobayashi/Repositories/trading/TODO.md) にまとめています。

## 取引所の前提

日本居住者前提では、海外取引所の現物・先物・レバレッジ商品をそのまま実運用対象にするのは危ないです。

- `Binance` と `Bybit` は日本居住者向けの扱いを商品単位で毎回確認する必要がある
- 実運用の初期対象は、国内登録業者かつ API 提供が明示されている取引所を優先する
- 海外取引所は、まず研究用データ取得や比較用途として切り分ける

この前提で、最初の live 候補は国内業者向け adapter を優先して作る想定です。

## ディレクトリ構成

- `src/trading_bot/`: 共通ランタイムとサンプルBot実装
- `bots/`: Bot ごとの設定ファイル置き場
- `data/`: 実行時に生成される記録とレポート
- `deploy/`: 配備用ファイル
- `docs/`: 設計メモと運用メモ
- `scripts/`: EC2 更新や配備用スクリプト
- `tests/`: 共通基盤の基本テスト

## 使い方

```bash
cd /Users/toshikikobayashi/Repositories/trading
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
trading-bot run-paper-bot --config bots/cex_swing/config.example.json
trading-bot summarize-records --root data/runtime/records --bot paper-cex-swing
```

依存をまだ入れたくない場合は、次でも動きます。

```bash
cd /Users/toshikikobayashi/Repositories/trading
PYTHONPATH=src python3 -m trading_bot run-paper-bot --config bots/cex_swing/config.example.json
PYTHONPATH=src python3 -m trading_bot summarize-records --root data/runtime/records --bot paper-cex-swing
```

このサンプルBotは紙上実行か BitFlyer 注文 dry-run/live の設定例を含みます。`market_data.adapter=synthetic` では疑似 snapshot、`market_data.adapter=bitflyer` または `market_data.source=bitflyer` では BitFlyer の public ticker を取得し、判定・リスクチェック・約定送信まで確認できます。

設定は `bot / risk / strategy / market_data / execution / credentials` に分かれています。`execution.mode` は `paper / dry-run / live` を想定し、`execution.adapter` は `paper` / `dry-run` / `bitflyer-dry-run` / `bitflyer-live` を利用できます。

### BitFlyer execution adapter

- `src/trading_bot/execution/bitflyer.py` に BitFlyer Private API 向けの execution adapter を追加しています
- `bitflyer-dry-run` は署名とリクエスト payload を生成しますが、HTTP 送信は行いません
- `bitflyer-live` は `POST /v1/me/sendchildorder` を送信し、`child_order_acceptance_id` を execution metadata に保存します
- 認証情報は `execution.credentials_ref` から `credentials` セクションを引き、`env` / `inline` / `aws_secrets_manager` を使えます
- dry-run の設定例は [config.bitflyer-dry-run.example.json](/home/ubuntu/.openclaw/workspace/trading/bots/cex_swing/config.bitflyer-dry-run.example.json) を参照してください。既存の paper 設定は [config.example.json](/home/ubuntu/.openclaw/workspace/trading/bots/cex_swing/config.example.json) に残しています

## テスト

標準の実行経路は次です。

```bash
cd /Users/toshikikobayashi/Repositories/trading
python3 -m unittest discover -s tests -t . -v
```

または:

```bash
cd /Users/toshikikobayashi/Repositories/trading
make test
```

AWS EC2 へ 24時間365日で常駐配備する場合は [aws-ec2-deploy.md](/Users/toshikikobayashi/Repositories/trading/docs/aws-ec2-deploy.md) を参照してください。

設計の全体像は [architecture.md](/Users/toshikikobayashi/Repositories/trading/docs/architecture.md)、調査整理は [yodakaart-crypto-bot-notes.md](/Users/toshikikobayashi/Repositories/trading/yodakaart-crypto-bot-notes.md)、Discord 通知方針は [discord-alerting.md](/Users/toshikikobayashi/Repositories/trading/docs/discord-alerting.md) を参照してください。

## Docker 実行

`9464` で `/metrics` を公開する常駐向け Dockerfile を追加済みです。

```bash
cd /Users/toshikikobayashi/Repositories/trading
docker build -t trading-bot:latest .
docker run --rm -p 9464:9464 -v "$(pwd)/data:/app/data" trading-bot:latest
```

確認:

```bash
curl http://127.0.0.1:9464/healthz
curl http://127.0.0.1:9464/metrics
```

監視込みで起動する場合:

- Prometheus
- Alertmanager
- Discord relay
- Grafana

```bash
cd /Users/toshikikobayashi/Repositories/trading
docker compose -f docker-compose.aws.yml up -d --build
```

主な確認先:

- Bot metrics: `http://127.0.0.1:9464/metrics`
- Prometheus: `http://127.0.0.1:9090`
- Alertmanager: `http://127.0.0.1:9093`
- Grafana: `http://127.0.0.1:3000`

## 出力先

- 実行ログ相当のイベントは `data/runtime/records/` 以下に日付ごとに保存されます
- `runtime/`, `market_snapshots/`, `decisions/`, `paper_fills/`, `risk_events/`, `reports/` に分かれます

集計例:

```bash
cd /Users/toshikikobayashi/Repositories/trading
PYTHONPATH=src python3 -m trading_bot summarize-records \
  --root data/runtime/records \
  --bot paper-cex-swing \
  --output data/runtime/summary-paper-cex-swing.json
```

## 補足

- サンドボックス環境ではローカル HTTP ポート bind が禁止される場合があります
- その場合でも Bot 本体は継続し、`metrics_http_enabled=false` を runtime 記録に残します
- 実機環境では `metrics_host` と `metrics_port` に応じて `/metrics` を公開できます
- EC2 常駐化の更新用に `scripts/deploy_ec2.sh` を追加しています
