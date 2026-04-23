#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import MinMaxScaler, StandardScaler


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SENTIMENT_PATH = PROJECT_DIR / "data" / "sentiment" / "experiment5_snownlp_scored.csv"
DEFAULT_LDA_ASSIGNMENT_PATH = PROJECT_DIR / "data" / "lda" / "experiment3_lda_topic_assignments.csv"

OUTPUT_ROOT = PROJECT_DIR / "outputs"
OUTPUT_IPA_DIR = OUTPUT_ROOT / "ipa"
OUTPUT_IPA_OVERALL_DIR = OUTPUT_IPA_DIR / "overall"
OUTPUT_IPA_SCENIC_DIR = OUTPUT_IPA_DIR / "by_scenic"
OUTPUT_CLUSTER_DIR = OUTPUT_ROOT / "clustering"

SCENIC_PANEL_PATH = OUTPUT_IPA_DIR / "experiment6_scenic_panel.csv"
THEME_PANEL_PATH = OUTPUT_IPA_DIR / "experiment6_theme_panel.csv"
OVERALL_IPA_PATH = OUTPUT_IPA_OVERALL_DIR / "experiment6_ipa_overall_matrix.csv"
SCENIC_IPA_PATH = OUTPUT_IPA_DIR / "experiment6_ipa_by_scenic.csv"
OVERALL_IPA_FIG_PATH = OUTPUT_IPA_OVERALL_DIR / "experiment6_ipa_overall.png"
OVERALL_REPORT_PATH = OUTPUT_IPA_OVERALL_DIR / "experiment6_ipa_overall_report.md"

CLUSTER_ASSIGNMENT_PATH = OUTPUT_CLUSTER_DIR / "experiment6_cluster_assignments.csv"
CLUSTER_PROFILE_PATH = OUTPUT_CLUSTER_DIR / "experiment6_cluster_profiles.csv"
CLUSTER_COMPARE_PATH = OUTPUT_CLUSTER_DIR / "experiment6_cluster_k_compare.csv"
CLUSTER_FEATURE_PATH = OUTPUT_CLUSTER_DIR / "experiment6_cluster_features.csv"
CLUSTER_FIG_PATH = OUTPUT_CLUSTER_DIR / "experiment6_cluster_scatter.png"
CLUSTER_REPORT_PATH = OUTPUT_CLUSTER_DIR / "experiment6_cluster_report.md"

SPLIT_LABELS = [
    "staff_service",
    "service_process",
    "guide_explanation",
    "queue_wait",
    "reservation_entry",
    "ticket_price",
    "traffic_access",
    "facility_hygiene",
    "crowding",
    "commercialization",
    "platform_transaction",
]

PRIORITY_FEATURES = [
    "issue_review_rate_hybrid",
    "issue_divergence_rate",
    "high_rating_with_issue_rate",
    "queue_wait_rate",
    "reservation_entry_rate",
    "service_process_rate",
    "ticket_price_rate",
    "traffic_access_rate",
    "crowding_rate",
]

PRIORITY_WEIGHTS = {
    "issue_review_rate_hybrid": 0.30,
    "issue_divergence_rate": 0.20,
    "high_rating_with_issue_rate": 0.15,
    "queue_wait_rate": 0.10,
    "reservation_entry_rate": 0.10,
    "service_process_rate": 0.06,
    "ticket_price_rate": 0.04,
    "traffic_access_rate": 0.03,
    "crowding_rate": 0.02,
}

IMPORTANCE_WEIGHTS = {
    "issue_divergence_rate": 0.40,
    "high_rating_with_issue_rate": 0.35,
    "priority_score": 0.25,
}

QUADRANT_LABELS = {
    "high_high": "高重要性高缺口 = 优先改进",
    "high_low": "高重要性低缺口 = 继续保持",
    "low_high": "低重要性高缺口 = 次级改进",
    "low_low": "低重要性低缺口 = 观察即可",
}

CLUSTER_NAME_POOL = [
    "高压力治理型",
    "结构性优化型",
    "稳态保持型",
    "低关注维持型",
    "特色提升型",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build IPA and clustering outputs for the scenic project.")
    parser.add_argument("--sentiment-path", type=Path, default=DEFAULT_SENTIMENT_PATH)
    parser.add_argument("--lda-assignment-path", type=Path, default=DEFAULT_LDA_ASSIGNMENT_PATH)
    return parser.parse_args()


def sanitize_filename(text: str) -> str:
    return re.sub(r"[\\\\/:*?\"<>|]+", "_", str(text or "").strip()) or "untitled"


def configure_matplotlib() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def minmax_scale(series: pd.Series) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    lower = float(series.min())
    upper = float(series.max())
    if math.isclose(lower, upper):
        return pd.Series(np.full(len(series), 0.5), index=series.index, dtype=float)
    return (series - lower) / (upper - lower)


def safe_corr(x: pd.Series, y: pd.Series) -> float:
    x = pd.to_numeric(x, errors="coerce")
    y = pd.to_numeric(y, errors="coerce")
    if x.nunique(dropna=True) <= 1 or y.nunique(dropna=True) <= 1:
        return 0.0
    value = x.corr(y)
    if pd.isna(value):
        return 0.0
    return float(value)


def assign_quadrant(importance: float, gap: float, importance_cut: float, gap_cut: float) -> str:
    high_importance = importance >= importance_cut
    high_gap = gap >= gap_cut
    if high_importance and high_gap:
        return QUADRANT_LABELS["high_high"]
    if high_importance and not high_gap:
        return QUADRANT_LABELS["high_low"]
    if (not high_importance) and high_gap:
        return QUADRANT_LABELS["low_high"]
    return QUADRANT_LABELS["low_low"]


def theme_color(quadrant: str) -> str:
    color_map = {
        QUADRANT_LABELS["high_high"]: "#c0392b",
        QUADRANT_LABELS["high_low"]: "#2980b9",
        QUADRANT_LABELS["low_high"]: "#f39c12",
        QUADRANT_LABELS["low_low"]: "#7f8c8d",
    }
    return color_map.get(quadrant, "#7f8c8d")


def load_sentiment_issue_df(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig").copy()
    df["review_id"] = df["review_id"].astype(str)
    df["official_scenic_id"] = df["official_scenic_id"].astype(str)
    df["scenic_name"] = df["scenic_name"].fillna("").astype(str)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["sentiment_score"] = pd.to_numeric(df["sentiment_score"], errors="coerce")
    df["sentiment_index"] = pd.to_numeric(df["sentiment_index"], errors="coerce")
    df["issue_flag"] = pd.to_numeric(df["issue_flag"], errors="coerce").fillna(0).astype(int)
    for tag in SPLIT_LABELS:
        col = f"tag_{tag}"
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = 0
    df["negative_flag"] = df["sentiment_class"].fillna("").astype(str).eq("negative").astype(int)
    df["high_rating_review_flag"] = df["rating"].ge(4).fillna(False).astype(int)
    df["issue_divergence_flag"] = ((df["rating"] >= 4) & (df["issue_flag"] == 1)).astype(int)
    df["high_rating_with_issue_flag"] = df["issue_divergence_flag"]
    return df


def load_lda_assignment_df(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig").copy()
    df["review_id"] = df["review_id"].astype(str)
    df["scenic_name"] = df["scenic_name"].fillna("").astype(str)
    df["theme_name_cn"] = df["lda_topic_name_cn"].fillna("").astype(str).str.strip()
    df["is_satisfaction_topic"] = pd.to_numeric(df["is_satisfaction_topic"], errors="coerce").fillna(0).astype(int)
    df["lda_topic_prob"] = pd.to_numeric(df["lda_topic_prob"], errors="coerce").fillna(0.0)
    return df


def build_scenic_panel(scored_df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        scored_df.groupby(["official_scenic_id", "scenic_name"], as_index=False)
        .agg(
            sample_n=("review_id", "size"),
            avg_rating=("rating", "mean"),
            avg_sentiment_score=("sentiment_score", "mean"),
            avg_sentiment_index=("sentiment_index", "mean"),
            negative_sentiment_rate=("negative_flag", "mean"),
            strict_issue_review_rate=("issue_flag", "mean"),
            issue_review_rate_hybrid=("issue_flag", "mean"),
            issue_divergence_rate=("issue_divergence_flag", "mean"),
            high_rating_share=("high_rating_review_flag", "mean"),
        )
    )

    high_rating_issue = (
        scored_df.loc[scored_df["high_rating_review_flag"].eq(1)]
        .groupby("official_scenic_id", as_index=False)["issue_flag"]
        .mean()
        .rename(columns={"issue_flag": "high_rating_with_issue_rate"})
    )
    grouped = grouped.merge(high_rating_issue, on="official_scenic_id", how="left")
    grouped["high_rating_with_issue_rate"] = grouped["high_rating_with_issue_rate"].fillna(0.0)

    for tag in SPLIT_LABELS:
        rate_df = (
            scored_df.groupby("official_scenic_id", as_index=False)[f"tag_{tag}"]
            .mean()
            .rename(columns={f"tag_{tag}": f"{tag}_rate"})
        )
        grouped = grouped.merge(rate_df, on="official_scenic_id", how="left")

    features = grouped[PRIORITY_FEATURES].fillna(0.0)
    scaled = pd.DataFrame(MinMaxScaler().fit_transform(features), columns=features.columns, index=grouped.index)
    grouped["priority_score"] = sum(scaled[col] * weight for col, weight in PRIORITY_WEIGHTS.items())
    grouped = grouped.sort_values(
        ["priority_score", "issue_review_rate_hybrid", "official_scenic_id"],
        ascending=[False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    grouped["priority_rank"] = range(1, len(grouped) + 1)
    grouped["priority_formula"] = (
        "0.30*issue_review_rate_hybrid + 0.20*issue_divergence_rate + "
        "0.15*high_rating_with_issue_rate + 0.10*queue_wait + 0.10*reservation_entry + "
        "0.06*service_process + 0.04*ticket_price + 0.03*traffic_access + 0.02*crowding"
    )
    return grouped


def build_theme_panel(scored_df: pd.DataFrame, lda_df: pd.DataFrame, scenic_panel_df: pd.DataFrame) -> pd.DataFrame:
    merge_cols = [
        "review_id",
        "scenic_name",
        "official_scenic_id",
        "rating",
        "issue_flag",
        "issue_divergence_flag",
        "high_rating_with_issue_flag",
        "negative_flag",
        "sentiment_score",
        "sentiment_class",
    ]
    merged = lda_df.merge(
        scored_df[merge_cols].drop_duplicates(subset=["review_id", "scenic_name"], keep="first"),
        on=["review_id", "scenic_name"],
        how="left",
    )
    merged["official_scenic_id"] = merged["official_scenic_id"].fillna("")

    grouped = (
        merged.groupby(["official_scenic_id", "scenic_name", "theme_name_cn", "is_satisfaction_topic"], as_index=False)
        .agg(
            theme_review_n=("review_id", "size"),
            theme_issue_n=("issue_flag", "sum"),
            theme_high_rating_issue_n=("high_rating_with_issue_flag", "sum"),
            theme_negative_n=("negative_flag", "sum"),
            theme_avg_sentiment_score=("sentiment_score", "mean"),
            theme_avg_topic_prob=("lda_topic_prob", "mean"),
        )
    )

    theme_panel = grouped.merge(
        scenic_panel_df[["official_scenic_id", "scenic_name", "sample_n", "priority_score", "priority_rank"]],
        on=["official_scenic_id", "scenic_name"],
        how="left",
    )
    denominator = theme_panel["sample_n"].replace(0, np.nan)
    theme_panel["theme_review_share_total"] = (theme_panel["theme_review_n"] / denominator).fillna(0.0)
    theme_panel["theme_issue_share_total"] = (theme_panel["theme_issue_n"] / denominator).fillna(0.0)
    theme_panel["theme_high_rating_issue_share_total"] = (theme_panel["theme_high_rating_issue_n"] / denominator).fillna(0.0)
    theme_panel["theme_negative_share_total"] = (theme_panel["theme_negative_n"] / denominator).fillna(0.0)
    theme_panel["theme_issue_rate_within_theme"] = np.where(
        theme_panel["theme_review_n"].gt(0),
        theme_panel["theme_issue_n"] / theme_panel["theme_review_n"],
        0.0,
    )
    theme_panel["theme_negative_rate_within_theme"] = np.where(
        theme_panel["theme_review_n"].gt(0),
        theme_panel["theme_negative_n"] / theme_panel["theme_review_n"],
        0.0,
    )
    theme_panel["theme_problem_strength"] = theme_panel["theme_issue_share_total"]
    return theme_panel.sort_values(
        ["priority_rank", "is_satisfaction_topic", "theme_name_cn"],
        ascending=[True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def build_overall_ipa_matrix(scenic_panel_df: pd.DataFrame, theme_panel_df: pd.DataFrame) -> pd.DataFrame:
    analysis_df = theme_panel_df.loc[theme_panel_df["is_satisfaction_topic"].eq(0)].copy()
    rows: List[Dict[str, object]] = []

    for theme_name, theme_df in analysis_df.groupby("theme_name_cn", sort=True):
        merged = scenic_panel_df.merge(
            theme_df[
                [
                    "official_scenic_id",
                    "theme_review_share_total",
                    "theme_issue_share_total",
                    "theme_issue_rate_within_theme",
                    "theme_high_rating_issue_share_total",
                    "theme_negative_share_total",
                    "theme_negative_rate_within_theme",
                    "theme_avg_sentiment_score",
                ]
            ],
            on="official_scenic_id",
            how="left",
        ).fillna(0.0)

        corr_issue_div = safe_corr(merged["theme_issue_share_total"], merged["issue_divergence_rate"])
        corr_high_rating_issue = safe_corr(merged["theme_issue_share_total"], merged["high_rating_with_issue_rate"])
        corr_priority = safe_corr(merged["theme_issue_share_total"], merged["priority_score"])
        importance_raw = (
            IMPORTANCE_WEIGHTS["issue_divergence_rate"] * abs(corr_issue_div)
            + IMPORTANCE_WEIGHTS["high_rating_with_issue_rate"] * abs(corr_high_rating_issue)
            + IMPORTANCE_WEIGHTS["priority_score"] * abs(corr_priority)
        )
        rows.append(
            {
                "theme_name_cn": theme_name,
                "theme_review_share_mean": float(merged["theme_review_share_total"].mean()),
                "theme_issue_share_mean": float(merged["theme_issue_share_total"].mean()),
                "theme_issue_rate_within_theme_mean": float(merged["theme_issue_rate_within_theme"].mean()),
                "theme_negative_share_mean": float(merged["theme_negative_share_total"].mean()),
                "theme_negative_rate_within_theme_mean": float(merged["theme_negative_rate_within_theme"].mean()),
                "theme_avg_sentiment_score_mean": float(merged["theme_avg_sentiment_score"].mean()),
                "corr_issue_divergence_rate": corr_issue_div,
                "corr_high_rating_with_issue_rate": corr_high_rating_issue,
                "corr_priority_score": corr_priority,
                "importance_raw": importance_raw,
                "gap_raw": float(merged["theme_issue_share_total"].mean()),
            }
        )

    overall_df = pd.DataFrame(rows).sort_values("theme_name_cn", kind="mergesort").reset_index(drop=True)
    overall_df["importance"] = minmax_scale(overall_df["importance_raw"])
    overall_df["gap"] = minmax_scale(overall_df["gap_raw"])
    overall_df["performance"] = 1 - overall_df["gap"]
    importance_cut = float(overall_df["importance"].mean())
    gap_cut = float(overall_df["gap"].mean())
    overall_df["quadrant"] = overall_df.apply(
        lambda row: assign_quadrant(float(row["importance"]), float(row["gap"]), importance_cut, gap_cut),
        axis=1,
    )
    overall_df["overall_priority_index"] = overall_df["importance"] * overall_df["gap"]
    overall_df["importance_cut"] = importance_cut
    overall_df["gap_cut"] = gap_cut
    overall_df = overall_df.sort_values(
        ["overall_priority_index", "importance", "gap", "theme_name_cn"],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    overall_df["overall_priority_rank"] = range(1, len(overall_df) + 1)
    return overall_df


def build_scenic_ipa_table(theme_panel_df: pd.DataFrame, overall_ipa_df: pd.DataFrame) -> pd.DataFrame:
    analysis_df = theme_panel_df.loc[theme_panel_df["is_satisfaction_topic"].eq(0)].copy()
    merged = analysis_df.merge(
        overall_ipa_df[["theme_name_cn", "importance"]],
        on="theme_name_cn",
        how="left",
    )

    rows: List[pd.DataFrame] = []
    overall_importance_cut = float(overall_ipa_df["importance"].mean())
    for scenic_id, scenic_df in merged.groupby("official_scenic_id", sort=False):
        scenic_df = scenic_df.copy()
        scenic_df["scenic_gap"] = minmax_scale(scenic_df["theme_problem_strength"])
        scenic_df["scenic_performance"] = 1 - scenic_df["scenic_gap"]
        scenic_gap_cut = float(scenic_df["scenic_gap"].mean())
        scenic_df["importance_cut"] = overall_importance_cut
        scenic_df["gap_cut"] = scenic_gap_cut
        scenic_df["quadrant"] = scenic_df.apply(
            lambda row: assign_quadrant(float(row["importance"]), float(row["scenic_gap"]), overall_importance_cut, scenic_gap_cut),
            axis=1,
        )
        scenic_df["scenic_priority_index"] = scenic_df["importance"] * scenic_df["scenic_gap"]
        scenic_df = scenic_df.sort_values(
            ["scenic_priority_index", "importance", "scenic_gap", "theme_name_cn"],
            ascending=[False, False, False, True],
            kind="mergesort",
        ).reset_index(drop=True)
        scenic_df["scenic_priority_rank"] = range(1, len(scenic_df) + 1)
        rows.append(scenic_df)

    result = pd.concat(rows, ignore_index=True) if rows else merged.iloc[0:0].copy()
    return result


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
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Importance")
    ax.set_ylabel("Gap (higher = worse)")
    ax.set_title(title)
    ax.grid(alpha=0.25, linestyle=":")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_overall_ipa_report(
    output_path: Path,
    scenic_panel_df: pd.DataFrame,
    overall_ipa_df: pd.DataFrame,
    scenic_ipa_df: pd.DataFrame,
    satisfaction_theme_names: Iterable[str],
) -> None:
    satisfaction_text = " | ".join(sorted({name for name in satisfaction_theme_names if str(name).strip()})) or "无"
    top_scenics = scenic_panel_df.sort_values("priority_rank", kind="mergesort").head(20)
    sections: List[str] = [
        "# IPA总体报告",
        "",
        "## 1. 计算口径",
        "- 景区优先级沿用项目原有混合口径：先在景区层计算 `priority_score`，再把一级主题的主题问题强度与景区优先级指标做相关，得到 IPA 的 `Importance`。",
        "- `Importance_raw = 0.40*|corr(theme_issue_share, issue_divergence_rate)| + 0.35*|corr(theme_issue_share, high_rating_with_issue_rate)| + 0.25*|corr(theme_issue_share, priority_score)|`。",
        "- `Gap` 使用主题问题强度 `theme_issue_share_mean` 的 Min-Max 标准化结果；`Performance = 1 - Gap`。",
        "- 当前景区样本的满意主题不进入 IPA 排序，被剔除的满意主题为：" + satisfaction_text,
        "",
        "## 2. 整体一级主题IPA",
        overall_ipa_df[
            [
                "overall_priority_rank",
                "theme_name_cn",
                "importance",
                "gap",
                "performance",
                "theme_issue_share_mean",
                "theme_negative_share_mean",
                "quadrant",
            ]
        ].to_markdown(index=False),
        "",
        "## 3. 20个景区的首要治理主题",
    ]

    for scenic_row in top_scenics.to_dict("records"):
        scenic_id = scenic_row["official_scenic_id"]
        scenic_name = scenic_row["scenic_name"]
        scenic_topics = scenic_ipa_df.loc[scenic_ipa_df["official_scenic_id"].eq(scenic_id)].sort_values(
            ["scenic_priority_index", "importance", "scenic_gap"],
            ascending=[False, False, False],
            kind="mergesort",
        )
        if scenic_topics.empty:
            continue
        top_topic = scenic_topics.iloc[0]
        sections.extend(
            [
                f"### {scenic_name}",
                f"- priority_rank: {int(scenic_row['priority_rank'])}",
                f"- priority_score: {float(scenic_row['priority_score']):.4f}",
                f"- 首要治理主题: {top_topic['theme_name_cn']}",
                (
                    f"- importance={float(top_topic['importance']):.4f}, "
                    f"gap={float(top_topic['scenic_gap']):.4f}, "
                    f"priority_index={float(top_topic['scenic_priority_index']):.4f}, "
                    f"quadrant={top_topic['quadrant']}"
                ),
                "",
            ]
        )

    output_path.write_text("\n".join(sections), encoding="utf-8")


def write_scenic_ipa_outputs(scenic_ipa_df: pd.DataFrame) -> None:
    for scenic_name, scenic_df in scenic_ipa_df.groupby("scenic_name", sort=False):
        safe_name = sanitize_filename(scenic_name)
        scenic_dir = OUTPUT_IPA_SCENIC_DIR / safe_name
        scenic_dir.mkdir(parents=True, exist_ok=True)

        csv_path = scenic_dir / f"{safe_name}_ipa_table.csv"
        md_path = scenic_dir / f"{safe_name}_ipa_summary.md"
        fig_path = scenic_dir / f"{safe_name}_ipa.png"

        scenic_df = scenic_df.sort_values(
            ["scenic_priority_rank", "importance", "scenic_gap"],
            ascending=[True, False, False],
            kind="mergesort",
        ).reset_index(drop=True)
        scenic_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        plot_ipa(
            scenic_df,
            x_col="importance",
            y_col="scenic_gap",
            x_cut=float(scenic_df["importance_cut"].iloc[0]),
            y_cut=float(scenic_df["gap_cut"].iloc[0]),
            title=f"{scenic_name} IPA",
            output_path=fig_path,
        )

        top_row = scenic_df.iloc[0]
        lines = [
            f"# {scenic_name} IPA",
            "",
            "## 1. 当前景区首要治理主题",
            f"- 主题：{top_row['theme_name_cn']}",
            f"- importance：{float(top_row['importance']):.4f}",
            f"- gap：{float(top_row['scenic_gap']):.4f}",
            f"- priority_index：{float(top_row['scenic_priority_index']):.4f}",
            f"- quadrant：{top_row['quadrant']}",
            "",
            "## 2. 主题排序表",
            scenic_df[
                [
                    "scenic_priority_rank",
                    "theme_name_cn",
                    "importance",
                    "scenic_gap",
                    "scenic_performance",
                    "theme_issue_share_total",
                    "theme_negative_share_total",
                    "quadrant",
                ]
            ].to_markdown(index=False),
        ]
        md_path.write_text("\n".join(lines), encoding="utf-8")


def build_cluster_features(scenic_panel_df: pd.DataFrame, theme_panel_df: pd.DataFrame) -> pd.DataFrame:
    theme_pivot = (
        theme_panel_df.loc[theme_panel_df["is_satisfaction_topic"].eq(0)]
        .pivot_table(
            index=["official_scenic_id", "scenic_name"],
            columns="theme_name_cn",
            values="theme_issue_share_total",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )
    renamed_cols = {}
    for col in theme_pivot.columns:
        if col in {"official_scenic_id", "scenic_name"}:
            continue
        renamed_cols[col] = f"theme_issue_share__{col}"
    theme_pivot = theme_pivot.rename(columns=renamed_cols)

    feature_cols = [
        "official_scenic_id",
        "scenic_name",
        "priority_score",
        "issue_review_rate_hybrid",
        "issue_divergence_rate",
        "high_rating_with_issue_rate",
        "negative_sentiment_rate",
        "avg_sentiment_index",
    ]
    features = scenic_panel_df[feature_cols].merge(
        theme_pivot,
        on=["official_scenic_id", "scenic_name"],
        how="left",
    ).fillna(0.0)
    return features


def choose_cluster_names(cluster_profile_df: pd.DataFrame) -> Dict[int, str]:
    profile = cluster_profile_df.copy()
    profile["severity_score"] = (
        profile["priority_score"]
        + profile["issue_review_rate_hybrid"]
        + profile["negative_sentiment_rate"]
    )
    profile = profile.sort_values(["severity_score", "priority_score"], ascending=[False, False], kind="mergesort").reset_index(drop=True)
    names: Dict[int, str] = {}
    for index, row in profile.iterrows():
        label = CLUSTER_NAME_POOL[index] if index < len(CLUSTER_NAME_POOL) else f"cluster_{index + 1:02d}"
        names[int(row["cluster_id"])] = label
    return names


def build_clustering_outputs(feature_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    id_cols = ["official_scenic_id", "scenic_name"]
    numeric_cols = [col for col in feature_df.columns if col not in id_cols]
    scaler = StandardScaler()
    scaled_values = scaler.fit_transform(feature_df[numeric_cols])

    compare_rows: List[Dict[str, float]] = []
    best_k = None
    best_score = float("-inf")
    max_k = min(5, len(feature_df) - 1)
    for k in range(2, max_k + 1):
        model = KMeans(n_clusters=k, random_state=42, n_init=30)
        labels = model.fit_predict(scaled_values)
        score = silhouette_score(scaled_values, labels)
        compare_rows.append(
            {
                "k": k,
                "silhouette_score": float(score),
                "inertia": float(model.inertia_),
            }
        )
        if score > best_score:
            best_score = score
            best_k = k

    compare_df = pd.DataFrame(compare_rows).sort_values(["silhouette_score", "k"], ascending=[False, True], kind="mergesort")
    selected_k = int(best_k if best_k is not None else 3)

    model = KMeans(n_clusters=selected_k, random_state=42, n_init=30)
    labels = model.fit_predict(scaled_values)
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(scaled_values)

    assignment_df = feature_df.copy()
    assignment_df["cluster_id"] = labels.astype(int)
    assignment_df["pca_x"] = coords[:, 0]
    assignment_df["pca_y"] = coords[:, 1]

    profile_df = (
        assignment_df.groupby("cluster_id", as_index=False)[numeric_cols]
        .mean()
        .sort_values("cluster_id", kind="mergesort")
        .reset_index(drop=True)
    )
    name_map = choose_cluster_names(profile_df)
    assignment_df["cluster_name"] = assignment_df["cluster_id"].map(name_map)
    profile_df["cluster_name"] = profile_df["cluster_id"].map(name_map)

    assignment_df = assignment_df.sort_values(["cluster_name", "priority_score"], ascending=[True, False], kind="mergesort").reset_index(drop=True)
    profile_df = profile_df.sort_values("cluster_name", kind="mergesort").reset_index(drop=True)
    compare_df["is_selected"] = compare_df["k"].eq(selected_k).astype(int)
    return assignment_df, profile_df, compare_df


def plot_cluster_scatter(assignment_df: pd.DataFrame, output_path: Path) -> None:
    configure_matplotlib()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    colors = ["#c0392b", "#2980b9", "#27ae60", "#8e44ad", "#f39c12", "#16a085"]
    cluster_names = assignment_df[["cluster_id", "cluster_name"]].drop_duplicates().sort_values("cluster_id")

    fig, ax = plt.subplots(figsize=(11, 8))
    for idx, row in cluster_names.iterrows():
        cluster_df = assignment_df.loc[assignment_df["cluster_id"].eq(row["cluster_id"])]
        color = colors[idx % len(colors)]
        ax.scatter(
            cluster_df["pca_x"],
            cluster_df["pca_y"],
            s=220,
            color=color,
            alpha=0.85,
            edgecolors="white",
            linewidths=1.2,
            label=row["cluster_name"],
        )
        for _, scenic_row in cluster_df.iterrows():
            ax.text(float(scenic_row["pca_x"]) + 0.03, float(scenic_row["pca_y"]) + 0.03, scenic_row["scenic_name"], fontsize=9)

    ax.set_title("Scenic Clustering")
    ax.set_xlabel("PCA 1")
    ax.set_ylabel("PCA 2")
    ax.grid(alpha=0.25, linestyle=":")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_cluster_report(
    output_path: Path,
    compare_df: pd.DataFrame,
    assignment_df: pd.DataFrame,
    profile_df: pd.DataFrame,
) -> None:
    selected_k = int(compare_df.loc[compare_df["is_selected"].eq(1), "k"].iloc[0])
    lines: List[str] = [
        "# 景区聚类报告",
        "",
        "## 1. 聚类口径",
        "- 聚类单位是 20 个景区。",
        "- 特征使用景区优先级、问题强度、情感表现，以及一级主题问题强度占比。",
        "- `k` 在 2 到 5 之间比较，最终选择轮廓系数最高的方案。",
        "",
        "## 2. K值比较",
        compare_df.to_markdown(index=False),
        "",
        f"## 3. 最终采用 k = {selected_k}",
        profile_df.to_markdown(index=False),
        "",
        "## 4. 各类景区成员",
    ]

    for cluster_name, cluster_df in assignment_df.groupby("cluster_name", sort=False):
        scenic_list = "、".join(cluster_df.sort_values("priority_score", ascending=False)["scenic_name"].tolist())
        lines.extend(
            [
                f"### {cluster_name}",
                f"- 景区：{scenic_list}",
                "",
            ]
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    OUTPUT_IPA_OVERALL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_IPA_SCENIC_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_CLUSTER_DIR.mkdir(parents=True, exist_ok=True)

    scored_df = load_sentiment_issue_df(args.sentiment_path.resolve())
    lda_df = load_lda_assignment_df(args.lda_assignment_path.resolve())

    scenic_panel_df = build_scenic_panel(scored_df)
    theme_panel_df = build_theme_panel(scored_df, lda_df, scenic_panel_df)
    overall_ipa_df = build_overall_ipa_matrix(scenic_panel_df, theme_panel_df)
    scenic_ipa_df = build_scenic_ipa_table(theme_panel_df, overall_ipa_df)

    scenic_panel_df.to_csv(SCENIC_PANEL_PATH, index=False, encoding="utf-8-sig")
    theme_panel_df.to_csv(THEME_PANEL_PATH, index=False, encoding="utf-8-sig")
    overall_ipa_df.to_csv(OVERALL_IPA_PATH, index=False, encoding="utf-8-sig")
    scenic_ipa_df.to_csv(SCENIC_IPA_PATH, index=False, encoding="utf-8-sig")

    plot_ipa(
        overall_ipa_df,
        x_col="importance",
        y_col="gap",
        x_cut=float(overall_ipa_df["importance_cut"].iloc[0]),
        y_cut=float(overall_ipa_df["gap_cut"].iloc[0]),
        title="Overall IPA",
        output_path=OVERALL_IPA_FIG_PATH,
    )
    write_overall_ipa_report(
        OVERALL_REPORT_PATH,
        scenic_panel_df=scenic_panel_df,
        overall_ipa_df=overall_ipa_df,
        scenic_ipa_df=scenic_ipa_df,
        satisfaction_theme_names=theme_panel_df.loc[theme_panel_df["is_satisfaction_topic"].eq(1), "theme_name_cn"].unique().tolist(),
    )
    write_scenic_ipa_outputs(scenic_ipa_df)

    cluster_feature_df = build_cluster_features(scenic_panel_df, theme_panel_df)
    cluster_assignment_df, cluster_profile_df, cluster_compare_df = build_clustering_outputs(cluster_feature_df)
    cluster_feature_df.to_csv(CLUSTER_FEATURE_PATH, index=False, encoding="utf-8-sig")
    cluster_assignment_df.to_csv(CLUSTER_ASSIGNMENT_PATH, index=False, encoding="utf-8-sig")
    cluster_profile_df.to_csv(CLUSTER_PROFILE_PATH, index=False, encoding="utf-8-sig")
    cluster_compare_df.to_csv(CLUSTER_COMPARE_PATH, index=False, encoding="utf-8-sig")
    plot_cluster_scatter(cluster_assignment_df, CLUSTER_FIG_PATH)
    write_cluster_report(CLUSTER_REPORT_PATH, cluster_compare_df, cluster_assignment_df, cluster_profile_df)

    print(f"scenic_panel_csv={SCENIC_PANEL_PATH}")
    print(f"theme_panel_csv={THEME_PANEL_PATH}")
    print(f"overall_ipa_csv={OVERALL_IPA_PATH}")
    print(f"overall_ipa_png={OVERALL_IPA_FIG_PATH}")
    print(f"scenic_ipa_csv={SCENIC_IPA_PATH}")
    print(f"cluster_assignments_csv={CLUSTER_ASSIGNMENT_PATH}")
    print(f"cluster_profiles_csv={CLUSTER_PROFILE_PATH}")
    print(f"cluster_compare_csv={CLUSTER_COMPARE_PATH}")
    print(f"cluster_scatter_png={CLUSTER_FIG_PATH}")


if __name__ == "__main__":
    main()
