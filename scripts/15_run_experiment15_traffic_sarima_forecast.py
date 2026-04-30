from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX


ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = (
    ROOT
    / "data"
    / "time_series"
    / "traffic"
    / "beijing_traffic_congestion_2023_2024.xlsx"
)
VALIDATION_PATH = (
    ROOT
    / "data"
    / "time_series"
    / "traffic"
    / "beijing_traffic_congestion_validation.xlsx"
)
OUTPUT_DIR = ROOT / "outputs" / "traffic_sarima_forecast"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


def load_frame(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    df["time"] = pd.to_datetime(df["time"])
    return df.sort_values("time").set_index("time")


def main() -> None:
    if not VALIDATION_PATH.exists():
        message = (
            "未找到交通主题外推验证文件："
            f"{VALIDATION_PATH.relative_to(ROOT).as_posix()}。"
            "该脚本保留给带有额外验证样本的预测对照使用。"
        )
        raise FileNotFoundError(message)

    df_train = load_frame(TRAIN_PATH).interpolate().bfill()
    df_test = load_frame(VALIDATION_PATH)
    df_test_real = df_test.dropna(subset=["rate"])

    model = SARIMAX(
        df_train["rate"],
        order=(1, 1, 2),
        seasonal_order=(1, 1, 1, 7),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    results = model.fit(disp=False)

    forecast_steps = len(df_test)
    forecast_res = results.get_forecast(steps=forecast_steps)
    forecast_df = forecast_res.summary_frame()
    forecast_df.index = df_test.index

    compare_df = pd.DataFrame(
        {
            "actual_rate": df_test["rate"],
            "forecast_rate": forecast_df["mean"],
            "forecast_ci_lower": forecast_df["mean_ci_lower"],
            "forecast_ci_upper": forecast_df["mean_ci_upper"],
        }
    )
    compare_df.to_csv(
        OUTPUT_DIR / "experiment15_sarima_forecast_compare.csv",
        index=True,
        encoding="utf-8-sig",
    )

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(
        df_test_real.index,
        df_test_real["rate"],
        label="验证期真实值",
        color="#2c3e50",
        marker="o",
        linewidth=2,
    )
    ax.plot(
        forecast_df.index,
        forecast_df["mean"],
        label="SARIMA 预测值",
        color="#e74c3c",
        linestyle="--",
        marker="s",
        linewidth=2,
    )
    ax.fill_between(
        forecast_df.index,
        forecast_df["mean_ci_lower"],
        forecast_df["mean_ci_upper"],
        color="#e74c3c",
        alpha=0.1,
        label="95% 置信区间",
    )
    ax.set_title("北京交通拥堵指数外推预测对照")
    ax.set_xlabel("日期")
    ax.set_ylabel("拥堵指数")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.6)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "experiment15_sarima_forecast_compare.png", dpi=180)
    plt.close(fig)

    report_lines = [
        "# 交通主题 SARIMA 外推预测说明",
        "",
        f"- 训练数据：`{TRAIN_PATH.relative_to(ROOT).as_posix()}`",
        f"- 验证数据：`{VALIDATION_PATH.relative_to(ROOT).as_posix()}`",
        f"- 预测步数：{forecast_steps}",
        "- 本脚本用于把固定参数 SARIMA(1,1,2)x(1,1,1,7) 的外推结果与额外验证期做对照。",
        "- 若当前仓库未提供验证期文件，可保留该脚本作为复现实验接口，而不强行生成替代样本。",
    ]
    (OUTPUT_DIR / "experiment15_sarima_forecast_report.md").write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
