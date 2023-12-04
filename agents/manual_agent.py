from typing import Callable, Tuple
import pygame

from trading_objects import Agent, Order
from command_display import CommandDisplay, Command, Argument


class SingleExchangeManualAgent(Agent):
    def __init__(
        self,
        num_orders_to_show=5,
        order_book_color: Tuple[int, int, int] = (0, 255, 255),
        selected_book_color: Tuple[int, int, int] = (255, 0, 255),
        order_column_width: int = 10,
        order_column_margin_len: int = 0,
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
                        Argument(float, float("inf")),
                        Argument(int, 1),
                    ],
                    short_name="b",
                ),
                Command(
                    self.order_id_wrapper(self.ask),
                    args_definitions=[
                        Argument(float, 0),
                        Argument(int, 1),
                    ],
                    short_name="a",
                ),
                Command(
                    self.order_id_wrapper(self.take),
                    args_definitions=[
                        Argument(int, 1),
                    ],
                    short_name="t",
                ),
                Command(
                    self.order_id_wrapper(self.sell),
                    args_definitions=[
                        Argument(int, 1),
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
            ],
            draw_fn_map={
                "market": self.visualize_market,
                "holdings": self.visualize_holdings,
            },
            handle_event_fn=self.handle_event,
            font_size=12,
            command_font_size=16,
        )

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
            order_id = f(*args, symbol=self.cur_symbol)
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

    def visualize_market(self, x: int, y: int, w: int, h: int) -> None:
        if self.cur_symbol is None:
            self.select_symbol(self.cur_symbol)

        order_books = self.exchange.public_info()
        market_open = self.exchange.open
        my_open_orders = set([order.id for order in self.open_orders])

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
                    if ask.id in my_open_orders:
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
                    if bid.id in my_open_orders:
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
    
        if not market_open:
            block = self.gui.font.render(
                "Market Closed!",
                True,
                self.order_book_color,
            )
            rect = block.get_rect()
            rect.left = x + self.gui.margin
            rect.bottom = y + h - self.gui.margin
            self.gui.screen.blit(block, rect)

    def visualize_holdings(self, x: int, y: int, w: int, h: int) -> None:
        pass

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
