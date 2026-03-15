# AWS EC2 配備メモ

## 結論

現段階では、MacBook 常駐より `EC2 1台 + Docker + systemd` の方が扱いやすい。

理由:

- 24時間稼働しやすい
- メトリクスを固定ポートで公開しやすい
- 再起動後の自動復帰が簡単
- 後から Prometheus や Grafana を足しやすい

このリポジトリでは、単体 Bot 常駐だけでなく `Bot + Prometheus + Grafana` の compose スタックも用意した。

## 重要な前提

この EC2 基盤は「どの取引所でもそのまま live で使う」前提ではない。

- 日本居住者向けの live 運用は国内登録業者優先
- 海外取引所はまず research 用、比較用、監視用として扱う
- レバレッジ系は商品提供可否と法規制を確認してから live 化する

## 推奨の最小構成

- EC2: `t3.small` 以上
- OS: Ubuntu 24.04 LTS か Amazon Linux 2023
- セキュリティグループ:
  - `22/tcp`: 自分のIPだけ許可
  - `9464/tcp`: 自分のIPだけ許可
  - `9090/tcp`: 必要なら自分のIPだけ許可
  - `9093/tcp`: 必要なら自分のIPだけ許可
  - `3000/tcp`: 必要なら自分のIPだけ許可
- IAM:
  - 最初は EC2 ロール最小権限
  - 後で Secrets Manager や CloudWatch を足す

## 費用感

基準日: 2026-03-14  
基準リージョン: `us-east-1`  
前提: Linux/Unix、オンデマンド、24時間365日 稼働、gp3 を 20GB

概算:

- `t3.micro`
  - インスタンス: 約 `0.0104 USD/時`
  - 月額計算: 約 `7.6 USD/月`
  - gp3 20GB を足すと: 約 `9.2 USD/月`
- `t3.small`
  - インスタンス: 約 `0.0209 USD/時`
  - 月額計算: 約 `15.3 USD/月`
  - gp3 20GB を足すと: 約 `16.9 USD/月`
- `t3a.small`
  - インスタンス: 約 `0.0188 USD/時`
  - 月額計算: 約 `13.7 USD/月`
  - gp3 20GB を足すと: 約 `15.3 USD/月`

判断:

- 紙上実行と監視だけなら、まずは `t3.micro` でも始められる
- 少し余裕を持って常駐させるなら `t3.small` が無難
- x86 のまま少し安くしたいなら `t3a.small` も有力

注意:

- 外向き通信量、CloudWatch Logs、Elastic IP、追加 EBS、スナップショットは別料金
- T3/T3a/T4g の Unlimited モードでは CPU クレジット超過時に追加課金がある
- Prometheus/Grafana を同居させるなら、`t3.micro` より `t3.small` の方が無難

## このリポジトリで使う設定

- 常駐向け設定: `bots/cex_swing/config.aws.json`
- メトリクスポート: `9464`
- Docker 起動時の公開ポート: `9464:9464`
- 監視スタック: `docker-compose.aws.yml`
- Prometheus 設定: `deploy/prometheus/prometheus.yml`
- Alertmanager 設定: `deploy/alertmanager/alertmanager.yml`
- Grafana: `3000`

`config.aws.json` は次の意図で作っている。

- `metrics_host=0.0.0.0`
- `metrics_port=9464`
- `max_iterations=0`
  - 無限ループで 24時間365日 常駐させる

## 初回セットアップ例

EC2 上で cloud-init を使うなら、起動時ユーザーデータに `deploy/cloud-init/ec2-bootstrap.yaml` の内容を入れる。

手動セットアップなら EC2 上で:

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
sudo mkdir -p /opt/trading
sudo chown -R ubuntu:ubuntu /opt/trading
```

コード配置後:

```bash
cd /opt/trading
docker build -t trading-bot:latest .
docker run --rm -p 9464:9464 -v /opt/trading/data:/app/data trading-bot:latest
```

確認:

```bash
curl http://127.0.0.1:9464/healthz
curl http://127.0.0.1:9464/metrics
```

監視込みで常駐する場合:

```bash
cd /opt/trading
docker compose -f docker-compose.aws.yml up -d --build
curl http://127.0.0.1:9090/-/ready
curl http://127.0.0.1:9093/-/ready
```

## systemd 常駐化

ユニットファイルの雛形を `deploy/systemd/trading-bot.service` に置いている。

監視込みで常駐する場合は `deploy/systemd/trading-stack.service` を使う。

配置例:

```bash
sudo cp deploy/systemd/trading-bot.service /etc/systemd/system/trading-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now trading-bot
sudo systemctl status trading-bot
```

compose スタック版:

```bash
sudo cp deploy/systemd/trading-stack.service /etc/systemd/system/trading-stack.service
sudo systemctl daemon-reload
sudo systemctl enable --now trading-stack
sudo systemctl status trading-stack
```

## 運用上の注意

- まずは紙上実行のまま回す
- API キーはまだコンテナに入れない
- `9464` は全世界公開せず、自分のIPに絞る
- `9090`, `9093`, `3000` も全世界公開しない
- 実取引用 Bot を動かす前に CloudWatch Logs か Loki 系へログ転送を足す
- 本番では `/metrics` と取引系ポートを分離する

## 次にやること

- CEX の実データ adapter を追加する
- Prometheus で `9464/metrics` を scrape する
- Grafana で `loop_latency_ms`, `risk_blocks_total`, `daily_realized_pnl` を可視化する
- Secrets Manager から API キーを読む構成にする
- Grafana の初期パスワードはデフォルトのまま使わず変更する
- `DISCORD_WEBHOOK_URL` を env 直書きから Secrets Manager 参照へ移す

基盤完成までの全体 TODO は [TODO.md](/Users/toshikikobayashi/Repositories/trading/TODO.md) を参照。

## 更新を流し込む方法

ローカルから EC2 へ更新して再起動するために `scripts/deploy_ec2.sh` を追加している。

```bash
cd /Users/toshikikobayashi/Repositories/trading
chmod +x scripts/deploy_ec2.sh
./scripts/deploy_ec2.sh ubuntu@<EC2のIP>
```

このスクリプトは次を行う。

- `rsync` で `/opt/trading` へ反映
- EC2 上で Docker イメージを再ビルド
- systemd サービスを更新して再起動

compose スタック版:

```bash
cd /Users/toshikikobayashi/Repositories/trading
chmod +x scripts/deploy_stack_ec2.sh
./scripts/deploy_stack_ec2.sh ubuntu@<EC2のIP>
```

こちらは Bot, Prometheus, Grafana をまとめて更新する。
