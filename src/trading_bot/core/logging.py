from __future__ import annotations

import logging
import sys


def setup_logging(bot_name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(f"trading_bot.{bot_name}")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                '{"ts":"%(asctime)s","level":"%(levelname)s",'
                '"logger":"%(name)s","msg":"%(message)s"}'
            )
        )
        logger.addHandler(handler)
    return logger
