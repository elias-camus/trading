FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY bots ./bots

RUN pip install --no-cache-dir .

EXPOSE 9464

CMD ["trading-bot", "run-paper-bot", "--config", "bots/cex_swing/config.aws.json"]
