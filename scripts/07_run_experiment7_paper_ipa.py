#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SENTIMENT_PATH = PROJECT_DIR / "data" / "sentiment" / "experiment5_snownlp_scored.csv"
DEFAULT_LDA_ASSIGNMENT_PATH = PROJECT_DIR / "data" / "lda" / "experiment3_lda_topic_assignments.csv"

OUTPUT_DIR = PROJECT_DIR / "outputs" / "ipa_paper"
OUTPUT_OVERALL_DIR = OUTPUT_DIR / "overall"
OUTPUT_SCENIC_DIR = OUTPUT_DIR / "by_scenic"

OUTPUT_THEME_PANEL_PATH = OUTPUT_DIR / "experiment7_theme_panel.csv"
OUTPUT_OVERALL_PATH = OUTPUT_OVERALL_DIR / "experiment7_ipa_overall_matrix.csv"
OUTPUT_OVERALL_PNG = OUTPUT_OVERALL_DIR / "experiment7_ipa_overall.png"
OUTPUT_OVERALL_MD = OUTPUT_OVERALL_DIR / "experiment7_ipa_overall_report.md"
OUTPUT_FORMULA_MD = PROJECT_DIR / "docs" / "论文口径IPA说明.md"

QUADRANT_LABELS = {
    "high_low_performance": "高重要性低表现 = 优先改进",
    "high_high_performance": "高重要性高表现 = 继续保持",
    "low_low_performance": "低重要性低表现 = 次级改进",
    "low_high_performance": "低重要性高表现 = 低优先级观察",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build paper-explainable IPA outputs from current scenic results.")
    parser.add_argument("--sentiment-path", type=Path, default=DEFAULT_SENTIMENT_PATH)
    parser.add_argument("--lda-assignment-path", type=Path, default=DEFAULT_LDA_ASSIGNMENT_PATH)
    return parser.parse_args()


def sanitize_filename(text: str) -> str:
    return re.sub(r"[\\\\/:*?\"<>|]+", "_", str(text or "").strip()) or "untitled"


def configure_matplotlib() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator is None or denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator) / float(denominator)


def assign_quadrant(importance: float, performance: float, importance_cut: float, performance_cut: float) -> str:
    high_importance = importance >= importance_cut
    high_performance = performance >= performance_cut
    if high_importance and not high_performance:
        return QUADRANT_LABELS["high_low_performance"]
    if high_importance and high_performance:
        return QUADRANT_LABELS["high_high_performance"]
    if (not high_importance) and (not high_performance):
        return QUADRANT_LABELS["low_low_performance"]
    return QUADRANT_LABELS["low_high_performance"]


def theme_color(quadrant: str) -> str:
    color_map = {
        QUADRANT_LABELS["high_low_performance"]: "#c0392b",
        QUADRANT_LABELS["high_high_performance"]: "#2980b9",
        QUADRANT_LABELS["low_low_performance"]: "#f39c12",
        QUADRANT_LABELS["low_high_performance"]: "#7f8c8d",
    }
    return color_map.get(quadrant, "#7f8c8d")


def load_scored_df(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig").copy()
    df["review_id"] = df["review_id"].astype(str)
    df["official_scenic_id"] = df["official_scenic_id"].astype(str)
    df["scenic_name"] = df["scenic_name"].fillna("").astype(str)
    df["issue_flag"] = pd.to_numeric(df["issue_flag"], errors="coerce").fillna(0).astype(int)
    df["negative_flag"] = df["sentiment_class"].fillna("").astype(str).eq("negative").astype(int)
    return df


def load_lda_df(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig").copy()
    df["review_id"] = df["review_id"].astype(str)
    df["scenic_name"] = df["scenic_name"].fillna("").astype(str)
    df["theme_name_cn"] = df["lda_topic_name_cn"].fillna("").astype(str).str.strip()
    df["is_satisfaction_topic"] = pd.to_numeric(df["is_satisfaction_topic"], errors="coerce").fillna(0).astype(int)
    return df


def build_theme_panel(scored_df: pd.DataFrame, lda_df: pd.DataFrame) -> pd.DataFrame:
    base_cols = ["review_id", "official_scenic_id", "scenic_name", "issue_flag", "negative_flag"]
    merged = lda_df.merge(
        scored_df[base_cols].drop_duplicates(subset=["review_id", "scenic_name"], keep="first"),
        on=["review_id", "scenic_name"],
        how="left",
    )
    sample_n_df = (
        merged.groupby(["official_scenic_id", "scenic_name"], as_index=False)
        .agg(sample_n=("review_id", "size"))
    )
    grouped = (
        merged.groupby(["official_scenic_id", "scenic_name", "theme_name_cn", "is_satisfaction_topic"], as_index=False)
        .agg(
            theme_review_n=("review_id", "size"),
            theme_issue_n=("issue_flag", "sum"),
            theme_negative_n=("negative_flag", "sum"),
        )
    )
    panel = grouped.merge(sample_n_df, on=["official_scenic_id", "scenic_name"], how="left")
    panel["importance"] = panel.apply(lambda row: safe_divide(row["theme_review_n"], row["sample_n"]), axis=1)
    panel["issue_rate"] = panel.apply(lambda row: safe_divide(row["theme_issue_n"], row["theme_review_n"]), axis=1)
    panel["negative_rate"] = panel.apply(lambda row: safe_divide(row["theme_negative_n"], row["theme_review_n"]), axis=1)
    panel["dissatisfaction_index"] = (panel["issue_rate"] + panel["negative_rate"]) / 2
    panel["performance"] = 1 - panel["dissatisfaction_index"]
    panel["priority_index"] = panel["importance"] * panel["dissatisfaction_index"]
    return panel.sort_values(
        ["official_scenic_id", "is_satisfaction_topic", "theme_name_cn"],
        ascending=[True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def build_overall_ipa(theme_panel_df: pd.DataFrame) -> pd.DataFrame:
    governance_df = theme_panel_df.loc[theme_panel_df["is_satisfaction_topic"].eq(0)].copy()
    rows: List[Dict[str, object]] = []
    total_reviews = float(governance_df[["official_scenic_id", "sample_n"]].drop_duplicates()["sample_n"].sum())

    for theme_name, group in governance_df.groupby("theme_name_cn", sort=True):
        theme_review_n = float(group["theme_review_n"].sum())
        theme_issue_n = float(group["theme_issue_n"].sum())
        theme_negative_n = float(group["theme_negative_n"].sum())
        importance = safe_divide(theme_review_n, total_reviews)
        issue_rate = safe_divide(theme_issue_n, theme_review_n)
        negative_rate = safe_divide(theme_negative_n, theme_review_n)
        dissatisfaction_index = (issue_rate + negative_rate) / 2
        performance = 1 - dissatisfaction_index
        priority_index = importance * dissatisfaction_index

        rows.append(
            {
                "theme_name_cn": theme_name,
                "theme_review_n": int(theme_review_n),
                "theme_issue_n": int(theme_issue_n),
                "theme_negative_n": int(theme_negative_n),
                "importance": importance,
                "issue_rate": issue_rate,
                "negative_rate": negative_rate,
                "dissatisfaction_index": dissatisfaction_index,
                "performance": performance,
                "priority_index": priority_index,
            }
        )

    overall_df = pd.DataFrame(rows)
    importance_cut = float(overall_df["importance"].mean())
    performance_cut = float(overall_df["performance"].mean())
    overall_df["importance_cut"] = importance_cut
    overall_df["performance_cut"] = performance_cut
    overall_df["quadrant"] = overall_df.apply(
        lambda row: assign_quadrant(float(row["importance"]), float(row["performance"]), importance_cut, performance_cut),
        axis=1,
    )
    overall_df = overall_df.sort_values(
        ["priority_index", "importance", "dissatisfaction_index", "theme_name_cn"],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    overall_df["overall_priority_rank"] = range(1, len(overall_df) + 1)
    return overall_df


def build_scenic_ipa(theme_panel_df: pd.DataFrame) -> pd.DataFrame:
    governance_df = theme_panel_df.loc[theme_panel_df["is_satisfaction_topic"].eq(0)].copy()
    rows: List[pd.DataFrame] = []
    for scenic_id, scenic_df in governance_df.groupby("official_scenic_id", sort=False):
        scenic_df = scenic_df.copy().sort_values(
            ["priority_index", "importance", "dissatisfaction_index", "theme_name_cn"],
            ascending=[False, False, False, True],
            kind="mergesort",
        ).reset_index(drop=True)
        importance_cut = float(scenic_df["importance"].mean())
        performance_cut = float(scenic_df["performance"].mean())
        scenic_df["importance_cut"] = importance_cut
        scenic_df["performance_cut"] = performance_cut
        scenic_df["quadrant"] = scenic_df.apply(
            lambda row: assign_quadrant(float(row["importance"]), float(row["performance"]), importance_cut, performance_cut),
            axis=1,
        )
        scenic_df["scenic_priority_rank"] = range(1, len(scenic_df) + 1)
        rows.append(scenic_df)
    return pd.concat(rows, ignore_index=True) if rows else governance_df.iloc[0:0].copy()


def plot_ipa(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    x_cut: float,
    y_cut: float,
    title: str,
    output_path: Path,
) -> None:
    configure_matplotlib()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 7))
    for row in df.to_dict("records"):
        ax.scatter(
            row[x_col],
            row[y_col],
            s=260,
            color=theme_color(str(row["quadrant"])),
            alpha=0.9,
            edgecolors="white",
            linewidths=1.2,
        )
        ax.text(row[x_col] + 0.01, row[y_col] + 0.01, str(row["theme_name_cn"]), fontsize=10)

    ax.axvline(x_cut, color="#333333", linestyle="--", linewidth=1)
    ax.axhline(y_cut, color="#333333", linestyle="--", linewidth=1)
    ax.set_xlim(-0.05, min(1.05, max(1.0, float(df[x_col].max()) + 0.05)))
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Importance")
    ax.set_ylabel("Performance")
    ax.set_title(title)
    ax.grid(alpha=0.25, linestyle=":")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_formula_doc(path: Path) -> None:
    lines = [
        "# 论文口径IPA说明",
        "",
        "## 1. 为什么重做",
        "- 本轮 IPA 不再沿用旧样本下的主观加权优先级公式。",
        "- 新指标只依赖当前这批 20 个景区、6000 条评论的现有结果，避免跨样本继承旧权重造成解释不稳。",
        "",
        "## 2. 基本思想",
        "- IPA 仍保留经典的 `Importance - Performance Analysis` 框架。",
        "- 但这里的 `Importance` 和 `Performance` 都直接由当前评论数据计算，不再引入上一轮实验的外部权重。",
        "",
        "## 3. 指标定义",
        "设景区为 `s`，一级主题为 `t`。",
        "",
        "### 3.1 重要性 Importance",
        "- `Importance_(s,t) = n_(s,t) / N_s`",
        "- 其中 `n_(s,t)` 是景区 `s` 中属于主题 `t` 的评论数，`N_s` 是景区 `s` 中进入 LDA/IPA 阶段的可用评论总数。",
        "- 含义：该主题在景区评论中被提及的比例，表示游客对该主题的关注度。",
        "",
        "### 3.2 问题率 Issue Rate",
        "- `IssueRate_(s,t) = m_(s,t) / n_(s,t)`",
        "- 其中 `m_(s,t)` 是主题 `t` 下被 LLM 识别为存在问题标签的评论数。",
        "",
        "### 3.3 负向情绪率 Negative Rate",
        "- `NegativeRate_(s,t) = u_(s,t) / n_(s,t)`",
        "- 其中 `u_(s,t)` 是主题 `t` 下被 SnowNLP 判为负向情绪的评论数。",
        "",
        "### 3.4 不满意指数 Dissatisfaction Index",
        "- `D_(s,t) = (IssueRate_(s,t) + NegativeRate_(s,t)) / 2`",
        "- 这里采用等权平均，不再使用主观权重。",
        "- 原因：显性问题标签反映“具体摩擦”，负向情绪反映“整体感受”，二者共同表征主题表现不佳的程度。",
        "",
        "### 3.5 表现 Performance",
        "- `Performance_(s,t) = 1 - D_(s,t)`",
        "- 表现越高，说明该主题的整体体验越好。",
        "",
        "### 3.6 优先级指数 Priority Index",
        "- `PriorityIndex_(s,t) = Importance_(s,t) * D_(s,t)`",
        "- 含义：一个主题既要“被大量提及”，又要“表现较差”，才会成为更高优先级的治理对象。",
        "",
        "## 4. 整体IPA",
        "- 整体层面按全部景区汇总后，用同样公式计算每个一级治理主题的 `Importance`、`Performance` 和 `PriorityIndex`。",
        "- 满意主题 `整体满意与感知评价` 不进入治理 IPA。",
        "",
        "## 5. 四象限划分",
        "- 横轴：Importance",
        "- 纵轴：Performance",
        "- 以当前样本中所有治理主题的平均 `Importance` 和平均 `Performance` 作为象限分割线。",
        "",
        "## 6. 解释优势",
        "- 指标全部来自当前样本，避免跨样本继承旧权重。",
        "- 每个指标都能直接落到评论计数和比例，论文中容易解释。",
        "- `PriorityIndex = Importance × Dissatisfaction` 兼顾关注度与问题强度，直观适合景区治理排序。",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_overall_report(path: Path, overall_df: pd.DataFrame, scenic_df: pd.DataFrame) -> None:
    lines = [
        "# 论文口径IPA总体报告",
        "",
        "## 1. 指标说明",
        "- Importance：主题评论占比",
        "- Performance：1 - 不满意指数",
        "- Dissatisfaction：0.5*问题率 + 0.5*负向情绪率",
        "- PriorityIndex：Importance * Dissatisfaction",
        "",
        "## 2. 整体一级治理主题IPA",
        overall_df[
            [
                "overall_priority_rank",
                "theme_name_cn",
                "importance",
                "issue_rate",
                "negative_rate",
                "dissatisfaction_index",
                "performance",
                "priority_index",
                "quadrant",
            ]
        ].to_markdown(index=False),
        "",
        "## 3. 各景区首要治理主题",
    ]

    scenic_top = scenic_df.sort_values(
        ["official_scenic_id", "scenic_priority_rank"],
        ascending=[True, True],
        kind="mergesort",
    ).groupby("official_scenic_id", as_index=False).head(1)

    for row in scenic_top.sort_values(["priority_index", "importance"], ascending=[False, False], kind="mergesort").to_dict("records"):
        lines.extend(
            [
                f"### {row['scenic_name']}",
                f"- 首要治理主题：{row['theme_name_cn']}",
                f"- importance：{float(row['importance']):.4f}",
                f"- performance：{float(row['performance']):.4f}",
                f"- dissatisfaction：{float(row['dissatisfaction_index']):.4f}",
                f"- priority_index：{float(row['priority_index']):.4f}",
                f"- quadrant：{row['quadrant']}",
                "",
            ]
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_scenic_outputs(scenic_df: pd.DataFrame) -> None:
    for scenic_name, group in scenic_df.groupby("scenic_name", sort=False):
        group = group.sort_values(
            ["scenic_priority_rank", "priority_index", "importance"],
            ascending=[True, False, False],
            kind="mergesort",
        ).reset_index(drop=True)
        scenic_dir = OUTPUT_SCENIC_DIR / sanitize_filename(scenic_name)
        scenic_dir.mkdir(parents=True, exist_ok=True)

        csv_path = scenic_dir / f"{sanitize_filename(scenic_name)}_ipa_table.csv"
        md_path = scenic_dir / f"{sanitize_filename(scenic_name)}_ipa_summary.md"
        png_path = scenic_dir / f"{sanitize_filename(scenic_name)}_ipa.png"

        group.to_csv(csv_path, index=False, encoding="utf-8-sig")
        plot_ipa(
            group,
            x_col="importance",
            y_col="performance",
            x_cut=float(group["importance_cut"].iloc[0]),
            y_cut=float(group["performance_cut"].iloc[0]),
            title=f"{scenic_name} IPA",
            output_path=png_path,
        )

        top = group.iloc[0]
        lines = [
            f"# {scenic_name} IPA",
            "",
            "## 1. 计算口径",
            "- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数",
            "- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]",
            "- PriorityIndex：Importance × Dissatisfaction",
            "",
            "## 2. 当前景区首要治理主题",
            f"- 主题：{top['theme_name_cn']}",
            f"- importance：{float(top['importance']):.4f}",
            f"- issue_rate：{float(top['issue_rate']):.4f}",
            f"- negative_rate：{float(top['negative_rate']):.4f}",
            f"- dissatisfaction：{float(top['dissatisfaction_index']):.4f}",
            f"- performance：{float(top['performance']):.4f}",
            f"- priority_index：{float(top['priority_index']):.4f}",
            f"- quadrant：{top['quadrant']}",
            "",
            "## 3. 主题排序表",
            group[
                [
                    "scenic_priority_rank",
                    "theme_name_cn",
                    "importance",
                    "issue_rate",
                    "negative_rate",
                    "dissatisfaction_index",
                    "performance",
                    "priority_index",
                    "quadrant",
                ]
            ].to_markdown(index=False),
        ]
        md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    OUTPUT_OVERALL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_SCENIC_DIR.mkdir(parents=True, exist_ok=True)

    scored_df = load_scored_df(args.sentiment_path.resolve())
    lda_df = load_lda_df(args.lda_assignment_path.resolve())
    theme_panel_df = build_theme_panel(scored_df, lda_df)
    overall_df = build_overall_ipa(theme_panel_df)
    scenic_df = build_scenic_ipa(theme_panel_df)

    theme_panel_df.to_csv(OUTPUT_THEME_PANEL_PATH, index=False, encoding="utf-8-sig")
    overall_df.to_csv(OUTPUT_OVERALL_PATH, index=False, encoding="utf-8-sig")
    plot_ipa(
        overall_df,
        x_col="importance",
        y_col="performance",
        x_cut=float(overall_df["importance_cut"].iloc[0]),
        y_cut=float(overall_df["performance_cut"].iloc[0]),
        title="Overall IPA (Paper Metric)",
        output_path=OUTPUT_OVERALL_PNG,
    )
    write_overall_report(OUTPUT_OVERALL_MD, overall_df, scenic_df)
    write_scenic_outputs(scenic_df)
    write_formula_doc(OUTPUT_FORMULA_MD)

    print(f"theme_panel_csv={OUTPUT_THEME_PANEL_PATH}")
    print(f"overall_ipa_csv={OUTPUT_OVERALL_PATH}")
    print(f"overall_ipa_png={OUTPUT_OVERALL_PNG}")
    print(f"overall_ipa_md={OUTPUT_OVERALL_MD}")
    print(f"scenic_dir={OUTPUT_SCENIC_DIR}")
    print(f"formula_doc={OUTPUT_FORMULA_MD}")


if __name__ == "__main__":
    main()
