from trading_objects import Exchange
from market_simulation import MarketSimulation
from agents import ManualAgent

from .config import *
from .agents import RetailTrader
from .products import PairedFlipProduct


def main() -> None:
    products = [PairedFlipProduct(symbol) for symbol in SYMBOLS]

    agents = [RetailTrader() for _ in range(NUM_RETAIL_TRADERS)]
    manual_agent = ManualAgent()

    sim = MarketSimulation(
        exchanges=Exchange(
            tick_size=TICK_SIZE,
        ),
        agents=[
            *agents,
            manual_agent,
        ],
        products=products,
        display_to_console=False,
        dt=DT,
        iter=ITER,
        save_results_path=f"results/{MOCK_NAME}",
    )
    sim.start()

    sim.connect_display(manual_agent.gui)
    manual_agent.gui.run()


if __name__ == "__main__":
    main()
