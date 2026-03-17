# Discord 通知メモ

## 方針

このリポジトリの通知先は、まず Discord を標準にする。

理由:

- 個人運用で見やすい
- Bot ごとにチャンネルを分けやすい
- Webhook と Bot Token の両方を選べる

## 想定構成

標準構成:

- Prometheus
- Alertmanager
- `discord-relay`
- Discord Webhook または Discord Bot API

このリポジトリでは、Alertmanager から Discord へ直接投げず、軽量な `discord-relay` を 1 つ挟む。

理由:

- 重複通知をまとめやすい
- ルーティングを切りやすい
- critical / warning の出し分けがしやすい
- Discord 向けの payload 変換をリポジトリ側で制御できる

## 通知したい内容

- Bot 停止
- `/metrics` 取得失敗
- 日次損失が閾値を超えた
- 連敗数が閾値を超えた
- API エラー急増
- WebSocket 再接続多発

## 秘密情報の扱い

- Discord Webhook URL はコードに直書きしない
- compose 実行時は `DISCORD_WEBHOOK_URL` または `DISCORD_BOT_TOKEN` / `DISCORD_CHANNEL_ID` で注入する
- Webhook URL を使う場合は AWS Secrets Manager へ移せる

## 現在の実装

- `deploy/alertmanager/alertmanager.yml`
  - Alertmanager から `discord-relay` へ webhook
- `docker-compose.aws.yml`
  - `alertmanager`, `discord-relay` を追加
- `trading_bot.alerting.discord_relay`
  - Alertmanager payload を Discord 送信用メッセージへ変換
  - Webhook URL または Discord Bot Token + Channel ID を解決して送信
  - `/healthz` を公開

## 送信先の優先順位

1. `DISCORD_WEBHOOK_URL`
2. `DISCORD_WEBHOOK_SECRET_NAME`
3. `DISCORD_BOT_TOKEN` + `DISCORD_CHANNEL_ID`

Webhook URL が設定されていればそちらを優先します。Webhook を発行したくない場合は Bot Token とチャンネル ID だけで通知できます。
