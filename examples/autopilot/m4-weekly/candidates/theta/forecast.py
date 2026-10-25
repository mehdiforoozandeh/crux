"""The M4 Theta benchmark (Theta.classic in M4's "Benchmarks and Evaluation.R") for Weekly
series: no seasonal adjustment (Weekly Frequency is 1 in M4), theta line 0 = OLS linear
trend, theta line 2 = 2*y - trend smoothed by SES, forecast = mean of the two lines,
negative forecasts set to 0. SES here is statsmodels' (optimised alpha and initial level),
not R forecast::ses, so the numbers differ slightly from the published Theta forecasts."""
import os, sys, warnings
from multiprocessing import Pool
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

H = int(os.environ.get("M4_HORIZON", 13))


def theta(y):
    n = len(y)
    t = np.arange(1, n + 1, dtype=float)
    b, a = np.polyfit(t, y, 1)
    line0_out = a + b * np.arange(n + 1, n + H + 1)
    line2 = 2 * y - (a + b * t)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ses = SimpleExpSmoothing(line2, initialization_method="estimated").fit()
    f = 0.5 * ses.forecast(H) + 0.5 * line0_out
    return np.maximum(f, 0.0)


def main():
    df = pd.read_csv(sys.argv[1], index_col=0)
    ys = [row.dropna().to_numpy(float) for _, row in df.iterrows()]
    with Pool(int(os.environ.get("M4_CPUS", 1))) as p:
        fc = p.map(theta, ys)
    out = pd.DataFrame(np.vstack(fc), index=df.index, columns=[f"F{i}" for i in range(1, H + 1)])
    out.to_csv(sys.argv[2], index_label="id")


if __name__ == "__main__":
    main()
