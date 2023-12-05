from __future__ import annotations
from typing import List, Dict, Any, Callable
import numpy as np
import matplotlib as plt

from simulation import SimulationObject


class MetricsAggregator(SimulationObject):
    def __init__(self) -> None:
        super().__init__()
        self.metrics = []

    def snapshot(self) -> Dict[str, Any]:
        return {}

    def update(self) -> None:
        self.metrics.append(self.snapshot())

    def get_metric(self, metric_name: str) -> List[Any]:
        return np.array([snapshot[metric_name] for snapshot in self.metrics])

class MetricsPlots:

    def __init__(self, plot_name: str, metric_names: List[str], plot_f: Callable) -> None:
        self.plot_name = plot_name
        self.metric_names = metric_names
        self.plot_f = plot_f

    def plot(self, agg: MetricsAggregator, results_dir: str) -> None:
        plt.figure()
        self.plot_f({k:agg.get_metric(k) for k in self.metric_names})
        plt.savefig(f"{results_dir}/{self.plot_name}.png")
