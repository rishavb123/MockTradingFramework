from trading_objects import Agent


class DumbAgent(Agent):
    def __init__(self) -> None:
        super().__init__()

    def update(self):
        for order in self.open_orders:
            self.cancel_order(order)

        self.bid(price=5, size=100)
        self.ask(price=15, size=100)
