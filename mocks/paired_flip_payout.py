import numpy as np

from trading_objects import Agent, Exchange, Product, Event
from market_simulation import MarketSimulation
from agents import ManualAgent


def generate_fact(thresh=0.5):
    return 2 * (np.random.random() < thresh) - 1


MAX_PAYOUT = 100


def fact_to_payout(fact):
    return MAX_PAYOUT * (fact + 1) // 2


SYMBOLS = ["A", "B"]
TICK_SIZE = 1
ITER = 300
DT = 0.1

FACT = generate_fact()
PAYOUT = fact_to_payout(FACT)

NUM_RETAIL_TRADERS = 20
RETAIL_PAYOUT_PRIOR_STRENGTH = 0.1
RETAIL_MIN_CONFIDENCE = 0.5
RETAIL_SIZING_RANGE = (1, 6)
RETAIL_ORDER_UPDATE_FREQ = 0.1


class PairedFlipProduct(Product):
    def __init__(self, symbol: str) -> None:
        super().__init__(symbol)

    def payout(self) -> None:
        return PAYOUT


class HedgeFund(Agent):
    def __init__(self) -> None:
        super().__init__()

        self.last_trades = {}
        self.opinion = FACT

    def register_exchange(self, exchange: Exchange) -> None:
        super().register_exchange(exchange)
        exchange.subscribe(self, self.process_event)

    def process_event(self, event: Event) -> None:
        if event.event_type == Event.TRADE:
            self.last_trades[event.symbol] = event.price

    def update(self) -> None:
        order_books = self.exchange.public_info()

        for symbol in order_books:
            bids = order_books[symbol].bids
            asks = order_books[symbol].asks

        return super().update()


class RetailTrader(Agent):
    def __init__(self) -> None:
        super().__init__()
        self.opinion = generate_fact(
            thresh=(
                0.5
                + (
                    RETAIL_PAYOUT_PRIOR_STRENGTH
                    if PAYOUT > 0
                    else -RETAIL_PAYOUT_PRIOR_STRENGTH
                )
            )
        )
        self.confidence = (
            np.random.random() * (1 - RETAIL_MIN_CONFIDENCE) + RETAIL_MIN_CONFIDENCE
        )
        self.expected_stock_value = self.confidence * fact_to_payout(self.opinion) + (
            1 - self.confidence
        ) * fact_to_payout(-self.opinion)

        self.sizing = np.random.randint(*RETAIL_SIZING_RANGE)

        self.symbol = SYMBOLS[np.random.randint(len(SYMBOLS))]

    def update(self) -> None:
        order_books = self.exchange.public_info()

        bids = order_books[self.symbol].bids
        asks = order_books[self.symbol].asks

        if len(bids) > 0 and len(asks) > 0:
            bid_order = bids[-1]
            ask_order = asks[-1]

            bid = bid_order.price
            ask = ask_order.price

            if np.random.random() < RETAIL_ORDER_UPDATE_FREQ:
                if self.opinion > 0:
                    if ask < self.expected_stock_value and ask - bid < 2 * TICK_SIZE:
                        self.cancel_all_open_orders()
                        self.bid(ask, ask_order.size, self.symbol, frames_to_expire=100)
                    elif (
                        bid + TICK_SIZE < self.expected_stock_value
                        and bid_order.id not in self.open_orders
                    ):
                        self.bid(
                            bid + TICK_SIZE,
                            self.sizing,
                            self.symbol,
                            frames_to_expire=100,
                        )
                else:
                    if bid > self.expected_stock_value and ask - bid < 2 * TICK_SIZE:
                        self.cancel_all_open_orders()
                        self.ask(bid, bid_order.size, self.symbol, frames_to_expire=100)
                    elif (
                        ask - TICK_SIZE > self.expected_stock_value
                        and ask_order.id not in self.open_orders
                    ):
                        self.cancel_all_open_orders()
                        self.ask(
                            ask - TICK_SIZE,
                            self.sizing,
                            self.symbol,
                            frames_to_expire=100,
                        )

        else:
            if self.opinion > 0 and len(bids) == 0:
                self.bid(1, self.sizing, self.symbol, frames_to_expire=100)
            elif self.opinion < 0 and len(asks) == 0:
                self.ask(99, self.sizing, self.symbol, frames_to_expire=100)

        return super().update()


def main() -> None:
    products = [PairedFlipProduct(symbol) for symbol in SYMBOLS]

    agents = [RetailTrader() for _ in range(NUM_RETAIL_TRADERS)]
    manual_agent = ManualAgent()

    sim = MarketSimulation(
        exchanges=Exchange(
            tick_size=TICK_SIZE,
        ),
        agents=[
            *agents,
            manual_agent,
        ],
        products=products,
        display_to_console=False,
        dt=DT,
        iter=ITER,
        save_results_path="results/paired_flip_payout",
    )
    sim.start()

    sim.connect_display(manual_agent.gui)
    manual_agent.gui.run()


if __name__ == "__main__":
    main()
