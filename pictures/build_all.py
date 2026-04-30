from __future__ import annotations

import math
import shutil
from pathlib import Path
from textwrap import fill

import numpy as np
import pandas as pd
import seaborn as sns
from PIL import Image, ImageDraw, ImageFont
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.stats import zscore
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm


REPO_ROOT = Path(__file__).resolve().parents[1]
PICTURES_ROOT = Path(__file__).resolve().parent

for font_path in [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]:
    if Path(font_path).exists():
        fm.fontManager.addfont(font_path)

plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Microsoft JhengHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.facecolor"] = "#FBF8F2"
plt.rcParams["axes.facecolor"] = "#FBF8F2"
plt.rcParams["savefig.facecolor"] = "#FBF8F2"
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.edgecolor"] = "#8A817C"
plt.rcParams["grid.color"] = "#D6CCC2"
plt.rcParams["grid.alpha"] = 0.7
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.linestyle"] = "--"
plt.rcParams["axes.axisbelow"] = True

sns.set_theme(
    style="whitegrid",
    rc={
        "font.family": "Microsoft YaHei",
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Microsoft JhengHei", "Arial Unicode MS"],
        "axes.unicode_minus": False,
    },
)

COLORS = {
    "ticket": "#D2693C",
    "service": "#5B8C5A",
    "traffic": "#4C78A8",
    "highlight": "#C8553D",
    "accent": "#8E6C88",
    "muted": "#7C6F64",
    "gold": "#C2A83E",
    "teal": "#2C7A7B",
}

THEME_COLORS = {
    "票务预约与入园体验": COLORS["ticket"],
    "现场服务与导览体验": COLORS["service"],
    "交通与开放空间体验": COLORS["traffic"],
    "整体满意与感知评价": COLORS["gold"],
}

TAG_NAME_MAP = {
    "staff_service": "工作人员服务",
    "service_process": "现场服务流程",
    "guide_explanation": "导览讲解",
    "queue_wait": "排队等候",
    "reservation_entry": "预约与入园",
    "ticket_price": "票价消费",
    "traffic_access": "交通到达",
    "facility_hygiene": "设施卫生",
    "crowding": "拥挤秩序",
    "commercialization": "商业化干扰",
    "platform_transaction": "平台交易",
}

REGRESSION_TERM_MAP = {
    "const": "常数项",
    "log_zoo_index": "动物园搜索热度（对数）",
    "log_ticket_lag1": "门票指数滞后1日（对数）",
    "log_ticket_lag7": "门票指数滞后7日（对数）",
    "log_ticket_ma7_prev": "门票指数前7日均值（对数）",
    "AQI": "空气质量指数",
    "is_weekend": "周末",
    "is_holiday": "法定假日",
    "is_school_holiday": "学校假期",
}


FIGURE_SPECS = [
    {
        "folder": "LDA一级主题关键词与主题结构图",
        "title": "LDA一级主题关键词与主题结构图",
        "builder": "build_lda_structure",
    },
    {
        "folder": "LDA主题关键词分布图",
        "title": "LDA主题关键词分布图",
        "builder": "build_lda_keyword_distribution",
    },
    {
        "folder": "一级主题—二级治理标签关联热力图",
        "title": "一级主题—二级治理标签关联热力图",
        "builder": "build_theme_tag_heatmap",
    },
    {
        "folder": "评论情感得分分布与三分类阈值图",
        "title": "评论情感得分分布与三分类阈值图",
        "builder": "build_sentiment_histogram",
    },
    {
        "folder": "游客评论情感分布图",
        "title": "游客评论情感分布图",
        "builder": "build_sentiment_class_bar",
    },
    {
        "folder": "不同治理标签下的平均情感得分图",
        "title": "不同治理标签下的平均情感得分图",
        "builder": "build_tag_sentiment_bar",
    },
    {
        "folder": "整体IPA四象限分布图",
        "title": "整体IPA四象限分布图",
        "builder": "build_ipa_overall",
    },
    {
        "folder": "北京动物园IPA四象限分布图",
        "title": "北京动物园IPA四象限分布图",
        "builder": "build_ipa_zoo",
    },
    {
        "folder": "景区治理画像聚类散点图",
        "title": "景区治理画像聚类散点图",
        "builder": "build_cluster_scatter",
    },
    {
        "folder": "景区治理画像层次聚类树状图",
        "title": "景区治理画像层次聚类树状图",
        "builder": "build_cluster_dendrogram",
    },
    {
        "folder": "景区类别平均治理压力对比图",
        "title": "景区类别平均治理压力对比图",
        "builder": "build_category_compare",
    },
    {
        "folder": "高紧迫度景区治理压力排序图",
        "title": "高紧迫度景区治理压力排序图",
        "builder": "build_urgency_ranking",
    },
    {
        "folder": "POI入口压力与票务入园治理压力关系图",
        "title": "POI入口压力与票务入园治理压力关系图",
        "builder": "build_poi_pressure_relation",
    },
    {
        "folder": "重点景区POI空间环境雷达图",
        "title": "重点景区POI空间环境雷达图",
        "builder": "build_poi_radar",
    },
    {
        "folder": "北京动物园POI解释指标比较图",
        "title": "北京动物园POI解释指标比较图",
        "builder": "build_zoo_poi_compare",
    },
    {
        "folder": "北京动物园内部外部POI构成图",
        "title": "北京动物园内部外部POI构成图",
        "builder": "build_zoo_poi_composition",
    },
    {
        "folder": "北京动物园票务压力指数时间序列图",
        "title": "北京动物园票务压力指数时间序列图",
        "builder": "build_ticket_timeseries",
    },
    {
        "folder": "北京动物园动态回归主模型系数图",
        "title": "北京动物园动态回归主模型系数图",
        "builder": "build_dynamic_coefficients",
    },
    {
        "folder": "北京动物园动态压力预测与残差诊断图",
        "title": "北京动物园动态压力预测与残差诊断图",
        "builder": "build_dynamic_fit_and_residuals",
    },
    {
        "folder": "北京动物园Attention风格时滞权重热力图",
        "title": "北京动物园Attention风格时滞权重热力图",
        "builder": "build_attention_heatmap",
    },
    {
        "folder": "SARIMA一阶差分预测与残差白噪声诊断图",
        "title": "SARIMA一阶差分预测与残差白噪声诊断图",
        "builder": "build_sarima_diagnostics",
    },
    {
        "folder": "LSTM-Attention预测效果与误差对比图",
        "title": "LSTM-Attention预测效果与误差对比图",
        "builder": "build_lstm_attention_composite",
    },
    {
        "folder": "Meta-LSTM北京动物园预测结果与不确定性区间图",
        "title": "Meta-LSTM北京动物园预测结果与不确定性区间图",
        "builder": "build_meta_lstm_uncertainty_composite",
    },
]

SKIPPED_FIGURES = [
    "北京旅游景区评论治理诊断技术路线图",
    "景区游客体验治理诊断模型总体流程图",
    "新增数据—模型—输出对应关系图",
    "北京动物园动态案例变量说明图",
    "四类时间序列模型评价指标对比图（仓库中缺少统一可复核的数值评价底表，暂不自动重建）",
]


def pictures_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = [
        ("C:/Windows/Fonts/msyhbd.ttc", True),
        ("C:/Windows/Fonts/msyh.ttc", False),
        ("C:/Windows/Fonts/simhei.ttf", False),
    ]
    if bold:
        font_candidates = [font_candidates[0], *font_candidates[1:]]
    for font_path, _ in font_candidates:
        try:
            return ImageFont.truetype(font_path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def ensure_folder(folder_name: str) -> Path:
    folder = PICTURES_ROOT / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def wrapper_script_text() -> str:
    return """from pathlib import Path
import sys

PICTURES_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PICTURES_ROOT))

from build_all import build_single


if __name__ == "__main__":
    build_single(Path(__file__).resolve().parent.name)
"""


def save_figure(fig: plt.Figure, folder_name: str, note: str | None = None) -> Path:
    folder = ensure_folder(folder_name)
    output_path = folder / "论文图片.png"
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path


def annotate_points(ax: plt.Axes, df: pd.DataFrame, x_col: str, y_col: str, label_col: str, limit: int = 6) -> None:
    focus = df.sort_values(y_col, ascending=False).head(limit)
    for _, row in focus.iterrows():
        ax.text(
            row[x_col] + 0.006,
            row[y_col] + 0.006,
            str(row[label_col]),
            fontsize=9,
            color="#3E3A39",
        )


def add_quadrants(ax: plt.Axes, x_cut: float, y_cut: float) -> None:
    ax.axvline(x_cut, color="#9A8C98", linewidth=1.3, linestyle="--")
    ax.axhline(y_cut, color="#9A8C98", linewidth=1.3, linestyle="--")
    ax.text(x_cut + 0.01, y_cut - 0.08, "优先改进区", color=COLORS["highlight"], fontsize=10, weight="bold")
    ax.text(x_cut + 0.01, y_cut + 0.04, "保持优势区", color=COLORS["service"], fontsize=10, weight="bold")
    ax.text(x_cut - 0.18, y_cut - 0.08, "次要改进区", color=COLORS["muted"], fontsize=10, weight="bold")
    ax.text(x_cut - 0.18, y_cut + 0.04, "低优先观察区", color=COLORS["traffic"], fontsize=10, weight="bold")


def build_lda_structure(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "data" / "lda" / "experiment3_lda_k4_topic_keywords.csv")
    df = df.sort_values("topic_share", ascending=True)
    fig = plt.figure(figsize=(14, 8))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.3])
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    colors = [THEME_COLORS.get(x, COLORS["accent"]) for x in df["topic_name_cn"]]
    ax1.barh(df["topic_name_cn"], df["topic_share"], color=colors)
    for y, value in enumerate(df["topic_share"]):
        ax1.text(value + 0.005, y, f"{value:.1%}", va="center", fontsize=10)
    ax1.set_xlabel("主题占比")
    ax1.set_ylabel("")
    ax1.set_title("一级主题结构占比")

    ax2.axis("off")
    y_pos = 0.92
    for _, row in df.sort_values("topic_share", ascending=False).iterrows():
        color = THEME_COLORS.get(row["topic_name_cn"], COLORS["accent"])
        keywords = "、".join(str(row["top_keywords"]).split("|")[:8])
        wrapped = fill(keywords, width=24)
        ax2.text(0.02, y_pos, row["topic_name_cn"], fontsize=13, weight="bold", color=color, transform=ax2.transAxes)
        ax2.text(
            0.02,
            y_pos - 0.12,
            f"主题定位：{'治理主题' if row['is_satisfaction_topic'] == 0 else '满意度背景主题'}\n核心关键词：{wrapped}",
            fontsize=10.5,
            color="#3E3A39",
            transform=ax2.transAxes,
            linespacing=1.7,
        )
        y_pos -= 0.24

    fig.suptitle(title, fontsize=18, weight="bold", y=0.98)
    return save_figure(fig, folder_name, "数据来源：data/lda/experiment3_lda_k4_topic_keywords.csv")


def build_lda_keyword_distribution(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "data" / "lda" / "experiment3_lda_k4_topic_keywords.csv")
    df = df.sort_values("dominant_review_share", ascending=True)
    fig, ax = plt.subplots(figsize=(13.5, 7.5))
    ax.barh(df["topic_name_cn"], df["dominant_review_share"], color=[THEME_COLORS.get(x, COLORS["accent"]) for x in df["topic_name_cn"]])
    for idx, row in df.iterrows():
        ax.text(
            row["dominant_review_share"] + 0.005,
            row["topic_name_cn"],
            "  " + "、".join(str(row["top_keywords"]).split("|")[:6]),
            va="center",
            fontsize=10,
            color="#514A46",
        )
    ax.set_xlabel("主题主导评论占比")
    ax.set_ylabel("")
    ax.set_title(title, fontsize=17, weight="bold")
    return save_figure(fig, folder_name, "主题关键词作为文本解释信息展示，不直接承担权重估计。")


def build_theme_tag_heatmap(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "ipa_paper" / "experiment7_theme_issue_tag_mapping.csv")
    df["tag_name_cn"] = df["tag_key"].map(TAG_NAME_MAP)
    pivot = df.pivot(index="lda_topic_name_cn", columns="tag_name_cn", values="tag_share_within_issue_reviews").fillna(0.0)
    ordered_rows = ["票务预约与入园体验", "现场服务与导览体验", "交通与开放空间体验"]
    ordered_cols = [
        "预约与入园",
        "排队等候",
        "票价消费",
        "平台交易",
        "工作人员服务",
        "现场服务流程",
        "导览讲解",
        "交通到达",
        "拥挤秩序",
        "设施卫生",
        "商业化干扰",
    ]
    pivot = pivot.reindex(index=ordered_rows, columns=[col for col in ordered_cols if col in pivot.columns])
    fig, ax = plt.subplots(figsize=(13, 5.8))
    sns.heatmap(
        pivot,
        cmap=sns.light_palette(COLORS["ticket"], as_cmap=True),
        annot=True,
        fmt=".0%",
        linewidths=0.8,
        cbar_kws={"label": "标签在问题评论中的占比"},
        ax=ax,
    )
    ax.set_title(title, fontsize=17, weight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.xticks(rotation=30, ha="right")
    return save_figure(fig, folder_name, "数据来源：outputs/ipa_paper/experiment7_theme_issue_tag_mapping.csv")


def build_sentiment_histogram(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "data" / "sentiment" / "experiment5_snownlp_scored.csv")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [1.8, 1.0]})
    ax1.hist(df["sentiment_score"], bins=30, color="#D9A679", edgecolor="white")
    ax1.axvline(0.10, color=COLORS["highlight"], linestyle="--", linewidth=2, label="负向阈值 0.10")
    ax1.axvline(0.85, color=COLORS["service"], linestyle="--", linewidth=2, label="正向阈值 0.85")
    ax1.set_xlabel("情感得分")
    ax1.set_ylabel("评论数量")
    ax1.legend(frameon=True)
    ax1.set_title("连续型情感得分分布")

    class_order = ["negative", "neutral", "positive"]
    class_name = {"negative": "负向", "neutral": "中性", "positive": "正向"}
    counts = df["sentiment_class"].value_counts().reindex(class_order).fillna(0)
    bars = ax2.bar(
        [class_name[x] for x in class_order],
        counts.values,
        color=[COLORS["highlight"], COLORS["gold"], COLORS["service"]],
    )
    total = counts.sum()
    for bar, value in zip(bars, counts.values):
        ax2.text(bar.get_x() + bar.get_width() / 2, value + total * 0.01, f"{value/total:.1%}", ha="center", fontsize=10)
    ax2.set_ylabel("评论数量")
    ax2.set_title("三分类情感结构")
    fig.suptitle(title, fontsize=17, weight="bold", y=1.02)
    return save_figure(fig, folder_name, "阈值口径：正向 >= 0.85；负向 <= 0.10；其余为中性。")


def build_sentiment_class_bar(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "data" / "sentiment" / "experiment5_snownlp_scored.csv")
    counts = df["sentiment_class"].value_counts().reindex(["negative", "neutral", "positive"]).fillna(0)
    labels = ["负向评论", "中性评论", "正向评论"]
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(labels, counts.values, color=[COLORS["highlight"], COLORS["gold"], COLORS["service"]], width=0.58)
    total = counts.sum()
    for bar, value in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + total * 0.012, f"{value:,}\n{value/total:.1%}", ha="center", fontsize=11)
    ax.set_ylabel("评论数量")
    ax.set_title(title, fontsize=17, weight="bold")
    return save_figure(fig, folder_name, "数据来源：data/sentiment/experiment5_snownlp_scored.csv")


def build_tag_sentiment_bar(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "data" / "sentiment" / "experiment5_snownlp_scored.csv")
    rows = []
    for tag_key, tag_name in TAG_NAME_MAP.items():
        col = f"tag_{tag_key}"
        if col not in df.columns:
            continue
        tagged = df[df[col] == 1]
        if tagged.empty:
            continue
        rows.append(
            {
                "tag_name": tag_name,
                "mean_sentiment": tagged["sentiment_score"].mean(),
                "sample_n": len(tagged),
            }
        )
    stat = pd.DataFrame(rows).sort_values("mean_sentiment", ascending=True)
    fig, ax = plt.subplots(figsize=(12.5, 6.6))
    bars = ax.barh(stat["tag_name"], stat["mean_sentiment"], color=sns.color_palette("crest", len(stat)))
    for bar, sample_n in zip(bars, stat["sample_n"]):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2, f"n={sample_n}", va="center", fontsize=9.5)
    ax.set_xlabel("平均情感得分")
    ax.set_ylabel("")
    ax.set_xlim(0, min(1.0, stat["mean_sentiment"].max() + 0.12))
    ax.set_title(title, fontsize=17, weight="bold")
    return save_figure(fig, folder_name, "情感得分越低，说明游客在该类治理问题上的负向体验越强。")


def _build_ipa_scatter(df: pd.DataFrame, title: str, folder_name: str, note: str) -> Path:
    fig, ax = plt.subplots(figsize=(10.8, 7))
    colors = [THEME_COLORS.get(x, COLORS["accent"]) for x in df["theme_name_cn"]]
    sizes = 2600 * df["priority_index"] / df["priority_index"].max()
    ax.scatter(df["importance"], df["performance"], s=sizes, color=colors, alpha=0.85, edgecolors="white", linewidths=1.5)
    for _, row in df.iterrows():
        ax.text(
            row["importance"] + 0.008,
            row["performance"],
            f"{row['theme_name_cn']}\n优先级={row['priority_index']:.3f}",
            fontsize=10,
            va="center",
        )
    add_quadrants(ax, float(df["importance_cut"].iloc[0]), float(df["performance_cut"].iloc[0]))
    ax.set_xlabel("重要性（评论占比）")
    ax.set_ylabel("表现值（1 - 不满意度）")
    ax.set_title(title, fontsize=17, weight="bold")
    return save_figure(fig, folder_name, note)


def build_ipa_overall(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "ipa_paper" / "overall" / "experiment7_ipa_overall_matrix.csv")
    return _build_ipa_scatter(df, title, folder_name, "整体IPA基于三类治理主题的主题重要性、表现值与优先级指数绘制。")


def build_ipa_zoo(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "ipa_paper" / "by_scenic" / "北京动物园" / "北京动物园_ipa_table.csv")
    return _build_ipa_scatter(df, title, folder_name, "单景区IPA以北京动物园为例，突出其票务预约与入园体验的主导治理压力。")


def build_cluster_scatter(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "clustering_paper" / "experiment8_cluster_assignments.csv")
    fig, ax = plt.subplots(figsize=(11.5, 7.4))
    palette = dict(zip(df["cluster_name"].unique(), sns.color_palette("Set2", df["cluster_name"].nunique())))
    sns.scatterplot(
        data=df,
        x="pca_x",
        y="pca_y",
        hue="cluster_name",
        size="total_priority_index",
        sizes=(120, 500),
        palette=palette,
        edgecolor="white",
        linewidth=1.0,
        alpha=0.9,
        ax=ax,
    )
    annotate_points(ax, df, "pca_x", "pca_y", "scenic_name", limit=8)
    ax.set_xlabel("聚类主成分 1")
    ax.set_ylabel("聚类主成分 2")
    ax.set_title(title, fontsize=17, weight="bold")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0)
    return save_figure(fig, folder_name, "气泡大小表示综合治理优先级，颜色表示聚类类型。")


def build_cluster_dendrogram(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "clustering_paper" / "experiment8_cluster_features.csv")
    feature_cols = [col for col in df.columns if col.startswith("priority_index__") or col.startswith("dissatisfaction__")]
    matrix = df[feature_cols].apply(zscore, axis=0).fillna(0.0)
    linked = linkage(matrix.values, method="ward")
    fig, ax = plt.subplots(figsize=(13, 7.5))
    dendrogram(linked, labels=df["scenic_name"].tolist(), leaf_rotation=70, leaf_font_size=9, color_threshold=None, ax=ax)
    ax.set_title(title, fontsize=17, weight="bold")
    ax.set_ylabel("Ward 距离")
    return save_figure(fig, folder_name, "聚类基于三类主题的优先级指数与不满意度特征进行Ward层次聚类。")


def build_category_compare(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "clustering_paper" / "experiment8_category_compare.csv")
    df = df.sort_values("mean_total_priority_index", ascending=True)
    fig, ax = plt.subplots(figsize=(13, 7.2))
    y = np.arange(len(df))
    ax.barh(y - 0.18, df["mean_total_priority_index"], height=0.32, color=COLORS["ticket"], label="平均综合治理优先级")
    ax.barh(y + 0.18, df["mean_mean_dissatisfaction"], height=0.32, color=COLORS["traffic"], label="平均不满意度")
    ax.set_yticks(y)
    ax.set_yticklabels([fill(str(x).replace(" / ", " / "), width=18) for x in df["category_name"]])
    ax.set_xlabel("指数值")
    ax.set_title(title, fontsize=17, weight="bold")
    ax.legend()
    return save_figure(fig, folder_name, "类别比较用于识别不同景区类型的平均治理压力差异。")


def build_urgency_ranking(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "clustering_paper" / "experiment8_urgency_tiers.csv")
    high = df[df["urgency_tier"] == "高"].sort_values("total_priority_index", ascending=True)
    fig, ax = plt.subplots(figsize=(11.5, 6))
    colors = sns.color_palette("flare", len(high))
    bars = ax.barh(high["scenic_name"], high["total_priority_index"], color=colors)
    for bar, diss in zip(bars, high["mean_dissatisfaction"]):
        ax.text(bar.get_width() + 0.004, bar.get_y() + bar.get_height() / 2, f"平均不满意度={diss:.3f}", va="center", fontsize=9.5)
    ax.set_xlabel("综合治理优先级指数")
    ax.set_ylabel("")
    ax.set_title(title, fontsize=17, weight="bold")
    return save_figure(fig, folder_name, "高紧迫度景区按综合治理优先级排序，兼顾不满意度水平解释。")


def build_poi_pressure_relation(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "poi_case_study" / "experiment11_poi_case_panel.csv")
    fig, ax = plt.subplots(figsize=(11, 7))
    sns.regplot(
        data=df,
        x="poi_entry_pressure_index",
        y="priority_index__票务预约与入园体验",
        scatter=False,
        line_kws={"color": COLORS["highlight"], "linewidth": 2},
        ax=ax,
    )
    sns.scatterplot(
        data=df,
        x="poi_entry_pressure_index",
        y="priority_index__票务预约与入园体验",
        hue="cluster_name",
        size="ticket_priority_rank",
        palette="Set2",
        sizes=(100, 280),
        edgecolor="white",
        linewidth=1,
        alpha=0.9,
        ax=ax,
    )
    annotate_points(ax, df.sort_values("priority_index__票务预约与入园体验", ascending=False), "poi_entry_pressure_index", "priority_index__票务预约与入园体验", "scenic_name", limit=7)
    ax.set_xlabel("POI入口压力指数")
    ax.set_ylabel("票务预约与入园体验优先级指数")
    ax.set_title(title, fontsize=17, weight="bold")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0)
    return save_figure(fig, folder_name, "散点越靠右上，说明景区越容易同时出现入口前端压力与票务治理压力。")


def build_poi_radar(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "poi_case_study" / "北京动物园" / "北京动物园_poi_index_compare.csv")
    radar = df[df["index_name_cn"].isin(["到达汇聚指数", "周边活动强度指数", "园内缓冲指数", "空间容量指数", "POI入口压力指数"])].copy()
    labels = radar["index_name_cn"].tolist()
    case_values = radar["case_score"].tolist()
    category_values = radar["same_category_mean"].tolist()
    sample_values = radar["all_sample_mean"].tolist()

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]
    case_values += case_values[:1]
    category_values += category_values[:1]
    sample_values += sample_values[:1]

    fig = plt.figure(figsize=(8.8, 8.2))
    ax = plt.subplot(111, polar=True)
    ax.plot(angles, case_values, color=COLORS["highlight"], linewidth=2.5, label="北京动物园")
    ax.fill(angles, case_values, color=COLORS["highlight"], alpha=0.18)
    ax.plot(angles, category_values, color=COLORS["traffic"], linewidth=2, label="同类别均值")
    ax.plot(angles, sample_values, color=COLORS["gold"], linewidth=2, label="全样本均值")
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 100)
    ax.set_title(title, fontsize=17, weight="bold", pad=22)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.15))
    return save_figure(fig, folder_name, "指标已统一为0至100分位尺度，便于比较北京动物园与同类景区。")


def build_zoo_poi_compare(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "poi_case_study" / "北京动物园" / "北京动物园_poi_index_compare.csv")
    df = df.sort_values("case_score", ascending=True)
    fig, ax = plt.subplots(figsize=(13, 8))
    y = np.arange(len(df))
    ax.barh(y - 0.22, df["case_score"], height=0.2, color=COLORS["highlight"], label="北京动物园")
    ax.barh(y, df["same_category_mean"], height=0.2, color=COLORS["traffic"], label="同类别均值")
    ax.barh(y + 0.22, df["all_sample_mean"], height=0.2, color=COLORS["gold"], label="全样本均值")
    ax.set_yticks(y)
    ax.set_yticklabels(df["index_name_cn"])
    ax.set_xlabel("标准化指数")
    ax.set_title(title, fontsize=17, weight="bold")
    ax.legend()
    return save_figure(fig, folder_name, "比较口径：北京动物园、同类别景区均值、全样本均值。")


def build_zoo_poi_composition(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "poi_case_study" / "北京动物园" / "北京动物园_zone_detail.csv")
    metric_cols = [
        ("transport_n", "交通设施"),
        ("parking_n", "停车设施"),
        ("food_retail_n", "餐饮零售"),
        ("commercial_n", "商业设施"),
        ("public_service_n", "公共服务"),
        ("nearby_attractions_n", "周边景点"),
    ]
    plot_df = df.set_index("poi_zone")
    fig, ax = plt.subplots(figsize=(12, 6.8))
    zones = ["external", "internal"]
    zone_labels = {"external": "外部POI", "internal": "内部POI"}
    bottoms = np.zeros(len(zones))
    colors = sns.color_palette("Set2", len(metric_cols))
    for color, (col, label) in zip(colors, metric_cols):
        values = [plot_df.loc[zone, col] for zone in zones]
        ax.bar([zone_labels[z] for z in zones], values, bottom=bottoms, color=color, label=label)
        bottoms += np.array(values)
    ax.set_ylabel("POI数量")
    ax.set_title(title, fontsize=17, weight="bold")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0)
    return save_figure(fig, folder_name, "北京动物园外围POI显著多于园内POI，说明入口前端吸附压力更强。")


def build_ticket_timeseries(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "data" / "multivariate" / "experiment12_beijing_zoo_dynamic_panel.csv", parse_dates=["date"])
    df["ticket_ma30"] = df["ticket_index"].rolling(30, min_periods=7).mean()
    fig, ax = plt.subplots(figsize=(13.5, 5.6))
    ax.plot(df["date"], df["ticket_index"], color=COLORS["ticket"], linewidth=1.0, alpha=0.55, label="日度门票指数")
    ax.plot(df["date"], df["ticket_ma30"], color=COLORS["highlight"], linewidth=2.4, label="30日移动均值")
    ax.set_ylabel("门票压力指数")
    ax.set_xlabel("")
    ax.set_title(title, fontsize=17, weight="bold")
    ax.legend()
    return save_figure(fig, folder_name, "时间跨度：2019-04-01 至 2026-04-18；用于展示北京动物园票务前端压力的长期波动。")


def build_dynamic_coefficients(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "dynamic_case_study" / "experiment12_dynamic_regression_coefficients.csv")
    df = df[df["term"] != "const"].copy()
    df["term_cn"] = df["term"].map(REGRESSION_TERM_MAP).fillna(df["term"])
    df["low"] = df["coef"] - 1.96 * df["std_error_hac"]
    df["high"] = df["coef"] + 1.96 * df["std_error_hac"]
    df = df.sort_values("coef")
    fig, ax = plt.subplots(figsize=(11.5, 6.6))
    ax.hlines(df["term_cn"], df["low"], df["high"], color="#B8B0A6", linewidth=3)
    ax.scatter(df["coef"], df["term_cn"], color=COLORS["highlight"], s=120, zorder=3)
    ax.axvline(0, color=COLORS["muted"], linestyle="--", linewidth=1.3)
    for _, row in df.iterrows():
        ax.text(row["coef"] + 0.01, row["term_cn"], f"{row['coef']:.3f}{row['signif']}", va="center", fontsize=10)
    ax.set_xlabel("回归系数（含95% HAC置信区间）")
    ax.set_ylabel("")
    ax.set_title(title, fontsize=17, weight="bold")
    return save_figure(fig, folder_name, "正式主模型采用OLS动态回归，并使用Newey-West/HAC稳健标准误。")


def build_dynamic_fit_and_residuals(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "dynamic_case_study" / "experiment12_dynamic_regression_panel_with_fit.csv", parse_dates=["date"])
    plot_df = df.dropna(subset=["main_model_fitted", "main_model_resid"]).copy().tail(365)
    fig, axes = plt.subplots(2, 1, figsize=(13.5, 7.6), sharex=True)
    axes[0].plot(plot_df["date"], plot_df["ticket_index"], color="#BBB8B1", linewidth=1.2, label="真实门票指数")
    axes[0].plot(plot_df["date"], plot_df["main_model_fitted"], color=COLORS["highlight"], linewidth=2.1, label="主模型拟合值")
    axes[0].set_ylabel("门票指数")
    axes[0].legend(loc="upper right")
    axes[0].set_title(title, fontsize=17, weight="bold")

    axes[1].axhline(0, color=COLORS["muted"], linestyle="--", linewidth=1.2)
    axes[1].bar(
        plot_df["date"],
        plot_df["main_model_resid"],
        color=np.where(plot_df["main_model_resid"] >= 0, "#E5989B", "#84DCC6"),
        width=3,
    )
    axes[1].set_ylabel("残差")
    axes[1].set_xlabel("")
    return save_figure(fig, folder_name, "展示最近一年动态回归拟合与残差波动，便于正文直接引用。")


def build_attention_heatmap(title: str, folder_name: str) -> Path:
    df = pd.read_csv(REPO_ROOT / "outputs" / "dynamic_case_study" / "experiment12_attention_like_heatmap_data.csv")
    plot_df = df.set_index("group_name")
    fig, ax = plt.subplots(figsize=(13, 4.3))
    sns.heatmap(
        plot_df,
        cmap=sns.color_palette(["#F4EDE4", COLORS["ticket"]], as_cmap=True),
        annot=True,
        fmt=".3f",
        linewidths=0.8,
        cbar_kws={"label": "相对权重"},
        ax=ax,
    )
    ax.set_xlabel("回看时滞")
    ax.set_ylabel("")
    ax.set_xticklabels([f"T-{i}" for i in range(1, len(plot_df.columns) + 1)], rotation=0)
    ax.set_title(title, fontsize=17, weight="bold")
    return save_figure(fig, folder_name, "高压日对近端时滞更敏感，说明压力具有短期累积与快速传导特征。")


def build_sarima_diagnostics(title: str, folder_name: str) -> Path:
    df = pd.read_excel(REPO_ROOT / "data" / "time_series" / "traffic" / "beijing_traffic_congestion_2023_2024.xlsx")
    df["time"] = pd.to_datetime(df["time"])
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce").interpolate().bfill()
    df = df.sort_values("time").set_index("time").asfreq("D")
    df["rate"] = df["rate"].interpolate().bfill().ffill()

    test_n = min(30, max(14, len(df) // 6))
    train = df.iloc[:-test_n]
    test = df.iloc[-test_n:]

    best_model = None
    best_aic = float("inf")
    best_order = None
    seasonal_order = (1, 1, 1, 7)
    for p in range(0, 3):
        for q in range(0, 3):
            try:
                model = SARIMAX(
                    train["rate"],
                    order=(p, 1, q),
                    seasonal_order=seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                result = model.fit(disp=False)
            except Exception:
                continue
            if result.aic < best_aic:
                best_aic = result.aic
                best_model = result
                best_order = (p, 1, q)

    if best_model is None:
        raise RuntimeError("SARIMA模型未成功拟合。")

    pred = best_model.get_forecast(steps=test_n)
    pred_mean = pred.predicted_mean
    conf = pred.conf_int()
    full_model = SARIMAX(
        df["rate"],
        order=best_order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False)
    resid = full_model.resid[seasonal_order[3] + 1 :].dropna()
    diff_series = df["rate"].diff().dropna()
    lb_p = float(acorr_ljungbox(resid, lags=[10], return_df=True)["lb_pvalue"].iloc[0])
    rmse = math.sqrt(mean_squared_error(test["rate"], pred_mean))
    mae = mean_absolute_error(test["rate"], pred_mean)

    fig, axes = plt.subplots(2, 2, figsize=(14.5, 9))
    axes[0, 0].plot(df.index, df["rate"], color=COLORS["traffic"], linewidth=1.4)
    axes[0, 0].set_title("原始交通拥堵指数序列")
    axes[0, 0].set_ylabel("拥堵指数")

    axes[0, 1].plot(diff_series.index, diff_series.values, color=COLORS["accent"], linewidth=1.2)
    axes[0, 1].axhline(0, color=COLORS["muted"], linestyle="--", linewidth=1)
    axes[0, 1].set_title("一阶差分序列")

    axes[1, 0].plot(train.index, train["rate"], color="#C9C5BE", linewidth=1.2, label="训练样本")
    axes[1, 0].plot(test.index, test["rate"], color=COLORS["traffic"], linewidth=1.6, label="真实值")
    axes[1, 0].plot(test.index, pred_mean, color=COLORS["highlight"], linewidth=2.0, label="SARIMA预测值")
    axes[1, 0].fill_between(test.index, conf.iloc[:, 0], conf.iloc[:, 1], color="#F4A261", alpha=0.18, label="95%置信区间")
    axes[1, 0].set_title(f"滚动外推预测（RMSE={rmse:.3f}, MAE={mae:.3f}）")
    axes[1, 0].legend(loc="upper left")

    plot_acf(resid, lags=min(30, len(resid) - 1), ax=axes[1, 1], color=COLORS["service"])
    axes[1, 1].set_title(f"残差自相关诊断（Ljung-Box p={lb_p:.3f}）")
    fig.suptitle(f"{title}\n最优模型：SARIMA{best_order}×{seasonal_order}", fontsize=17, weight="bold", y=0.98)
    return save_figure(fig, folder_name, "若Ljung-Box检验p值大于0.05，可视为残差近似白噪声。")


def add_title_strip(base_image: Image.Image, title: str, subtitle: str | None = None) -> Image.Image:
    width, height = base_image.size
    top_padding = 88 if not subtitle else 120
    canvas = Image.new("RGB", (width, height + top_padding), color="#FBF8F2")
    canvas.paste(base_image, (0, top_padding))
    draw = ImageDraw.Draw(canvas)
    title_font = pictures_font(32, bold=True)
    sub_font = pictures_font(17)
    draw.text((36, 24), title, font=title_font, fill="#2F2A26")
    if subtitle:
        draw.text((36, 72), subtitle, font=sub_font, fill="#655C56")
        line_y = 102
    else:
        line_y = 70
    draw.line((32, line_y, width - 32, line_y), fill="#D6CCC2", width=2)
    return canvas


def save_pil_image(image: Image.Image, folder_name: str) -> Path:
    folder = ensure_folder(folder_name)
    output_path = folder / "论文图片.png"
    image.save(output_path)
    return output_path


def build_lstm_attention_composite(title: str, folder_name: str) -> Path:
    source = REPO_ROOT / "outputs" / "LSTM_Attention_Metacognitio" / "LSTM_Attention_Metacognitio" / "第二版1.png"
    image = Image.open(source).convert("RGB")
    final_image = add_title_strip(image, title)
    return save_pil_image(final_image, folder_name)


def build_meta_lstm_uncertainty_composite(title: str, folder_name: str) -> Path:
    source = REPO_ROOT / "outputs" / "Meta_LSTM_Zoo_result" / "第六版" / "Figure_4.png"
    image = Image.open(source).convert("RGB")
    final_image = add_title_strip(image, title)
    return save_pil_image(final_image, folder_name)


def build_single(folder_name: str) -> Path:
    spec = next((item for item in FIGURE_SPECS if item["folder"] == folder_name), None)
    if spec is None:
        raise KeyError(f"未找到图名配置：{folder_name}")
    builder = globals()[spec["builder"]]
    return builder(spec["title"], spec["folder"])


def write_wrappers() -> None:
    wrapper = wrapper_script_text()
    for spec in FIGURE_SPECS:
        folder = ensure_folder(spec["folder"])
        script_path = folder / "生成图片.py"
        script_path.write_text(wrapper, encoding="utf-8")


def write_readme(generated_paths: list[Path]) -> None:
    lines = [
        "# 论文图片目录",
        "",
        "本目录按论文图片中文名称建立文件夹，每个文件夹包含：",
        "",
        "- `生成图片.py`：该图的独立生图脚本入口",
        "- `论文图片.png`：已运行生成的图片结果",
        "",
        "## 已自动生成的图片",
        "",
    ]
    for spec, path in zip(FIGURE_SPECS, generated_paths):
        lines.append(f"- `{spec['folder']}` -> `{path.relative_to(PICTURES_ROOT).as_posix()}`")
    lines += [
        "",
        "## 暂不自动生图的图片",
        "",
    ]
    for item in SKIPPED_FIGURES:
        lines.append(f"- {item}")
    (PICTURES_ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    PICTURES_ROOT.mkdir(parents=True, exist_ok=True)
    write_wrappers()
    outputs = []
    for spec in FIGURE_SPECS:
        outputs.append(build_single(spec["folder"]))
    write_readme(outputs)


if __name__ == "__main__":
    main()
