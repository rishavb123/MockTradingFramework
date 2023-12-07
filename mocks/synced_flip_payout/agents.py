from typing import Union
import numpy as np

from trading_objects import Agent, Exchange, Event

from .config import *


class RetailInvestor(Agent):
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
        self.sizing = np.random.randint(*RETAIL_SIZING_RANGE)
        self.resting_order_expire_time = 100

    def update(self) -> None:
        order_books = self.exchange.public_info()

        cheapest_investment = None
        for symbol in order_books:
            if self.opinion == 1:
                asks = order_books[symbol].asks
                if len(asks) > 0 and (
                    cheapest_investment is None
                    or asks[-1].price < cheapest_investment[1]
                ):
                    cheapest_investment = symbol, asks[-1].price
            else:
                bids = order_books[symbol].bids
                if len(bids) > 0 and (
                    cheapest_investment is None
                    or bids[-1].price > cheapest_investment[1]
                ):
                    cheapest_investment = symbol, bids[-1].price

        if (
            cheapest_investment is not None
            and np.random.random() < RETAIL_ORDER_UPDATE_FREQ
        ):
            self.limit_order(
                dir=self.opinion,
                price=cheapest_investment[1],
                size=self.sizing,
                symbol=cheapest_investment[0],
                frames_to_expire=self.resting_order_expire_time,
            )


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

        symbol_picker = np.random.random()
        rng_ranges = np.cumsum(RETAIL_TRADER_SYMBOL_RATIO)

        symbol_idx = None

        for i in range(len(rng_ranges) - 1, -1, -1):
            if symbol_picker < rng_ranges[i]:
                symbol_idx = i

        self.symbol = SYMBOLS[symbol_idx]

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


class HedgeFund(Agent):
    def __init__(self) -> None:
        super().__init__()
        self.opinion = FACT
        self.confidence = 1
        self.payout = PAYOUT

        self.sizing = 100
        self.spread_to_cross = 4 * TICK_SIZE
        self.penny_by = 2 * TICK_SIZE
        self.take_all_orders_at = 20
        self.resting_order_expire_time = 100

        self.retail_mock_sizing = np.random.randint(*RETAIL_SIZING_RANGE)

        self.cur_spread = {}

    def register_exchange(self, exchange: Exchange) -> None:
        super().register_exchange(exchange)
        exchange.subscribe(self, self.process_event)

    def process_event(self, event: Event) -> None:
        if event.event_type == Event.TRADE:
            return
        if event.order_id in self.open_orders:
            return

        if self.opinion == 1:
            if event.event_type == Event.BID:
                if (
                    event.symbol not in self.cur_spread
                    or event.price < self.cur_spread[event.symbol][1]
                ):
                    self.bid(
                        price=event.price + self.penny_by,
                        size=2 * event.size,
                        symbol=event.symbol,
                        frames_to_expire=self.resting_order_expire_time,
                    )
            if (
                event.event_type == Event.ASK
                and event.symbol in self.cur_spread
                and self.cur_spread[event.symbol][1] - self.cur_spread[event.symbol][0]
                < self.spread_to_cross
            ):
                self.bid(price=event.price, size=event.size, symbol=event.symbol)
        else:
            if event.event_type == Event.ASK:
                if (
                    event.symbol not in self.cur_spread
                    or event.price > self.cur_spread[event.symbol][0]
                ):
                    self.ask(
                        price=event.price - self.penny_by,
                        size=2 * event.size,
                        symbol=event.symbol,
                        frames_to_expire=self.resting_order_expire_time,
                    )
            if (
                event.event_type == Event.BID
                and event.symbol in self.cur_spread
                and self.cur_spread[event.symbol][1] - self.cur_spread[event.symbol][0]
                < self.spread_to_cross
            ):
                self.ask(price=event.price, size=event.size, symbol=event.symbol)

    def update(self) -> None:
        order_books = self.exchange.public_info()

        for symbol in order_books:
            bids = order_books[symbol].bids
            asks = order_books[symbol].asks

            if len(bids) > 0 and len(asks) > 0:
                self.cur_spread[symbol] = bids[-1].price, asks[-1].price

            if self.exchange.time_remaining < self.take_all_orders_at:
                if self.opinion == 1:
                    self.bid(
                        price=MAX_PAYOUT - TICK_SIZE,
                        size=self.sizing,
                        symbol=symbol,
                        frames_to_expire=2,
                    )
                else:
                    self.ask(
                        price=TICK_SIZE,
                        size=self.sizing,
                        symbol=symbol,
                        frames_to_expire=2,
                    )

        cheapest_investment = None
        for symbol in order_books:
            if self.opinion == 1:
                asks = order_books[symbol].asks
                if len(asks) > 0 and (
                    cheapest_investment is None
                    or asks[-1].price < cheapest_investment[1]
                ):
                    cheapest_investment = symbol, asks[-1].price
            else:
                bids = order_books[symbol].bids
                if len(bids) > 0 and (
                    cheapest_investment is None
                    or bids[-1].price > cheapest_investment[1]
                ):
                    cheapest_investment = symbol, bids[-1].price

        if (
            cheapest_investment is not None
            and np.random.random() < RETAIL_ORDER_UPDATE_FREQ
        ):
            self.limit_order(
                dir=self.opinion,
                price=cheapest_investment[1],
                size=self.retail_mock_sizing,
                symbol=cheapest_investment[0],
                frames_to_expire=self.resting_order_expire_time,
            )

        return super().update()


class ArbAgent(Agent):
    def __init__(self) -> None:
        super().__init__()

    def update(self) -> None:
        order_books = self.exchange.public_info()

        markets = {}

        for symbol in order_books:
            bids = order_books[symbol].bids
            asks = order_books[symbol].asks

            if len(bids) > 0 and len(asks) > 0:
                markets[symbol] = (
                    bids[-1].price,
                    bids[-1].size,
                    asks[-1].price,
                    asks[-1].size,
                )

        if len(markets) > 0:
            highest_bid_symbol = max(markets, key=lambda symbol: markets[symbol][0])
            lowest_ask_symbol = min(markets, key=lambda symbol: markets[symbol][2])

            if markets[highest_bid_symbol][0] > markets[lowest_ask_symbol][2]:
                size = min(
                    markets[highest_bid_symbol][1], markets[lowest_ask_symbol][3]
                )
                self.ask(
                    price=markets[highest_bid_symbol][0] - 1,
                    size=size,
                    symbol=highest_bid_symbol,
                )
                self.bid(
                    price=markets[lowest_ask_symbol][2] + 1,
                    size=size,
                    symbol=lowest_ask_symbol,
                )

        return super().update()


class MarketMaker(Agent):
    def __init__(self) -> None:
        super().__init__()

        self.fair_value = 50  # Calculate a current fair for the stock
        self.edge = 5  # Place orders around the fair value
        self.close_out_positions_at = 50

    def update(self) -> None:
        if self.exchange.time_remaining < self.close_out_positions_at:
            self.holdings = self.exchange.get_account_holdings(self)
            pass  # Get rid of any positions now
