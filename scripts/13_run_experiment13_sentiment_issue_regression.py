from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "regression" / "sentiment_regression.xlsx"
OUTPUT_DIR = ROOT / "outputs" / "sentiment_regression"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TAG_COLUMNS = [
    "tag_staff_service",
    "tag_service_process",
    "tag_guide_explanation",
    "tag_queue_wait",
    "tag_reservation_entry",
    "tag_ticket_price",
    "tag_traffic_access",
    "tag_facility_hygiene",
    "tag_crowding",
    "tag_commercialization",
    "tag_platform_transaction",
]


def build_linear_summary(model: sm.regression.linear_model.RegressionResultsWrapper) -> pd.DataFrame:
    conf = model.conf_int()
    return pd.DataFrame(
        {
            "term": model.params.index,
            "coef": model.params.values,
            "std_error": model.bse.values,
            "t_value": model.tvalues.values,
            "p_value": model.pvalues.values,
            "ci_low": conf[0].values,
            "ci_high": conf[1].values,
        }
    )


def build_mnlogit_summary(
    model: sm.discrete.discrete_model.MultinomialResultsWrapper,
    class_order: list[str],
) -> pd.DataFrame:
    coef = model.params.copy()
    std_err = model.bse.copy()
    z_value = coef / std_err
    p_value = 2 * (1 - stats.norm.cdf(np.abs(z_value)))
    odds_ratio = np.exp(coef)

    rows: list[dict[str, float | str]] = []
    for category_code, label in enumerate(class_order):
        if category_code == 0:
            continue
        column_key = category_code - 1
        for term in coef.index:
            rows.append(
                {
                    "comparison": f"{label} vs {class_order[0]}",
                    "term": term,
                    "coef": coef.loc[term, column_key],
                    "std_error": std_err.loc[term, column_key],
                    "z_value": z_value.loc[term, column_key],
                    "p_value": p_value.loc[term, column_key],
                    "odds_ratio": odds_ratio.loc[term, column_key],
                }
            )
    return pd.DataFrame(rows)


def top_terms(frame: pd.DataFrame, value_col: str, n: int = 3) -> list[str]:
    work = frame.loc[frame["term"] != "const"].copy()
    work = work.reindex(work[value_col].abs().sort_values(ascending=False).index)
    return work.head(n)["term"].tolist()


def main() -> None:
    df = pd.read_excel(INPUT_PATH)

    X = sm.add_constant(df[TAG_COLUMNS].astype(float), has_constant="add")

    y_score = pd.to_numeric(df["sentiment_score"], errors="coerce")
    linear_model = sm.OLS(y_score, X, missing="drop").fit(cov_type="HC3")
    linear_summary = build_linear_summary(linear_model)
    linear_summary.to_csv(
        OUTPUT_DIR / "experiment13_linear_regression_coefficients.csv",
        index=False,
        encoding="utf-8-sig",
    )

    class_order = ["positive", "neutral", "negative"]
    y_class = pd.Categorical(df["sentiment_class"], categories=class_order, ordered=False)
    class_codes = pd.Series(y_class.codes, index=df.index, name="sentiment_class_code")
    mnlogit_model = sm.MNLogit(class_codes, X).fit(method="newton", maxiter=200, disp=False)
    mnlogit_summary = build_mnlogit_summary(mnlogit_model, class_order)
    mnlogit_summary.to_csv(
        OUTPUT_DIR / "experiment13_multinomial_logit_coefficients.csv",
        index=False,
        encoding="utf-8-sig",
    )

    prevalence = pd.DataFrame(
        {
            "tag_name": TAG_COLUMNS,
            "share": [df[column].mean() for column in TAG_COLUMNS],
        }
    ).sort_values("share", ascending=False)
    prevalence.to_csv(
        OUTPUT_DIR / "experiment13_issue_tag_prevalence.csv",
        index=False,
        encoding="utf-8-sig",
    )

    top_linear = top_terms(linear_summary, "coef")
    top_negative = top_terms(
        mnlogit_summary.loc[mnlogit_summary["comparison"] == "negative vs positive"],
        "coef",
    )
    top_neutral = top_terms(
        mnlogit_summary.loc[mnlogit_summary["comparison"] == "neutral vs positive"],
        "coef",
    )

    report_lines = [
        "# 情感得分与治理标签回归报告",
        "",
        "## 1. 数据说明",
        f"- 输入文件：`{INPUT_PATH.relative_to(ROOT).as_posix()}`",
        f"- 样本量：{len(df)}",
        f"- 连续因变量：`sentiment_score`",
        f"- 离散因变量：`sentiment_class`，类别分布为 {df['sentiment_class'].value_counts().to_dict()}",
        "- 自变量：11 个二级治理标签哑变量",
        "",
        "## 2. 建模口径",
        "- 连续情感得分部分采用多元线性回归，并使用 `HC3` 稳健标准误。",
        "- 离散情感类别部分采用多项逻辑回归，以 `positive` 为基准类别。",
        "- 回归目的不是替代主题识别，而是检验二级治理问题与情绪结果之间的方向与强度关系。",
        "",
        "## 3. 结果摘要",
        f"- 线性回归 R²：{linear_model.rsquared:.4f}；调整后 R²：{linear_model.rsquared_adj:.4f}",
        f"- 线性回归中绝对系数较大的标签：{', '.join(top_linear) if top_linear else '暂无'}",
        f"- `negative vs positive` 比较中绝对系数较大的标签：{', '.join(top_negative) if top_negative else '暂无'}",
        f"- `neutral vs positive` 比较中绝对系数较大的标签：{', '.join(top_neutral) if top_neutral else '暂无'}",
        "",
        "## 4. 输出文件",
        "- `experiment13_linear_regression_coefficients.csv`：连续情感得分回归系数表",
        "- `experiment13_multinomial_logit_coefficients.csv`：离散情感类别多项逻辑回归系数与优势比",
        "- `experiment13_issue_tag_prevalence.csv`：11 个二级标签在样本中的出现频率",
    ]
    (OUTPUT_DIR / "experiment13_regression_report.md").write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
