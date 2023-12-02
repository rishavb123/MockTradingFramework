class Time:
    now = 0


class SimulatorObj:
    def __init__(self) -> None:
        self.created_at = Time.now

    def update(self):
        pass


class Order(SimulatorObj):
    DISPLAY_COLUMN_WIDTH = 7
    DISPLAY_COLUMN_MARGIN = 3

    BUY_DIR = 1
    SELL_DIR = -1

    last_id = -1
    margin = DISPLAY_COLUMN_MARGIN * " "

    def __init__(self, sender, dir, price, size, frames_to_expire=None) -> None:
        super().__init__()
        self.id = Order.generate_id()
        self.sender = sender
        self.dir = dir
        self.price = price
        self.size = size
        self.frames_to_expire = frames_to_expire
        self.expired = frames_to_expire == 0

    def update(self):
        if self.frames_to_expire is None:
            self.frames_to_expire -= 1
            if self.frames_to_expire <= 0:
                self.expired = True

    def filled_or_expired(self):
        return self.size == 0 or self.expired

    def is_bid(self):
        return self.dir == Order.BUY_DIR

    def is_ask(self):
        return self.dir == Order.SELL_DIR

    def display(self):
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
    def display_header(dir):
        price_label = "Bid" if dir == Order.BUY_DIR else "Ask"
        return (
            f"{'ID'        :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}"
            f"{price_label :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}"
            f"{'Size'      :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}"
            f"{'Expiring'  :<{Order.DISPLAY_COLUMN_WIDTH + Order.DISPLAY_COLUMN_MARGIN}}\n"
        )

    @staticmethod
    def generate_id():
        Order.last_id += 1
        return Order.last_id


class OrderBook(SimulatorObj):
    def __init__(self, symbol="A", exchange=None) -> None:
        super().__init__()
        self.bids = []
        self.asks = []
        self.symbol = symbol
        self.exchange = exchange

        self._orders_to_place = []
        self._orders_to_cancel = []

    def __place_orders(self, *orders):
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

    def __match_orders(self):
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
                self.exchange.trade(
                    self.symbol,
                    trade_price,
                    trade_size,
                    matched_bid.sender,
                    matched_ask.sender,
                )  # TODO: implement this function within the exchange class
            matched_ask.size -= trade_size
            matched_bid.size -= trade_size
            if matched_bid.filled_or_expired():
                self.bids.pop()
            if matched_ask.filled_or_expired():
                self.asks.pop()

    def __clean_orders(self):
        self.bids = [order for order in self.bids if not order.filled_or_expired()]
        self.asks = [order for order in self.asks if not order.filled_or_expired()]

    def __cancel_orders(self, *order_ids):
        order_ids = set(order_ids)
        self.bids = [order for order in self.bids if order.id not in order_ids]
        self.asks = [order for order in self.asks if order.id not in order_ids]

    def bid(self, sender, price, size, frames_to_expire=None):
        self._orders_to_place.append(
            Order(
                sender=sender,
                dir=Order.BUY_DIR,
                price=price,
                size=size,
                frames_to_expire=frames_to_expire,
            )
        )

    def ask(self, sender, price, size, frames_to_expire=None):
        self._orders_to_place.append(
            Order(
                sender=sender,
                dir=Order.SELL_DIR,
                price=price,
                size=size,
                frames_to_expire=frames_to_expire,
            )
        )

    def cancel_order(self, order_id):
        self._orders_to_cancel.append(order_id)

    def update(self):
        self.__place_orders(*self._orders_to_place)
        self.__cancel_orders(*self._orders_to_cancel)
        self.__match_orders()
        self.__clean_orders()
        self._orders_to_place = []
        self._orders_to_cancel = []

    def display(self, k=5):
        if k == -1:
            k = max(len(self.bids), len(self.asks))

        s = Order.display_header(Order.SELL_DIR)
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
        s += Order.display_header(Order.BUY_DIR)

        return s
