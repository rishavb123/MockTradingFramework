from typing import Union

from trading_objects import Agent, Order


class SingleExchangeFixedAgent(Agent):
    def __init__(
        self,
        fixed_bid: float,
        fixed_ask: float,
        fixed_size: int,
        fixed_symbol: Union[str, None] = None,
    ) -> None:
        super().__init__()
        self.fixed_bid = fixed_bid
        self.fixed_ask = fixed_ask
        self.fixed_size = fixed_size
        self.fixed_symbol = fixed_symbol

    def update(self) -> None:
        super().update()

        have_bid = False
        have_ask = False

        for order in self.open_orders:
            if order.dir == Order.BUY_DIR:
                have_bid = True
            elif order.dir == Order.SELL_DIR:
                have_ask = True

        if not have_bid:
            self.bid(
                price=self.fixed_bid, size=self.fixed_size, symbol=self.fixed_symbol
            )
        if not have_ask:
            self.ask(
                price=self.fixed_ask, size=self.fixed_size, symbol=self.fixed_symbol
            )
