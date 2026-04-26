from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "多元数据" / "multi_data_for_MetaLSTM.xlsx"
DATA_DIR = ROOT / "data" / "multivariate"
OUTPUT_DIR = ROOT / "outputs" / "dynamic_case_study"


MAIN_FEATURES = [
    "log_zoo_index",
    "aqi_good_z",
    "is_weekend",
    "is_holiday",
    "is_school_holiday",
    "log_ticket_lag1",
    "log_ticket_lag7",
]

LAG_WINDOW = 14


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def p_value_from_z(z_value: float) -> float:
    return 2 * (1 - normal_cdf(abs(z_value)))


def significance_star(p_value: float) -> str:
    if p_value < 0.01:
        return "***"
    if p_value < 0.05:
        return "**"
    if p_value < 0.1:
        return "*"
    return ""


def softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.nanmax(values)
    exp_values = np.exp(shifted)
    total = exp_values.sum()
    if total == 0:
        return np.full_like(values, 1 / len(values))
    return exp_values / total


def fit_ols_hac(df: pd.DataFrame, y_col: str, feature_cols: Iterable[str], hac_lag: int = 7) -> dict:
    work = df[[y_col, *feature_cols]].dropna().copy()
    y = work[y_col].to_numpy(dtype=float)
    x = work[list(feature_cols)].to_numpy(dtype=float)
    x = np.column_stack([np.ones(len(work)), x])
    names = ["const", *feature_cols]

    xtx = x.T @ x
    xtx_inv = np.linalg.inv(xtx)
    beta = xtx_inv @ (x.T @ y)
    resid = y - x @ beta
    n = len(y)
    k = x.shape[1]

    s = np.zeros((k, k))
    for t in range(n):
        xt = x[t : t + 1].T
        s += resid[t] ** 2 * (xt @ xt.T)

    for lag in range(1, hac_lag + 1):
        weight = 1 - lag / (hac_lag + 1)
        gamma = np.zeros((k, k))
        for t in range(lag, n):
            xt = x[t : t + 1].T
            xl = x[t - lag : t - lag + 1].T
            gamma += resid[t] * resid[t - lag] * (xt @ xl.T)
        s += weight * (gamma + gamma.T)

    cov = xtx_inv @ s @ xtx_inv
    se = np.sqrt(np.diag(cov))
    z_values = beta / se
    p_values = np.array([p_value_from_z(value) for value in z_values])
    fitted = x @ beta
    r2 = 1 - ((y - fitted) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k)

    coef_table = pd.DataFrame(
        {
            "term": names,
            "coef": beta,
            "std_error_hac": se,
            "z_value": z_values,
            "p_value": p_values,
            "signif": [significance_star(v) for v in p_values],
        }
    )

    return {
        "n": n,
        "k": k,
        "r2": r2,
        "adj_r2": adj_r2,
        "coef_table": coef_table,
        "fitted": pd.Series(fitted, index=work.index, name="fitted"),
        "resid": pd.Series(resid, index=work.index, name="resid"),
        "used_index": work.index,
    }


def format_effect(term: str, coef: float) -> str:
    if term == "const":
        return "截距项"
    if term in {"log_zoo_index", "log_ticket_lag1", "log_ticket_lag7"}:
        return f"弹性解释：自变量增加1%，目标约变化 {coef:.3f}%"
    if term in {"is_weekend", "is_holiday", "is_school_holiday"}:
        pct = (math.exp(coef) - 1) * 100
        return f"相对非该状态日，目标约变化 {pct:.2f}%"
    if term == "aqi_good_z":
        pct = (math.exp(coef) - 1) * 100
        return f"AQI改善1个标准差，目标约变化 {pct:.2f}%"
    return ""


def prepare_panel() -> pd.DataFrame:
    df = pd.read_excel(INPUT_PATH).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    df["log_ticket_index"] = np.log1p(df["ticket_index"])
    df["log_zoo_index"] = np.log1p(df["zoo_index"])
    df["aqi_good"] = df["AQI"].max() - df["AQI"]
    df["aqi_good_z"] = (df["aqi_good"] - df["aqi_good"].mean()) / df["aqi_good"].std(ddof=0)

    df["ticket_lag1"] = df["ticket_index"].shift(1)
    df["ticket_lag7"] = df["ticket_index"].shift(7)
    df["ticket_ma7_prev"] = df["ticket_index"].shift(1).rolling(7).mean()
    df["log_ticket_lag1"] = np.log1p(df["ticket_lag1"])
    df["log_ticket_lag7"] = np.log1p(df["ticket_lag7"])
    df["log_ticket_ma7_prev"] = np.log1p(df["ticket_ma7_prev"])

    df["high_pressure_day"] = (df["ticket_index"] >= df["ticket_index"].quantile(0.9)).astype(int)
    df["very_high_pressure_day"] = (df["ticket_index"] >= df["ticket_index"].quantile(0.95)).astype(int)
    df["moderate_pressure_day"] = (
        (df["ticket_index"] >= df["ticket_index"].quantile(0.4))
        & (df["ticket_index"] <= df["ticket_index"].quantile(0.6))
    ).astype(int)

    return df


def build_attention_weights(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    work = df.copy()
    for lag in range(1, LAG_WINDOW + 1):
        work[f"log_ticket_lag{lag}"] = np.log1p(work["ticket_index"].shift(lag))
        work[f"log_zoo_lag{lag}"] = np.log1p(work["zoo_index"].shift(lag))

    feature_cols = []
    for lag in range(1, LAG_WINDOW + 1):
        feature_cols.extend([f"log_ticket_lag{lag}", f"log_zoo_lag{lag}"])

    model = fit_ols_hac(work, "log_ticket_index", feature_cols, hac_lag=7)
    coef_table = model["coef_table"].set_index("term")

    zscored = work.copy()
    for col in feature_cols:
        mean = zscored[col].mean()
        std = zscored[col].std(ddof=0)
        zscored[col] = (zscored[col] - mean) / std if std not in (0, np.nan) else 0

    heat_rows = []
    for idx, row in zscored.iterrows():
        contributions = []
        for lag in range(1, LAG_WINDOW + 1):
            ticket_term = f"log_ticket_lag{lag}"
            zoo_term = f"log_zoo_lag{lag}"
            ticket_coef = coef_table.at[ticket_term, "coef"] if ticket_term in coef_table.index else 0.0
            zoo_coef = coef_table.at[zoo_term, "coef"] if zoo_term in coef_table.index else 0.0
            value = abs(ticket_coef * row[ticket_term]) + abs(zoo_coef * row[zoo_term])
            contributions.append(value)
        if np.isnan(contributions).any():
            continue
        weights = softmax(np.array(contributions, dtype=float))
        record = {"date": row["date"], "high_pressure_day": row["high_pressure_day"], "moderate_pressure_day": row["moderate_pressure_day"]}
        for lag in range(1, LAG_WINDOW + 1):
            record[f"lag_{lag}"] = weights[lag - 1]
        heat_rows.append(record)

    heat_df = pd.DataFrame(heat_rows)
    summary = pd.DataFrame(
        [
            {"group_name": "高压日", **heat_df.loc[heat_df["high_pressure_day"] == 1, [f"lag_{i}" for i in range(1, LAG_WINDOW + 1)]].mean().to_dict()},
            {"group_name": "常态日", **heat_df.loc[heat_df["moderate_pressure_day"] == 1, [f"lag_{i}" for i in range(1, LAG_WINDOW + 1)]].mean().to_dict()},
        ]
    )
    return summary, model["coef_table"]


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text{font-family:"Microsoft YaHei","SimHei","Arial Unicode MS",sans-serif;fill:#222} .title{font-size:22px;font-weight:700} .label{font-size:14px} .tick{font-size:11px;fill:#555} .legend{font-size:13px}</style>',
        '<rect width="100%" height="100%" fill="white"/>',
    ]


def write_svg(path: Path, elements: list[str]) -> None:
    path.write_text("\n".join(elements + ["</svg>"]), encoding="utf-8")


def render_time_series(df: pd.DataFrame, path: Path) -> None:
    width, height = 1120, 520
    left, right, top, bottom = 70, 30, 65, 70
    plot_w = width - left - right
    plot_h = height - top - bottom

    values = df["ticket_index"].to_numpy(dtype=float)
    n = len(df)
    y_min, y_max = 0, math.ceil(values.max() / 200) * 200

    def sx(i: int) -> float:
        return left + i / (n - 1) * plot_w

    def sy(v: float) -> float:
        return top + plot_h - (v - y_min) / (y_max - y_min) * plot_h

    elements = svg_header(width, height)
    elements.append(f'<text x="{width/2}" y="36" text-anchor="middle" class="title">北京动物园门票关注指数时间序列</text>')
    elements.append(f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#333" stroke-width="1.2"/>')
    elements.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#333" stroke-width="1.2"/>')

    for tick in np.linspace(y_min, y_max, 6):
        py = sy(tick)
        elements.append(f'<line x1="{left}" y1="{py}" x2="{left+plot_w}" y2="{py}" stroke="#e5e5e5"/>')
        elements.append(f'<text x="{left-8}" y="{py+4}" text-anchor="end" class="tick">{int(tick)}</text>')

    year_positions = df.groupby(df["date"].dt.year).head(1).index.tolist()
    for idx in year_positions:
        px = sx(idx)
        year = df.loc[idx, "date"].year
        elements.append(f'<line x1="{px}" y1="{top}" x2="{px}" y2="{top+plot_h}" stroke="#f0f0f0"/>')
        elements.append(f'<text x="{px}" y="{top+plot_h+20}" text-anchor="middle" class="tick">{year}</text>')

    points = " ".join(f"{sx(i)},{sy(v)}" for i, v in enumerate(values))
    elements.append(f'<polyline points="{points}" fill="none" stroke="#2E86AB" stroke-width="1.5"/>')

    high_idx = df.index[df["high_pressure_day"] == 1].tolist()
    for idx in high_idx:
        px = sx(idx)
        py = sy(df.loc[idx, "ticket_index"])
        elements.append(f'<circle cx="{px}" cy="{py}" r="2.4" fill="#D1495B" opacity="0.75"/>')

    elements.append(f'<text x="{width-230}" y="90" class="legend" fill="#2E86AB">蓝线：ticket_index</text>')
    elements.append(f'<text x="{width-230}" y="112" class="legend" fill="#D1495B">红点：高压日（前10%）</text>')
    write_svg(path, elements)


def render_attention_heatmap(summary: pd.DataFrame, path: Path) -> None:
    width, height = 1000, 300
    left, top = 110, 80
    cell_w, cell_h = 54, 54
    lags = [f"lag_{i}" for i in range(1, LAG_WINDOW + 1)]

    elements = svg_header(width, height)
    elements.append(f'<text x="{width/2}" y="36" text-anchor="middle" class="title">时滞 attention 风格热力图</text>')
    elements.append(f'<text x="{width/2}" y="58" text-anchor="middle" class="tick">基于滞后贡献绝对值经 softmax 归一化，仅用于叙事可视化</text>')

    for j, lag in enumerate(lags):
        x = left + j * cell_w
        elements.append(f'<text x="{x + cell_w/2}" y="{top - 12}" text-anchor="middle" class="tick">{lag.replace("_", "")}</text>')

    for i, (_, row) in enumerate(summary.iterrows()):
        y = top + i * cell_h
        elements.append(f'<text x="{left-16}" y="{y + cell_h/2 + 4}" text-anchor="end" class="label">{row["group_name"]}</text>')
        for j, lag in enumerate(lags):
            value = row[lag]
            intensity = int(255 - min(max(value * 1800, 0), 180))
            fill = f"rgb(209,{intensity},{intensity})"
            x = left + j * cell_w
            elements.append(f'<rect x="{x}" y="{y}" width="{cell_w-2}" height="{cell_h-2}" fill="{fill}" stroke="#fff"/>')
            elements.append(f'<text x="{x + cell_w/2}" y="{y + cell_h/2 + 4}" text-anchor="middle" class="tick">{value:.2f}</text>')

    write_svg(path, elements)


def render_coef_svg(coef_df: pd.DataFrame, path: Path) -> None:
    plot_df = coef_df.loc[coef_df["term"] != "const"].copy()
    width, height = 980, 420
    left, right, top, bottom = 240, 40, 60, 50
    plot_w = width - left - right
    plot_h = height - top - bottom

    min_x = float(min(plot_df["coef"].min(), 0))
    max_x = float(max(plot_df["coef"].max(), 0))
    pad = (max_x - min_x) * 0.1 if max_x != min_x else 0.1
    min_x -= pad
    max_x += pad

    def sx(v: float) -> float:
        return left + (v - min_x) / (max_x - min_x) * plot_w

    elements = svg_header(width, height)
    elements.append(f'<text x="{width/2}" y="34" text-anchor="middle" class="title">动态回归系数图（HAC稳健标准误）</text>')
    zero_x = sx(0)
    elements.append(f'<line x1="{zero_x}" y1="{top}" x2="{zero_x}" y2="{top+plot_h}" stroke="#999" stroke-dasharray="4,4"/>')

    row_h = plot_h / len(plot_df)
    for i, (_, row) in enumerate(plot_df.iterrows()):
        y = top + row_h * i + row_h / 2
        ci_low = row["coef"] - 1.96 * row["std_error_hac"]
        ci_high = row["coef"] + 1.96 * row["std_error_hac"]
        elements.append(f'<text x="{left-10}" y="{y+4}" text-anchor="end" class="label">{row["term"]}</text>')
        elements.append(f'<line x1="{sx(ci_low)}" y1="{y}" x2="{sx(ci_high)}" y2="{y}" stroke="#2E86AB" stroke-width="2"/>')
        elements.append(f'<circle cx="{sx(row["coef"])}" cy="{y}" r="5" fill="#D1495B"/>')
        elements.append(f'<text x="{sx(ci_high)+8}" y="{y+4}" class="tick">{row["signif"]}</text>')

    for tick in np.linspace(min_x, max_x, 6):
        x = sx(tick)
        elements.append(f'<line x1="{x}" y1="{top+plot_h}" x2="{x}" y2="{top+plot_h+6}" stroke="#333"/>')
        elements.append(f'<text x="{x}" y="{top+plot_h+22}" text-anchor="middle" class="tick">{tick:.2f}</text>')

    write_svg(path, elements)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    panel = prepare_panel()
    panel.to_csv(DATA_DIR / "experiment12_beijing_zoo_dynamic_panel.csv", index=False, encoding="utf-8-sig")

    main_result = fit_ols_hac(panel, "log_ticket_index", MAIN_FEATURES, hac_lag=7)
    coef_table = main_result["coef_table"].copy()
    coef_table["interpretation"] = [format_effect(term, coef) for term, coef in zip(coef_table["term"], coef_table["coef"])]
    coef_table.to_csv(OUTPUT_DIR / "experiment12_dynamic_regression_coefficients.csv", index=False, encoding="utf-8-sig")

    panel["main_model_fitted"] = np.nan
    panel["main_model_resid"] = np.nan
    panel.loc[main_result["used_index"], "main_model_fitted"] = main_result["fitted"]
    panel.loc[main_result["used_index"], "main_model_resid"] = main_result["resid"]
    panel.to_csv(OUTPUT_DIR / "experiment12_dynamic_regression_panel_with_fit.csv", index=False, encoding="utf-8-sig")

    attention_summary, lag_coef_table = build_attention_weights(panel)
    attention_summary.to_csv(OUTPUT_DIR / "experiment12_attention_like_heatmap_data.csv", index=False, encoding="utf-8-sig")
    lag_coef_table.to_csv(OUTPUT_DIR / "experiment12_attention_like_lag_coefficients.csv", index=False, encoding="utf-8-sig")

    feature_selection = pd.DataFrame(
        [
            {"column_name": "zoo_index", "use_status": "保留", "role": "总体景区关注度/潜在需求信号", "reason": "与票务前端压力具有直接需求联系，解释性强"},
            {"column_name": "ticket_index", "use_status": "保留为目标变量", "role": "票务与入园前端压力代理量", "reason": "与全文“票务预约与入园体验”主线一致"},
            {"column_name": "AQI", "use_status": "保留并反向处理", "role": "天气环境条件", "reason": "天气好坏会影响外出与游园需求"},
            {"column_name": "is_weekend", "use_status": "保留", "role": "周末效应", "reason": "解释短周期日历波动，口径清楚"},
            {"column_name": "is_holiday", "use_status": "保留", "role": "法定节假日冲击", "reason": "对动物园短期需求冲击强，叙事价值高"},
            {"column_name": "is_school_holiday", "use_status": "保留", "role": "学生假期冲击", "reason": "北京动物园亲子出游属性强"},
            {"column_name": "day_of_week", "use_status": "不进入主模型", "role": "细分星期效应", "reason": "与 is_weekend 高度重叠，正文模型保持简洁"},
            {"column_name": "diff_1", "use_status": "不直接使用", "role": "工程型短期变化量", "reason": "定义依赖旧建模口径，解释性弱，改为自建 lag1"},
            {"column_name": "diff_7", "use_status": "不直接使用", "role": "工程型周同比变化量", "reason": "与 lag7 含义重复，正文口径不够直观"},
            {"column_name": "rolling_mean_7", "use_status": "不直接使用", "role": "工程型平滑基线", "reason": "与滞后项共线性强，且不利于系数解释"},
            {"column_name": "history_error", "use_status": "不直接使用", "role": "旧模型误差代理", "reason": "不等同严格 MA 项，正文使用风险高"},
        ]
    )
    feature_selection.to_csv(OUTPUT_DIR / "experiment12_feature_selection_rationale.csv", index=False, encoding="utf-8-sig")

    calendar_summary = pd.DataFrame(
        [
            {
                "group_name": "工作日非假期",
                "sample_n": int(((panel["is_weekend"] == 0) & (panel["is_holiday"] == 0)).sum()),
                "ticket_index_mean": panel.loc[(panel["is_weekend"] == 0) & (panel["is_holiday"] == 0), "ticket_index"].mean(),
                "zoo_index_mean": panel.loc[(panel["is_weekend"] == 0) & (panel["is_holiday"] == 0), "zoo_index"].mean(),
            },
            {
                "group_name": "周末",
                "sample_n": int((panel["is_weekend"] == 1).sum()),
                "ticket_index_mean": panel.loc[panel["is_weekend"] == 1, "ticket_index"].mean(),
                "zoo_index_mean": panel.loc[panel["is_weekend"] == 1, "zoo_index"].mean(),
            },
            {
                "group_name": "法定节假日",
                "sample_n": int((panel["is_holiday"] == 1).sum()),
                "ticket_index_mean": panel.loc[panel["is_holiday"] == 1, "ticket_index"].mean(),
                "zoo_index_mean": panel.loc[panel["is_holiday"] == 1, "zoo_index"].mean(),
            },
            {
                "group_name": "学校假期",
                "sample_n": int((panel["is_school_holiday"] == 1).sum()),
                "ticket_index_mean": panel.loc[panel["is_school_holiday"] == 1, "ticket_index"].mean(),
                "zoo_index_mean": panel.loc[panel["is_school_holiday"] == 1, "zoo_index"].mean(),
            },
            {
                "group_name": "高压日(前10%)",
                "sample_n": int((panel["high_pressure_day"] == 1).sum()),
                "ticket_index_mean": panel.loc[panel["high_pressure_day"] == 1, "ticket_index"].mean(),
                "zoo_index_mean": panel.loc[panel["high_pressure_day"] == 1, "zoo_index"].mean(),
            },
        ]
    )
    calendar_summary.to_csv(OUTPUT_DIR / "experiment12_calendar_group_summary.csv", index=False, encoding="utf-8-sig")

    summary_rows = [
        {"metric": "sample_n", "value": len(panel)},
        {"metric": "date_min", "value": panel["date"].min().date().isoformat()},
        {"metric": "date_max", "value": panel["date"].max().date().isoformat()},
        {"metric": "high_pressure_threshold_q90", "value": round(panel["ticket_index"].quantile(0.9), 2)},
        {"metric": "very_high_pressure_threshold_q95", "value": round(panel["ticket_index"].quantile(0.95), 2)},
        {"metric": "main_model_r2", "value": round(main_result["r2"], 4)},
        {"metric": "main_model_adj_r2", "value": round(main_result["adj_r2"], 4)},
    ]
    pd.DataFrame(summary_rows).to_csv(OUTPUT_DIR / "experiment12_dynamic_case_summary.csv", index=False, encoding="utf-8-sig")

    render_time_series(panel, OUTPUT_DIR / "experiment12_ticket_index_timeseries.svg")
    render_attention_heatmap(attention_summary, OUTPUT_DIR / "experiment12_attention_like_heatmap.svg")
    render_coef_svg(coef_table, OUTPUT_DIR / "experiment12_dynamic_regression_coefficients.svg")

    sig_terms = coef_table.loc[(coef_table["term"] != "const") & (coef_table["p_value"] < 0.05), "term"].tolist()
    report_lines = [
        "# 北京动物园动态案例报告",
        "",
        "## 1. 研究定位",
        "- 该部分不是替代 20 景区横截面分析，而是作为北京动物园的动态案例补充。",
        "- 目标是解释：在已经被识别为“票务高压治理型”的前提下，北京动物园的票务前端压力在什么条件下更容易升高。",
        "",
        "## 2. 正式主模型",
        "- 主模型：可解释动态回归（OLS + Newey-West/HAC 稳健标准误）",
        "- 目标变量：`log_ticket_index`",
        "- 正式入模变量：`log_zoo_index`、`aqi_good_z`、`is_weekend`、`is_holiday`、`is_school_holiday`、`log_ticket_lag1`、`log_ticket_lag7`",
        f"- 样本期：{panel['date'].min().date().isoformat()} 至 {panel['date'].max().date().isoformat()}，共 {len(panel)} 天",
        f"- 主模型 R²：{main_result['r2']:.4f}；调整后 R²：{main_result['adj_r2']:.4f}",
        "",
        "## 3. 为什么不直接沿用队友那组工程列",
        "- `diff_1`、`diff_7`、`rolling_mean_7`、`history_error` 更偏建模工程特征，而不是论文里最稳的解释变量。",
        "- 本文改为使用更容易解释的滞后项：`lag1` 和 `lag7`。",
        "- 这样既保留短期惯性和周周期信息，也更利于统计显著性和正文叙事。",
        "",
        "## 4. 显著性结果摘要",
        f"- 在 5% 显著性水平下，当前显著项包括：{', '.join(sig_terms) if sig_terms else '暂无'}。",
        "- 连续变量使用对数或标准化口径，便于解释弹性和方向。",
        "- 二元变量使用相对变化解释，便于转成“节假日是否推高票务前端压力”的结论。",
        "",
        "## 5. attention 如何保留",
        "- 旧版 `Meta + LSTM + Attention` 未通过统计显著性检验，因此不作为正式主模型。",
        "- 但保留一个 `attention 风格时滞热力图` 作为辅助可视化：它基于 14 天滞后贡献绝对值经 softmax 归一化得到。",
        "- 它的作用是展示高压日更依赖哪些近期时滞信息，而不是承担显著性推断。",
        "",
        "## 6. 论文建议口径",
        "- 横截面部分说明：北京动物园属于票务高压治理型，且 POI 环境体现出高到达汇聚和高周边活动。",
        "- 动态部分补充说明：当景区总体关注度上升、假期因素叠加且近期票务压力已经抬升时，北京动物园的票务前端压力更容易继续升高。",
    ]
    (OUTPUT_DIR / "experiment12_dynamic_case_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    readme_lines = [
        "# 动态案例输出",
        "",
        "## 1. 目的",
        "- 将 `multi_data_for_MetaLSTM.xlsx` 转成适合论文叙事的北京动物园动态案例数据。",
        "- 主模型强调可解释性和显著性；attention 仅保留为辅助热力图。",
        "",
        "## 2. 核心文件",
        "- `experiment12_dynamic_regression_coefficients.csv`：主模型系数、稳健标准误与显著性",
        "- `experiment12_dynamic_regression_coefficients.svg`：主模型系数图",
        "- `experiment12_dynamic_regression_panel_with_fit.csv`：带拟合值与残差的日度面板",
        "- `experiment12_attention_like_heatmap.svg`：attention 风格时滞热力图",
        "- `experiment12_attention_like_heatmap_data.csv`：热力图底表",
        "- `experiment12_feature_selection_rationale.csv`：为什么选这些变量、不选哪些列",
        "- `experiment12_calendar_group_summary.csv`：按周末/节假日/学校假期/高压日的描述性汇总",
        "- `experiment12_dynamic_case_report.md`：案例方法与解释报告",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
