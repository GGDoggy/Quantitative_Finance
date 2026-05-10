from gui.plots.orderbook import build_orderbook_view
from gui.plots.trades import build_trade_volume_timeline_view, build_trades_scatter_view


PLOT_BUILDERS = {
    "orderbook": build_orderbook_view,
    "trades_scatter": build_trades_scatter_view,
    "trade_volume_timeline": build_trade_volume_timeline_view,
}
