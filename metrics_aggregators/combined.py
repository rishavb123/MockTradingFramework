from typing import Dict, List, Any

from metrics import MetricsAggregator


class CombinedMetricsAggregator(MetricsAggregator):
    def __init__(
        self,
        *metrics_aggregators: List[MetricsAggregator],
    ) -> None:
        super().__init__()
        self.metrics_aggregators = metrics_aggregators

    def snapshot(self) -> Dict[str, Any]:
        snapshot = {}
        for ma in self.metrics_aggregators:
            snapshot = snapshot | ma.snapshot()
        return snapshot
