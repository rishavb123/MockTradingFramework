import time

from trading_objects import Exchange
from market_simulation import MarketSimulation
from agents import ManualAgent
from metrics_aggregators.prices import PriceAggregator, PricePlot

from .config import *
from .agents import RetailInvestor, RetailTrader, HedgeFund, ArbAgent
from .products import PairedFlipProduct


def main() -> None:
    products = [PairedFlipProduct(symbol) for symbol in SYMBOLS]

    agents = (
        [RetailTrader() for _ in range(NUM_RETAIL_TRADERS)]
        + [RetailInvestor() for _ in range(NUM_RETAIL_TRADERS)]
        + [
            HedgeFund(),
            ArbAgent(),
            ManualAgent(),
        ]
    )
    manual_agent = agents[-1]

    exchange = Exchange(
        tick_size=TICK_SIZE,
    )

    price_aggregator = PriceAggregator(exchange=exchange, products=products)
    plots = [PricePlot(symbol=symbol) for symbol in SYMBOLS]

    def run_info():
        WIDTH = 30
        s = ""

        def add(name, val):
            return f"{name:<{WIDTH}}: {val}\n"

        s += add("SYMBOLS", SYMBOLS)
        s += add("TICK_SIZE", TICK_SIZE)
        s += add("ITER", ITER)
        s += add("DT", DT)
        s += add("FACT", FACT)
        s += add("PAYOUT", PAYOUT)
        s += add("MAX_PAYOUT", MAX_PAYOUT)
        s += add("NUM_RETAIL_TRADERS", NUM_RETAIL_TRADERS)
        s += add("RETAIL_PAYOUT_PRIOR_STRENGTH", RETAIL_PAYOUT_PRIOR_STRENGTH)
        s += add("RETAIL_MIN_CONFIDENCE", RETAIL_MIN_CONFIDENCE)
        s += add("RETAIL_SIZING_RANGE", RETAIL_SIZING_RANGE)
        s += add("RETAIL_ORDER_UPDATE_FREQ", RETAIL_ORDER_UPDATE_FREQ)
        s += add("RETAIL_TRADER_SYMBOL_RATIO", RETAIL_TRADER_SYMBOL_RATIO)
        s += add("MOCK_NAME", MOCK_NAME)

        return s

    sim = MarketSimulation(
        exchanges=exchange,
        agents=agents,
        products=products,
        display_to_console=False,
        dt=DT,
        iter=ITER,
        metrics_aggregator=price_aggregator,
        metrics_plots=plots,
        save_results_path=f"results/{MOCK_NAME}_{int(time.time())}"
        if SAVE_RESULTS
        else None,
        save_run_info=run_info,
    )
    sim.start()

    sim.connect_display(manual_agent.gui)
    manual_agent.gui.run()


if __name__ == "__main__":
    main()
