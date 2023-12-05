from typing import Any, Callable, Dict, List
from metrics import MetricsAggregator, MetricsPlots
from trading_objects import Exchange, Product
import matplotlib.pyplot as plt
import numpy as np


class PriceAggregator(MetricsAggregator):
    def __init__(self, exchange: Exchange, products: List[Product]) -> None:
        super().__init__()
        self.exchange = exchange
        self.products = products

    def snapshot(self) -> Dict[str, Any]:
        order_books = self.exchange.public_info()

        metrics = {}

        for product in self.products:
            symbol = product.symbol

            bids = order_books[symbol].bids
            asks = order_books[symbol].asks

            bid = np.nan
            bid_size = np.nan
            if len(bids) > 0:
                bid = bids[-1].price
                bid_size = bids[-1].size
                cur_idx = 2
                while len(bids) - cur_idx > -1 and bids[-cur_idx].price == bid:
                    bid_size += bids[-cur_idx].size
                    cur_idx += 1

            ask = np.nan
            ask_size = np.nan
            if len(asks) > 0:
                ask = asks[-1].price
                ask_size = asks[-1].size
                cur_idx = 2
                while len(asks) - cur_idx > -1 and asks[-cur_idx].price == ask:
                    ask_size += asks[-cur_idx].size
                    cur_idx += 1

            last_traded_price = np.nan
            if len(product.trades) > 0:
                last_traded_price = product.trades[-1].price

            metrics = metrics | {
                f"{symbol}_bid": bid,
                f"{symbol}_bid_size": bid_size,
                f"{symbol}_ask": ask,
                f"{symbol}_ask_size": ask_size,
                f"{symbol}_last_traded_price": last_traded_price,
            }

        return metrics


class PricePlot(MetricsPlots):
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(
            f"{symbol}_prices",
            [
                f"{symbol}_bid",
                f"{symbol}_bid_size",
                f"{symbol}_ask",
                f"{symbol}_ask_size",
                f"{symbol}_last_traded_price",
            ],
            self.price_plot,
        )

    def price_plot(self, **kwargs):
        bid = kwargs[f"{self.symbol}_bid"]
        bid_size = kwargs[f"{self.symbol}_bid_size"]
        ask = kwargs[f"{self.symbol}_ask"]
        ask_size = kwargs[f"{self.symbol}_ask_size"]
        last_traded_price = kwargs[f"{self.symbol}_last_traded_price"]

        times = np.arange(len(bid))

        mid = (bid + ask) / 2
        swmid = (bid * ask_size + ask * bid_size) / (bid_size + ask_size)

        plt.plot(times, bid, label="bid")
        plt.plot(times, ask, label="ask")
        plt.plot(times, last_traded_price, label="last_traded_price")
        plt.plot(times, mid, label="mid")
        plt.plot(times, swmid, label="swmid")

        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.title(f"{self.symbol} Prices")

        plt.legend()
