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
    BiasedStockAgent,
    OptimisticBiasedBondAgent,
    RealisticBiasedBondAgent,
)
from .products import CompanyStock, CorporateBond


MANUAL_AGENT_BASE_CLS = None


def main() -> None:
    stock = CompanyStock(COMPANY_SYMBOL)
    bond = CorporateBond(stock)
    products = [stock, bond]

    SYMBOLS = [p.symbol for p in products]

    agents = (
        [BiasedStockAgent(stock) for _ in range(NUM_STOCK_AGENTS)]
        + [OptimisticBiasedBondAgent(bond) for _ in range(NUM_OPT_BOND_AGENTS)]
        + [RealisticBiasedBondAgent(bond) for _ in range(NUM_REAL_BOND_AGENTS)]
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
        info["MU"] = MU
        info["SIGMA"] = SIGMA
        info["STARTING_VALUE"] = STARTING_VALUE
        info["BANKRUPTCY_VALUE_THRESH"] = BANKRUPTCY_VALUE_THRESH
        info["UPDATE_FREQ"] = UPDATE_FREQ
        info["COUPON_PAYOUT"] = COUPON_PAYOUT
        info["COUPON_FREQ"] = COUPON_FREQ
        info["PAR_VALUE"] = PAR_VALUE
        info["MATURITY"] = MATURITY
        info["NUM_STOCK_AGENTS"] = NUM_STOCK_AGENTS
        info["NUM_OPT_BOND_AGENTS"] = NUM_OPT_BOND_AGENTS
        info["NUM_REAL_BOND_AGENTS"] = NUM_REAL_BOND_AGENTS
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
