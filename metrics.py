from __future__ import annotations
import matplotlib

matplotlib.use("Agg")

from typing import List, Dict, Any, Callable
import numpy as np
import matplotlib.pyplot as plt
import csv
import json

from simulation import SimulationObject, Time


class MetricsAggregator(SimulationObject):
    def __init__(self, initial_metrics: List[Dict[str, Any]] = []) -> None:
        super().__init__()
        self.metrics = initial_metrics

    def snapshot(self) -> Dict[str, Any]:
        return {}

    def update(self) -> None:
        self.metrics.append(self.snapshot() | {"time": Time.now})

    def get_metric(self, metric_name: str) -> List[Any]:
        def none_to_nan(x):
            return np.nan if x is None else x

        return np.array(
            [none_to_nan(snapshot[metric_name]) for snapshot in self.metrics]
        )

    def save_to_json(self, fname: str) -> None:
        if len(self.metrics) > 0:
            with open(fname, "w") as f:
                json.dump(self.metrics, f, ensure_ascii=False, indent=4)

    def save_to_csv(self, fname: str) -> None:
        if len(self.metrics) > 0:
            with open(fname, "w", newline="") as f:
                w = csv.DictWriter(f, self.metrics[0].keys())
                w.writeheader()
                w.writerows(self.metrics)


class MetricsPlots:
    def __init__(
        self, plot_name: str, metric_names: List[str], plot_f: Callable
    ) -> None:
        self.plot_name = plot_name
        self.metric_names = metric_names
        self.plot_f = plot_f

    def plot(self, agg: MetricsAggregator, results_dir: str) -> None:
        plt.figure()
        self.plot_f(**{k: agg.get_metric(k) for k in self.metric_names})
        plt.savefig(f"{results_dir}/{self.plot_name}.png")
