import numpy as np

from trading_objects import Agent, Exchange, Product
from market_simulation import MarketSimulation
from agents import SingleExchangeManualAgent

payout = 100 if np.random.random() < 0.5 else 0

class PairedFlipProduct(Product):

    def __init__(self, symbol: str) -> None:
        super().__init__(symbol)

    def payout(self) -> None:
        return payout
    


def main() -> None:

    products = [PairedFlipProduct('A'), PairedFlipProduct('B')]

    agents = []
    manual_agent = SingleExchangeManualAgent()

    sim = MarketSimulation(
        exchanges=Exchange(
            tick_size=1,
        ),
        agents=[
            *agents,
            manual_agent,
        ],
        products=products,
        display_to_console=False,
        dt=0.1,
        iter=10000,
    )
    sim.start()

    sim.connect_display(manual_agent.gui)
    manual_agent.gui.run()


if __name__ == "__main__":
    main()