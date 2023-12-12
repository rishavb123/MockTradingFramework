from typing import Any, Callable, Dict, List, Union
import numpy as np
import matplotlib.pyplot as plt

from trading_objects import Agent
from metrics import MetricsAggregator, MetricsPlots


class PnlAggregator(MetricsAggregator):
    def __init__(
        self, agents: List[Agent], mark_to_f: Union[Callable, str] = "mid"
    ) -> None:
        super().__init__()
        self.agents = agents
        self.mark_to_f = mark_to_f
        if type(mark_to_f) == str:
            self.mark_to_f_name = mark_to_f
        else:
            self.mark_to_f_name = mark_to_f.__name__

    def snapshot(self) -> Dict[str, Any]:
        pnls_per_class = {}
        for agent in self.agents:
            if agent.__class__ not in pnls_per_class:
                pnls_per_class[agent.__class__] = []

            pnls_per_class[agent.__class__].append(agent.get_marked_pnl())

        return (
            {
                f"{k.__name__}_{self.mark_to_f_name}_pnl_mean": np.mean(
                    pnls_per_class[k]
                ).astype(np.float64)
                for k in pnls_per_class.keys()
            }
            | {
                f"{k.__name__}_{self.mark_to_f_name}_pnl_std": np.std(
                    pnls_per_class[k]
                ).astype(np.float64)
                for k in pnls_per_class.keys()
            }
            | {
                f"{k.__name__}_{self.mark_to_f_name}_pnl_max": np.max(
                    pnls_per_class[k]
                ).astype(np.float64)
                for k in pnls_per_class.keys()
            }
            | {
                f"{k.__name__}_{self.mark_to_f_name}_pnl_min": np.min(
                    pnls_per_class[k]
                ).astype(np.float64)
                for k in pnls_per_class.keys()
            }
        )


class PnlPlot(MetricsPlots):
    def __init__(self, agent_class_name: str, mark_to_f_name: str) -> None:
        self.agent_class_name = agent_class_name
        self.mark_to_f_name = mark_to_f_name
        super().__init__(
            f"pnls/{self.mark_to_f_name}/{self.agent_class_name}_pnl",
            [
                f"{self.agent_class_name}_{self.mark_to_f_name}_pnl_mean",
                f"{self.agent_class_name}_{self.mark_to_f_name}_pnl_std",
                f"{self.agent_class_name}_{self.mark_to_f_name}_pnl_min",
                f"{self.agent_class_name}_{self.mark_to_f_name}_pnl_max",
                "time",
            ],
            self.pnl_plot,
        )

    def pnl_plot(self, **kwargs):
        pnl_means = kwargs[f"{self.agent_class_name}_{self.mark_to_f_name}_pnl_mean"]
        pnl_stds = kwargs[f"{self.agent_class_name}_{self.mark_to_f_name}_pnl_std"]

        bottom_band = pnl_means - pnl_stds
        top_band = pnl_means + pnl_stds

        pnl_min = kwargs[f"{self.agent_class_name}_{self.mark_to_f_name}_pnl_min"]
        pnl_max = kwargs[f"{self.agent_class_name}_{self.mark_to_f_name}_pnl_max"]

        times = kwargs["time"]

        plt.plot(times, [0 for _ in times], label="0", c="red", alpha=0.5)
        plt.plot(
            times,
            pnl_min,
            label="min pnl",
            c="red",
            alpha=0.5,
        )
        plt.plot(
            times,
            pnl_max,
            label="max pnl",
            c="green",
            alpha=0.5,
        )
        plt.plot(
            times,
            bottom_band,
            label="pnl - std",
            c="purple",
            alpha=0.5,
        )
        plt.plot(
            times,
            top_band,
            label="pnl + std",
            c="orange",
            alpha=0.5,
        )

        plt.plot(times, pnl_means, label="average pnl", c="blue", alpha=0.9)

        plt.title(
            f"{self.agent_class_name} PNL Marked to {self.mark_to_f_name.title()}"
        )
        plt.xlabel("Time")
        plt.ylabel("PNL")

        plt.legend()
