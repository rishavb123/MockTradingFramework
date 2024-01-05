from __future__ import annotations
from typing import Union, List, Dict, Tuple, Callable
from collections import namedtuple

from util import prefix_lines, effective_inf
from simulation import Time, SimulationObject


class Order(SimulationObject):
    DISPLAY_COLUMN_WIDTH = 10
    DISPLAY_COLUMN_MARGIN = 5

    BUY_DIR = 1
    SELL_DIR = -1

    margin = DISPLAY_COLUMN_MARGIN * " "

    PublicInfo = namedtuple("OrderInfo", ["id", "price", "size"])

    def __init__(
        self,
        sender: Agent,
        symbol: str,
        dir: int,
        price: float,
        size: int,
        exchange: Exchange,
        frames_to_expire: Union[int, None] = None,
    ) -> None:
        super().__init__()

        self.__symbol = symbol.upper()
        self.__sender = sender
        self.__dir = dir
        self.__price = price
        self.__size = size
        self.__exchange = exchange
        if frames_to_expire is not None:
            self.__frames_to_expire = frames_to_expire + 1  # decremented on add
        else:
            self.__frames_to_expire = None
        self.__expired = frames_to_expire == 0
        self.__cancelled = False

    def place(self) -> int:
        self.__exchange.place_order(self)
        return self.id

    def update(self) -> None:
        super().update()
        if self.__frames_to_expire is not None:
            self.__frames_to_expire -= 1
            if self.__frames_to_expire <= 0:
                self.__expired = True

    def decrement_size(self, amount: int, book: OrderBook) -> None:
        if isinstance(book, OrderBook):
            self.__size -= amount

    def voided(self) -> bool:
        return self.__size == 0 or self.__expired or self.__cancelled

    def is_bid(self) -> bool:
        return self.__dir == Order.BUY_DIR

    def is_ask(self) -> bool:
        return self.__dir == Order.SELL_DIR

    def cancel(self) -> None:
        self.__cancelled = True

    def public_info(self) -> Order.PublicInfo:
        return Order.PublicInfo(self.id, self.price, self.size)

    @property
    def symbol(self):
        return self.__symbol

    @property
    def sender(self):
        return self.__sender

    @property
    def dir(self):
        return self.__dir

    @property
    def price(self):
        return self.__price

    @property
    def size(self):
        return self.__size

    @property
    def exchange(self):
        return self.__exchange

    @property
    def frames_to_expire(self):
        return self.__frames_to_expire

    def display_str(self, viewer: Union[Agent, None] = None) -> str:
        frames_to_expire = (
            "" if self.__frames_to_expire is None else self.__frames_to_expire
        )
        sender = "You" if self.sender == viewer else "Anon"

        return (
            f"{self.id          :<{Order.DISPLAY_COLUMN_WIDTH}}{Order.margin}"
            f"{self.__price     :<{Order.DISPLAY_COLUMN_WIDTH}}{Order.margin}"
            f"{self.__size      :<{Order.DISPLAY_COLUMN_WIDTH}}{Order.margin}"
            f"{sender           :<{Order.DISPLAY_COLUMN_WIDTH}}{Order.margin}"
            f"{frames_to_expire :<{Order.DISPLAY_COLUMN_WIDTH}}{Order.margin}\n"
        )

    @staticmethod
    def display_header_str(dir: int) -> str:
        price_label = "Bid" if dir == Order.BUY_DIR else "Ask"
        return (
            f"{'ID'        :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}"
            f"{price_label :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}"
            f"{'Size'      :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}"
            f"{'Sender'    :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}"
            f"{'Expiring'  :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}\n"
        )


class OrderBook(SimulationObject):
    PublicInfo = namedtuple("OrderBookInfo", ["bids", "asks"])

    def __init__(self, symbol: str, exchange: Exchange) -> None:
        super().__init__()

        self.bids = []
        self.asks = []
        self.symbol = symbol.upper()
        self.exchange = exchange

        self._orders_to_place = []

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
            if self.exchange is not None and matched_bid.sender != matched_ask.sender:
                self.exchange.execute_trade(
                    self.symbol,
                    trade_price,
                    trade_size,
                    matched_bid.sender,
                    matched_ask.sender,
                )
            matched_ask.decrement_size(trade_size, self)
            matched_bid.decrement_size(trade_size, self)
            if matched_bid.voided():
                self.bids.pop()
            if matched_ask.voided():
                self.asks.pop()

    def __clean_orders(self) -> None:
        self.bids = [order for order in self.bids if not order.voided()]
        self.asks = [order for order in self.asks if not order.voided()]

    def __remove_resting_market_orders(self):
        for order in self.bids:
            if order.price >= effective_inf:
                order.cancel()
        for order in self.asks:
            if order.price <= 0:
                order.cancel()
        self.__clean_orders()

    def place_order(self, order: Order) -> None:
        self._orders_to_place.append(order)

    def cancel_order(self, order_id: int) -> None:
        Order.get_instance(order_id).cancel()

    def update(self) -> None:
        super().update()
        self.__place_orders(*self._orders_to_place)
        self.__clean_orders()
        self.__match_orders()
        self.__clean_orders()
        self.__remove_resting_market_orders()
        for order in self._orders_to_place:
            if not order.voided():
                self.exchange.send_order_update(order)
        self._orders_to_place = []
        self._orders_to_cancel = []

    def public_info(self) -> Tuple[List[Order.PublicInfo], List[Order.PublicInfo]]:
        return OrderBook.PublicInfo(
            bids=[order.public_info() for order in self.bids],
            asks=[order.public_info() for order in self.asks],
        )

    def display_str(self, viewer: Union[Agent, None] = None, k: int = 5) -> None:
        if k == -1:
            k = max(len(self.bids), len(self.asks))

        s = Order.display_header_str(Order.SELL_DIR)
        width = len(s) - 1
        s += "-" * width + "\n"

        if len(self.asks) < k:
            s += "\n" * (k - len(self.asks))

        for order in self.asks[-k:]:
            s += order.display_str(viewer=viewer)

        s += "\n\n"

        for order in self.bids[-1 : -k - 1 : -1]:
            s += order.display_str(viewer=viewer)

        if len(self.bids) < k:
            s += "\n" * (k - len(self.bids))

        s += "-" * width + "\n"
        s += Order.display_header_str(Order.BUY_DIR)

        return s


class Agent(SimulationObject):
    def __init__(self) -> None:
        super().__init__()
        self.exchanges = {}
        self.open_orders = {}

    def register_exchange(self, exchange: Exchange) -> None:
        self.exchanges[exchange.name] = exchange

    def limit_order(
        self,
        dir: int,
        price: float,
        size: int,
        symbol: Union[str, None] = None,
        exchange_name: Union[str, None] = None,
        frames_to_expire: Union[int, None] = None,
    ) -> int:
        if (exchange_name is not None and exchange_name not in self.exchanges) or len(
            self.exchanges.values()
        ) == 0:
            raise Exception("Exchange does not exist")
        exchange = (
            list(self.exchanges.values())[0]
            if exchange_name is None
            else self.exchanges[exchange_name]
        )
        if symbol is None and len(exchange.symbols) == 0:
            raise Exception("Symbol does not exist")
        symbol = exchange.symbols[0] if symbol is None else symbol
        price = round(round(price / exchange.tick_size) * exchange.tick_size, 2)
        order = Order(
            sender=self,
            symbol=symbol,
            dir=dir,
            price=price,
            size=size,
            exchange=exchange,
            frames_to_expire=frames_to_expire,
        )
        self.add_dependent(order)
        self.open_orders[order.id] = order
        return order.place()

    def market_order(
        self,
        dir: int,
        size: int,
        symbol: Union[str, None] = None,
        exchange_name: Union[str, None] = None,
        frames_to_expire: Union[int, None] = None,
    ) -> int:
        return self.limit_order(
            symbol=symbol,
            dir=dir,
            price=(0 if dir == Order.SELL_DIR else effective_inf),
            size=size,
            exchange_name=exchange_name,
            frames_to_expire=frames_to_expire,
        )

    def bid(
        self,
        price: float,
        size: int,
        symbol: Union[str, None] = None,
        exchange_name: Union[str, None] = None,
        frames_to_expire: Union[int, None] = None,
    ) -> int:
        return self.limit_order(
            symbol=symbol,
            dir=Order.BUY_DIR,
            price=price,
            size=size,
            exchange_name=exchange_name,
            frames_to_expire=frames_to_expire,
        )

    def ask(
        self,
        price: float,
        size: int,
        symbol: Union[str, None] = None,
        exchange_name: Union[str, None] = None,
        frames_to_expire: Union[int, None] = None,
    ) -> int:
        return self.limit_order(
            symbol=symbol,
            dir=Order.SELL_DIR,
            price=price,
            size=size,
            exchange_name=exchange_name,
            frames_to_expire=frames_to_expire,
        )

    def take(
        self,
        size: int,
        exchange_name: Union[str, None] = None,
        symbol: Union[str, None] = None,
        frames_to_expire: Union[int, None] = None,
    ) -> int:
        return self.market_order(
            symbol=symbol,
            dir=Order.BUY_DIR,
            size=size,
            exchange_name=exchange_name,
            frames_to_expire=frames_to_expire,
        )

    def sell(
        self,
        size: int,
        exchange_name: Union[str, None] = None,
        symbol: Union[str, None] = None,
        frames_to_expire: Union[int, None] = None,
    ) -> int:
        return self.market_order(
            symbol=symbol,
            dir=Order.SELL_DIR,
            size=size,
            exchange_name=exchange_name,
            frames_to_expire=frames_to_expire,
        )

    def cancel(self, order_id: int) -> None:
        order = Order.get_instance(order_id)
        if order.sender == self:
            order.cancel()
            return order_id

    def cancel_all_open_orders(self) -> None:
        for order_id in self.open_orders:
            self.cancel(order_id)

    def executed_trade(self, symbol: str, dir: int, price: float, size: int) -> None:
        pass

    def update(self) -> None:
        super().update()
        self.open_orders = {
            order_id: order
            for order_id, order in self.open_orders.items()
            if not order.voided()
        }

    def get_marked_pnl(self, marked_to: Union[Callable, str] = "mid") -> float:
        return sum(
            [
                exchange.get_marked_pnl(self, marked_to)
                for exchange in self.exchanges.values()
            ]
        )

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
        return self.__holdings.get(symbol.upper(), 0)

    def set_holding(self, symbol: str, val: int) -> None:
        self.__holdings[symbol.upper()] = val

    def update_holding(self, symbol: str, val: int) -> None:
        super().update()
        self.set_holding(symbol.upper(), val=val + self.get_holding(symbol))


class Trade(SimulationObject):
    def __init__(
        self, symbol: str, price: float, size: int, buyer_id: str, seller_id: str
    ) -> None:
        super().__init__()

        self.symbol = symbol.upper()
        self.price = price
        self.size = size
        self.buyer_id = buyer_id
        self.seller_id = seller_id
        self.time = Time.now


class Product(SimulationObject):
    def __init__(self, symbol: str) -> None:
        super().__init__()
        self.symbol = symbol.upper()
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

    def payout(self) -> float:
        if len(self.trades) > 0:
            return self.trades[-1].price
        return 0

    def dividend(self) -> float:
        return 0


class Event:
    BID = 0
    ASK = 1
    TRADE = 2

    def __init__(
        self, symbol: str, event_type: int, price: float, size: int, id: int
    ) -> None:
        self.symbol = symbol
        self.event_type = event_type
        self.price = price
        self.size = size
        if event_type == Event.TRADE:
            self.order_id = None
        else:
            self.order_id = id


class Exchange(SimulationObject):
    def __init__(
        self,
        products: Union[List[Product], Product] = [],
        agents: List[Agent] = [],
        tick_size: float = 0.01,
        order_fee: float = 0,
        name: Union[str, None] = None,
    ) -> None:
        super().__init__(z_index=10)
        self.__name = self.global_id if name is None else name

        self.__products = {}
        self.__agents = {}

        self.__order_books = {}
        self.__accounts = {}

        if isinstance(products, Product):
            products = [products]

        [self.register_product(product) for product in products]
        [self.register_agent(agent) for agent in agents]

        self.__tick_size = tick_size
        self.__order_fee = order_fee

        self.__subscribed_callbacks = {}

    def __on_event(self, event: Event) -> None:
        for callback in self.__subscribed_callbacks.values():
            callback(event)

    def get_account_holdings(self, agent):
        return {
            symbol: self.__accounts[agent.global_id].get_holding(symbol)
            for symbol in ([Account.CASH_SYM] + list(self.__products.keys()))
        }

    def mark_to_mid(self, symbol):
        order_book = self.public_info()
        bids = order_book[symbol].bids
        asks = order_book[symbol].asks

        if len(bids) > 0 and len(asks) > 0:
            mid = (bids[-1].price + asks[-1].price) / 2
        elif len(bids) > 0:
            mid = bids[-1].price
        elif len(asks) > 0:
            mid = asks[-1].price
        else:
            mid = 0

        return mid

    def mark_to_last_traded(self, symbol):
        if len(self.__products[symbol].trades) > 0:
            return self.__products[symbol].trades[-1].price
        return 0

    def mark_to_payout(self, symbol):
        return self.__products[symbol].payout()

    def mark_to_zero(self, symbol):
        return 0

    def get_marked_pnl(self, agent: Agent, mark_to_f: Union[Callable, str] = "mid"):
        if mark_to_f is None:
            mark_to_f = self.mark_to_mid
        elif type(mark_to_f) == str:
            mark_to_f = {
                "mid": self.mark_to_mid,
                "last_traded": self.mark_to_last_traded,
                "payout": self.mark_to_payout,
                "zero": self.mark_to_zero,
            }[mark_to_f]

        pnl = self.__accounts[agent.global_id].get_holding(Account.CASH_SYM)
        for symbol in list(self.__products.keys()):
            marked_to = mark_to_f(symbol=symbol)
            pnl += self.__accounts[agent.global_id].get_holding(symbol) * marked_to
        return pnl

    def place_order(self, order: Order) -> None:
        self.__accounts[order.sender.global_id].update_holding(
            Account.CASH_SYM, -self.order_fee
        )
        self.__order_books[order.symbol].place_order(order)

    def send_order_update(self, order: Order) -> None:
        self.__on_event(
            Event(
                order.symbol,
                Event.BID if order.dir == Order.BUY_DIR else Event.ASK,
                order.price,
                order.size,
                order.id,
            )
        )

    def execute_trade(
        self, symbol: str, price: float, size: int, buyer: Agent, seller: Agent
    ) -> None:
        self.__on_event(Event(symbol, Event.TRADE, price, size, None))
        self.__products[symbol.upper()].record_trade(price, size, buyer, seller)
        self.__accounts[buyer.global_id].update_holding(Account.CASH_SYM, -price * size)
        self.__accounts[buyer.global_id].update_holding(symbol, size)
        self.__accounts[seller.global_id].update_holding(Account.CASH_SYM, price * size)
        self.__accounts[seller.global_id].update_holding(symbol, -size)
        buyer.executed_trade(symbol=symbol, dir=Order.BUY_DIR, price=price, size=size)
        seller.executed_trade(symbol=symbol, dir=Order.SELL_DIR, price=price, size=size)

    def register_product(self, product: Product) -> bool:
        if product.symbol not in self.__order_books:
            self.__order_books[product.symbol] = OrderBook(product.symbol, self)
            self.__products[product.symbol] = product
            self.add_dependent(self.__products[product.symbol])
            self.add_dependent(self.__order_books[product.symbol])
            return True
        return False

    def register_agent(self, agent: Agent) -> bool:
        if agent.global_id not in self.__accounts:
            self.__accounts[agent.global_id] = Account(agent)
            self.__agents[agent.global_id] = agent
            agent.register_exchange(self)
            return True
        return False

    def subscribe(self, agent: Agent, callback: Callable[[Event], None]) -> None:
        self.__subscribed_callbacks[agent.global_id] = callback

    def unsubscribe(self, agent: Agent) -> None:
        del self.__subscribed_callbacks[agent.global_id]

    def update(self) -> None:
        super().update()
        for symbol in self.__products:
            product = self.__products[symbol]
            dividend = product.dividend()
            for agent_id in self.__accounts:
                product_holding = self.__accounts[agent_id].get_holding(symbol)
                self.__accounts[agent_id].set_holding(symbol, 0)
                self.__accounts[agent_id].update_holding(
                    Account.CASH_SYM, product_holding * dividend
                )

    @SimulationObject.cache_wrapper
    def public_info(self) -> Dict[str, OrderBook.PublicInfo]:
        return {
            symbol: self.__order_books[symbol].public_info() for symbol in self.symbols
        }

    def display_str(self, viewer: Union[Agent, None] = None, k: int = 5) -> str:
        s = f"Exchange: {self.name}\n"
        for symbol in self.symbols:
            s += f"\tSymbol: {symbol}\n"
            s += prefix_lines(
                self.__order_books[symbol].display_str(viewer=viewer, k=k), "\t\t"
            )[:-2]
        return s + "\n\n"

    def payout_for_holdings(self):
        for symbol in self.__products:
            product = self.__products[symbol]
            payout = product.payout()
            for agent_id in self.__accounts:
                product_holding = self.__accounts[agent_id].get_holding(symbol)
                self.__accounts[agent_id].set_holding(symbol, 0)
                self.__accounts[agent_id].update_holding(
                    Account.CASH_SYM, product_holding * payout
                )

    @property
    def time_remaining(self) -> int:
        return self.simulation.iter - Time.now

    @property
    def open(self) -> bool:
        return self.simulation.started and not self.simulation.finished

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
        return list(self.__products)

    def trades_symbol(self, symbol) -> bool:
        return symbol in self.__products
