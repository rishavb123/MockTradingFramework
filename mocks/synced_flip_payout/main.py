import time

from trading_objects import Exchange
from market_simulation import MarketSimulation
from agents import create_manual_agent
from metrics_aggregators import (
    PriceAggregator,
    PricePlot,
    VolumeAggregator,
    VolumePlot,
    PnlAggregator,
    PnlPlot,
    CombinedMetricsAggregator,
)

from .config import *
from .agents import (
    RetailInvestor,
    RetailTrader,
    BandwagonInvestor,
    HedgeFund,
    ArbAgent,
    MarketMaker,
    WideMaker,
)
from .products import PairedFlipProduct


MANUAL_AGENT_BASE_CLS = None


def main() -> None:
    products = [PairedFlipProduct(symbol) for symbol in SYMBOLS]

    agents = (
        [RetailTrader() for _ in range(NUM_RETAIL_TRADERS)]
        + [RetailInvestor() for _ in range(NUM_RETAIL_INVESTORS)]
        + [BandwagonInvestor() for _ in range(NUM_BANDWAGON_INVESTORS)]
        + [
            HedgeFund(),
            ArbAgent(),
            MarketMaker(),
            WideMaker(),
        ]
    )
    if CONNECT_MANUAL_AGENT:
        manual_agent = create_manual_agent(agent_cls=MANUAL_AGENT_BASE_CLS)
        agents.append(manual_agent)

    agent_classes = list(set([agent.__class__ for agent in agents]))

    exchange = Exchange(
        tick_size=TICK_SIZE,
    )

    pnl_markers = ["mid", "last_traded", "payout", "zero"]

    price_aggregator = PriceAggregator(exchange=exchange, products=products)
    volume_aggregator = VolumeAggregator(
        products=products, window_size=VOLUME_WINDOW_SIZE
    )
    pnl_aggregators = [
        PnlAggregator(agents=agents, mark_to_f=pnl_marker) for pnl_marker in pnl_markers
    ]
    combined_aggregator = CombinedMetricsAggregator(
        price_aggregator, volume_aggregator, *pnl_aggregators
    )
    plots = (
        [PricePlot(symbol=symbol) for symbol in SYMBOLS]
        + [VolumePlot(SYMBOLS)]
        + [
            PnlPlot(agent_class_name=agent_class.__name__, mark_to_f_name=pnl_marker)
            for agent_class in agent_classes
            for pnl_marker in pnl_markers
        ]
    )

    def run_info():
        info = {}

        info["SYMBOLS"] = SYMBOLS
        info["TICK_SIZE"] = TICK_SIZE
        info["ITER"] = ITER
        info["DT"] = DT if CONNECT_MANUAL_AGENT else 0
        info["VOLUME_WINDOW_SIZE"] = VOLUME_WINDOW_SIZE
        info["FACT"] = FACT
        info["PAYOUT"] = PAYOUT
        info["MAX_PAYOUT"] = MAX_PAYOUT
        info["NUM_RETAIL_TRADERS"] = NUM_RETAIL_TRADERS
        info["NUM_RETAIL_INVESTORS"] = NUM_RETAIL_INVESTORS
        info["NUM_BANDWAGON_INVESTORS"] = NUM_BANDWAGON_INVESTORS
        info["RETAIL_PAYOUT_PRIOR_STRENGTH"] = RETAIL_PAYOUT_PRIOR_STRENGTH
        info["RETAIL_MIN_CONFIDENCE"] = RETAIL_MIN_CONFIDENCE
        info["RETAIL_SIZING_RANGE"] = RETAIL_SIZING_RANGE
        info["RETAIL_ORDER_UPDATE_FREQ"] = RETAIL_ORDER_UPDATE_FREQ
        info["RETAIL_TRADER_SYMBOL_RATIO"] = RETAIL_TRADER_SYMBOL_RATIO
        info["MOCK_NAME"] = MOCK_NAME

        return info

    sim = MarketSimulation(
        exchanges=exchange,
        agents=agents,
        products=products,
        display_to_console=DISPLAY_TO_CONSOLE,
        dt=DT if CONNECT_MANUAL_AGENT else 0,
        iter=ITER,
        metrics_aggregator=combined_aggregator,
        metrics_plots=plots,
        save_results_path=f"results/{MOCK_NAME}_{int(time.time())}"
        if SAVE_RESULTS
        else None,
        save_run_info=run_info,
        additional_dirs_required=["graphs/pnls"]
        + [f"graphs/pnls/{pnl_marker}" for pnl_marker in pnl_markers],
    )
    sim.start()

    if CONNECT_MANUAL_AGENT:
        sim.connect_display(manual_agent.gui)
        manual_agent.gui.run()


if __name__ == "__main__":
    main()
