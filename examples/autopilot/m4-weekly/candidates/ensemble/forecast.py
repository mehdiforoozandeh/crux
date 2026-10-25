"""An honest stronger baseline: the mean of three statsmodels exponential-smoothing style
forecasts per series -- SES, damped-trend Holt, and the M4 Theta method -- in the spirit of
M4's Comb benchmark (which averages SES, Holt and damped Holt). No seasonal adjustment."""
import os, sys, warnings
from multiprocessing import Pool
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing, SimpleExpSmoothing

H = int(os.environ.get("M4_HORIZON", 13))


def one(y):
    n = len(y)
    t = np.arange(1, n + 1, dtype=float)
    b, a = np.polyfit(t, y, 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ses = SimpleExpSmoothing(y, initialization_method="estimated").fit().forecast(H)
        damped = ExponentialSmoothing(y, trend="add", damped_trend=True,
                                      initialization_method="estimated").fit().forecast(H)
        line2 = SimpleExpSmoothing(2 * y - (a + b * t),
                                   initialization_method="estimated").fit().forecast(H)
    theta = 0.5 * line2 + 0.5 * (a + b * np.arange(n + 1, n + H + 1))
    f = (np.asarray(ses) + np.asarray(damped) + np.maximum(theta, 0.0)) / 3
    return np.where(np.isfinite(f), f, y[-1])


def main():
    df = pd.read_csv(sys.argv[1], index_col=0)
    ys = [row.dropna().to_numpy(float) for _, row in df.iterrows()]
    with Pool(int(os.environ.get("M4_CPUS", 1))) as p:
        fc = p.map(one, ys)
    out = pd.DataFrame(np.vstack(fc), index=df.index, columns=[f"F{i}" for i in range(1, H + 1)])
    out.to_csv(sys.argv[2], index_label="id")


if __name__ == "__main__":
    main()
