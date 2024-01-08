from __future__ import annotations

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
        self.bond = None

        self.expired = False
        self.expiring_in = 20

    def set_bond(self, bond: CorporateBond) -> None:
        self.bond = bond

    def update(self) -> None:
        super().update()
        if not self.bankrupt and Time.now % self.update_freq == 0:
            W = 1 if np.random.random() > 0.5 else -1
            self.current_value += self.current_value * (self.mu + self.sigma * W)
            if self.current_value <= self.bankruptcy_value_thresh:
                self.current_value = self.bankruptcy_value_thresh
                self.bankrupt = True
        elif self.bankrupt:
            if self.expiring_in > 0:
                self.expiring_in -= 1
            else:
                self.expired = True

    def payout(self) -> float:
        if self.bankrupt and self.bond is not None:
            return 0
        else:
            return int(self.current_value)

    def is_expired(self) -> bool:
        return self.expired


class CorporateBond(Product):
    def __init__(self, company_stock: CompanyStock, **kwargs: Dict[str, float]) -> None:
        super().__init__(f"{company_stock.symbol}B")
        self.company_stock = company_stock
        self.company_stock.set_bond(self)
        self.par_value = kwargs.get("par_value", PAR_VALUE)
        self.coupon_payout = kwargs.get("coupon_payout", COUPON_PAYOUT)
        self.coupon_freq = kwargs.get("coupon_freq", COUPON_FREQ)
        self.maturity = kwargs.get("maturity", MATURITY)
        self.matured = False
        self.cached_payout = None

    def dividend(self) -> float:
        if (
            not self.matured
            and self.coupon_freq > 0
            and Time.now % self.coupon_freq == 0
            and not self.company_stock.bankrupt
        ):
            return self.coupon_payout
        return 0

    def payout(self) -> float:
        if self.cached_payout is None:
            if not self.company_stock.bankrupt and self.coupon_freq == 0:
                payout = self.par_value + self.coupon_payout
            elif not self.company_stock.bankrupt:
                payout = self.par_value
            else:
                bond_count = self.exchange.get_total_product_count(self.symbol)
                if bond_count > 0:
                    payout = min(
                        np.round(self.company_stock.current_value
                        * self.exchange.get_total_product_count(self.company_stock.symbol)
                        / bond_count, 2),
                        self.par_value,
                    )
                else:
                    return self.par_value
            if self.is_expired():
                self.cached_payout = payout
            return payout
        else:
            return self.cached_payout

    def is_expired(self) -> bool:
        return (
            self.maturity > -1 and Time.now >= self.maturity
        ) or self.company_stock.bankrupt
