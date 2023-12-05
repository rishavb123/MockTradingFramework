from trading_objects import Exchange
from market_simulation import MarketSimulation
from agents import ManualAgent
from metrics_aggregators.prices import PriceAggregator, PricePlot

from .config import *
from .agents import RetailTrader
from .products import PairedFlipProduct


def main() -> None:
    products = [PairedFlipProduct(symbol) for symbol in SYMBOLS]

    agents = [RetailTrader() for _ in range(NUM_RETAIL_TRADERS)] + [ManualAgent()]
    manual_agent = agents[-1]

    exchange = Exchange(
        tick_size=TICK_SIZE,
    )

    price_aggregator = PriceAggregator(exchange=exchange, products=products)
    plots = [PricePlot(symbol=symbol) for symbol in SYMBOLS]

    sim = MarketSimulation(
        exchanges=exchange,
        agents=agents,
        products=products,
        display_to_console=False,
        dt=DT,
        iter=ITER,
        metrics_aggregator=price_aggregator,
        metrics_plots=plots,
        save_results_path=f"results/{MOCK_NAME}",
    )
    sim.start()

    sim.connect_display(manual_agent.gui)
    manual_agent.gui.run()


if __name__ == "__main__":
    main()
