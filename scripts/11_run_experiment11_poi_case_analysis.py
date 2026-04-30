from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "poi"
CLUSTER_PATH = ROOT / "outputs" / "clustering_paper" / "experiment8_cluster_assignments.csv"
OUTPUT_DIR = ROOT / "outputs" / "poi_case_study"
CASE_SCENIC_NAME = "北京动物园"


RAW_METRIC_COLUMNS = [
    "transport_count_1000m",
    "parking_count_1000m",
    "nearest_transport_dist_m_1000m",
    "nearest_parking_dist_m_1000m",
    "food_retail_count_2000m",
    "commercial_count_2000m",
    "nearby_attractions_count_2000m",
    "public_service_count_2000m",
    "scenic_area_km2",
    "internal_poi_share",
    "internal_service_share",
]

PRESSURE_COLUMNS = [
    "arrival_pressure_index",
    "surrounding_activity_pressure_index",
    "buffer_shortage_index",
    "space_constraint_index",
]

INDEX_LABELS = {
    "arrival_concentration_index": "到达汇聚指数",
    "surrounding_activity_index": "周边活动强度指数",
    "internal_buffer_index": "园内缓冲指数",
    "space_capacity_index": "空间容量指数",
    "arrival_pressure_index": "到达汇聚压力",
    "surrounding_activity_pressure_index": "周边活动压力",
    "buffer_shortage_index": "园内缓冲不足",
    "space_constraint_index": "空间约束压力",
    "poi_entry_pressure_index": "POI入口压力指数",
}


def percentile_score(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if not higher_is_better:
        numeric = -numeric
    scores = pd.Series(np.nan, index=series.index, dtype=float)
    mask = numeric.notna()
    if mask.any():
        scores.loc[mask] = numeric.loc[mask].rank(method="average", pct=True) * 100
    return scores


def mean_of_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.Series:
    return df[list(columns)].mean(axis=1, skipna=True)


def spearman_corr(series_a: pd.Series, series_b: pd.Series) -> float:
    frame = pd.concat(
        [
            pd.to_numeric(series_a, errors="coerce"),
            pd.to_numeric(series_b, errors="coerce"),
        ],
        axis=1,
    ).dropna()
    if frame.empty:
        return float("nan")
    ranked = frame.rank(method="average")
    return ranked.iloc[:, 0].corr(ranked.iloc[:, 1], method="pearson")


def flatten_zone_summary(zone_df: pd.DataFrame) -> pd.DataFrame:
    value_columns = [
        "poi_n",
        "transport_n",
        "parking_n",
        "food_retail_n",
        "lodging_n",
        "commercial_n",
        "public_service_n",
        "nearby_attractions_n",
    ]
    wide = zone_df.pivot_table(
        index=["official_scenic_id", "scenic_name", "category_name", "has_boundary_polygon"],
        columns="poi_zone",
        values=value_columns,
        aggfunc="first",
    )
    wide.columns = [f"{zone}_{metric}" for metric, zone in wide.columns]
    wide = wide.reset_index()
    return wide


def pick_diagnosis(row: pd.Series) -> str:
    arrival = row["arrival_pressure_index"]
    surrounding = row["surrounding_activity_pressure_index"]
    buffer_shortage = row["buffer_shortage_index"]
    space_constraint = row["space_constraint_index"]

    if arrival >= 60 and surrounding >= 60 and buffer_shortage >= 50:
        return "高汇聚-弱缓冲"
    if arrival >= 60 and surrounding >= 60 and buffer_shortage < 50:
        return "高汇聚-中强缓冲"
    if arrival >= 60 and buffer_shortage >= 50:
        return "高到达-弱缓冲"
    if surrounding >= 60 and buffer_shortage >= 50:
        return "高活动-弱缓冲"
    if space_constraint >= 75 and buffer_shortage >= 50:
        return "空间约束-弱缓冲"
    return "相对平稳"


def fmt(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text{font-family:"Microsoft YaHei","SimHei","Arial Unicode MS",sans-serif;fill:#222} .small{font-size:12px} .tick{font-size:11px;fill:#555} .title{font-size:22px;font-weight:700} .label{font-size:14px} .legend{font-size:13px}</style>',
        '<rect width="100%" height="100%" fill="white"/>',
    ]


def write_svg(path: Path, elements: list[str]) -> None:
    content = "\n".join(elements + ["</svg>"])
    path.write_text(content, encoding="utf-8")


def render_scatter(panel: pd.DataFrame, path: Path) -> None:
    width, height = 960, 680
    left, right, top, bottom = 90, 40, 70, 85
    plot_w = width - left - right
    plot_h = height - top - bottom

    x = panel["poi_entry_pressure_index"]
    y = panel["priority_index__票务预约与入园体验"]
    x_min, x_max = math.floor(x.min() / 10) * 10, math.ceil(x.max() / 10) * 10
    y_min, y_max = 0, math.ceil(y.max() * 10) / 10

    def sx(value: float) -> float:
        return left + (value - x_min) / (x_max - x_min) * plot_w

    def sy(value: float) -> float:
        return top + plot_h - (value - y_min) / (y_max - y_min) * plot_h

    palette = ["#D1495B", "#2E86AB", "#3D9970", "#8E5EA2", "#E67E22"]
    cluster_names = panel["cluster_name"].fillna("未分组").unique().tolist()
    color_map = {name: palette[idx % len(palette)] for idx, name in enumerate(cluster_names)}

    elements = svg_header(width, height)
    elements.append(f'<text x="{width/2}" y="38" text-anchor="middle" class="title">POI入口压力指数与票务预约/入园治理压力</text>')
    elements.append(f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#333" stroke-width="1.4"/>')
    elements.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#333" stroke-width="1.4"/>')

    for tick in np.linspace(x_min, x_max, 6):
        px = sx(tick)
        elements.append(f'<line x1="{px}" y1="{top}" x2="{px}" y2="{top+plot_h}" stroke="#ddd" stroke-width="1"/>')
        elements.append(f'<text x="{px}" y="{top+plot_h+22}" text-anchor="middle" class="tick">{fmt(tick)}</text>')
    for tick in np.linspace(y_min, y_max, 6):
        py = sy(tick)
        elements.append(f'<line x1="{left}" y1="{py}" x2="{left+plot_w}" y2="{py}" stroke="#ddd" stroke-width="1"/>')
        elements.append(f'<text x="{left-10}" y="{py+4}" text-anchor="end" class="tick">{fmt(tick)}</text>')

    elements.append(f'<text x="{left+plot_w/2}" y="{height-25}" text-anchor="middle" class="label">POI入口压力指数</text>')
    elements.append(
        f'<text x="24" y="{top+plot_h/2}" transform="rotate(-90 24 {top+plot_h/2})" text-anchor="middle" class="label">票务预约与入园主题 priority_index</text>'
    )

    label_names = {"北京动物园", "明十三陵", "北京天文馆", "中国科学技术馆"}
    for _, row in panel.iterrows():
        px = sx(row["poi_entry_pressure_index"])
        py = sy(row["priority_index__票务预约与入园体验"])
        fill = color_map[row["cluster_name"]]
        radius = 7 if row["scenic_name"] == "北京动物园" else 5.5
        stroke = "#111" if row["scenic_name"] == "北京动物园" else "white"
        stroke_width = 1.8 if row["scenic_name"] == "北京动物园" else 1.0
        elements.append(
            f'<circle cx="{px}" cy="{py}" r="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" opacity="0.9"/>'
        )
        if row["scenic_name"] in label_names:
            elements.append(
                f'<text x="{px+8}" y="{py-8}" class="small">{row["scenic_name"]}</text>'
            )

    legend_x = width - 220
    legend_y = 88
    elements.append(f'<rect x="{legend_x-12}" y="{legend_y-28}" width="190" height="{26 + 24*len(cluster_names)}" fill="white" stroke="#ddd"/>')
    elements.append(f'<text x="{legend_x}" y="{legend_y-10}" class="legend">聚类类型</text>')
    for idx, cluster_name in enumerate(cluster_names):
        yy = legend_y + idx * 24
        elements.append(f'<circle cx="{legend_x}" cy="{yy}" r="6" fill="{color_map[cluster_name]}"/>')
        elements.append(f'<text x="{legend_x+14}" y="{yy+4}" class="legend">{cluster_name}</text>')

    corr = spearman_corr(
        panel["poi_entry_pressure_index"],
        panel["priority_index__票务预约与入园体验"],
    )
    elements.append(f'<text x="{left}" y="{height-52}" class="small">Spearman相关系数: {corr:.3f}</text>')
    write_svg(path, elements)


def render_radar(case_df: pd.DataFrame, category_df: pd.DataFrame, all_df: pd.DataFrame, path: Path) -> None:
    width, height = 820, 820
    cx, cy = 390, 410
    radius = 255
    labels = [INDEX_LABELS[col] for col in PRESSURE_COLUMNS]
    case_values = case_df.iloc[0][PRESSURE_COLUMNS].tolist()
    category_values = category_df[PRESSURE_COLUMNS].mean().tolist()
    all_values = all_df[PRESSURE_COLUMNS].mean().tolist()
    series = [
        ("北京动物园", case_values, "#D1495B", 0.18),
        ("同类景区均值", category_values, "#2E86AB", 0.08),
        ("全样本均值", all_values, "#3D9970", 0.08),
    ]

    def point(angle: float, value: float) -> tuple[float, float]:
        r = radius * value / 100.0
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    angles = [(-math.pi / 2) + i * 2 * math.pi / len(labels) for i in range(len(labels))]

    elements = svg_header(width, height)
    elements.append(f'<text x="{width/2}" y="38" text-anchor="middle" class="title">北京动物园POI压力画像</text>')

    for level in [25, 50, 75, 100]:
        pts = [point(angle, level) for angle in angles]
        path_str = " ".join(f"{x},{y}" for x, y in pts)
        elements.append(f'<polygon points="{path_str}" fill="none" stroke="#d9d9d9" stroke-width="1"/>')
        elements.append(f'<text x="{cx+5}" y="{cy-radius*level/100-4}" class="tick">{level}</text>')

    for angle, label in zip(angles, labels):
        x2 = cx + radius * math.cos(angle)
        y2 = cy + radius * math.sin(angle)
        lx = cx + (radius + 36) * math.cos(angle)
        ly = cy + (radius + 36) * math.sin(angle)
        elements.append(f'<line x1="{cx}" y1="{cy}" x2="{x2}" y2="{y2}" stroke="#bfbfbf" stroke-width="1"/>')
        elements.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" class="label">{label}</text>')

    for name, values, color, opacity in series:
        pts = [point(angle, value) for angle, value in zip(angles, values)]
        path_str = " ".join(f"{x},{y}" for x, y in pts)
        elements.append(f'<polygon points="{path_str}" fill="{color}" fill-opacity="{opacity}" stroke="{color}" stroke-width="2"/>')

    legend_x = 640
    legend_y = 110
    for idx, (name, _, color, _) in enumerate(series):
        yy = legend_y + idx * 24
        elements.append(f'<line x1="{legend_x}" y1="{yy}" x2="{legend_x+24}" y2="{yy}" stroke="{color}" stroke-width="3"/>')
        elements.append(f'<text x="{legend_x+34}" y="{yy+4}" class="legend">{name}</text>')

    write_svg(path, elements)


def render_internal_external(case_zone: pd.DataFrame, path: Path) -> None:
    subset = case_zone.loc[case_zone["poi_zone"].isin(["internal", "external"])].copy()
    categories = [
        "transport_n",
        "parking_n",
        "food_retail_n",
        "commercial_n",
        "public_service_n",
        "nearby_attractions_n",
    ]
    labels = ["交通", "停车", "餐饮零售", "商业", "公共服务", "周边吸引物"]
    internal = subset.loc[subset["poi_zone"] == "internal", categories]
    external = subset.loc[subset["poi_zone"] == "external", categories]

    internal_values = internal.iloc[0].tolist() if not internal.empty else [0] * len(categories)
    external_values = external.iloc[0].tolist() if not external.empty else [0] * len(categories)
    width, height = 920, 600
    left, right, top, bottom = 70, 40, 70, 80
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_value = max(max(internal_values), max(external_values), 1)
    group_gap = plot_w / len(labels)
    bar_width = 26

    def sy(value: float) -> float:
        return top + plot_h - (value / max_value) * plot_h

    elements = svg_header(width, height)
    elements.append(f'<text x="{width/2}" y="38" text-anchor="middle" class="title">北京动物园内部/外部POI构成</text>')
    elements.append(f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#333" stroke-width="1.4"/>')
    elements.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#333" stroke-width="1.4"/>')

    for tick in np.linspace(0, max_value, 6):
        py = sy(tick)
        elements.append(f'<line x1="{left}" y1="{py}" x2="{left+plot_w}" y2="{py}" stroke="#ddd" stroke-width="1"/>')
        elements.append(f'<text x="{left-10}" y="{py+4}" text-anchor="end" class="tick">{fmt(tick)}</text>')

    for idx, label in enumerate(labels):
        center_x = left + group_gap * idx + group_gap / 2
        x1 = center_x - bar_width - 4
        x2 = center_x + 4
        y1 = sy(internal_values[idx])
        y2 = sy(external_values[idx])
        elements.append(
            f'<rect x="{x1}" y="{y1}" width="{bar_width}" height="{top+plot_h-y1}" fill="#2E86AB"/>'
        )
        elements.append(
            f'<rect x="{x2}" y="{y2}" width="{bar_width}" height="{top+plot_h-y2}" fill="#D1495B"/>'
        )
        elements.append(f'<text x="{center_x}" y="{top+plot_h+24}" text-anchor="middle" class="tick">{label}</text>')

    legend_x = width - 160
    legend_y = 100
    elements.append(f'<rect x="{legend_x}" y="{legend_y}" width="14" height="14" fill="#2E86AB"/>')
    elements.append(f'<text x="{legend_x+22}" y="{legend_y+12}" class="legend">内部</text>')
    elements.append(f'<rect x="{legend_x}" y="{legend_y+26}" width="14" height="14" fill="#D1495B"/>')
    elements.append(f'<text x="{legend_x+22}" y="{legend_y+38}" class="legend">外部</text>')
    write_svg(path, elements)


def main() -> None:
    feature_panel = pd.read_csv(DATA_DIR / "scenic_poi_feature_panel.csv")
    zone_summary = pd.read_csv(DATA_DIR / "scenic_poi_zone_summary.csv")
    area_summary = pd.read_csv(DATA_DIR / "scenic_area_summary.csv")
    cluster_assign = pd.read_csv(CLUSTER_PATH)

    zone_wide = flatten_zone_summary(zone_summary)

    panel = feature_panel.merge(
        area_summary[
            ["official_scenic_id", "has_boundary_polygon", "boundary_status", "scenic_area_km2"]
        ],
        on="official_scenic_id",
        how="left",
        suffixes=("", "_area"),
    )
    panel = panel.merge(
        zone_wide.drop(columns=["scenic_name", "category_name", "has_boundary_polygon"], errors="ignore"),
        on="official_scenic_id",
        how="left",
    )
    panel = panel.merge(
        cluster_assign[
            [
                "official_scenic_id",
                "cluster_name",
                "priority_index__票务预约与入园体验",
                "total_priority_index",
                "mean_dissatisfaction",
            ]
        ],
        on="official_scenic_id",
        how="left",
    )

    fill_zero_columns = [
        "internal_poi_n",
        "external_poi_n",
        "unknown_poi_n",
        "internal_food_retail_n",
        "external_food_retail_n",
        "internal_public_service_n",
        "external_public_service_n",
        "internal_transport_n",
        "external_transport_n",
        "internal_parking_n",
        "external_parking_n",
        "internal_nearby_attractions_n",
        "external_nearby_attractions_n",
    ]
    for column in fill_zero_columns:
        if column in panel.columns:
            panel[column] = panel[column].fillna(0)

    panel["total_zone_poi_n"] = (
        panel.get("internal_poi_n", 0)
        + panel.get("external_poi_n", 0)
        + panel.get("unknown_poi_n", 0)
    )
    panel["internal_service_n"] = panel.get("internal_food_retail_n", 0) + panel.get("internal_public_service_n", 0)
    panel["external_service_n"] = panel.get("external_food_retail_n", 0) + panel.get("external_public_service_n", 0)
    panel["total_service_n"] = panel["internal_service_n"] + panel["external_service_n"]
    panel["internal_poi_share"] = np.where(
        panel["total_zone_poi_n"] > 0,
        panel.get("internal_poi_n", 0) / panel["total_zone_poi_n"],
        np.nan,
    )
    panel["internal_service_share"] = np.where(
        panel["total_service_n"] > 0,
        panel["internal_service_n"] / panel["total_service_n"],
        np.nan,
    )

    panel["score_transport_count_1000m"] = percentile_score(panel["transport_count_1000m"], higher_is_better=True)
    panel["score_parking_count_1000m"] = percentile_score(panel["parking_count_1000m"], higher_is_better=True)
    panel["score_nearest_transport_dist_m_1000m"] = percentile_score(
        panel["nearest_transport_dist_m_1000m"], higher_is_better=False
    )
    panel["score_nearest_parking_dist_m_1000m"] = percentile_score(
        panel["nearest_parking_dist_m_1000m"], higher_is_better=False
    )
    panel["arrival_concentration_index"] = mean_of_columns(
        panel,
        [
            "score_transport_count_1000m",
            "score_parking_count_1000m",
            "score_nearest_transport_dist_m_1000m",
            "score_nearest_parking_dist_m_1000m",
        ],
    )

    panel["score_food_retail_count_2000m"] = percentile_score(panel["food_retail_count_2000m"], higher_is_better=True)
    panel["score_commercial_count_2000m"] = percentile_score(panel["commercial_count_2000m"], higher_is_better=True)
    panel["score_nearby_attractions_count_2000m"] = percentile_score(
        panel["nearby_attractions_count_2000m"], higher_is_better=True
    )
    panel["score_poi_diversity_2000m"] = percentile_score(panel["poi_diversity_2000m"], higher_is_better=True)
    panel["surrounding_activity_index"] = mean_of_columns(
        panel,
        [
            "score_food_retail_count_2000m",
            "score_commercial_count_2000m",
            "score_nearby_attractions_count_2000m",
            "score_poi_diversity_2000m",
        ],
    )

    panel["score_internal_poi_share"] = percentile_score(panel["internal_poi_share"], higher_is_better=True)
    panel["score_internal_service_share"] = percentile_score(panel["internal_service_share"], higher_is_better=True)
    panel["score_internal_public_service_n"] = percentile_score(
        panel.get("internal_public_service_n", pd.Series(np.nan, index=panel.index)),
        higher_is_better=True,
    )
    panel["score_internal_food_retail_n"] = percentile_score(
        panel.get("internal_food_retail_n", pd.Series(np.nan, index=panel.index)),
        higher_is_better=True,
    )
    panel["internal_buffer_index"] = mean_of_columns(
        panel,
        [
            "score_internal_poi_share",
            "score_internal_service_share",
            "score_internal_public_service_n",
            "score_internal_food_retail_n",
        ],
    )

    panel["space_capacity_index"] = percentile_score(panel["scenic_area_km2"], higher_is_better=True)

    panel["arrival_pressure_index"] = panel["arrival_concentration_index"]
    panel["surrounding_activity_pressure_index"] = panel["surrounding_activity_index"]
    panel["buffer_shortage_index"] = 100 - panel["internal_buffer_index"]
    panel["space_constraint_index"] = 100 - panel["space_capacity_index"]
    panel["poi_entry_pressure_index"] = mean_of_columns(panel, PRESSURE_COLUMNS)
    panel["poi_entry_pressure_rank"] = panel["poi_entry_pressure_index"].rank(
        method="min", ascending=False
    )
    panel["poi_entry_pressure_rank_in_category"] = panel.groupby("category_name")[
        "poi_entry_pressure_index"
    ].rank(method="min", ascending=False)
    panel["ticket_priority_rank"] = panel["priority_index__票务预约与入园体验"].rank(
        method="min", ascending=False
    )
    panel["ticket_priority_rank_in_category"] = panel.groupby("category_name")[
        "priority_index__票务预约与入园体验"
    ].rank(method="min", ascending=False)
    panel["poi_case_diagnosis"] = panel.apply(pick_diagnosis, axis=1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    case_dir = OUTPUT_DIR / CASE_SCENIC_NAME
    case_dir.mkdir(parents=True, exist_ok=True)

    export_columns = [
        "official_scenic_id",
        "scenic_name",
        "category_name",
        "cluster_name",
        "has_boundary_polygon",
        "boundary_status",
        "priority_index__票务预约与入园体验",
        "ticket_priority_rank",
        "total_priority_index",
        "mean_dissatisfaction",
        "arrival_concentration_index",
        "surrounding_activity_index",
        "internal_buffer_index",
        "space_capacity_index",
        "arrival_pressure_index",
        "surrounding_activity_pressure_index",
        "buffer_shortage_index",
        "space_constraint_index",
        "poi_entry_pressure_index",
        "poi_entry_pressure_rank",
        "poi_entry_pressure_rank_in_category",
        "poi_case_diagnosis",
        "ticket_priority_rank_in_category",
        "scenic_area_km2",
        "internal_poi_share",
        "internal_service_share",
        "internal_poi_n",
        "external_poi_n",
        "internal_service_n",
        "external_service_n",
    ] + RAW_METRIC_COLUMNS
    panel[export_columns].sort_values("poi_entry_pressure_index", ascending=False).to_csv(
        OUTPUT_DIR / "experiment11_poi_case_panel.csv", index=False, encoding="utf-8-sig"
    )

    case_df = panel.loc[panel["scenic_name"] == CASE_SCENIC_NAME].copy()
    if case_df.empty:
        raise ValueError(f"未找到案例景区: {CASE_SCENIC_NAME}")

    category_name = case_df.iloc[0]["category_name"]
    category_df = panel.loc[panel["category_name"] == category_name].copy()

    # Case raw metric comparison.
    metric_rows = []
    for column in RAW_METRIC_COLUMNS:
        case_value = case_df.iloc[0][column] if column in case_df.columns else np.nan
        category_mean = category_df[column].mean() if column in category_df.columns else np.nan
        all_mean = panel[column].mean() if column in panel.columns else np.nan
        overall_percentile = percentile_score(panel[column], higher_is_better=True).loc[case_df.index[0]]
        if column.startswith("nearest_"):
            overall_percentile = percentile_score(panel[column], higher_is_better=False).loc[case_df.index[0]]
        metric_rows.append(
            {
                "metric_name": column,
                "case_value": case_value,
                "same_category_mean": category_mean,
                "all_sample_mean": all_mean,
                "case_overall_percentile": overall_percentile,
            }
        )
    metric_compare = pd.DataFrame(metric_rows)
    metric_compare.to_csv(
        case_dir / "北京动物园_poi_raw_metric_compare.csv",
        index=False,
        encoding="utf-8-sig",
    )

    dimension_rows = []
    for column in [
        "arrival_concentration_index",
        "surrounding_activity_index",
        "internal_buffer_index",
        "space_capacity_index",
        "arrival_pressure_index",
        "surrounding_activity_pressure_index",
        "buffer_shortage_index",
        "space_constraint_index",
        "poi_entry_pressure_index",
    ]:
        dimension_rows.append(
            {
                "index_key": column,
                "index_name_cn": INDEX_LABELS[column],
                "case_score": case_df.iloc[0][column],
                "same_category_mean": category_df[column].mean(),
                "all_sample_mean": panel[column].mean(),
                "overall_rank_desc": int(panel[column].rank(method="min", ascending=False).loc[case_df.index[0]]),
                "same_category_rank_desc": int(
                    category_df[column].rank(method="min", ascending=False).loc[case_df.index[0]]
                ),
                "sample_size": int(panel[column].notna().sum()),
            }
        )
    case_index_compare = pd.DataFrame(dimension_rows)
    case_index_compare.to_csv(
        case_dir / "北京动物园_poi_index_compare.csv",
        index=False,
        encoding="utf-8-sig",
    )

    zone_case = zone_summary.loc[zone_summary["scenic_name"] == CASE_SCENIC_NAME].copy()
    zone_case.to_csv(case_dir / "北京动物园_zone_detail.csv", index=False, encoding="utf-8-sig")

    render_scatter(panel, OUTPUT_DIR / "experiment11_poi_pressure_vs_ticket_priority.svg")
    render_radar(case_df, category_df, panel, case_dir / "北京动物园_poi_pressure_radar.svg")
    render_internal_external(zone_case, case_dir / "北京动物园_internal_external_bar.svg")

    report_lines = [
        "# 北京动物园 POI 案例研究报告",
        "",
        "## 1. 案例选择",
        f"- 案例景区：{CASE_SCENIC_NAME}",
        f"- 聚类类型：{case_df.iloc[0]['cluster_name']}",
        f"- 票务预约与入园主题 priority_index：{case_df.iloc[0]['priority_index__票务预约与入园体验']:.4f}",
        f"- 票务预约与入园主题压力排名：{int(case_df.iloc[0]['ticket_priority_rank'])} / {len(panel)}",
        f"- 同类景区内票务预约与入园压力排名：{int(case_df.iloc[0]['ticket_priority_rank_in_category'])} / {len(category_df)}",
        f"- POI入口压力指数：{case_df.iloc[0]['poi_entry_pressure_index']:.2f}",
        f"- POI入口压力排名：{int(case_df.iloc[0]['poi_entry_pressure_rank'])} / {len(panel)}",
        f"- 同类景区内POI入口压力排名：{int(case_df.iloc[0]['poi_entry_pressure_rank_in_category'])} / {len(category_df)}",
        f"- POI诊断类型：{case_df.iloc[0]['poi_case_diagnosis']}",
        "",
        "## 2. 核心判断",
        "- 北京动物园并不是单纯“园内服务差”，而是“高到达汇聚 + 高周边活动”共同作用下的入口治理压力景区。",
        "- 从POI环境看，它更像一个高强度城市活动节点，而不是相对封闭、慢进入的郊野型景区。",
        "- 园内缓冲并非样本中最弱，但不足以完全抵消外部高强度汇聚，因此压力更容易前置到预约、检票和入园组织环节。",
        "- 该方法更适合做“同类景区比较下的环境解释”，而不是把 POI 指数直接当作所有景区票务压力的线性预测器。",
        "",
        "## 3. 维度解读",
        f"- 到达汇聚指数：{case_df.iloc[0]['arrival_concentration_index']:.2f}。北京动物园周边公交/地铁接驳密集，停车资源也较丰富，意味着客流更容易在短时间内向入口集中。",
        f"- 周边活动强度指数：{case_df.iloc[0]['surrounding_activity_index']:.2f}。周边餐饮零售、公共服务和其他活动节点较多，放大了景区入口周边的人流叠加效应。",
        f"- 园内缓冲指数：{case_df.iloc[0]['internal_buffer_index']:.2f}。北京动物园园内并非毫无缓冲，但园内POI占比和服务占比仍然偏低，说明游客在进入景区前后仍较多依赖外部环境，而不是被园内设施完全吸收。",
        f"- 空间容量指数：{case_df.iloc[0]['space_capacity_index']:.2f}。北京动物园面积并不算最小，因此它的首要矛盾并不主要来自绝对面积不足，而是汇聚速度快于入口前端管理的吸收能力。",
        "",
        "## 4. 论文建议写法",
        "- 若将POI环境理解为治理压力的外部成因，北京动物园体现出的不是单一“交通差”或“商业化高”，而是高可达城市景区在入口前端面临的汇聚性治理压力。",
        "- 这类景区的首要优化方向应放在预约、检票、分时入园、排队组织与入口空间疏导，而不是优先从园内游览内容入手。",
    ]
    (case_dir / "北京动物园_case_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    readme_lines = [
        "# POI案例研究输出",
        "",
        "## 1. 方法定位",
        "- 该目录用于把POI环境从“点位数量表”转成“可解释的治理环境指标”。",
        "- 核心不是直接证明票务差，而是解释哪些景区更容易形成入口汇聚压力。",
        "",
        "## 2. 四个维度",
        "- 到达汇聚指数：交通与停车的近距离可达性，越高表示客流越容易在入口前端集中。",
        "- 周边活动强度指数：周边餐饮零售、商业、吸引物和POI多样性，越高表示景区周边活动叠加越强。",
        "- 园内缓冲指数：园内POI占比、园内服务占比及园内基础服务数量，越高表示游客进入景区后越容易被内部设施吸收。",
        "- 空间容量指数：景区边界面积，越高表示物理空间约束越弱。",
        "",
        "## 3. 综合指数",
        "- POI入口压力指数 = 平均值(到达汇聚压力, 周边活动压力, 园内缓冲不足, 空间约束压力)",
        "- 其中：园内缓冲不足 = 100 - 园内缓冲指数；空间约束压力 = 100 - 空间容量指数。",
        "- 所有基础分值均用样本内百分位得分表示，范围 0-100，便于跨指标比较。",
        "",
        "## 4. 主要文件",
        "- `experiment11_poi_case_panel.csv`：20个景区的POI解释面板。",
        "- `experiment11_poi_pressure_vs_ticket_priority.svg`：POI入口压力与票务/入园治理压力关系图。",
        "- `北京动物园/北京动物园_case_report.md`：北京动物园案例报告。",
        "- `北京动物园/北京动物园_poi_pressure_radar.svg`：北京动物园案例雷达图。",
        "- `北京动物园/北京动物园_internal_external_bar.svg`：北京动物园内部/外部POI构成图。",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
