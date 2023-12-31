import numpy as np

MAX_PAYOUT = 100


def generate_fact(thresh=0.5):
    return 2 * (np.random.random() < thresh) - 1


def fact_to_payout(fact):
    return MAX_PAYOUT * (fact + 1) // 2


SYMBOLS = ["A", "B"]
TICK_SIZE = 1
ITER = 1200
DT = 0.1
VOLUME_WINDOW_SIZE = 50

FACT = generate_fact()
PAYOUT = fact_to_payout(FACT)

NUM_RETAIL_TRADERS = 40
NUM_RETAIL_INVESTORS = 20
NUM_BANDWAGON_INVESTORS = 1
RETAIL_PAYOUT_PRIOR_STRENGTH = 0.015
RETAIL_MIN_CONFIDENCE = 0.5
RETAIL_SIZING_RANGE = (1, 6)
RETAIL_ORDER_UPDATE_FREQ = 0.1
RETAIL_TRADER_SYMBOL_RATIO = [0.65, 0.35]

MOCK_NAME = "synced_flip_payout"
SAVE_RESULTS = True

CONNECT_MANUAL_AGENT = True
DISPLAY_TO_CONSOLE = not CONNECT_MANUAL_AGENT
