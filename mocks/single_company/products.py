from typing import Dict
import numpy as np

from trading_objects import Product, Time
from .config import *


class CompanyStock(Product):
    def __init__(self, symbol: str, **kwargs: Dict[str, float]) -> None:
        super().__init__(symbol)
        self.mu = kwargs.get("mu", MU)
        self.sigma = kwargs.get("sigma", SIGMA)
        self.current_value = kwargs.get("value", STARTING_VALUE)
        self.bankruptcy_value_thresh = kwargs.get(
            "bankruptcy_value_thresh", BANKRUPTCY_VALUE_THRESH
        )
        self.update_freq = kwargs.get("update_freq", UPDATE_FREQ)
        self.bankrupt = False

    def update(self) -> None:
        super().update()
        if not self.bankrupt and Time.now % self.update_freq == 0:
            W = 1 if np.random.random() > 0.5 else -1
            self.current_value += self.current_value * (self.mu + self.sigma * W)
            if self.current_value < self.bankruptcy_value_thresh:
                self.current_value = 0
                self.bankrupt = True

    def payout(self) -> float:
        return int(self.current_value)


class CorporateBond(Product):
    def __init__(self, company_stock: CompanyStock, **kwargs: Dict[str, float]) -> None:
        super().__init__(f"{company_stock.symbol}B")
        self.company_stock = company_stock
        self.par_value = kwargs.get("par_value", PAR_VALUE)
        self.coupon_payout = kwargs.get("coupon_payout", COUPON_PAYOUT)
        self.coupon_freq = kwargs.get("coupon_freq", COUPON_FREQ)
        self.maturity = kwargs.get("maturity", MATURITY)
        self.matured = False

    def dividend(self) -> float:
        if (
            not self.matured
            and self.coupon_freq > 0
            and Time.now % self.coupon_freq == 0
            and self.company_stock.current_value > 0
        ):
            return self.coupon_payout
        return 0

    def payout(self) -> float:
        if self.company_stock.current_value > 0 and self.coupon_freq == 0:
            return self.par_value + self.coupon_payout
        elif self.company_stock.current_value > 0:
            return self.par_value
        return 0

    def is_expired(self) -> bool:
        return self.maturity > -1 and Time.now >= self.maturity
