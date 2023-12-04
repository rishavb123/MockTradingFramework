from typing import Union, List
import threading

from simulation import Simulation
from trading_objects import Agent, Exchange, Product
from command_display import CommandDisplay, Argument, Command
from agents import SingleProductFixedAgent, SingleExchangeManualAgent


class MarketSimulation(Simulation):
    def __init__(
        self,
        exchanges: Union[List[Exchange], Exchange] = [],
        agents: List[Agent] = [],
        products: List[Product] = [],
        dt: Union[float, None] = None,
        iter: int = 100000,
        lock: Union[threading.Lock, None] = None,
        display_to_console: bool = False,
    ) -> None:
        if isinstance(exchanges, Exchange):
            exchanges = [exchanges]
        self.exchanges = exchanges
        self.agents = agents
        self.display_to_console = display_to_console
        for exchange in exchanges:
            for agent in agents:
                exchange.register_agent(agent)
            for product in products:
                exchange.register_product(product)

        simulation_objs = exchanges + agents
        super().__init__(dt, iter, lock, simulation_objs)

    def update(self) -> None:
        super().update()
        if self.display_to_console:
            for exchange in self.exchanges:
                print(exchange.display_str(viewer=self.agents[1]))


def main() -> None:

    symbols = ["AAAA", "BBBB", "CCCC"]

    fixed_agents = [SingleProductFixedAgent(7, 13, 100, symbol) for symbol in symbols]
    manual_agent = SingleExchangeManualAgent()

    sim = MarketSimulation(
        exchanges=Exchange(
            tick_size=0.05,
        ),
        agents=[
            *fixed_agents,
            manual_agent,
        ],
        products=[Product(symbol) for symbol in symbols],
        display_to_console=False,
        dt=1,
        iter=100,
    )
    sim.start()

    sim.connect_display(manual_agent.gui)
    manual_agent.gui.run()


if __name__ == "__main__":
    main()
