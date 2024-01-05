import numpy as np

SYMBOLS = ["A"]
TICK_SIZE = 1
ITER = 1200
DT = 0.1
VOLUME_WINDOW_SIZE = 50

MU = (np.random.random() * 2 - 1) / 25
SIGMA = (np.random.random() / 3 + 0.1) * (-1 if np.random.random() < 0.5 else 1)

NUM_BIASED_AGENTS = 10

MOCK_NAME = "single_company"
SAVE_RESULTS = True

CONNECT_MANUAL_AGENT = True
DISPLAY_TO_CONSOLE = not CONNECT_MANUAL_AGENT
