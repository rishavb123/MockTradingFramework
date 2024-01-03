import numpy as np

from trading_objects import Agent, Exchange, Event, Account
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
        self.resting_order_expiration_time = 100
        self.order_price_margin_to_ensure_lift = 3

    def update(self) -> None:
        super().update()

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
                price=cheapest_investment[1]
                + self.opinion * TICK_SIZE * self.order_price_margin_to_ensure_lift,
                size=self.sizing,
                symbol=cheapest_investment[0],
                frames_to_expire=self.resting_order_expiration_time,
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
        self.resting_order_expiration_time = 100
        self.edge = 5

    def update(self) -> None:
        super().update()

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
                        self.bid(
                            ask,
                            ask_order.size,
                            self.symbol,
                            frames_to_expire=self.resting_order_expiration_time,
                        )
                    elif (
                        bid + TICK_SIZE < self.expected_stock_value
                        and bid_order.id not in self.open_orders
                    ):
                        self.bid(
                            bid + TICK_SIZE,
                            self.sizing,
                            self.symbol,
                            frames_to_expire=self.resting_order_expiration_time,
                        )
                else:
                    if bid > self.expected_stock_value and ask - bid < 2 * TICK_SIZE:
                        self.cancel_all_open_orders()
                        self.ask(
                            bid,
                            bid_order.size,
                            self.symbol,
                            frames_to_expire=self.resting_order_expiration_time,
                        )
                    elif (
                        ask - TICK_SIZE > self.expected_stock_value
                        and ask_order.id not in self.open_orders
                    ):
                        self.cancel_all_open_orders()
                        self.ask(
                            ask - TICK_SIZE,
                            self.sizing,
                            self.symbol,
                            frames_to_expire=self.resting_order_expiration_time,
                        )
        else:
            if self.opinion > 0 and len(bids) == 0:
                self.bid(
                    1,
                    self.sizing,
                    self.symbol,
                    frames_to_expire=self.resting_order_expiration_time,
                )
            elif self.opinion < 0 and len(asks) == 0:
                self.ask(
                    99,
                    self.sizing,
                    self.symbol,
                    frames_to_expire=self.resting_order_expiration_time,
                )


class BandwagonInvestor(RetailInvestor):
    def __init__(self) -> None:
        super().__init__()

    def update(self) -> None:
        order_books = self.exchange.public_info()

        mid_sum = 0
        mid_count = 0

        for symbol in order_books:
            bids = order_books[symbol].bids
            asks = order_books[symbol].asks

            if len(bids) > 0 and len(asks) > 0:
                mid = (bids[-1].price + asks[-1].price) / 2
                mid_sum += mid
                mid_count += 1

        if mid_count > 0:
            if mid_sum > 50 * mid_count:
                self.opinion = 1
            else:
                self.opinion = -1

        super().update()


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
        self.resting_order_expiration_time = 100

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
                        frames_to_expire=self.resting_order_expiration_time,
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
                        frames_to_expire=self.resting_order_expiration_time,
                    )
            if (
                event.event_type == Event.BID
                and event.symbol in self.cur_spread
                and self.cur_spread[event.symbol][1] - self.cur_spread[event.symbol][0]
                < self.spread_to_cross
            ):
                self.ask(price=event.price, size=event.size, symbol=event.symbol)

    def update(self) -> None:
        super().update()

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
                frames_to_expire=self.resting_order_expiration_time,
            )


class ArbAgent(Agent):
    def __init__(self) -> None:
        super().__init__()
        self.margin_to_ensure_trade = 1
        self.resting_order_expiration_time = 2

    def get_total_holding(self) -> int:
        self.holdings = self.exchange.get_account_holdings(self)
        total_holding = sum(self.holdings.values()) - self.holdings[Account.CASH_SYM]
        return total_holding

    def close_positions(self) -> None:
        order_books = self.exchange.public_info()
        self.holdings = self.exchange.get_account_holdings(self)
        total_holding = self.get_total_holding()

        if total_holding == 0:
            self.cancel_all_open_orders()
            return

        best_price = None

        for symbol in order_books:
            bids = order_books[symbol].bids
            asks = order_books[symbol].asks

            if total_holding > 0:
                if len(asks) > 0 and (
                    best_price is None or asks[-1].price < best_price[1]
                ):
                    best_price = symbol, asks[-1].price, asks[-1].size
            else:
                if len(bids) > 0 and (
                    best_price is None or bids[-1].price > best_price[1]
                ):
                    best_price = symbol, bids[-1].price, bids[-1].size

        if best_price is not None:
            if total_holding < 0:
                self.bid(
                    price=best_price[1] + 5 * TICK_SIZE,
                    size=min(best_price[2], -total_holding),
                    symbol=best_price[0],
                    frames_to_expire=self.resting_order_expiration_time,
                )
            else:
                self.ask(
                    price=best_price[1] - 5 * TICK_SIZE,
                    size=min(best_price[2], total_holding),
                    symbol=best_price[0],
                    frames_to_expire=self.resting_order_expiration_time,
                )

    def update(self) -> None:
        super().update()

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
                    price=markets[highest_bid_symbol][0]
                    - self.margin_to_ensure_trade * TICK_SIZE,
                    size=size,
                    symbol=highest_bid_symbol,
                    frames_to_expire=self.resting_order_expiration_time,
                )
                self.bid(
                    price=markets[lowest_ask_symbol][2]
                    + self.margin_to_ensure_trade * TICK_SIZE,
                    size=size,
                    symbol=lowest_ask_symbol,
                    frames_to_expire=self.resting_order_expiration_time,
                )
            elif self.exchange.time_remaining % 5 == 0:
                self.close_positions()


class MarketMaker(Agent):
    def __init__(self) -> None:
        super().__init__()

        self.sizing = 10
        self.close_out_positions_at = 50
        self.price_margin_on_close = 5
        self.resting_order_expiration_time = 2
        self.min_edge = 5 * TICK_SIZE
        self.holding_adjustment_mult_range = 0.25

    def register_exchange(self, exchange: Exchange) -> None:
        super().register_exchange(exchange)

        self.fairs = {k: 50 for k in self.exchange.symbols}

        self.tight_market_mids = {k: [] for k in self.exchange.symbols}
        self.tight_market_max_spread = 5

    def limit_order(
        self,
        dir: int,
        price: float,
        size: int,
        symbol: str | None = None,
        exchange_name: str | None = None,
        frames_to_expire: int | None = None,
    ) -> int:
        return super().limit_order(
            dir, price, size, symbol, exchange_name, frames_to_expire
        )

    def get_total_holding(self) -> int:
        self.holdings = self.exchange.get_account_holdings(self)
        total_holding = sum(self.holdings.values()) - self.holdings[Account.CASH_SYM]
        return total_holding

    def clip(self, x: float) -> float:
        return min(max(x, 0), MAX_PAYOUT)

    def close_positions(self) -> None:
        order_books = self.exchange.public_info()
        self.holdings = self.exchange.get_account_holdings(self)
        total_holding = self.get_total_holding()

        if total_holding == 0:
            self.cancel_all_open_orders()
            return

        best_price = None

        for symbol in order_books:
            bids = order_books[symbol].bids
            asks = order_books[symbol].asks

            if total_holding > 0:
                if len(asks) > 0 and (
                    best_price is None or asks[-1].price < best_price[1]
                ):
                    best_price = symbol, asks[-1].price, asks[-1].size
            else:
                if len(bids) > 0 and (
                    best_price is None or bids[-1].price > best_price[1]
                ):
                    best_price = symbol, bids[-1].price, bids[-1].size

        if best_price is not None:
            if total_holding < 0:
                self.bid(
                    price=best_price[1] + 5 * TICK_SIZE,
                    size=min(best_price[2], -total_holding),
                    symbol=best_price[0],
                    frames_to_expire=self.resting_order_expiration_time,
                )
            else:
                self.ask(
                    price=best_price[1] - 5 * TICK_SIZE,
                    size=min(best_price[2], total_holding),
                    symbol=best_price[0],
                    frames_to_expire=self.resting_order_expiration_time,
                )

    def update_fair_value(self):
        order_books = self.exchange.public_info()
        total_holding = self.get_total_holding()

        mult = 1

        if total_holding != 0:
            mult = (
                self.holding_adjustment_mult_range / (1 + np.exp(total_holding / 5))
                + 1
                - self.holding_adjustment_mult_range / 2
            )

        for symbol in order_books:
            fair_estimators = []

            bids = order_books[symbol].bids
            asks = order_books[symbol].asks

            if len(bids) > 0 and len(asks) > 0:
                bid_prices = np.array([bid.price for bid in bids])
                bid_sizes = np.array([bid.size for bid in bids])
                ask_prices = np.array([ask.price for ask in asks])
                ask_sizes = np.array([ask.size for ask in asks])

                spread = ask_prices[-1] - bid_prices[-1]

                mid = (bid_prices[-1] + ask_prices[-1]) / 2
                fair_estimators.append(mid)

                buy_side_mean = np.mean(bid_prices[-5:])
                buy_side_volume = np.sum(bid_sizes[-5:])

                sell_side_mean = np.mean(ask_prices[-5:])
                sell_side_volume = np.sum(ask_sizes[-5:])

                swmid = (
                    buy_side_mean * sell_side_volume + sell_side_mean * buy_side_volume
                ) / (buy_side_volume + sell_side_volume)
                fair_estimators.append(swmid)

                if spread <= self.tight_market_max_spread * TICK_SIZE:
                    self.tight_market_mids[symbol].append(mid)

            if len(self.tight_market_mids[symbol]) > 0:
                self.tight_market_mids[symbol] = self.tight_market_mids[symbol][-20:]
                tight_market_estimator = np.mean(self.tight_market_mids[symbol])
                fair_estimators.append(tight_market_estimator)

            if len(fair_estimators) > 0:
                self.fairs[symbol] = np.mean(fair_estimators) * mult

    def provide_liquidity(self):
        order_books = self.exchange.public_info()

        for symbol in order_books:
            bids = order_books[symbol].bids
            asks = order_books[symbol].asks

            if len(bids) > 0 and len(asks) > 0:
                bid_prices = np.array([bid.price for bid in bids])
                ask_prices = np.array([ask.price for ask in asks])

                spread = ask_prices[-1] - bid_prices[-1]

                edge = max(spread * 0.4, self.min_edge)
                if not bids[-1].id in self.open_orders:
                    self.bid(
                        price=self.clip(self.fairs[symbol] - edge),
                        size=self.sizing,
                        symbol=symbol,
                        frames_to_expire=self.resting_order_expiration_time,
                    )
                if not asks[-1].id in self.open_orders:
                    self.ask(
                        price=self.clip(self.fairs[symbol] + edge),
                        size=self.sizing,
                        symbol=symbol,
                        frames_to_expire=self.resting_order_expiration_time,
                    )

            else:
                self.bid(
                    price=0,
                    size=self.sizing,
                    symbol=symbol,
                    frames_to_expire=self.resting_order_expiration_time,
                )
                self.ask(
                    price=MAX_PAYOUT,
                    size=self.sizing,
                    symbol=symbol,
                    frames_to_expire=self.resting_order_expiration_time,
                )

    def update(self) -> None:
        super().update()
        if self.exchange.time_remaining < self.close_out_positions_at:
            if self.exchange.time_remaining % 3 == 0:
                self.close_positions()
        else:
            self.update_fair_value()
            self.provide_liquidity()


class WideMaker(Agent):
    def __init__(self) -> None:
        super().__init__()

        self.margin = 2
        self.sizing = 100
        self.stop_time_remaining = 150

    def update(self) -> None:
        super().update()
        if (
            len(self.open_orders) < 2 * len(SYMBOLS)
            and self.exchange.time_remaining > self.stop_time_remaining
        ):
            self.cancel_all_open_orders()
            for symbol in SYMBOLS:
                self.bid(self.margin, self.sizing, symbol)
                self.ask(MAX_PAYOUT - self.margin, self.sizing, symbol)
        elif self.exchange.time_remaining < self.stop_time_remaining:
            self.cancel_all_open_orders()
