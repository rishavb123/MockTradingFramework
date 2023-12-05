from typing import Callable, Tuple
import numpy as np
import matplotlib.pyplot as plt
import pygame

from util import effective_inf
from simulation import Time
from trading_objects import Agent, Exchange, Order, Event
from command_display import CommandDisplay, Command, Argument


class ManualAgent(Agent):
    # Note this only works for a single exchange for now

    def __init__(
        self,
        num_orders_to_show=5,
        order_book_color: Tuple[int, int, int] = (0, 255, 255),
        selected_book_color: Tuple[int, int, int] = (255, 0, 255),
        order_column_width: int = 10,
        order_column_margin_len: int = 0,
        max_events_stored: int = 100,
        event_column_width: int = 10,
        events_color: Tuple[int, int, int] = (0, 255, 255),
    ) -> None:
        super().__init__()
        self.num_orders_to_show = num_orders_to_show
        self.order_column_width = order_column_width
        self.order_column_margin_len = order_column_margin_len
        self.order_column_margin = order_column_margin_len * " "
        self.order_book_color = order_book_color
        self.selected_book_color = selected_book_color
        self.cur_symbol = None
        self.gui = CommandDisplay(
            commands=[
                Command(
                    self.order_id_wrapper(self.bid),
                    args_definitions=[
                        Argument(float, effective_inf),
                        Argument(int, 1),
                        Argument(int, None),
                    ],
                    short_name="b",
                ),
                Command(
                    self.order_id_wrapper(self.ask),
                    args_definitions=[
                        Argument(float, 0),
                        Argument(int, 1),
                        Argument(int, None),
                    ],
                    short_name="a",
                ),
                Command(
                    self.order_id_wrapper(self.take),
                    args_definitions=[
                        Argument(int, 1),
                        Argument(int, None),
                    ],
                    short_name="t",
                ),
                Command(
                    self.order_id_wrapper(self.sell),
                    args_definitions=[
                        Argument(int, 1),
                        Argument(int, None),
                    ],
                    short_name="s",
                ),
                Command(
                    self.cancel,
                    args_definitions=[
                        Argument(int, 0),
                    ],
                    short_name="c",
                ),
                Command(
                    self.select_symbol,
                    args_definitions=[
                        Argument(str, None),
                    ],
                    short_name="ss",
                ),
                Command(
                    self.update_event_symbols,
                    name="events_set_symbol",
                    args_definitions=[Argument(str, "all"), 0],
                    short_name="ess",
                ),
                Command(
                    self.update_event_symbols,
                    name="events_add_symbol",
                    args_definitions=[Argument(str, "all"), 1],
                    short_name="eas",
                ),
                Command(
                    self.update_event_symbols,
                    name="event_remove_symbol",
                    args_definitions=[Argument(str, "all"), 2],
                    short_name="ers",
                ),
                Command(
                    self.update_event_types,
                    name="events_set_type",
                    args_definitions=[Argument(str, "all"), 0],
                    short_name="est",
                ),
                Command(
                    self.update_event_types,
                    name="events_add_type",
                    args_definitions=[Argument(str, "all"), 1],
                    short_name="eat",
                ),
                Command(
                    self.update_event_types,
                    name="event_remove_type",
                    args_definitions=[Argument(str, "all"), 2],
                    short_name="ert",
                ),
            ],
            macros={},
            draw_fn_map={
                "market": self.visualize_market,
                "events": self.visualize_events,
                "holdings": self.visualize_holdings,
            },
            handle_event_fn=self.handle_event,
            font_size=12,
            command_font_size=16,
        )
        self.max_events_stored = max_events_stored
        self.event_column_width = event_column_width
        self.events_color = events_color

    def register_exchange(self, exchange: Exchange) -> None:
        super().register_exchange(exchange)

        self.events = []
        self.event_types_map = {
            "trades": Event.TRADE,
            "bids": Event.BID,
            "asks": Event.ASK,
        }
        self.event_type_reverse_map = {v: k for k, v in self.event_types_map.items()}
        self.allowed_event_types = set(self.event_types_map.values())
        self.allowed_symbols = set(exchange.symbols)

        exchange.subscribe(self, self.process_event)

    def process_event(self, event: Event) -> None:
        self.events.append(event)
        if len(self.events) > 1.5 * self.max_events_stored:
            self.events = self.events[-self.max_events_stored :]

    def update_event_symbols(self, symbol: str, operation: int) -> None:
        symbol = symbol.upper()
        if symbol != "ALL":
            if operation == 0:
                self.allowed_symbols = set([symbol])
            elif operation == 1:
                self.allowed_symbols.add(symbol)
            elif operation == 2:
                self.allowed_symbols.remove(symbol)
        else:
            if operation == 0:
                self.allowed_symbols = set(self.exchange.symbols)
            elif operation == 1:
                self.allowed_symbols = set(self.exchange.symbols)
            elif operation == 2:
                self.allowed_symbols = set()

    def update_event_types(self, event_type_str: str, operation: int) -> None:
        event_type = self.event_types_map[event_type_str.lower()]
        if event_type != "all":
            if operation == 0:
                self.allowed_event_types = set([event_type])
            elif operation == 1:
                self.allowed_event_types.add(event_type)
            elif operation == 2:
                self.allowed_event_types.remove(event_type)
        else:
            if operation == 0:
                self.allowed_symbols = set(self.event_types_map.values())
            elif operation == 1:
                self.allowed_symbols = set(self.event_types_map.values())
            elif operation == 2:
                self.allowed_symbols = set()

    def select_symbol(self, symbol):
        symbols = self.exchange.symbols
        if symbol is None:
            symbol = symbols[0]
        if symbol.upper() not in symbols:
            return f"Symbol {symbol} does not exist"
        self.cur_symbol = symbol.upper()
        return f"Selected {self.cur_symbol}"

    def cancel(self, order_id: int) -> None:
        order_id = super().cancel(order_id)
        if order_id is None:
            return "Cancel failed."
        else:
            return f"Cancel successful. Order id {order_id} is cancelled."

    def order_id_wrapper(self, f: Callable) -> Callable:
        def g(
            *args,
        ):
            order_id = f(
                *args[:-1],
                symbol=self.cur_symbol,
                exchange_name=None,
                frames_to_expire=args[-1],
            )
            if order_id is None:
                return f"{f.__name__.title()} failed."
            else:
                return f"{f.__name__.title()} successful. Order id is {order_id}."

        g.__name__ = f.__name__
        return g

    def order_string(self, order_info: Order.PublicInfo) -> str:
        return (
            f"{order_info.id        :<{self.order_column_width}}{self.order_column_margin}"
            f"{order_info.price     :^{self.order_column_width}}{self.order_column_margin}"
            f"{order_info.size      :>{self.order_column_width}}{self.order_column_margin}"
        )

    def visualize_market_status(self, x: int, y: int, w: int, h: int) -> None:
        market_open = self.exchange.open
        market_paused = self.simulation.paused

        market_status = "Open"

        if not market_open:
            market_status = "Closed"
        elif market_paused:
            market_status = "Paused"

        block = self.gui.font.render(
            f"Market {market_status}!",
            True,
            self.order_book_color,
        )
        rect = block.get_rect()
        rect.left = x + self.gui.margin
        rect.bottom = y + h - self.gui.margin
        self.gui.screen.blit(block, rect)

        block = self.gui.font.render(
            f"Time Remaining {self.simulation.iter - Time.now} / {self.simulation.iter}",
            True,
            self.order_book_color,
        )
        rect = block.get_rect()
        rect.right = x + w - self.gui.margin
        rect.bottom = y + h - self.gui.margin
        self.gui.screen.blit(block, rect)

    def visualize_market(self, x: int, y: int, w: int, h: int) -> None:
        if self.cur_symbol is None:
            self.select_symbol(self.cur_symbol)

        order_books = self.exchange.public_info()

        cur_x = x
        starting_y = y

        bid_str_header = (
            f"{'Id'   :<{self.order_column_width}}{self.order_column_margin}"
            f"{'Bid'  :^{self.order_column_width}}{self.order_column_margin}"
            f"{'Size' :>{self.order_column_width}}{self.order_column_margin}"
        )
        ask_str_header = (
            f"{'Id'   :<{self.order_column_width}}{self.order_column_margin}"
            f"{'Bid'  :^{self.order_column_width}}{self.order_column_margin}"
            f"{'Size' :>{self.order_column_width}}{self.order_column_margin}"
        )

        for symbol in order_books:
            bids = order_books[symbol].bids
            asks = order_books[symbol].asks

            color = (
                self.selected_book_color
                if symbol == self.cur_symbol
                else self.order_book_color
            )

            def show(s: str, use: bool = True, c=color) -> None:
                block = self.gui.font.render(
                    s,
                    True,
                    c,
                )
                rect = block.get_rect()
                rect.left = cur_x + self.gui.margin
                rect.top = show.cur_y
                show.bottom_y = rect.bottom
                self.gui.screen.blit(block, rect)
                show.cur_y += rect.height
                if show.x_incr is None and use:
                    show.x_incr = rect.width + 2 * self.gui.margin

            show.cur_y = starting_y
            show.x_incr = None
            show.bottom_y = None

            symbol_header = (" " + symbol.upper() + " ").center(
                3 * (self.order_column_width + self.order_column_margin_len), "-"
            )
            show(symbol_header)

            show(ask_str_header)

            for i in range(self.num_orders_to_show - 1, -1, -1):
                if len(asks) - i - 1 < 0:
                    show(" ", False)
                else:
                    ask = asks[-i - 1]
                    s = self.order_string(ask)
                    if ask.id in self.open_orders:
                        show(
                            s,
                            c=(color[0] // 2, color[1] // 2, color[2] // 2),
                        )
                    else:
                        show(s)

            show(" ", False)

            for i in range(self.num_orders_to_show):
                if len(bids) - i - 1 < 0:
                    show(" ", False)
                else:
                    bid = bids[-i - 1]
                    s = self.order_string(bid)
                    if bid.id in self.open_orders:
                        show(
                            s,
                            c=(color[0] // 2, color[1] // 2, color[2] // 2),
                        )
                    else:
                        show(s)

            show(bid_str_header)

            pygame.draw.rect(
                self.gui.screen,
                color,
                (cur_x, starting_y, show.x_incr, show.bottom_y - starting_y),
                width=1,
            )

            cur_x += show.x_incr + self.gui.margin
            if cur_x + show.x_incr > x + w:
                cur_x = x
                starting_y = show.bottom_y + self.gui.margin

        self.visualize_market_status(x, y, w, h)

    def visualize_events(self, x: int, y: int, w: int, h: int) -> None:
        def to_line(symbol, price, size, event_type):
            symbol = symbol.upper()
            event_type_str = self.event_type_reverse_map[event_type][:-1].upper()
            return f"{symbol:<{self.event_column_width}}{price:<{self.event_column_width}}{size:<{self.event_column_width}}{event_type_str:<{self.event_column_width}}"

        lines = [
            f"{'Symbol':<{self.event_column_width}}{'Price':<{self.event_column_width}}{'Size':<{self.event_column_width}}{'Event Type':<{self.event_column_width}}"
        ] + list(
            reversed(
                [
                    to_line(event.symbol, event.price, event.size, event.event_type)
                    for event in self.events
                    if event.symbol in self.allowed_symbols
                    and event.event_type in self.allowed_event_types
                ]
            )
        )

        self.gui.wrap_text(lines, x, y, w, h, self.events_color)

        self.visualize_market_status(x, y, w, h)

    def visualize_holdings(self, x: int, y: int, w: int, h: int) -> None:
        holdings = self.exchange.get_account_holdings(self)

        def show_holding(symbol):
            block = self.gui.font.render(
                f"{symbol:<{self.order_column_width}}: {holdings[symbol]}",
                True,
                self.order_book_color,
            )
            rect = block.get_rect()
            rect.left = show_holding.cur_x
            rect.top = show_holding.cur_y
            if show_holding.x_incr is None:
                show_holding.x_incr = rect.width
            show_holding.cur_y += rect.height
            self.gui.screen.blit(block, rect)

        show_holding.cur_x = x + self.gui.margin
        show_holding.cur_y = y + self.gui.margin
        show_holding.x_incr = None

        for symbol in holdings:
            show_holding(symbol)

        pygame.draw.rect(
            self.gui.screen,
            self.order_book_color,
            (
                x,
                y,
                show_holding.x_incr + 2 * self.gui.margin,
                show_holding.cur_y - y + self.gui.margin,
            ),
            width=1,
        )

        self.visualize_market_status(x, y, w, h)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                symbols = self.exchange.symbols
                symbol_idx = symbols.index(self.cur_symbol)
                self.cur_symbol = symbols[symbol_idx - 1]
            if event.key == pygame.K_RIGHT:
                symbols = self.exchange.symbols
                symbol_idx = symbols.index(self.cur_symbol)
                self.cur_symbol = symbols[(symbol_idx + 1) % len(symbols)]
