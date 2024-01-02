import os
import glob

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy
import tensorflow as tf

from .config import *

# Data Loading and Preprocessing

prefix = f"results/{MOCK_NAME}_"
lookahead_time = 10
lookback_times = [1, 2, 5, 10]
metric_names = [
    "bid",
    "bid_size",
    "ask",
    "ask_size",
    "last_traded_price",
    "volume_per_tick",
]
columns = sum(
    [[f"{symbol}_{metric_name}" for metric_name in metric_names] for symbol in SYMBOLS],
    start=[],
)

run_ids = [int(dir_name[len(prefix) :]) for dir_name in glob.glob(f"{prefix}*")]

full_dataset = []

future_stats = ["bid", "ask"]
normalization_params_list = [
    (
        params[0]
        + [
            f"past_{lookback_time}_{metric_name}"
            for lookback_time in lookback_times
            for metric_name in params[0]
            if "future" not in metric_name
        ],
        params[1],
    )
    for params in [
        (
            ["bid_size"],
            "ask_size",
        ),
        (["volume_per_tick"], None),
        (
            [
                "bid",
                "ask",
                f"future_{lookahead_time}_bid",
                f"future_{lookahead_time}_ask",
            ],
            "last_traded_price",
        ),
    ]
]


for run_id in run_ids:
    filename = f"results/{MOCK_NAME}_{run_id}/data/metrics.csv"

    df = pd.read_csv(filename, index_col="time")[columns].ffill().bfill().iloc[:-100]

    for symbol in SYMBOLS:
        for lookback_time in lookback_times:
            df_past = df.shift(lookback_time)
            for metric_name in metric_names:
                df[f"{symbol}_past_{lookback_time}_{metric_name}"] = df_past[
                    f"{symbol}_{metric_name}"
                ]

        df_future = df.shift(-lookahead_time)

        for stat in future_stats:
            df[f"{symbol}_future_{lookahead_time}_{stat}"] = df_future[
                f"{symbol}_{stat}"
            ]

    df.index = df.index + 10 * run_id
    df = df.dropna()

    normalized_df = pd.DataFrame()

    for to_normalize_list, normalize_by in normalization_params_list:
        for to_normalize in to_normalize_list:
            for symbol in SYMBOLS:
                if normalize_by is None:
                    normalized_df[f"{symbol}_{to_normalize}"] = df[
                        f"{symbol}_{to_normalize}"
                    ]
                else:
                    normalized_df[
                        f"{symbol}_{to_normalize}_normalized_by_{normalize_by}"
                    ] = (
                        df[f"{symbol}_{to_normalize}"] - df[f"{symbol}_{normalize_by}"]
                    )

    full_dataset.append(normalized_df)

df = pd.concat(full_dataset)
df = df.dropna()
df = df.sample(frac=1)

print(df.head())
print(df.shape)

# Train a neural network

train_frac = 0.8
epochs = 20
relu_alpha = 0.3

x_columns = [column_name for column_name in df.columns if "future" not in column_name]
y_columns = [column_name for column_name in df.columns if "future" in column_name]

print(x_columns, y_columns)

X = df[x_columns].values
y = df[y_columns].values
n = len(X)

X_train = X[: int(train_frac * n)]
y_train = y[: int(train_frac * n)]
X_test = X[int(train_frac * n) :]
y_test = y[int(train_frac * n) :]
print(n, X.shape)

model = tf.keras.models.Sequential()
model.add(tf.keras.layers.Dense(24, input_shape=(len(x_columns),)))
model.add(tf.keras.layers.LeakyReLU(relu_alpha))
model.add(tf.keras.layers.Dense(16))
model.add(tf.keras.layers.LeakyReLU(relu_alpha))
model.add(tf.keras.layers.Dense(10))
model.add(tf.keras.layers.LeakyReLU(relu_alpha))
model.add(tf.keras.layers.Dense(len(y_columns)))

model.compile(loss="mse", optimizer="adam")
model.summary()

print("Training...")
model.fit(X_train, y_train, epochs=epochs)

print("\nEvaluation:")
model.evaluate(X_test, y_test)

model.save(
    f"models/{MOCK_NAME}/model_{lookahead_time}_{'o'.join([str(lookback_time) for lookback_time in lookback_times])}.keras"
)  # load with tf.keras.models.load_model(filename)
