from typing import Dict
import numpy as np

from trading_objects import Product, Time
from .config import MU, SIGMA


class CompanyStock(Product):
    def __init__(self, symbol: str, **kwargs: Dict[str, float]) -> None:
        super().__init__(symbol)
        self.mu = kwargs.get("mu", MU)
        self.sigma = kwargs.get("sigma", SIGMA)
        self.current_value = kwargs.get("value", 50)
        self.bankruptcy_value_thresh = kwargs.get(
            "bankruptcy_value_thresh", self.current_value * np.random.random() * 0.1
        )
        self.update_freq = kwargs.get("update_freq", 10)
        self.bankrupt = False

    def update(self) -> None:
        super().update()
        if not self.bankrupt and Time.now % self.update_freq == 0:
            W = 1 if np.random.random() > 0.5 else -1
            self.current_value += self.current_value * (self.mu + self.sigma * W)
            if self.current_value < self.bankruptcy_value_thresh:
                self.current_value = 0
                self.bankrupt = True

    def payout(self) -> None:
        return int(self.current_value)
    