import glob
import numpy as np
import matplotlib.pyplot as plt
import json

from .config import *

prefix = f"research/{MOCK_NAME}/dataset/{MOCK_NAME}_"

data = {}

run_ids = [int(dir_name[len(prefix) :]) for dir_name in glob.glob(f"{prefix}*")]

for run_id in run_ids:
    filename = f"research/{MOCK_NAME}/dataset/{MOCK_NAME}_{run_id}/data/agent_pnl.json"
    with open(filename, "rb") as f:
        agent_pnl = json.load(f)
    for agent_name in agent_pnl:
        data[agent_name] = data.get(agent_name, []) + agent_pnl[agent_name]["results"]

for agent_name in data:
    print(f"{agent_name}:")
    mu = np.mean(data[agent_name])
    sigma = np.std(data[agent_name])
    print(f"\tpnl mean: {mu}")
    print(f"\tpnl std: {sigma}")
    print(f"\tsharpe ratio: {mu / sigma}")
    print(f"\tn trials: {len(data[agent_name])}")
    print()

    plt.title(f"{agent_name} pnls")
    plt.hist(data[agent_name], bins=20, color="c", alpha=0.65)
    plt.axvline(0, color="k", linewidth=1)
    plt.axvline(mu, color="b", linewidth=1)
    plt.axvline(mu - sigma, color="r", linestyle="dashed", linewidth=1)
    plt.axvline(mu + sigma, color="r", linestyle="dashed", linewidth=1)
    plt.show()
