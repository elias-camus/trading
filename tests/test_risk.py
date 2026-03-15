import unittest
from datetime import datetime, timedelta, timezone

from trading_bot.core.config import RiskConfig
from trading_bot.core.risk import RiskManager


class RiskManagerTest(unittest.TestCase):
    def test_position_limit_blocks_large_order(self) -> None:
        manager = RiskManager(
            RiskConfig(
                max_position_notional=100.0,
                max_daily_loss=50.0,
                max_consecutive_losses=2,
                min_order_interval_seconds=0,
            )
        )
        allowed, reason = manager.can_open_order(120.0)
        self.assertFalse(allowed)
        self.assertEqual(reason, "position_limit")

    def test_consecutive_losses_trigger_kill_switch(self) -> None:
        manager = RiskManager(
            RiskConfig(
                max_position_notional=1000.0,
                max_daily_loss=50.0,
                max_consecutive_losses=2,
                min_order_interval_seconds=0,
            )
        )
        manager.register_fill(order_notional=10.0, realized_pnl=-5.0)
        manager.flatten_position()
        manager.register_fill(order_notional=10.0, realized_pnl=-5.0)
        manager.flatten_position()

        allowed, reason = manager.can_open_order(10.0)
        self.assertFalse(allowed)
        self.assertEqual(reason, "consecutive_loss_limit")

    def test_daily_loss_limit_blocks(self) -> None:
        manager = RiskManager(
            RiskConfig(
                max_position_notional=1000.0,
                max_daily_loss=20.0,
                max_consecutive_losses=5,
                min_order_interval_seconds=0,
            )
        )
        manager.register_fill(order_notional=10.0, realized_pnl=-25.0)
        manager.flatten_position()

        allowed, reason = manager.can_open_order(10.0)
        self.assertFalse(allowed)
        self.assertEqual(reason, "daily_loss_limit")

    def test_min_order_interval_blocks(self) -> None:
        manager = RiskManager(
            RiskConfig(
                max_position_notional=1000.0,
                max_daily_loss=100.0,
                max_consecutive_losses=5,
                min_order_interval_seconds=30,
            )
        )
        manager.state.last_order_at = datetime.now(timezone.utc) - timedelta(seconds=10)

        allowed, reason = manager.can_open_order(10.0)
        self.assertFalse(allowed)
        self.assertEqual(reason, "min_order_interval")


if __name__ == "__main__":
    unittest.main()
