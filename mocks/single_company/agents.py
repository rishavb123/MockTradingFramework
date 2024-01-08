import numpy as np
from scipy.stats import lognorm

from simulation import SimulationObject
from trading_objects import Agent, Time, Account, Order

from .config import ITER, COMPANY_SYMBOL, BOND_SYMBOL
from .products import CompanyStock, CorporateBond


class BiasedStockAgent(Agent):
    def __init__(self) -> None:
        super().__init__()
        self.bias = np.random.random() * 10 - 5
        self.product = CompanyStock.get_instance(0)
        self.edge = 2
        self.sizing = np.random.randint(1, 30)
        self.place_orders_at = np.random.randint(self.product.update_freq)

    def update(self) -> None:
        super().update()

        if self.product.bankrupt:
            self.cancel_all_open_orders()
        elif Time.now % self.product.update_freq == self.place_orders_at:
            extra_noise = np.random.random() * 6 - 3
            self.bid(
                price=max(
                    0, self.product.current_value - self.edge + self.bias + extra_noise
                ),
                size=self.sizing,
                symbol=self.product.symbol,
                frames_to_expire=self.product.update_freq,
            )
            self.ask(
                price=self.product.current_value + self.edge + self.bias + extra_noise,
                size=self.sizing,
                symbol=self.product.symbol,
                frames_to_expire=self.product.update_freq,
            )


class OptimisticBiasedBondAgent(Agent):
    def __init__(self) -> None:
        super().__init__()
        self.bias = np.random.random() * 10 - 5
        self.bond = CorporateBond.get_instance(0)
        self.edge = 2
        self.sizing = np.random.randint(1, 30)
        self.order_freq = 50
        self.place_orders_at = np.random.randint(self.order_freq)

    @SimulationObject.cache_wrapper
    def estimate_fair_value(self) -> float:
        if self.bond.coupon_freq == 0:
            return self.bond.coupon_payout + self.bond.par_value
        else:
            if self.bond.maturity == -1:
                end_time = ITER
            else:
                end_time = self.bond.maturity

            return (
                self.bond.par_value
                + self.bond.coupon_payout
                * (end_time - Time.now)
                // self.bond.coupon_freq
            )

    def update(self) -> None:
        super().update()

        if self.bond.company_stock.bankrupt or self.bond.matured:
            self.cancel_all_open_orders()
        elif Time.now % self.order_freq == self.place_orders_at:
            fair = self.estimate_fair_value()
            extra_noise = np.random.random() * 6 - 3
            self.bid(
                max(0, fair - self.edge + self.bias + extra_noise),
                size=self.sizing,
                symbol=self.bond.symbol,
                frames_to_expire=self.order_freq,
            )
            self.ask(
                max(0, fair + self.edge + self.bias + extra_noise),
                size=self.sizing,
                symbol=self.bond.symbol,
                frames_to_expire=self.order_freq,
            )


class RealisticBiasedBondAgent(OptimisticBiasedBondAgent):
    def __init__(self) -> None:
        super().__init__()

    @SimulationObject.cache_wrapper
    def estimate_chance_of_default(self) -> float:
        if self.bond.maturity == -1:
            time_remaining = ITER - Time.now
        else:
            time_remaining = self.bond.maturity - Time.now

        mean = (
            self.bond.company_stock.current_value
            + self.bond.company_stock.mu * time_remaining
        )
        std = self.bond.company_stock.sigma * np.sqrt(time_remaining)

        return lognorm.cdf(
            self.bond.company_stock.bankruptcy_value_thresh,
            s=std,
            scale=np.exp(mean),
        )

    @SimulationObject.cache_wrapper
    def fair_value_if_default(self) -> float:
        price_drop = (
            self.bond.company_stock.current_value
            - self.bond.company_stock.bankruptcy_value_thresh
        ) / self.bond.company_stock.sigma
        return (self.bond.coupon_payout / self.bond.coupon_freq) * int(
            price_drop
        ) * 2 + self.bond.par_value / 5

    def estimate_fair_value(self) -> float:
        p = self.estimate_chance_of_default()
        return (
            1 - p
        ) * super().estimate_fair_value() + p * self.fair_value_if_default()


class LongStockShortBond(Agent):
    def __init__(self) -> None:
        super().__init__()

        self.stock_price_thresh = 80
        self.bond_price_thresh = 50

        self.stock_symbol = COMPANY_SYMBOL
        self.bond_symbol = BOND_SYMBOL

        self.stock_sizing = 10
        self.bond_sizing = 5

        self.frames_to_expire = 20
        self.bond = CorporateBond.get_instance(0)

        self.total_put_into_stock = 0

    def executed_trade(self, symbol: str, dir: int, price: float, size: int) -> None:
        super().executed_trade(symbol, dir, price, size)

        if symbol == self.stock_symbol:
            if dir == Order.BUY_DIR:
                self.total_put_into_stock += price * size
            else:
                self.total_put_into_stock -= price * size

    def update(self) -> None:
        super().update()

        if self.bond.company_stock.bankrupt:
            self.cancel_all_open_orders()

        else:
            order_books = self.exchange.public_info()
            holdings = self.exchange.get_account_holdings(self)

            cash = holdings[Account.CASH_SYM]

            have_open_bond_order = False
            have_open_stock_order = False
            for order_id in self.open_orders:
                if self.open_orders[order_id].symbol == self.bond_symbol:
                    have_open_bond_order = True
                elif self.open_orders[order_id].symbol == self.stock_symbol:
                    have_open_stock_order = True

            asks = order_books[self.stock_symbol].asks

            if len(asks) > 0:
                if (
                    asks[-1].price <= self.stock_price_thresh
                    and not have_open_stock_order
                ):
                    self.bid(
                        price=self.stock_price_thresh,
                        size=self.stock_sizing,
                        symbol=self.stock_symbol,
                        frames_to_expire=self.frames_to_expire,
                    )

            if cash < self.total_put_into_stock and not have_open_bond_order:
                self.ask(
                    price=self.bond_price_thresh,
                    size=self.bond_sizing,
                    symbol=self.bond_symbol,
                    frames_to_expire=self.frames_to_expire,
                )
