from __future__ import annotations

from .common import PreprocessContext, build_trade_arrays


def build_trades_scatter_payload(context: PreprocessContext) -> dict[str, object]:
    trade_time, trade_price, trade_volume, trade_side = build_trade_arrays(
        context.trade_rows,
        context.batch.timestamp,
    )
    return {
        "trade_time": trade_time,
        "trade_price": trade_price,
        "trade_volume": trade_volume,
        "trade_side": trade_side,
    }
