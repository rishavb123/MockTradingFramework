import numpy as np

from trading_objects import Agent, Time
from .products import CompanyStock


class RandomBiasedAgent(Agent):
    def __init__(self, company_stock: CompanyStock) -> None:
        super().__init__()
        self.bias = np.random.random() * 5 - 2.5
        self.product = company_stock
        self.edge = 0.1
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
