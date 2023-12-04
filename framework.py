from __future__ import annotations

from typing import Union, List, Dict


class Time:
    now = 0

    @staticmethod
    def incr_time():
        Time.now += 1


class SimulationObject:
    last_id = -1
    __objects = {}

    def __init__(self) -> None:
        self.created_at = Time.now
        self.id = self.__class__.generate_id()
        self.global_id = f"{self.__class__.__name__.lower()}{self.id}"
        SimulationObject.__objects[self.global_id] = self

    def update(self) -> None:
        pass

    def display_str(self) -> str:
        return self.global_id

    @classmethod
    def generate_id(cls) -> int:
        cls.last_id += 1
        return cls.last_id

    @staticmethod
    def get_object(global_id: str) -> SimulationObject:
        return SimulationObject.__objects.get(global_id, None)


class Order(SimulationObject):
    DISPLAY_COLUMN_WIDTH = 7
    DISPLAY_COLUMN_MARGIN = 3

    BUY_DIR = 1
    SELL_DIR = -1

    margin = DISPLAY_COLUMN_MARGIN * " "

    def __init__(
        self,
        sender: Agent,
        dir: int,
        price: float,
        size: int,
        frames_to_expire: Union[int, None] = None,
    ) -> None:
        super().__init__()

        self.sender = sender
        self.dir = dir
        self.price = price
        self.size = size
        self.frames_to_expire = frames_to_expire
        self.expired = frames_to_expire == 0

    def update(self) -> None:
        if self.frames_to_expire is None:
            self.frames_to_expire -= 1
            if self.frames_to_expire <= 0:
                self.expired = True

    def filled_or_expired(self) -> bool:
        return self.size == 0 or self.expired

    def is_bid(self) -> bool:
        return self.dir == Order.BUY_DIR

    def is_ask(self) -> bool:
        return self.dir == Order.SELL_DIR

    def display_str(self) -> str:
        frames_to_expire = (
            "" if self.frames_to_expire is None else self.frames_to_expire
        )

        return (
            f"{self.id          :<{Order.DISPLAY_COLUMN_WIDTH}}{Order.margin}"
            f"{self.price       :<{Order.DISPLAY_COLUMN_WIDTH}}{Order.margin}"
            f"{self.size        :<{Order.DISPLAY_COLUMN_WIDTH}}{Order.margin}"
            f"{frames_to_expire :<{Order.DISPLAY_COLUMN_WIDTH}}{Order.margin}\n"
        )

    @staticmethod
    def display_header_str(dir: int) -> str:
        price_label = "Bid" if dir == Order.BUY_DIR else "Ask"
        return (
            f"{'ID'        :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}"
            f"{price_label :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}"
            f"{'Size'      :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}"
            f"{'Expiring'  :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}\n"
        )


class OrderBook(SimulationObject):
    def __init__(self, symbol: str, exchange: Exchange) -> None:
        super().__init__()

        self.bids = []
        self.asks = []
        self.symbol = symbol
        self.exchange = exchange

        self._orders_to_place = []
        self._orders_to_cancel = []

    def __place_orders(self, *orders: List[Order]) -> None:
        # Place Bids
        bids_to_place = sorted(
            [order for order in orders if order.is_bid()],
            key=lambda order: order.price,
        )

        bids_to_place_idx = 0
        cur_bid_idx = 0
        new_bids = []

        while cur_bid_idx < len(self.bids) and bids_to_place_idx < len(bids_to_place):
            if bids_to_place[bids_to_place_idx].price <= self.bids[cur_bid_idx].price:
                new_bids.append(bids_to_place[bids_to_place_idx])
                bids_to_place_idx += 1
            else:
                new_bids.append(self.bids[cur_bid_idx])
                cur_bid_idx += 1

        while bids_to_place_idx < len(bids_to_place):
            new_bids.append(bids_to_place[bids_to_place_idx])
            bids_to_place_idx += 1
        while cur_bid_idx < len(self.bids):
            new_bids.append(self.bids[cur_bid_idx])
            cur_bid_idx += 1

        self.bids = new_bids

        # Place Asks
        asks_to_place = sorted(
            [order for order in orders if order.is_ask()],
            key=lambda order: order.price,
            reverse=True,
        )

        asks_to_place_idx = 0
        cur_ask_idx = 0
        new_asks = []

        while cur_ask_idx < len(self.asks) and asks_to_place_idx < len(asks_to_place):
            if asks_to_place[asks_to_place_idx].price >= self.asks[cur_ask_idx].price:
                new_asks.append(asks_to_place[asks_to_place_idx])
                asks_to_place_idx += 1
            else:
                new_asks.append(self.asks[cur_ask_idx])
                cur_ask_idx += 1

        while asks_to_place_idx < len(asks_to_place):
            new_asks.append(asks_to_place[asks_to_place_idx])
            asks_to_place_idx += 1
        while cur_ask_idx < len(self.asks):
            new_asks.append(self.asks[cur_ask_idx])
            cur_ask_idx += 1

        self.asks = new_asks

    def __match_orders(self) -> None:
        while (
            len(self.bids) > 0
            and len(self.asks) > 0
            and self.bids[-1].price >= self.asks[-1].price
        ):
            matched_bid = self.bids[-1]
            matched_ask = self.asks[-1]
            if matched_bid.created_at <= matched_ask.created_at:
                trade_price = matched_bid.price
            else:
                trade_price = matched_ask.price
            trade_size = min(matched_bid.size, matched_ask.size)
            if self.exchange is not None:
                self.exchange.execute_trade(
                    self.symbol,
                    trade_price,
                    trade_size,
                    matched_bid.sender,
                    matched_ask.sender,
                )
            matched_ask.size -= trade_size
            matched_bid.size -= trade_size
            if matched_bid.filled_or_expired():
                self.bids.pop()
            if matched_ask.filled_or_expired():
                self.asks.pop()

    def __clean_orders(self) -> None:
        self.bids = [order for order in self.bids if not order.filled_or_expired()]
        self.asks = [order for order in self.asks if not order.filled_or_expired()]

    def __cancel_orders(self, *order_ids: List[int]) -> None:
        order_ids = set(order_ids)
        self.bids = [order for order in self.bids if order.id not in order_ids]
        self.asks = [order for order in self.asks if order.id not in order_ids]

    def bid(
        self,
        sender: Agent,
        price: float,
        size: int,
        frames_to_expire: Union[int, None] = None,
    ) -> None:
        self._orders_to_place.append(
            Order(
                sender=sender,
                dir=Order.BUY_DIR,
                price=price,
                size=size,
                frames_to_expire=frames_to_expire,
            )
        )

    def ask(
        self,
        sender: Agent,
        price: float,
        size: int,
        frames_to_expire: Union[int, None] = None,
    ) -> None:
        self._orders_to_place.append(
            Order(
                sender=sender,
                dir=Order.SELL_DIR,
                price=price,
                size=size,
                frames_to_expire=frames_to_expire,
            )
        )

    def cancel_order(self, order_id: int) -> None:
        self._orders_to_cancel.append(order_id)

    def update(self) -> None:
        self.__place_orders(*self._orders_to_place)
        self.__cancel_orders(*self._orders_to_cancel)
        self.__match_orders()
        self.__clean_orders()
        self._orders_to_place = []
        self._orders_to_cancel = []

    def display_str(self, k: int = 5) -> None:
        if k == -1:
            k = max(len(self.bids), len(self.asks))

        s = Order.display_header_str(Order.SELL_DIR)
        s += (
            "-" * (4 * (Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN))
            + "\n"
        )

        for order in self.asks[-k:]:
            s += order.display()

        s += "\n\n"

        for order in self.bids[-1 : -k - 1 : -1]:
            s += order.display()

        s += (
            "-" * (4 * (Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN))
            + "\n"
        )
        s += Order.display_header_str(Order.BUY_DIR)

        return s


class Agent(SimulationObject):
    def __init__(self) -> None:
        super().__init__()
        self.exchanges = {}

    def register_exchange(self, exchange: Exchange) -> None:
        self.exchanges[exchange.name] = exchange

    def update(self) -> None:
        return super().update()

    @property
    def exchange(self) -> Union[Exchange, Dict[str, Exchange]]:
        if len(self.exchanges) == 1:
            return list(self.exchanges.values())[0]
        return self.exchanges


class Account(SimulationObject):
    CASH_SYM = "USD"

    def __init__(self, agent: Agent) -> None:
        super().__init__()

        self.agent = agent
        self.__holdings = {}

    def get_holding(self, symbol: str) -> int:
        return self.__holdings.get(symbol)

    def set_holding(self, symbol: str, val: int) -> None:
        self.__holdings[symbol] = val

    def add_holding(self, symbol: str, val: int) -> None:
        self.set_holding(symbol, val=val + self.get_holding(symbol))


class Trade:
    def __init__(
        self, symbol: str, price: float, size: int, buyer_id: str, seller_id: str
    ) -> None:
        self.symbol = symbol
        self.price = price
        self.size = size
        self.buyer_id = buyer_id
        self.seller_id = seller_id
        self.time = Time.now


class Product(SimulationObject):
    def __init__(self, symbol: str) -> None:
        super().__init__()
        self.symbol = symbol
        self.num_trades = 0
        self.volume = 0
        self.trades = []

    def record_trade(
        self, price: float, size: int, buyer: Agent, seller: Agent
    ) -> None:
        self.volume += size
        self.trades.append(
            Trade(self.symbol, price, size, buyer.global_id, seller.global_id)
        )

    def payout(self) -> None:
        if len(self.trades) > 0:
            return self.trades[-1].price
        return 0


class Exchange(SimulationObject):
    def __init__(
        self,
        products: List[Product] = [],
        agents: List[Agent] = [],
        tick_size: float = 0.01,
        order_fee: float = 0,
        name: Union[str, None] = None,
    ) -> None:
        super().__init__()
        self.__name = self.global_id if name is None else name

        self.__products = {}
        self.__agents = {}

        self.__order_books = {}
        self.__accounts = {}

        [self.register_product(product) for product in products]
        [self.register_agent(agent) for agent in agents]

        self.__tick_size = tick_size
        self.__order_fee = order_fee

    def execute_trade(
        self, symbol: str, price: float, size: int, buyer: Agent, seller: Agent
    ) -> None:
        self.__products[symbol].record_trade(price, size)
        self.__accounts[buyer.global_id].add_holding(Account.CASH_SYM, -price * size)
        self.__accounts[buyer.global_id].add_holding(symbol, size)
        self.__accounts[seller.global_id].add_holding(Account.CASH_SYM, price * size)
        self.__accounts[seller.global_id].add_holding(symbol, -size)

    def register_product(self, product: Product) -> bool:
        if product.symbol not in self.__order_books:
            self.__order_books[product.symbol] = OrderBook(product.symbol, self)
            self.__products[product.symbol] = product
            return True
        return False

    def register_agent(self, agent: Agent) -> bool:
        if agent.global_id not in self.__accounts:
            self.__accounts[agent.global_id] = Account(agent)
            self.__agents[agent.global_id] = agent
            return True
        return False

    @property
    def order_fee(self) -> float:
        return self.__order_fee

    @property
    def tick_size(self) -> float:
        return self.__tick_size

    @property
    def name(self) -> str:
        return self.__name

    @property
    def symbols(self) -> List[str]:
        return [product.symbol for product in self.__products.values()]