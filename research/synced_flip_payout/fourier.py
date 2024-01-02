import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy
import scipy.fftpack

from .config import *

filename = f"results/{MOCK_NAME}_{RUN_ID}/data/metrics.csv"

df = pd.read_csv(filename, index_col="time").ffill().bfill()

fourier_df = pd.DataFrame()

for symbol in SYMBOLS:
    mid = (df[f"{symbol}_bid"] + df[f"{symbol}_ask"]) / 2
    df[f"{symbol}_mid"] = mid
    mid_fft = np.fft.fft(mid)
    fourier_df[f"{symbol}_mid_fourier"] = np.abs(mid_fft)

fourier_df.set_index(np.fft.fftfreq(len(df.index)))

k = 1
fourier_df.iloc[k:len(fourier_df.index) // 2].plot()
plt.show()
