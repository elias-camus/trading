# 設計メモ

## 目的

- 戦略コードを薄く保ち、差し替えやすくする
- Recorder、Metrics、Risk を共通化する
- 実弾の前に紙上実行を標準経路にする
- 後から検証できるだけのイベント記録を必ず残す

## アーキテクチャ

```
[Market Data Adapter] → MarketSnapshot
        ↓
[Strategy] → compute_signal_bps(snapshot) → signal_bps
        ↓
[Risk Guard] → 連敗/損失/ポジション/間隔チェック
        ↓
[Execution Adapter] → ExecutionResult
        ↓
[Recorder] → NDJSON イベント記録
        ↓
[Metrics] → Prometheus /metrics
        ↓
[Alertmanager] → Discord 通知
```

すべてのレイヤーが adapter pattern で差し替え可能。
config.json の設定だけで market data / strategy / execution を切り替えられる。

## 共通モジュール

- `trading_bot.core.config` — JSON 設定を dataclass に読み込む
- `trading_bot.core.metrics` — インメモリのメトリクスレジストリ + HTTP `/metrics`
- `trading_bot.core.recorder` — NDJSON でイベントを日付単位に保存
- `trading_bot.core.risk` — 連敗数、日次損失、ポジション量、最小発注間隔を管理
- `trading_bot.core.runtime` — 単一起動ロックと設定フィンガープリント
- `trading_bot.core.logging` — JSON-line 構造化ログ (CloudWatch/Loki 互換)

## Strategy レイヤー

```python
class Strategy(ABC):
    @abstractmethod
    def compute_signal_bps(self, snapshot: MarketSnapshot) -> float:
        """売買シグナルを basis points で返す。正=買い、負=売り。"""
```

- `PassthroughStrategy`: snapshot.signal_bps をそのまま返す（後方互換）
- `MomentumStrategy`: deque で直近 N 個の価格を保持、最古→最新の変化率を bps で返す
- `build_strategy(config)`: config.metadata["strategy_type"] で dispatch

新しい戦略を追加するには:
1. `strategy/` に Strategy サブクラスを作る
2. `strategy/factory.py` に分岐を追加する

## Market Data Adapter

- `BitFlyerMarketDataAdapter` — BitFlyer HTTP Public API の `getticker`
  - `ltp` を価格として取得、`best_bid`/`best_ask`/`volume_by_product` は metadata に保持
  - adapter 自体は `signal_bps=0.0` を返す（Strategy レイヤーがシグナルを計算する）
  - 5分500回の API 制限に対応した `min_interval_sec` 制御あり
- `SyntheticMarketDataAdapter` — テスト用の疑似データ

## Execution Adapter

- `PaperExecutionAdapter` — 模擬約定 (0.06% 固定手数料 + ランダムノイズ)
- `DryRunExecutionAdapter` — リクエスト組み立てまで (HTTP 送信なし)
- `BitFlyerLiveExecutionAdapter` — BitFlyer Private API で実注文
  - HMAC-SHA256 認証
  - `getexecutions` で fill 確認 (3秒タイムアウト)
  - `fill_status: confirmed/unconfirmed` を metadata に記録

## Graceful Shutdown

- `BaseBot` が SIGTERM/SIGINT を捕捉して `_stop_requested` フラグを立てる
- `should_stop()` がフラグを見てループを安全に終了
- 終了前に `after_loop()` でレポートを出力

## 生成される記録

| カテゴリ | 内容 |
|---|---|
| runtime | 起動時の設定情報、実行フラグ |
| market_snapshots | 入力価格とシグナル |
| decisions | 見送り判断の理由 |
| paper_fills | 紙上約定の結果 |
| risk_events | リスク制限の発動理由 |
| reports | 実行後の集計 |

## デプロイ

AWS Lightsail に Docker Compose でデプロイ:
- Bot + Prometheus + Grafana + Alertmanager + Discord relay
- systemd で自動起動
- 詳細: [aws-ec2-deploy.md](aws-ec2-deploy.md)

## 基盤完成の定義

すべて達成済み:

- [x] 実データを安定取得できる (BitFlyer ticker)
- [x] paper / dry-run / live を切り替えられる
- [x] recorder と metrics が揃っている
- [x] Secrets Manager で秘密情報を安全に扱える
- [x] 監視と通知がある (Prometheus / Grafana / Alertmanager / Discord)
- [x] 新規 Bot をテンプレートから増やせる
- [x] 戦略ロジック層がある (Strategy ABC + factory)
- [x] Graceful shutdown (SIGTERM/SIGINT)
- [x] 構造化ログ

## 今後の拡張候補

- CloudWatch Logs か Loki へのログ集約
- backtest / replay 基盤
- CEX/DEX 裁定向け adapter
- DeFi イベント検知 adapter
- Grafana ダッシュボードのコード管理
- CI/CD パイプライン

## 取引所選定の前提

日本居住者向けに live Bot を組む場合は、取引所の選定自体を基盤要件として扱う。

- live の初期対象は国内登録業者を優先する
- 海外取引所は research と比較用途を優先する
- レバレッジやデリバティブは、商品提供可否と API 提供可否の両方を確認してから対応する
