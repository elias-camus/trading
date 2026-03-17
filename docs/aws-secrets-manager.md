# AWS Secrets Manager 連携メモ

## 概要

このリポジトリでは、取引所 API キーと Discord 通知用の Webhook URL を環境変数へ直書きせず、AWS Secrets Manager から取得できます。

対象:

- `credentials.provider = "aws_secrets_manager"` の取引所認証情報
- `DISCORD_WEBHOOK_SECRET_NAME` を使う Discord Webhook URL

## シークレット名の命名規則

例:

- `trading-bot/bitflyer`
- `trading-bot/binance`
- `trading-bot/discord-webhook`

`trading-bot/<用途>` の形で揃えると、IAM の resource 制限と運用時の識別がしやすいです。

## 取引所 API キーの JSON 形式

Secrets Manager の `SecretString` は JSON を推奨します。

```json
{
  "api_key": "YOUR_API_KEY",
  "api_secret": "YOUR_API_SECRET"
}
```

登録イメージ:

```bash
aws secretsmanager create-secret \
  --name trading-bot/bitflyer \
  --secret-string '{"api_key":"YOUR_API_KEY","api_secret":"YOUR_API_SECRET"}' \
  --region ap-northeast-1
```

## credentials セクションの設定例

```json
{
  "credentials": {
    "bitflyer": {
      "provider": "aws_secrets_manager",
      "secret_name": "trading-bot/bitflyer",
      "region": "ap-northeast-1"
    }
  }
}
```

`execution.credentials_ref` でこの `bitflyer` を参照すると、実行時に Secrets Manager から `api_key` と `api_secret` を解決します。

## Discord 通知の使い方

`discord_relay` は次の優先順位で送信先を解決します。

1. `DISCORD_WEBHOOK_URL`
2. `DISCORD_WEBHOOK_SECRET_NAME`
3. `DISCORD_BOT_TOKEN` + `DISCORD_CHANNEL_ID`

`DISCORD_WEBHOOK_URL` または `DISCORD_WEBHOOK_SECRET_NAME` があれば Webhook モードで送ります。Webhook がなく、`DISCORD_BOT_TOKEN` と `DISCORD_CHANNEL_ID` の両方があれば Bot モードで `POST /api/v10/channels/{channel_id}/messages` を使って送ります。

Secrets Manager を使う場合の `SecretString` は次の JSON を推奨します。

```json
{
  "webhook_url": "https://discord.com/api/webhooks/..."
}
```

設定例:

```bash
export DISCORD_WEBHOOK_SECRET_NAME=trading-bot/discord-webhook
export AWS_REGION=ap-northeast-1
```

OpenClaw の既存 Discord Bot を使う場合は Webhook URL を発行せず、OpenClaw が動いているサーバーで次を設定します。

```bash
export DISCORD_BOT_TOKEN=YOUR_OPENCLAW_BOT_TOKEN
export DISCORD_CHANNEL_ID=123456789012345678
```

- `DISCORD_BOT_TOKEN`: サーバー上で既に運用している Discord Bot の token
- `DISCORD_CHANNEL_ID`: 通知を受けたい Discord チャンネル ID

`docker-compose.aws.yml` で渡す場合は次のように `.env` か shell 環境変数へ設定します。

```bash
export DISCORD_WEBHOOK_URL=
export DISCORD_WEBHOOK_SECRET_NAME=
export DISCORD_BOT_TOKEN=YOUR_OPENCLAW_BOT_TOKEN
export DISCORD_CHANNEL_ID=123456789012345678
export AWS_REGION=ap-northeast-1
docker compose -f docker-compose.aws.yml up -d --build
```

Webhook URL を使う場合は `DISCORD_WEBHOOK_URL` または `DISCORD_WEBHOOK_SECRET_NAME` のどちらかだけ設定すれば十分です。Webhook と Bot Token の両方を入れた場合は Webhook が優先されます。

## IAM 最小権限例

Secrets Manager の読み取りだけに絞るなら、EC2 ロールや task role には `secretsmanager:GetSecretValue` のみを付与します。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": [
        "arn:aws:secretsmanager:ap-northeast-1:<ACCOUNT_ID>:secret:trading-bot/bitflyer*",
        "arn:aws:secretsmanager:ap-northeast-1:<ACCOUNT_ID>:secret:trading-bot/discord-webhook*"
      ]
    }
  ]
}
```

ワイルドカードは Secrets Manager の ARN 末尾サフィックス対策です。対象シークレットを増やす場合も `trading-bot/` 配下に揃えると制御しやすくなります。
