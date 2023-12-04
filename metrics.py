from __future__ import annotations
from typing import List, Dict, Any

from simulation import SimulationObject


class MetricAggregator(SimulationObject):
    def __init__(self) -> None:
        super().__init__()
        self.metrics = []

    def snapshot(self) -> Dict[str, Any]:
        return {}

    def update(self) -> None:
        self.metrics.append(self.snapshot())

    def get_metric(self, metric_name: str) -> List[Any]:
        return [snapshot[metric_name] for snapshot in self.metrics]
