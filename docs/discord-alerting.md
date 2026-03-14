# Discord 通知メモ

## 方針

このリポジトリの通知先は、まず Discord を標準にする。

理由:

- 個人運用で見やすい
- Bot ごとにチャンネルを分けやすい
- Webhook ベースでつなぎやすい

## 想定構成

最小構成:

- Prometheus
- Alertmanager
- Discord Webhook

または、軽量構成:

- Bot 側から直接 Discord Webhook へ送る

ただし運用上は、まず `Prometheus -> Alertmanager -> Discord` の方がよい。

理由:

- 重複通知をまとめやすい
- ルーティングを切りやすい
- critical / warning の出し分けがしやすい

## 通知したい内容

- Bot 停止
- `/metrics` 取得失敗
- 日次損失が閾値を超えた
- 連敗数が閾値を超えた
- API エラー急増
- WebSocket 再接続多発

## 秘密情報の扱い

- Discord Webhook URL はコードに直書きしない
- AWS Secrets Manager から読む
- `.env` への直書きは開発時だけにとどめる

## 次の実装方針

1. Alertmanager を compose に追加する
2. Discord Webhook を Secrets Manager から渡せるようにする
3. Alertmanager の receiver を Discord 向けに設定する
4. 重要アラートだけ先に通知する

