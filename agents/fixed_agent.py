from trading_objects import Agent


class FixedAgent(Agent):
    def __init__(self, fixed_bid: float, fixed_ask: float, fixed_size: int) -> None:
        super().__init__()
        self.fixed_bid = fixed_bid
        self.fixed_ask = fixed_ask
        self.fixed_size = fixed_size

    def update(self):
        for order in self.open_orders:
            self.cancel_order(order)

        self.bid(price=self.fixed_bid, size=self.fixed_size)
        self.ask(price=self.fixed_ask, size=self.fixed_size)
