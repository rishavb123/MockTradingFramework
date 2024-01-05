import numpy as np

from trading_objects import Agent, Time

from .config import ITER
from .products import CompanyStock, CorporateBond


class BiasedStockAgent(Agent):
    def __init__(self, company_stock: CompanyStock) -> None:
        super().__init__()
        self.bias = np.random.random() * 10 - 5
        self.product = company_stock
        self.edge = 2
        self.sizing = np.random.randint(1, 30)
        self.place_orders_at = np.random.randint(self.product.update_freq)

    def update(self) -> None:
        super().update()

        if self.product.bankrupt:
            self.cancel_all_open_orders()
        elif Time.now % self.product.update_freq == self.place_orders_at:
            self.bid(
                price=max(0, self.product.current_value - self.edge + self.bias),
                size=self.sizing,
                symbol=self.product.symbol,
                frames_to_expire=self.product.update_freq,
            )
            self.ask(
                price=self.product.current_value + self.edge + self.bias,
                size=self.sizing,
                symbol=self.product.symbol,
                frames_to_expire=self.product.update_freq,
            )


class OptimisticBiasedBondAgent(Agent):
    def __init__(self, bond: CorporateBond) -> None:
        super().__init__()
        self.bias = np.random.random() * 10 - 5
        self.bond = bond
        self.edge = 2
        self.sizing = np.random.randint(1, 30)
        self.order_freq = 50
        self.place_orders_at = np.random.randint(self.order_freq)

    def estimate_fair_value_assuming_no_default(self) -> float:
        if self.bond.coupon_freq == 0:
            return self.bond.coupon_payout + self.bond.par_value
        else:
            if self.bond.maturity == -1:
                end_time = ITER
            else:
                end_time = self.bond.maturity

            return (
                self.bond.par_value
                + self.bond.coupon_payout
                * (end_time - Time.now)
                // self.bond.coupon_freq
            )

    def update(self) -> None:
        super().update()

        if self.bond.company_stock.bankrupt or self.bond.matured:
            self.cancel_all_open_orders()
        elif Time.now % self.order_freq == self.place_orders_at:
            fair = self.estimate_fair_value_assuming_no_default()
            self.bid(
                max(0, fair - self.edge + self.bias),
                size=self.sizing,
                symbol=self.bond.symbol,
                frames_to_expire=self.order_freq,
            )
            self.ask(
                max(0, fair + self.edge + self.bias),
                size=self.sizing,
                symbol=self.bond.symbol,
                frames_to_expire=self.order_freq,
            )
