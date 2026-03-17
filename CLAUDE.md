# Trading Bot 開発ガイド

## このリポジトリの目的

仮想通貨の自動売買 Bot を量産・運用するための Python フレームワーク。
基盤（データ取得・注文・リスク管理・記録・監視・通知・デプロイ）は完成済み。
**やるべきことは戦略ロジックの開発とテスト。**

## 戦略を追加する手順

### 1. Strategy クラスを書く

`src/trading_bot/strategy/` に新しいファイルを作る。

```python
# src/trading_bot/strategy/my_strategy.py
from __future__ import annotations
from trading_bot.market_data.base import MarketSnapshot
from trading_bot.strategy.base import Strategy

class MyStrategy(Strategy):
    def __init__(self, param1: int = 10) -> None:
        # 内部状態の初期化（価格履歴など）
        pass

    def compute_signal_bps(self, snapshot: MarketSnapshot) -> float:
        # snapshot.price, snapshot.metadata (bid/ask/volume) を使って
        # 売買シグナルを basis points で返す
        # 正 = 買い、負 = 売り、0付近 = 見送り
        return 0.0
```

### 2. Factory に登録する

`src/trading_bot/strategy/factory.py` の `build_strategy()` に分岐を追加:

```python
if strategy_type == "my_strategy":
    param1 = int(config.metadata.get("my_param1", "10"))
    return MyStrategy(param1=param1)
```

### 3. Config を作る

`bots/` 以下にディレクトリを作り、config.json を置く:

```json
{
  "strategy": {
    "symbol": "BTC_JPY",
    "base_price": 10000000.0,
    "signal_threshold_bps": 5.0,
    "metadata": {
      "strategy_type": "my_strategy",
      "my_param1": "20"
    }
  }
}
```

他のセクション (bot, risk, market_data, execution, credentials) は `bots/template_bot/config.example.json` からコピー。

### 4. テストを書く

`tests/test_strategy.py` にテストを追加（既存パターンを参照）。

### 5. 実行

```bash
PYTHONPATH=src python3 -m trading_bot run-paper-bot --config bots/my_bot/config.json
```

## Strategy インターフェース

```python
class Strategy(ABC):
    def compute_signal_bps(self, snapshot: MarketSnapshot) -> float:
        """売買シグナルを basis points で返す。正=買い、負=売り。"""
```

### MarketSnapshot の中身

```python
@dataclass
class MarketSnapshot:
    symbol: str          # "BTC_JPY"
    price: float         # 直近価格 (ltp)
    signal_bps: float    # market data adapter が設定した初期値（通常 0.0）
    ts: str              # UTC ISO 8601 タイムスタンプ
    venue: str           # "bitflyer" など
    source: str          # "http_ticker" など
    metadata: dict       # {"best_bid": "...", "best_ask": "...", "volume_by_product": "..."}
```

Strategy は `snapshot.price` と `snapshot.metadata` を使ってシグナルを計算する。
内部状態（価格履歴、移動平均など）は Strategy クラス自身が保持する。

## 既存の戦略

| 名前 | ファイル | 説明 |
|---|---|---|
| passthrough | `strategy/passthrough.py` | snapshot の signal_bps をそのまま返す（後方互換用） |
| momentum | `strategy/momentum.py` | 直近 N 個の価格から rate-of-change を bps で返す |

## Bot の動作フロー

```
[Market Data] → snapshot取得
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

## テスト

```bash
cd /Users/toshikikobayashi/Repositories/trading
PYTHONPATH=src python3 -m unittest discover -s tests -t . -v
```

## 触らなくていいファイル

- `src/trading_bot/core/` — 設定、メトリクス、記録、リスク管理（完成済み）
- `src/trading_bot/execution/` — 注文実行アダプタ（完成済み）
- `src/trading_bot/market_data/` — 市場データ取得（完成済み）
- `src/trading_bot/alerting/` — Discord 通知（完成済み）
- `src/trading_bot/bots/base.py` — Bot 共通ループ（完成済み）
- `deploy/` — デプロイ設定（完成済み）

## 触るファイル

- `src/trading_bot/strategy/` — **ここに戦略を書く**
- `src/trading_bot/strategy/factory.py` — 新しい戦略を登録する
- `bots/*/config.json` — Bot の設定
- `tests/test_strategy.py` — 戦略のテスト
- `src/trading_bot/bots/paper_cex_swing.py` — Bot ロジックを変えたい場合のみ

## 設定のパラメータチューニング

戦略パラメータは `strategy.metadata` に入れる（文字列の key-value）。
リスクパラメータは `risk.*` で調整:
- `signal_threshold_bps`: シグナルの発火閾値
- `max_daily_loss`: 日次損失上限
- `max_consecutive_losses`: 連敗上限
- `min_order_interval_seconds`: 注文間隔の最小秒数

## 集計

```bash
PYTHONPATH=src python3 -m trading_bot summarize-records --root data/runtime/records --bot <bot-name>
```

勝率・損益・slippage・リスクブロック理由が出る。
