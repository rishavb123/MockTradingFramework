import matplotlib

matplotlib.use("Agg")

import os
import shutil

from typing import Union, List, Callable, Dict, Any

import threading
import numpy as np
import matplotlib.pyplot as plt
import json

from simulation import Simulation
from trading_objects import Agent, Exchange, Product, Account
from agents import SingleProductFixedAgent, ManualAgent
from metrics import MetricsAggregator, MetricsPlots


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
        payout_on_finish: bool = True,
        metrics_aggregator: Union[MetricsAggregator, None] = None,
        metrics_plots: List[MetricsPlots] = [],
        save_results_path: Union[str, None] = None,
        save_run_info: Union[Callable[[None], Dict[str, Any]], None] = None,
    ) -> None:
        if isinstance(exchanges, Exchange):
            exchanges = [exchanges]
        self.exchanges = exchanges
        self.agents = agents
        self.display_to_console = display_to_console
        self.payout_on_finish = payout_on_finish
        self.save_results_path = save_results_path
        self.save_run_info = save_run_info
        self.metrics_aggregator = metrics_aggregator
        self.metrics_plots = metrics_plots
        for exchange in exchanges:
            for product in products:
                exchange.register_product(product)
            for agent in agents:
                exchange.register_agent(agent)
        simulation_objs = exchanges + agents
        if self.metrics_aggregator is not None:
            simulation_objs.append(self.metrics_aggregator)
        super().__init__(dt, iter, lock, simulation_objs)

    def update(self) -> None:
        super().update()
        if self.display_to_console:
            for exchange in self.exchanges:
                print(exchange.display_str(viewer=self.agents[1]))

    def on_finish(self) -> None:
        super().on_finish()
        if self.save_results_path is not None:
            if os.path.exists(self.save_results_path):
                shutil.rmtree(self.save_results_path)
            os.mkdir(self.save_results_path)
        if self.payout_on_finish:
            for exchange in self.exchanges:
                exchange.payout_for_holdings()
        cash_results = [
            sum(
                [
                    exchange.get_account_holdings(agent)[Account.CASH_SYM]
                    for exchange in self.exchanges
                ]
            )
            for agent in self.agents
        ]
        cash_results_by_cls = {}
        for i in range(len(self.agents)):
            cash = cash_results[i]
            agent = self.agents[i]
            if agent.__class__.__name__ not in cash_results_by_cls:
                cash_results_by_cls[agent.__class__.__name__] = []
            cash_results_by_cls[agent.__class__.__name__].append(cash)
        agent_classes = [c for c in cash_results_by_cls]
        cash_means_by_cls = [np.mean(cash_results_by_cls[c]) for c in agent_classes]
        cash_stds_by_cls = [np.std(cash_results_by_cls[c]) for c in agent_classes]

        if self.save_results_path:
            plt.figure()
            plt.bar(
                agent_classes,
                cash_means_by_cls,
                color=[("red" if c < 0 else "green") for c in cash_means_by_cls],
            )
            plt.errorbar(
                agent_classes,
                cash_means_by_cls,
                yerr=cash_stds_by_cls,
                fmt="o",
                c="blue",
            )
            plt.xlabel("Agent Class")
            plt.ylabel("PNL")
            plt.title("PNL by Agent Class")
            plt.savefig(f"{self.save_results_path}/pnl_by_agent_cls.png")

            with open(f"{self.save_results_path}/agent_pnl.json", "w") as f:
                json.dump(
                    {
                        agent_cls: {
                            "mean": cash_mean,
                            "std": cash_std,
                            "results": cash_results_by_cls[agent_cls],
                        }
                        for agent_cls, cash_mean, cash_std in zip(
                            agent_classes, cash_means_by_cls, cash_stds_by_cls
                        )
                    },
                    f,
                    ensure_ascii=False,
                    indent=4,
                )

            if self.metrics_aggregator is not None:
                for plot in self.metrics_plots:
                    plot.plot(self.metrics_aggregator, self.save_results_path)

            with open(f"{self.save_results_path}/info.json", "w") as f:
                json.dump(self.save_run_info(), f, ensure_ascii=False, indent=4)


def main() -> None:
    symbols = ["AAAA", "BBBB", "CCCC"]

    fixed_agents = [SingleProductFixedAgent(7, 13, 100, symbol) for symbol in symbols]
    manual_agent = ManualAgent()

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
