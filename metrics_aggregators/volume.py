from typing import Any, Dict, List
import numpy as np
import matplotlib.pyplot as plt

from metrics import MetricsAggregator, MetricsPlots
from trading_objects import Product


class VolumeAggregator(MetricsAggregator):
    def __init__(self, products: List[Product], window_size=50) -> None:
        super().__init__()
        self.products = {p.symbol: p for p in products}
        self.product_volume_deltas = {symbol: [] for symbol in self.products}
        self.last_product_volume = {symbol: 0 for symbol in self.products}
        self.window_size = window_size

    def snapshot(self) -> Dict[str, Any]:
        metrics = {}
        for symbol in self.products:
            product_volume = self.products[symbol].volume
            self.product_volume_deltas[symbol].append(
                product_volume - self.last_product_volume[symbol]
            )
            self.last_product_volume[symbol] = product_volume
            metrics[f"{symbol}_volume_per_tick"] = np.mean(
                self.product_volume_deltas[symbol][-self.window_size :]
            )
        return metrics


class VolumePlot(MetricsPlots):
    def __init__(self, symbols: List[str]) -> None:
        self.symbols = symbols
        super().__init__(
            f"volume_per_tick",
            [f"{symbol}_volume_per_tick" for symbol in self.symbols] + ["time"],
            self.volume_plot,
        )

    def volume_plot(self, **kwargs):
        symbol_volumes = [
            kwargs[f"{symbol}_volume_per_tick"] for symbol in self.symbols
        ]

        times = kwargs["time"]

        for symbol, volume_per_tick in zip(self.symbols, symbol_volumes):
            plt.plot(times, volume_per_tick, label=symbol)

        plt.xlabel("Time")
        plt.ylabel("Volume Per Tick")

        plt.title(f"Volume Per Tick")

        plt.legend()
