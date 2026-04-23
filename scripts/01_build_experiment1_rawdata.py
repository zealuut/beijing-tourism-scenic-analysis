#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT_DIR / "data" / "景区数据"
OUTPUT_DIR = ROOT_DIR / "旅游景点分析" / "data" / "rawdata"
COMBINED_OUTPUT = OUTPUT_DIR / "experiment1_景区300条汇总大表.csv"
SUMMARY_OUTPUT = OUTPUT_DIR / "experiment1_景区抽样汇总.csv"
TARGET_N = 300


def evenly_sample_on_sorted_time(df: pd.DataFrame, target_n: int) -> pd.DataFrame:
    ordered = df.sort_values(
        ["review_time", "page_index", "page_order", "comment_id"],
        kind="mergesort",
    ).reset_index(drop=True)

    if len(ordered) <= target_n:
        return ordered.copy()

    step = (len(ordered) - 1) / (target_n - 1)
    indices = sorted({int(round(i * step)) for i in range(target_n)})

    if len(indices) < target_n:
        seen = set(indices)
        for idx in range(len(ordered)):
            if idx not in seen:
                indices.append(idx)
                seen.add(idx)
            if len(indices) >= target_n:
                break
        indices = sorted(indices[:target_n])
    elif len(indices) > target_n:
        indices = indices[:target_n]

    sampled = ordered.iloc[indices].copy().reset_index(drop=True)
    return sampled


def build_experiment1() -> tuple[pd.DataFrame, pd.DataFrame]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    combined_parts: list[pd.DataFrame] = []
    summary_rows: list[dict] = []

    for source_file in sorted(SOURCE_DIR.glob("*.csv")):
        df = pd.read_csv(source_file, encoding="utf-8-sig")
        if df.empty:
            continue

        df["review_time"] = pd.to_datetime(df["review_time"], errors="coerce")
        df = df[df["review_time"].notna()].copy()
        if df.empty:
            continue

        available_n = len(df)
        sampled = evenly_sample_on_sorted_time(df, TARGET_N)
        sampled["review_time"] = sampled["review_time"].dt.strftime("%Y-%m-%d")
        sampled.insert(0, "experiment_name", "experiment1")
        sampled.insert(1, "source_file_name", source_file.name)
        sampled.insert(2, "source_total_n", available_n)
        sampled.insert(3, "sample_target_n", TARGET_N)
        sampled.insert(4, "sample_actual_n", len(sampled))
        sampled.insert(
            5,
            "sample_rule",
            "time_sorted_evenly_spaced" if available_n > TARGET_N else "keep_all_because_lt_300",
        )
        sampled.insert(6, "sample_rank_within_scenic", range(1, len(sampled) + 1))
        combined_parts.append(sampled)

        summary_rows.append(
            {
                "experiment_name": "experiment1",
                "slot_rank": int(sampled["slot_rank"].iloc[0]),
                "category_name": str(sampled["category_name"].iloc[0]),
                "requested_name": str(sampled["requested_name"].iloc[0]),
                "selected_name": str(sampled["selected_name"].iloc[0]),
                "selected_from": str(sampled["selected_from"].iloc[0]),
                "source_file_name": source_file.name,
                "scenic_name": source_file.stem,
                "available_n": available_n,
                "sample_target_n": TARGET_N,
                "sample_actual_n": len(sampled),
                "sample_rule": "time_sorted_evenly_spaced" if available_n > TARGET_N else "keep_all_because_lt_300",
                "is_full_300": 1 if len(sampled) == TARGET_N else 0,
                "min_review_time": sampled["review_time"].min(),
                "max_review_time": sampled["review_time"].max(),
            }
        )

    combined_df = pd.concat(combined_parts, ignore_index=True) if combined_parts else pd.DataFrame()
    if not combined_df.empty:
        combined_df = combined_df.sort_values(
            ["slot_rank", "review_time", "sample_rank_within_scenic"],
            kind="mergesort",
        ).reset_index(drop=True)

    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(["slot_rank"], kind="mergesort").reset_index(drop=True)

    combined_df.to_csv(COMBINED_OUTPUT, index=False, encoding="utf-8-sig")
    summary_df.to_csv(SUMMARY_OUTPUT, index=False, encoding="utf-8-sig")
    return combined_df, summary_df


if __name__ == "__main__":
    combined_df, summary_df = build_experiment1()
    print(f"COMBINED_OUTPUT={COMBINED_OUTPUT}")
    print(f"SUMMARY_OUTPUT={SUMMARY_OUTPUT}")
    print(f"SCENIC_N={len(summary_df)}")
    print(f"TOTAL_ROWS={len(combined_df)}")
