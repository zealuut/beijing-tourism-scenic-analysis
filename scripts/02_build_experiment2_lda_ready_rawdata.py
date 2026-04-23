#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import jieba
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT_DIR / "data" / "景区数据"
OUTPUT_DIR = ROOT_DIR / "旅游景点分析" / "data" / "rawdata"
COMBINED_OUTPUT = OUTPUT_DIR / "experiment2_lda_评分分层300条汇总大表.csv"
SUMMARY_OUTPUT = OUTPUT_DIR / "experiment2_lda_景区汇总.csv"
STRATA_OUTPUT = OUTPUT_DIR / "experiment2_lda_评分分层配额明细.csv"
TOKEN_FREQ_OUTPUT = OUTPUT_DIR / "experiment2_lda_全局词频表.csv"

TARGET_N = 300
MIN_TEXT_CHAR_LEN = 6
MIN_TOKEN_FREQ = 5
MIN_TOKEN_COUNT = 5

BASE_STOPWORDS = {
    "我们", "你们", "他们", "这个", "那个", "这里", "那里", "还是", "就是", "感觉", "真的", "比较",
    "特别", "非常", "已经", "可以", "觉得", "一个", "一下", "没有", "不是", "而且", "如果", "因为",
    "所以", "很多", "一些", "时候", "里面", "外面", "的话", "出来", "进去", "景区", "景点", "地方",
    "北京", "故宫", "长城", "公园", "博物馆", "景山", "颐和园", "天坛", "值得", "真的很", "还是很",
    "一次", "就是个", "这里的", "还有", "一下子", "有点", "一些人", "太多", "但是", "而且还",
}


def normalize_review_text(text: str) -> str:
    text = str(text or "").replace("\u3000", " ").replace("\xa0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def build_dynamic_stopwords(frames: list[pd.DataFrame]) -> set[str]:
    dynamic_stopwords = set(BASE_STOPWORDS)
    name_cols = ["requested_name", "selected_name", "scenic_name"]
    for df in frames:
        for col in name_cols:
            if col not in df.columns:
                continue
            for value in df[col].dropna().astype(str).tolist():
                value = re.sub(r"[（）()\-—·\s]", "", value)
                if len(value) >= 2:
                    dynamic_stopwords.add(value)
                for token in jieba.lcut(value, cut_all=False):
                    token = token.strip()
                    if len(token) >= 2:
                        dynamic_stopwords.add(token)
    return dynamic_stopwords


def tokenize_text(text: str, stopwords: set[str]) -> list[str]:
    tokens: list[str] = []
    for token in jieba.lcut(str(text), cut_all=False):
        token = token.strip().lower()
        if len(token) < 2:
            continue
        if token in stopwords:
            continue
        if token.isdigit():
            continue
        if re.fullmatch(r"[\W_]+", token):
            continue
        tokens.append(token)
    return tokens


def evenly_sample_on_sorted_time(df: pd.DataFrame, target_n: int) -> pd.DataFrame:
    ordered = df.sort_values(
        ["review_time", "page_index", "page_order", "comment_id"],
        kind="mergesort",
    ).reset_index(drop=True)

    if len(ordered) <= target_n:
        return ordered.copy()

    if target_n <= 1:
        return ordered.iloc[[0]].copy().reset_index(drop=True)

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

    return ordered.iloc[indices].copy().reset_index(drop=True)


def allocate_quota(group_sizes: pd.Series, total: int) -> dict[int, int]:
    if group_sizes.empty:
        return {}

    group_sizes = group_sizes.astype(int)
    if total >= int(group_sizes.sum()):
        return {int(key): int(value) for key, value in group_sizes.items()}

    raw = group_sizes / group_sizes.sum() * total
    base = raw.apply(math.floor).astype(int)
    remainders = (raw - base).sort_values(ascending=False)
    deficit = total - int(base.sum())

    for key in remainders.index[:deficit]:
        base.loc[key] += 1

    positive_keys = [key for key, value in group_sizes.items() if value > 0]
    for key in positive_keys:
        if base.loc[key] == 0:
            base.loc[key] = 1

    overflow = int(base.sum()) - total
    if overflow > 0:
        for key in base.sort_values(ascending=False).index:
            reducible = min(overflow, max(base.loc[key] - 1, 0))
            if reducible > 0:
                base.loc[key] -= reducible
                overflow -= reducible
            if overflow <= 0:
                break

    for key in base.index:
        base.loc[key] = min(int(base.loc[key]), int(group_sizes.loc[key]))

    current_total = int(base.sum())
    if current_total < total:
        for key in remainders.index:
            spare = int(group_sizes.loc[key] - base.loc[key])
            if spare <= 0:
                continue
            add_n = min(spare, total - current_total)
            base.loc[key] += add_n
            current_total += add_n
            if current_total >= total:
                break

    return {int(key): int(value) for key, value in base.items() if int(value) > 0}


def rating_bucket_from_score(score: float) -> int:
    rounded = int(round(float(score)))
    return max(1, min(5, rounded))


def format_bucket_counts(series: pd.Series) -> str:
    parts = [f"{int(bucket)}:{int(count)}" for bucket, count in series.sort_index().items()]
    return "|".join(parts)


def build_experiment2() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    scenic_frames: list[pd.DataFrame] = []
    summary_rows: list[dict] = []
    strata_rows: list[dict] = []

    for source_file in sorted(SOURCE_DIR.glob("*.csv")):
        df = pd.read_csv(source_file, encoding="utf-8-sig")
        if df.empty:
            continue

        source_total_raw_n = len(df)
        df["review_text"] = df["review_text"].map(normalize_review_text)
        df["review_time"] = pd.to_datetime(df["review_time"], errors="coerce")
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        df = df[df["review_time"].notna() & df["rating"].notna()].copy()
        if df.empty:
            continue

        valid_time_rating_n = len(df)
        df = df[df["review_text"].str.len() >= MIN_TEXT_CHAR_LEN].copy()
        if df.empty:
            continue

        df["source_file_name"] = source_file.name
        df["source_total_raw_n"] = source_total_raw_n
        df["valid_time_rating_n"] = valid_time_rating_n
        df["after_short_text_filter_n"] = len(df)
        df["text_char_len"] = df["review_text"].str.len()
        df["rating_bucket"] = df["rating"].map(rating_bucket_from_score)
        scenic_frames.append(df)

    if not scenic_frames:
        empty = pd.DataFrame()
        empty.to_csv(COMBINED_OUTPUT, index=False, encoding="utf-8-sig")
        empty.to_csv(SUMMARY_OUTPUT, index=False, encoding="utf-8-sig")
        empty.to_csv(STRATA_OUTPUT, index=False, encoding="utf-8-sig")
        empty.to_csv(TOKEN_FREQ_OUTPUT, index=False, encoding="utf-8-sig")
        return empty, empty, empty, empty

    dynamic_stopwords = build_dynamic_stopwords(scenic_frames)

    tokenized_frames: list[pd.DataFrame] = []
    token_counter: Counter[str] = Counter()
    for df in scenic_frames:
        current = df.copy()
        current["tokens_before_freq_filter"] = current["review_text"].map(
            lambda text: tokenize_text(text, dynamic_stopwords)
        )
        token_counter.update(token for tokens in current["tokens_before_freq_filter"] for token in tokens)
        tokenized_frames.append(current)

    token_freq_df = (
        pd.DataFrame(
            [{"token": token, "global_freq": freq} for token, freq in token_counter.items()]
        )
        .sort_values(["global_freq", "token"], ascending=[False, True], kind="mergesort")
        .reset_index(drop=True)
    )
    token_freq_df.to_csv(TOKEN_FREQ_OUTPUT, index=False, encoding="utf-8-sig")

    filtered_parts: list[pd.DataFrame] = []
    for df in tokenized_frames:
        current = df.copy()
        current["tokens_list"] = current["tokens_before_freq_filter"].map(
            lambda xs: [token for token in xs if token_counter[token] >= MIN_TOKEN_FREQ]
        )
        current["token_count"] = current["tokens_list"].map(len)
        current = current[current["token_count"] >= MIN_TOKEN_COUNT].copy()
        current["tokens_text"] = current["tokens_list"].map(lambda xs: " ".join(xs))
        current["tokens_pipe"] = current["tokens_list"].map(lambda xs: "|".join(xs))
        filtered_parts.append(current)

    combined_candidates = pd.concat(filtered_parts, ignore_index=True) if filtered_parts else pd.DataFrame()
    sampled_parts: list[pd.DataFrame] = []

    for scenic_name, group in combined_candidates.groupby("scenic_name", sort=False):
        ordered_group = group.sort_values(
            ["review_time", "page_index", "page_order", "comment_id"],
            kind="mergesort",
        ).reset_index(drop=True)

        raw_available_n = int(len(ordered_group))
        sampled_n = min(TARGET_N, raw_available_n)
        before_bucket_counts = ordered_group["rating_bucket"].value_counts().sort_index()

        if raw_available_n <= TARGET_N:
            scenic_sampled = ordered_group.copy().reset_index(drop=True)
            quota_map = {int(bucket): int(count) for bucket, count in before_bucket_counts.items()}
            sample_rule = "keep_all_after_lda_filter_because_lt_300"
        else:
            quota_map = allocate_quota(before_bucket_counts, TARGET_N)
            stratum_samples: list[pd.DataFrame] = []
            for bucket, quota in quota_map.items():
                bucket_group = ordered_group[ordered_group["rating_bucket"] == bucket].copy()
                bucket_sampled = evenly_sample_on_sorted_time(bucket_group, quota)
                bucket_sampled["sample_quota_in_bucket"] = quota
                bucket_sampled["sample_rank_within_rating_bucket"] = range(1, len(bucket_sampled) + 1)
                stratum_samples.append(bucket_sampled)

            scenic_sampled = pd.concat(stratum_samples, ignore_index=True)
            scenic_sampled = scenic_sampled.sort_values(
                ["review_time", "rating_bucket", "page_index", "page_order", "comment_id"],
                kind="mergesort",
            ).reset_index(drop=True)
            sample_rule = "rating_stratified_time_sorted_evenly_spaced"

        if "sample_quota_in_bucket" not in scenic_sampled.columns:
            scenic_sampled["sample_quota_in_bucket"] = scenic_sampled["rating_bucket"].map(quota_map)
        if "sample_rank_within_rating_bucket" not in scenic_sampled.columns:
            scenic_sampled["sample_rank_within_rating_bucket"] = scenic_sampled.groupby("rating_bucket").cumcount() + 1

        scenic_sampled["review_time"] = scenic_sampled["review_time"].dt.strftime("%Y-%m-%d")
        scenic_sampled.insert(0, "experiment_name", "experiment2_lda_ready")
        scenic_sampled.insert(1, "available_after_lda_filter_n", raw_available_n)
        scenic_sampled.insert(2, "sample_target_n", TARGET_N)
        scenic_sampled.insert(3, "sample_actual_n", len(scenic_sampled))
        scenic_sampled.insert(4, "sample_rule", sample_rule)
        scenic_sampled.insert(5, "low_freq_min_token_freq", MIN_TOKEN_FREQ)
        scenic_sampled.insert(6, "lda_min_token_count", MIN_TOKEN_COUNT)
        scenic_sampled.insert(7, "sample_rank_within_scenic", range(1, len(scenic_sampled) + 1))
        sampled_parts.append(scenic_sampled)

        sampled_bucket_counts = scenic_sampled["rating_bucket"].value_counts().sort_index()
        summary_rows.append(
            {
                "experiment_name": "experiment2_lda_ready",
                "slot_rank": int(scenic_sampled["slot_rank"].iloc[0]),
                "category_name": str(scenic_sampled["category_name"].iloc[0]),
                "requested_name": str(scenic_sampled["requested_name"].iloc[0]),
                "selected_name": str(scenic_sampled["selected_name"].iloc[0]),
                "selected_from": str(scenic_sampled["selected_from"].iloc[0]),
                "source_file_name": str(scenic_sampled["source_file_name"].iloc[0]),
                "scenic_name": scenic_name,
                "source_total_raw_n": int(scenic_sampled["source_total_raw_n"].iloc[0]),
                "valid_time_rating_n": int(scenic_sampled["valid_time_rating_n"].iloc[0]),
                "after_short_text_filter_n": int(scenic_sampled["after_short_text_filter_n"].iloc[0]),
                "available_after_lda_filter_n": raw_available_n,
                "sample_target_n": TARGET_N,
                "sample_actual_n": len(scenic_sampled),
                "sample_rule": sample_rule,
                "is_full_300": 1 if len(scenic_sampled) == TARGET_N else 0,
                "min_review_time": scenic_sampled["review_time"].min(),
                "max_review_time": scenic_sampled["review_time"].max(),
                "mean_token_count": round(float(scenic_sampled["token_count"].mean()), 2),
                "rating_bucket_dist_before_sample": format_bucket_counts(before_bucket_counts),
                "rating_bucket_dist_sampled": format_bucket_counts(sampled_bucket_counts),
            }
        )

        for bucket in sorted(before_bucket_counts.index.tolist()):
            strata_rows.append(
                {
                    "experiment_name": "experiment2_lda_ready",
                    "slot_rank": int(scenic_sampled["slot_rank"].iloc[0]),
                    "scenic_name": scenic_name,
                    "rating_bucket": int(bucket),
                    "available_in_bucket_after_lda_filter_n": int(before_bucket_counts.get(bucket, 0)),
                    "sample_quota_n": int(quota_map.get(int(bucket), 0)),
                    "sample_actual_n": int(sampled_bucket_counts.get(bucket, 0)),
                }
            )

    combined_df = pd.concat(sampled_parts, ignore_index=True) if sampled_parts else pd.DataFrame()
    if not combined_df.empty:
        combined_df = combined_df.sort_values(
            ["slot_rank", "review_time", "rating_bucket", "sample_rank_within_scenic"],
            kind="mergesort",
        ).reset_index(drop=True)
        combined_df = combined_df.drop(columns=["tokens_before_freq_filter", "tokens_list"], errors="ignore")

    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(["slot_rank"], kind="mergesort").reset_index(drop=True)

    strata_df = pd.DataFrame(strata_rows)
    if not strata_df.empty:
        strata_df = strata_df.sort_values(["slot_rank", "rating_bucket"], kind="mergesort").reset_index(drop=True)

    combined_df.to_csv(COMBINED_OUTPUT, index=False, encoding="utf-8-sig")
    summary_df.to_csv(SUMMARY_OUTPUT, index=False, encoding="utf-8-sig")
    strata_df.to_csv(STRATA_OUTPUT, index=False, encoding="utf-8-sig")
    return combined_df, summary_df, strata_df, token_freq_df


if __name__ == "__main__":
    combined_df, summary_df, strata_df, token_freq_df = build_experiment2()
    print(f"COMBINED_OUTPUT={COMBINED_OUTPUT}")
    print(f"SUMMARY_OUTPUT={SUMMARY_OUTPUT}")
    print(f"STRATA_OUTPUT={STRATA_OUTPUT}")
    print(f"TOKEN_FREQ_OUTPUT={TOKEN_FREQ_OUTPUT}")
    print(f"SCENIC_N={len(summary_df)}")
    print(f"TOTAL_ROWS={len(combined_df)}")
