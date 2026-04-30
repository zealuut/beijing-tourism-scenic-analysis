from __future__ import annotations

from pathlib import Path
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.statespace.sarimax import SARIMAX


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = (
    ROOT
    / "data"
    / "time_series"
    / "traffic"
    / "beijing_traffic_congestion_2023_2024.xlsx"
)
OUTPUT_DIR = ROOT / "outputs" / "traffic_sarima"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

warnings.filterwarnings("ignore")
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


def plot_and_test(series: pd.Series, title: str, filename: str) -> float:
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(series.index, series.values, color="tab:blue", linewidth=1.4)
    ax.set_title(title)
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=180)
    plt.close(fig)
    return adfuller(series.dropna())[1]


def main() -> None:
    df = pd.read_excel(INPUT_PATH)
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").set_index("time")
    df["rate"] = df["rate"].interpolate(method="linear").bfill()

    raw_p = plot_and_test(df["rate"], "北京交通拥堵指数原始序列", "experiment14_raw_timeseries.png")

    d = 1
    df_diff = df["rate"].diff().dropna()
    diff_p = plot_and_test(
        df_diff,
        "北京交通拥堵指数一阶差分序列",
        "experiment14_diff_timeseries.png",
    )

    p_range = range(0, 3)
    q_range = range(0, 3)
    seasonal_order = (1, 1, 1, 7)
    best_aic = float("inf")
    best_order = (0, d, 0)

    for p in p_range:
        for q in q_range:
            try:
                tmp_model = SARIMAX(
                    df["rate"],
                    order=(p, d, q),
                    seasonal_order=seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                tmp_res = tmp_model.fit(disp=False)
            except Exception:
                continue
            if tmp_res.aic < best_aic:
                best_aic = tmp_res.aic
                best_order = (p, d, q)

    final_model = SARIMAX(
        df["rate"],
        order=best_order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    final_results = final_model.fit(disp=False)

    residuals = final_results.resid[seasonal_order[3] + 1 :]
    lb_res = acorr_ljungbox(residuals, lags=[10], return_df=True)
    lb_pvalue = float(lb_res["lb_pvalue"].iloc[0])

    residual_frame = pd.DataFrame({"time": residuals.index, "residual": residuals.values})
    residual_frame.to_csv(
        OUTPUT_DIR / "experiment14_residuals.csv",
        index=False,
        encoding="utf-8-sig",
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 4))
    axes[0].plot(residuals.index, residuals.values, color="#2E86AB", linewidth=1.2)
    axes[0].set_title("SARIMA 残差序列")
    axes[0].grid(True, linestyle="--", alpha=0.5)
    plot_acf(residuals, ax=axes[1], lags=40, title="SARIMA 残差 ACF")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "experiment14_residual_diagnostics.png", dpi=180)
    plt.close(fig)

    summary_text = final_results.summary().as_text()
    (OUTPUT_DIR / "experiment14_sarima_summary.txt").write_text(summary_text, encoding="utf-8")

    report_lines = [
        "# 交通主题 SARIMA 建模报告",
        "",
        f"- 输入数据：`{INPUT_PATH.relative_to(ROOT).as_posix()}`",
        f"- 样本期：{df.index.min().date().isoformat()} 至 {df.index.max().date().isoformat()}",
        f"- 原始序列 ADF p 值：{raw_p:.6f}",
        f"- 一阶差分后 ADF p 值：{diff_p:.6f}",
        f"- 最优阶数：SARIMA{best_order}x{seasonal_order}",
        f"- AIC：{best_aic:.4f}",
        f"- Ljung-Box p 值：{lb_pvalue:.6f}",
        "- 若 p 值大于 0.05，可将残差视为近似白噪声，说明模型已提取主要时序结构。",
    ]
    (OUTPUT_DIR / "experiment14_sarima_report.md").write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
