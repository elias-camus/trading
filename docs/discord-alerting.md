# Discord 通知メモ

## 方針

このリポジトリの通知先は、まず Discord を標準にする。

理由:

- 個人運用で見やすい
- Bot ごとにチャンネルを分けやすい
- Webhook ベースでつなぎやすい

## 想定構成

標準構成:

- Prometheus
- Alertmanager
- `discord-relay`
- Discord Webhook

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
- compose 実行時は `DISCORD_WEBHOOK_URL` で注入する
- live 化では AWS Secrets Manager へ移す

## 現在の実装

- `deploy/alertmanager/alertmanager.yml`
  - Alertmanager から `discord-relay` へ webhook
- `docker-compose.aws.yml`
  - `alertmanager`, `discord-relay` を追加
- `trading_bot.alerting.discord_relay`
  - Alertmanager payload を Discord 送信用メッセージへ変換
  - `/healthz` を公開

## 次の実装方針

1. `DISCORD_WEBHOOK_URL` を env 直書きから Secrets Manager 参照へ移す
2. severity ごとの文面整形を追加する
3. bot 名や venue 名を通知文面へ含める
4. 重要アラートだけ先に通知する
