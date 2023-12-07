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
        + [RetailInvestor() for _ in range(NUM_RETAIL_INVESTORS)]
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
        info = {}

        info["SYMBOLS"] = SYMBOLS
        info["TICK_SIZE"] = TICK_SIZE
        info["ITER"] = ITER
        info["DT"] = DT
        info["FACT"] = FACT
        info["PAYOUT"] = PAYOUT
        info["MAX_PAYOUT"] = MAX_PAYOUT
        info["NUM_RETAIL_TRADERS"] = NUM_RETAIL_TRADERS
        info["NUM_RETAIL_INVESTORS"] = NUM_RETAIL_INVESTORS
        info["RETAIL_PAYOUT_PRIOR_STRENGTH"] = RETAIL_PAYOUT_PRIOR_STRENGTH
        info["RETAIL_MIN_CONFIDENCE"] = RETAIL_MIN_CONFIDENCE
        info["RETAIL_SIZING_RANGE"] = RETAIL_SIZING_RANGE
        info["RETAIL_ORDER_UPDATE_FREQ"] = RETAIL_ORDER_UPDATE_FREQ
        info["RETAIL_TRADER_SYMBOL_RATIO"] = RETAIL_TRADER_SYMBOL_RATIO
        info["MOCK_NAME"] = MOCK_NAME

        return info

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
