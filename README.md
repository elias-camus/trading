# trading

仮想通貨の自動売買 Bot を量産・運用するための Python フレームワーク。

## 概要

基盤（データ取得・注文・リスク管理・記録・監視・通知・デプロイ）は完成済み。
**やるべきことは戦略ロジックの開発とテスト。**

### 主要機能

- **Market Data**: BitFlyer HTTP Public API (ticker) / Synthetic (テスト用)
- **Strategy**: 戦略ロジックの抽象化 (Strategy ABC + factory pattern)
- **Execution**: paper (模擬) / dry-run / live (BitFlyer Private API)
- **Risk**: 連敗上限、日次損失上限、ポジション上限、注文間隔
- **Recording**: NDJSON イベント記録 + 日次集計 CLI
- **Monitoring**: Prometheus / Grafana / Alertmanager / Discord 通知
- **Secrets**: AWS Secrets Manager / 環境変数 / inline
- **Deploy**: Docker Compose + systemd (AWS Lightsail)
- **Graceful Shutdown**: SIGTERM/SIGINT ハンドリング
- **Structured Logging**: JSON-line 形式 (CloudWatch/Loki 互換)

## Bot の動作フロー

```
[Market Data] → snapshot 取得
    ↓
[Strategy] → compute_signal_bps(snapshot) → signal_bps
    ↓
[Threshold Check] → abs(signal_bps) < threshold なら見送り
    ↓
[Risk Check] → 連敗/日次損失/ポジション上限/間隔チェック
    ↓
[Execution] → paper(模擬) / dry-run / live
    ↓
[Recorder] → NDJSON で全イベント記録
```

## 戦略を追加する手順

CLAUDE.md に詳しく書いてある。要約:

1. `src/trading_bot/strategy/` に Strategy クラスを作る
2. `src/trading_bot/strategy/factory.py` に登録する
3. `bots/` に config.json を作る
4. `tests/test_strategy.py` にテストを追加する
5. `PYTHONPATH=src python3 -m trading_bot run-paper-bot --config bots/my_bot/config.json` で実行

## 既存の戦略

| 名前 | ファイル | 説明 |
|---|---|---|
| passthrough | `strategy/passthrough.py` | snapshot の signal_bps をそのまま返す（後方互換用） |
| momentum | `strategy/momentum.py` | 直近 N 個の価格から rate-of-change を bps で返す |

## ディレクトリ構成

- `src/trading_bot/` — 共通ランタイムと Bot 実装
  - `strategy/` — 戦略ロジック (ここに新しい戦略を書く)
  - `core/` — 設定、メトリクス、記録、リスク管理、ログ
  - `bots/` — Bot 実装
  - `execution/` — 注文実行アダプタ
  - `market_data/` — 市場データアダプタ
  - `alerting/` — Discord 通知
- `bots/` — Bot ごとの設定ファイル
- `data/` — 実行時に生成される記録とレポート
- `deploy/` — 配備用ファイル (Prometheus, Grafana, Alertmanager)
- `docs/` — 設計メモと運用メモ
- `tests/` — テスト

## セットアップ

```bash
cd /Users/toshikikobayashi/Repositories/trading
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 使い方

```bash
# Paper bot (synthetic data)
PYTHONPATH=src python3 -m trading_bot run-paper-bot --config bots/cex_swing/config.example.json

# Paper bot (BitFlyer real data + momentum strategy)
PYTHONPATH=src python3 -m trading_bot run-paper-bot --config bots/cex_swing/config.bitflyer-momentum.json

# 集計
PYTHONPATH=src python3 -m trading_bot summarize-records --root data/runtime/records --bot paper-cex-swing
```

## テスト

```bash
cd /Users/toshikikobayashi/Repositories/trading
PYTHONPATH=src python3 -m unittest discover -s tests -t . -v
# または
make test
```

## Docker 実行

```bash
# Bot 単体
docker build -t trading-bot:latest .
docker run --rm -p 9464:9464 -v "$(pwd)/data:/app/data" trading-bot:latest

# 監視込み (Bot + Prometheus + Grafana + Alertmanager + Discord relay)
docker compose -f docker-compose.aws.yml up -d --build
```

確認先:
- Bot metrics: `http://localhost:9464/metrics`
- Prometheus: `http://localhost:9090`
- Alertmanager: `http://localhost:9093`
- Grafana: `http://localhost:3000`

## 取引所の前提

日本居住者前提では、海外取引所の商品をそのまま実運用対象にするのは危ない。

- 実運用の初期対象は国内登録業者 (BitFlyer) を優先
- 海外取引所は研究用データ取得や比較用途として切り分ける
- レバレッジやデリバティブは商品提供可否と API 提供可否の両方を確認してから対応する

## 設定

設定は `bot / risk / strategy / market_data / execution / credentials` に分かれている。

- `execution.adapter`: `paper` / `dry-run` / `bitflyer-dry-run` / `bitflyer-live`
- `market_data.adapter`: `synthetic` / `bitflyer`
- `strategy.metadata.strategy_type`: `passthrough` / `momentum`
- BitFlyer の設定例: `bots/cex_swing/config.bitflyer-*.json`

## ドキュメント

- [CLAUDE.md](CLAUDE.md) — 戦略開発ガイド
- [TODO.md](TODO.md) — 残タスク
- [docs/architecture.md](docs/architecture.md) — 設計メモ
- [docs/aws-ec2-deploy.md](docs/aws-ec2-deploy.md) — AWS デプロイ手順
- [docs/aws-secrets-manager.md](docs/aws-secrets-manager.md) — Secrets Manager 設定
- [docs/discord-alerting.md](docs/discord-alerting.md) — Discord 通知設定
