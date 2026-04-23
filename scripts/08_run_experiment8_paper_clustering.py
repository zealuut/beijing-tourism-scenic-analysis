#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_THEME_PANEL_PATH = PROJECT_DIR / "outputs" / "ipa_paper" / "experiment7_theme_panel.csv"
DEFAULT_SCORED_PATH = PROJECT_DIR / "data" / "sentiment" / "experiment5_snownlp_scored.csv"

OUTPUT_DIR = PROJECT_DIR / "outputs" / "clustering_paper"
FEATURE_PATH = OUTPUT_DIR / "experiment8_cluster_features.csv"
COMPARE_PATH = OUTPUT_DIR / "experiment8_cluster_k_compare.csv"
ASSIGNMENT_PATH = OUTPUT_DIR / "experiment8_cluster_assignments.csv"
PROFILE_PATH = OUTPUT_DIR / "experiment8_cluster_profiles.csv"
CATEGORY_COMPARE_PATH = OUTPUT_DIR / "experiment8_category_compare.csv"
URGENCY_PATH = OUTPUT_DIR / "experiment8_urgency_tiers.csv"
SCATTER_PATH = OUTPUT_DIR / "experiment8_cluster_scatter.png"
DENDROGRAM_PATH = OUTPUT_DIR / "experiment8_cluster_dendrogram.png"
REPORT_PATH = OUTPUT_DIR / "experiment8_cluster_report.md"
DOC_PATH = PROJECT_DIR / "docs" / "论文口径聚类说明.md"

THEME_ORDER = [
    "票务预约与入园体验",
    "现场服务与导览体验",
    "交通与开放空间体验",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build interpretable clustering outputs from paper IPA metrics.")
    parser.add_argument("--theme-panel-path", type=Path, default=DEFAULT_THEME_PANEL_PATH)
    parser.add_argument("--scored-path", type=Path, default=DEFAULT_SCORED_PATH)
    return parser.parse_args()


def configure_matplotlib() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def load_theme_panel(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig").copy()
    df["official_scenic_id"] = df["official_scenic_id"].astype(str)
    df["scenic_name"] = df["scenic_name"].fillna("").astype(str)
    df["theme_name_cn"] = df["theme_name_cn"].fillna("").astype(str)
    numeric_cols = ["importance", "issue_rate", "negative_rate", "dissatisfaction_index", "performance", "priority_index"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def load_scored_df(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig").copy()
    df["official_scenic_id"] = df["official_scenic_id"].astype(str)
    df["scenic_name"] = df["scenic_name"].fillna("").astype(str)
    df["category_name"] = df["category_name"].fillna("").astype(str)
    return df


def build_feature_table(theme_df: pd.DataFrame, scored_df: pd.DataFrame) -> pd.DataFrame:
    governance_df = theme_df.loc[theme_df["theme_name_cn"].isin(THEME_ORDER)].copy()
    category_map = (
        scored_df.groupby(["official_scenic_id", "scenic_name"], as_index=False)
        .agg(category_name=("category_name", "first"))
    )

    pivot_priority = governance_df.pivot_table(
        index=["official_scenic_id", "scenic_name"],
        columns="theme_name_cn",
        values="priority_index",
        aggfunc="sum",
        fill_value=0.0,
    )
    pivot_diss = governance_df.pivot_table(
        index=["official_scenic_id", "scenic_name"],
        columns="theme_name_cn",
        values="dissatisfaction_index",
        aggfunc="mean",
        fill_value=0.0,
    )

    priority_cols = {}
    diss_cols = {}
    for theme_name in THEME_ORDER:
        priority_cols[theme_name] = f"priority_index__{theme_name}"
        diss_cols[theme_name] = f"dissatisfaction__{theme_name}"

    pivot_priority = pivot_priority.rename(columns=priority_cols)
    pivot_diss = pivot_diss.rename(columns=diss_cols)

    feature_df = pivot_priority.join(pivot_diss, how="outer").reset_index().fillna(0.0)
    feature_df = feature_df.merge(category_map, on=["official_scenic_id", "scenic_name"], how="left")

    priority_feature_cols = [priority_cols[name] for name in THEME_ORDER]
    diss_feature_cols = [diss_cols[name] for name in THEME_ORDER]
    feature_df["total_priority_index"] = feature_df[priority_feature_cols].sum(axis=1)
    feature_df["mean_dissatisfaction"] = feature_df[diss_feature_cols].mean(axis=1)
    return feature_df


def choose_cluster_name(
    profile_row: pd.Series,
    cluster_order: int,
    low_pressure_cut: float,
    min_total: float,
    max_total: float,
    mean_dissatisfaction_cut: float,
) -> str:
    theme_priority_cols = [f"priority_index__{theme}" for theme in THEME_ORDER]
    total_priority = float(profile_row["total_priority_index"])
    dominant_col = max(theme_priority_cols, key=lambda col: float(profile_row[col]))
    second_col = sorted(theme_priority_cols, key=lambda col: float(profile_row[col]), reverse=True)[1]
    spread = max_total - min_total
    very_low_cut = min_total + 0.25 * spread if spread > 0 else low_pressure_cut

    if total_priority <= very_low_cut:
        if float(profile_row["mean_dissatisfaction"]) <= mean_dissatisfaction_cut:
            return "整体低压稳态型"
        return "低压票务型"
    if total_priority <= low_pressure_cut:
        if dominant_col == "priority_index__票务预约与入园体验":
            return "低压票务型"
        if dominant_col == "priority_index__现场服务与导览体验":
            return "低压服务型"
        return "低压交通型"
    if dominant_col == "priority_index__票务预约与入园体验":
        return "票务高压治理型"
    if dominant_col == "priority_index__现场服务与导览体验":
        if float(profile_row[second_col]) >= float(profile_row[dominant_col]) * 0.8:
            return "服务票务复合型"
        return "服务导览改善型"
    return "交通空间优化型"


def build_clustering_outputs(feature_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray]:
    id_cols = ["official_scenic_id", "scenic_name", "category_name"]
    model_cols = [
        f"priority_index__{theme}" for theme in THEME_ORDER
    ] + [
        f"dissatisfaction__{theme}" for theme in THEME_ORDER
    ] + [
        "total_priority_index",
        "mean_dissatisfaction",
    ]

    scaler = StandardScaler()
    scaled = scaler.fit_transform(feature_df[model_cols])

    compare_rows: List[Dict[str, float]] = []
    best_k = None
    best_score = float("-inf")
    for k in range(2, min(5, len(feature_df) - 1) + 1):
        model = AgglomerativeClustering(n_clusters=k, linkage="ward")
        labels = model.fit_predict(scaled)
        score = silhouette_score(scaled, labels)
        compare_rows.append({"k": k, "silhouette_score": float(score)})
        if score > best_score:
            best_score = score
            best_k = k

    compare_df = pd.DataFrame(compare_rows).sort_values(["silhouette_score", "k"], ascending=[False, True], kind="mergesort")
    selected_k = int(best_k if best_k is not None else 3)
    compare_df["is_selected"] = compare_df["k"].eq(selected_k).astype(int)

    model = AgglomerativeClustering(n_clusters=selected_k, linkage="ward")
    labels = model.fit_predict(scaled)

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(scaled)

    assignment_df = feature_df.copy()
    assignment_df["cluster_id"] = labels.astype(int)
    assignment_df["pca_x"] = coords[:, 0]
    assignment_df["pca_y"] = coords[:, 1]

    numeric_cols = [col for col in assignment_df.columns if col not in id_cols + ["cluster_id", "pca_x", "pca_y"]]
    profile_df = (
        assignment_df.groupby("cluster_id", as_index=False)[numeric_cols]
        .mean()
        .sort_values("cluster_id", kind="mergesort")
        .reset_index(drop=True)
    )
    profile_df = profile_df.sort_values(["total_priority_index", "mean_dissatisfaction"], ascending=[False, False], kind="mergesort").reset_index(drop=True)
    low_pressure_cut = float(profile_df["total_priority_index"].median())
    min_total = float(profile_df["total_priority_index"].min())
    max_total = float(profile_df["total_priority_index"].max())
    mean_dissatisfaction_cut = float(profile_df["mean_dissatisfaction"].median())

    name_map: Dict[int, str] = {}
    used_names: set[str] = set()
    for idx, row in profile_df.iterrows():
        base_name = choose_cluster_name(row, idx, low_pressure_cut, min_total, max_total, mean_dissatisfaction_cut)
        cluster_name = base_name
        suffix = 2
        while cluster_name in used_names:
            cluster_name = f"{base_name}{suffix}"
            suffix += 1
        used_names.add(cluster_name)
        name_map[int(row["cluster_id"])] = cluster_name

    assignment_df["cluster_name"] = assignment_df["cluster_id"].map(name_map)
    profile_df["cluster_name"] = profile_df["cluster_id"].map(name_map)
    assignment_df = assignment_df.sort_values(["cluster_name", "total_priority_index"], ascending=[True, False], kind="mergesort").reset_index(drop=True)
    profile_df = profile_df.sort_values(["total_priority_index", "cluster_id"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    return assignment_df, profile_df, compare_df, scaled


def build_category_compare(feature_df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    priority_cols = [f"priority_index__{theme}" for theme in THEME_ORDER]
    for category_name, group in feature_df.groupby("category_name", sort=True):
        mean_priority = {col: float(group[col].mean()) for col in priority_cols}
        dominant_col = max(priority_cols, key=lambda col: mean_priority[col])
        dominant_theme = dominant_col.replace("priority_index__", "")
        row = {
            "category_name": category_name,
            "scenic_n": int(len(group)),
            "mean_total_priority_index": float(group["total_priority_index"].mean()),
            "mean_mean_dissatisfaction": float(group["mean_dissatisfaction"].mean()),
            "dominant_governance_theme": dominant_theme,
        }
        for col in priority_cols:
            row[col] = mean_priority[col]
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["mean_total_priority_index", "mean_mean_dissatisfaction"],
        ascending=[False, False],
        kind="mergesort",
    ).reset_index(drop=True)


def build_urgency_tiers(feature_df: pd.DataFrame) -> pd.DataFrame:
    tier_df = feature_df.copy()
    ranks = tier_df["total_priority_index"].rank(method="first")
    tier_df["urgency_tier"] = pd.qcut(ranks, q=3, labels=["低", "中", "高"]).astype(str)
    tier_df = tier_df.sort_values(["total_priority_index", "mean_dissatisfaction"], ascending=[False, False], kind="mergesort").reset_index(drop=True)
    return tier_df[
        [
            "official_scenic_id",
            "scenic_name",
            "category_name",
            "total_priority_index",
            "mean_dissatisfaction",
            "urgency_tier",
        ]
    ]


def plot_cluster_scatter(assignment_df: pd.DataFrame, output_path: Path) -> None:
    configure_matplotlib()
    colors = ["#c0392b", "#2980b9", "#27ae60", "#8e44ad", "#f39c12"]
    fig, ax = plt.subplots(figsize=(11, 8))
    cluster_names = assignment_df[["cluster_id", "cluster_name"]].drop_duplicates().sort_values("cluster_id")

    for idx, row in cluster_names.iterrows():
        group = assignment_df.loc[assignment_df["cluster_id"].eq(row["cluster_id"])]
        color = colors[idx % len(colors)]
        ax.scatter(group["pca_x"], group["pca_y"], s=220, color=color, alpha=0.85, edgecolors="white", linewidths=1.2, label=row["cluster_name"])
        for _, scenic_row in group.iterrows():
            ax.text(float(scenic_row["pca_x"]) + 0.03, float(scenic_row["pca_y"]) + 0.03, scenic_row["scenic_name"], fontsize=9)

    ax.set_title("Paper IPA Scenic Clustering")
    ax.set_xlabel("PCA 1")
    ax.set_ylabel("PCA 2")
    ax.grid(alpha=0.25, linestyle=":")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_dendrogram(feature_df: pd.DataFrame, scaled: np.ndarray, output_path: Path) -> None:
    configure_matplotlib()
    linkage_matrix = linkage(scaled, method="ward")
    fig, ax = plt.subplots(figsize=(12, 8))
    dendrogram(linkage_matrix, labels=feature_df["scenic_name"].tolist(), leaf_rotation=45, leaf_font_size=9, ax=ax)
    ax.set_title("Hierarchical Clustering Dendrogram")
    ax.set_ylabel("Distance")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_doc(path: Path) -> None:
    lines = [
        "# 论文口径聚类说明",
        "",
        "## 1. 为什么不用景区原有类别直接做聚类输入",
        "- 景区原有类别是先验分类变量，适合做解释，不适合直接与治理指标一起混入无监督聚类。",
        "- 如果把它直接编码进聚类，会让聚类结果偏向复现原有景区类型，而不是发现治理问题结构。",
        "- 当前样本只有 20 个景区，而且各类别数量不平衡，直接混入类别变量会削弱聚类稳定性。",
        "",
        "## 2. 本轮采用的三层结构",
        "1. 景区原有类别：作为外部解释维度",
        "2. 治理画像聚类：作为主聚类结果",
        "3. 治理紧迫度分层：作为辅助排序结果",
        "",
        "## 3. 主聚类特征",
        "- 每个景区在三个一级治理主题上的 `priority_index`",
        "- 每个景区在三个一级治理主题上的 `dissatisfaction_index`",
        "- `total_priority_index`",
        "- `mean_dissatisfaction`",
        "",
        "## 4. 为什么这套更可解释",
        "- 聚类直接基于 IPA 核心指标，不需要再解释额外黑箱特征。",
        "- 每个类都可以回到“哪个主题优先级更高、哪个主题表现更差”来命名。",
        "- 景区原有类别不参与聚类计算，但可以在聚类后解释“哪些类型景区更容易落在哪类治理画像中”。",
        "",
        "## 5. 论文建议表达",
        "- 用“景区原有类别”回答：哪些类型景区更容易出现什么问题。",
        "- 用“治理画像聚类”回答：哪些景区在问题结构上相似。",
        "- 用“治理紧迫度分层”回答：哪些景区更需要优先治理。",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report(
    path: Path,
    compare_df: pd.DataFrame,
    assignment_df: pd.DataFrame,
    profile_df: pd.DataFrame,
    category_df: pd.DataFrame,
    urgency_df: pd.DataFrame,
) -> None:
    selected_k = int(compare_df.loc[compare_df["is_selected"].eq(1), "k"].iloc[0])
    lines = [
        "# 论文口径聚类报告",
        "",
        "## 1. 主聚类方法",
        "- 聚类对象：20 个景区",
        "- 聚类方法：Ward 层次聚类",
        "- 聚类特征：三个一级治理主题的 priority_index 与 dissatisfaction_index，以及 total_priority_index、mean_dissatisfaction",
        "- 说明：景区原有类别不作为聚类输入，而作为聚类后的解释变量",
        "",
        "## 2. K值比较",
        compare_df.to_markdown(index=False),
        "",
        f"## 3. 最终采用 k = {selected_k}",
        profile_df.to_markdown(index=False),
        "",
        "## 4. 各聚类成员",
    ]

    for cluster_name, group in assignment_df.groupby("cluster_name", sort=False):
        scenic_list = "、".join(group.sort_values("total_priority_index", ascending=False)["scenic_name"].tolist())
        lines.extend([f"### {cluster_name}", f"- 景区：{scenic_list}", ""])

    lines.extend(
        [
            "## 5. 景区原有类别对照",
            category_df.to_markdown(index=False),
            "",
            "## 6. 治理紧迫度分层",
            urgency_df.to_markdown(index=False),
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    theme_df = load_theme_panel(args.theme_panel_path.resolve())
    scored_df = load_scored_df(args.scored_path.resolve())
    feature_df = build_feature_table(theme_df, scored_df)
    assignment_df, profile_df, compare_df, scaled = build_clustering_outputs(feature_df)
    category_df = build_category_compare(feature_df)
    urgency_df = build_urgency_tiers(feature_df)

    feature_df.to_csv(FEATURE_PATH, index=False, encoding="utf-8-sig")
    compare_df.to_csv(COMPARE_PATH, index=False, encoding="utf-8-sig")
    assignment_df.to_csv(ASSIGNMENT_PATH, index=False, encoding="utf-8-sig")
    profile_df.to_csv(PROFILE_PATH, index=False, encoding="utf-8-sig")
    category_df.to_csv(CATEGORY_COMPARE_PATH, index=False, encoding="utf-8-sig")
    urgency_df.to_csv(URGENCY_PATH, index=False, encoding="utf-8-sig")
    plot_cluster_scatter(assignment_df, SCATTER_PATH)
    plot_dendrogram(feature_df, scaled, DENDROGRAM_PATH)
    write_doc(DOC_PATH)
    write_report(REPORT_PATH, compare_df, assignment_df, profile_df, category_df, urgency_df)

    print(f"feature_csv={FEATURE_PATH}")
    print(f"k_compare_csv={COMPARE_PATH}")
    print(f"assignment_csv={ASSIGNMENT_PATH}")
    print(f"profile_csv={PROFILE_PATH}")
    print(f"category_compare_csv={CATEGORY_COMPARE_PATH}")
    print(f"urgency_csv={URGENCY_PATH}")
    print(f"scatter_png={SCATTER_PATH}")
    print(f"dendrogram_png={DENDROGRAM_PATH}")
    print(f"report_md={REPORT_PATH}")


if __name__ == "__main__":
    main()
