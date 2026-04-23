#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_DIR / "data" / "rawdata" / "experiment2_lda_评分分层300条汇总大表.csv"
OUTPUT_DIR = PROJECT_DIR / "data" / "lda"
OUTPUT_COMPARE_PATH = OUTPUT_DIR / "experiment3_lda_candidate_compare.csv"
OUTPUT_KEYWORDS_PATH = OUTPUT_DIR / "experiment3_lda_topic_keywords.csv"
OUTPUT_TOP_REVIEWS_PATH = OUTPUT_DIR / "experiment3_lda_topic_top_reviews.csv"
OUTPUT_ASSIGNMENTS_PATH = OUTPUT_DIR / "experiment3_lda_topic_assignments.csv"
OUTPUT_SCENIC_SHARE_PATH = OUTPUT_DIR / "experiment3_lda_scenic_topic_share.csv"
OUTPUT_REPORT_PATH = OUTPUT_DIR / "experiment3_lda_report.md"

CANDIDATE_K = [4, 5, 6]
TOP_WORD_N = 12
TOP_REVIEW_N = 5
MIN_DF = 5
MAX_DF = 0.75
RANDOM_STATE = 42
LDA_MAX_ITER = 80
MIN_REVIEW_LENGTH_FOR_REPR = 12
LDA_MIN_TEXT_CHAR_LEN = 8
LDA_MAX_TEXT_CHAR_LEN = 240
LDA_MIN_TOKEN_COUNT = 5
LDA_MAX_TOKEN_COUNT = 60
MIN_UNIQUE_TOKEN_RATIO = 0.45
MAX_SINGLE_TOKEN_SHARE = 0.34

LDA_EXTRA_STOPWORDS = {
    "历史",
    "建筑",
    "皇家",
    "园林",
    "古代",
    "位于",
    "游客",
    "看到",
    "感受",
    "展览",
    "之一",
    "皇帝",
    "今天",
    "开始",
    "现在",
    "每年",
    "春天",
    "樱花",
    "红叶",
    "北京城",
    "巡山",
    "动物",
    "水立方",
    "孩子",
    "看看",
}

NOISE_MARKERS = {
    "以下是对",
    "我给你写了",
    "直接复制",
    "简短版",
    "详细版",
    "点评通用",
    "游玩点评",
    "相关照片",
    "作为中国现存",
    "融合了自然景观",
    "历史文化价值",
}

POSITIVE_THEME_WORDS = {
    "不错",
    "推荐",
    "漂亮",
    "好看",
    "喜欢",
    "方便",
    "适合",
    "美丽",
    "震撼",
    "壮观",
    "夜景",
    "景色",
    "体验",
    "舒服",
    "经典",
    "完美",
}

THEME_CODEBOOK = {
    "service_guide": {
        "name": "现场服务与导览体验",
        "keyword_groups": {
            "服务", "客服", "工作人员", "态度", "流程", "安排", "讲解", "导游",
            "引导", "专业", "老师", "耐心", "详细", "体验", "讲得",
        },
    },
    "leisure_landscape": {
        "name": "景观游逛与休闲体验",
        "keyword_groups": {
            "漂亮", "风景", "景色", "景观", "好看", "散步", "休闲", "适合",
            "拍照", "夜景", "美丽", "舒服", "打卡", "喜欢", "很大",
        },
    },
    "traffic_space": {
        "name": "交通与开放空间体验",
        "keyword_groups": {
            "交通", "停车", "地铁", "公交", "换乘", "方便", "开放", "中心",
            "中轴线", "北园", "南园", "面积", "休闲", "入口", "路线",
        },
    },
    "ticket_entry": {
        "name": "票务预约与入园体验",
        "keyword_groups": {
            "门票", "预约", "预订", "购票", "购买", "提前", "入园", "入场",
            "排队", "时间", "缆车", "票价", "检票", "需要", "入口",
        },
    },
}


@dataclass
class CandidateResult:
    k: int
    lda_model: LatentDirichletAllocation
    doc_topic_matrix: np.ndarray
    topic_keywords: dict[int, list[str]]
    topic_summary: pd.DataFrame
    topic_name_map: dict[int, str]
    satisfaction_topic_id: int | None
    coherence_umass: float
    keyword_overlap: float
    selection_score: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LDA on experiment2 LDA-ready review data.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--candidate-k", type=int, nargs="+", default=CANDIDATE_K)
    return parser.parse_args()


def load_corpus(input_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path, encoding="utf-8-sig")
    df["review_time"] = pd.to_datetime(df["review_time"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["tokens_text"] = df["tokens_text"].fillna("").astype(str).str.strip()
    df["review_text"] = df["review_text"].fillna("").astype(str)
    df = df[
        df["rating"].notna()
        & df["tokens_text"].astype(bool)
    ].copy()
    df["text_char_len"] = df["review_text"].str.len()
    df["tokens_list"] = df["tokens_text"].str.split().map(
        lambda xs: [token for token in xs if token and token not in LDA_EXTRA_STOPWORDS]
    )
    df["token_count"] = df["tokens_list"].map(len)
    df["unique_token_ratio"] = df["tokens_list"].map(
        lambda xs: (len(set(xs)) / len(xs)) if xs else 0.0
    )
    df["max_single_token_share"] = df["tokens_list"].map(
        lambda xs: (max(xs.count(token) for token in set(xs)) / len(xs)) if xs else 1.0
    )
    df["tokens_text"] = df["tokens_list"].map(lambda xs: " ".join(xs))
    df = df[
        df["text_char_len"].between(LDA_MIN_TEXT_CHAR_LEN, LDA_MAX_TEXT_CHAR_LEN)
        & df["token_count"].between(LDA_MIN_TOKEN_COUNT, LDA_MAX_TOKEN_COUNT)
        & df["unique_token_ratio"].ge(MIN_UNIQUE_TOKEN_RATIO)
        & df["max_single_token_share"].le(MAX_SINGLE_TOKEN_SHARE)
        & df["tokens_text"].astype(bool)
        & ~df["review_text"].map(is_noise_review)
    ].copy()
    df["review_id"] = df["comment_id"].astype(str)
    return df.reset_index(drop=True)


def is_noise_review(text: str) -> bool:
    text = str(text or "").strip()
    if not text:
        return True

    if len(text) >= 80 and any(marker in text for marker in NOISE_MARKERS):
        return True

    if re.search(r"(.{2,8})\1{3,}", text):
        return True

    if re.search(r"(好|棒|赞|差|啊)\1{6,}", text):
        return True

    return False


def build_vectorizer() -> CountVectorizer:
    return CountVectorizer(
        tokenizer=str.split,
        preprocessor=None,
        token_pattern=None,
        min_df=MIN_DF,
        max_df=MAX_DF,
    )


def pairwise_umass(binary_matrix, word_ids: Sequence[int]) -> float:
    if len(word_ids) <= 1:
        return float("-inf")

    scores: list[float] = []
    for upper_index in range(1, len(word_ids)):
        w_i = word_ids[upper_index]
        col_i = binary_matrix[:, w_i]
        for lower_index in range(upper_index):
            w_j = word_ids[lower_index]
            col_j = binary_matrix[:, w_j]
            d_wj = float(col_j.sum())
            if d_wj <= 0:
                continue
            d_pair = float(col_i.multiply(col_j).sum())
            scores.append(math.log((d_pair + 1.0) / d_wj))
    return float(np.mean(scores)) if scores else float("-inf")


def mean_keyword_jaccard(topic_keywords: dict[int, list[str]]) -> float:
    topic_ids = sorted(topic_keywords)
    if len(topic_ids) <= 1:
        return 0.0

    values: list[float] = []
    for i, topic_id_a in enumerate(topic_ids):
        set_a = set(topic_keywords[topic_id_a])
        for topic_id_b in topic_ids[i + 1 :]:
            set_b = set(topic_keywords[topic_id_b])
            union = len(set_a | set_b)
            if union == 0:
                continue
            values.append(len(set_a & set_b) / union)
    return float(np.mean(values)) if values else 0.0


def positive_keyword_hits(words: Sequence[str]) -> int:
    return sum(1 for word in words if word in POSITIVE_THEME_WORDS)


def compute_theme_code_scores(topic_keywords: Sequence[str]) -> dict[str, float]:
    topic_word_set = set(topic_keywords)
    scores: dict[str, float] = {}
    for code, rule in THEME_CODEBOOK.items():
        scores[code] = sum(1.0 for word in rule["keyword_groups"] if word in topic_word_set)
    return scores


def build_topic_summary(
    corpus_df: pd.DataFrame,
    doc_topic_matrix: np.ndarray,
    topic_keywords: dict[int, list[str]],
) -> pd.DataFrame:
    dominant_topic_ids = doc_topic_matrix.argmax(axis=1)
    rating_values = pd.to_numeric(corpus_df["rating"], errors="coerce").to_numpy()
    high_rating = (rating_values >= 4.0).astype(float)
    low_rating = (rating_values <= 2.0).astype(float)
    summary_rows: list[dict[str, object]] = []

    for topic_id in range(doc_topic_matrix.shape[1]):
        weights = doc_topic_matrix[:, topic_id]
        weight_sum = float(weights.sum())
        dominant_n = int((dominant_topic_ids == topic_id).sum())
        theme_code_scores = compute_theme_code_scores(topic_keywords.get(topic_id, []))

        summary_rows.append(
            {
                "lda_topic_id": topic_id,
                "topic_share": float(weights.mean()),
                "dominant_review_n": dominant_n,
                "dominant_review_share": dominant_n / len(corpus_df),
                "avg_rating_weighted": float(np.dot(weights, np.nan_to_num(rating_values, nan=0.0)) / weight_sum) if weight_sum > 0 else np.nan,
                "high_rating_rate_weighted": float(np.dot(weights, high_rating) / weight_sum) if weight_sum > 0 else np.nan,
                "low_rating_rate_weighted": float(np.dot(weights, low_rating) / weight_sum) if weight_sum > 0 else np.nan,
                "positive_keyword_hits": positive_keyword_hits(topic_keywords.get(topic_id, [])),
                "top_keywords": "|".join(topic_keywords.get(topic_id, [])),
                **{f"theme_score_{code}": value for code, value in theme_code_scores.items()},
            }
        )

    return pd.DataFrame(summary_rows).sort_values("lda_topic_id").reset_index(drop=True)


def choose_satisfaction_topic(summary_df: pd.DataFrame) -> int | None:
    scored = summary_df.copy()
    scored["satisfaction_score"] = (
        scored["positive_keyword_hits"] * 0.35
        + scored["high_rating_rate_weighted"].fillna(0.0) * 1.00
        + (scored["avg_rating_weighted"].fillna(0.0) / 5.0) * 0.50
        - scored["low_rating_rate_weighted"].fillna(0.0) * 0.90
    )
    best_row = scored.sort_values("satisfaction_score", ascending=False).iloc[0]
    if float(best_row["satisfaction_score"]) < 1.10:
        return None
    if int(best_row["positive_keyword_hits"]) < 2:
        return None
    if float(best_row["avg_rating_weighted"]) < 4.0:
        return None
    return int(best_row["lda_topic_id"])


def assign_topic_names(summary_df: pd.DataFrame, satisfaction_topic_id: int | None) -> dict[int, str]:
    name_map: dict[int, str] = {}
    used_codes: set[str] = set()

    for row in summary_df.sort_values("dominant_review_share", ascending=False).to_dict("records"):
        topic_id = int(row["lda_topic_id"])
        if satisfaction_topic_id is not None and topic_id == satisfaction_topic_id:
            name_map[topic_id] = "整体满意与感知评价"
            continue

        code_scores = {code: float(row.get(f"theme_score_{code}", 0.0)) for code in THEME_CODEBOOK}
        ranked_codes = sorted(code_scores.items(), key=lambda item: item[1], reverse=True)
        chosen_code = ranked_codes[0][0] if ranked_codes else "service_guide"
        for code, score in ranked_codes:
            if code not in used_codes and score > 0:
                chosen_code = code
                break
        used_codes.add(chosen_code)
        name_map[topic_id] = THEME_CODEBOOK[chosen_code]["name"]

    return name_map


def score_candidate(summary_df: pd.DataFrame, coherence_umass: float, keyword_overlap: float, k: int, satisfaction_topic_id: int | None) -> float:
    issue_theme_count = len(summary_df) - (1 if satisfaction_topic_id is not None else 0)
    has_balanced_issue_themes = 1.0 if 3 <= issue_theme_count <= 4 else 0.0
    satisfaction_bonus = 0.18 if satisfaction_topic_id is not None else 0.0
    k_bonus = 0.05 if k == 5 else (0.03 if k == 4 else 0.0)
    return coherence_umass - 0.35 * keyword_overlap + satisfaction_bonus + has_balanced_issue_themes * 0.08 + k_bonus


def fit_candidate_models(corpus_df: pd.DataFrame, dtm, vectorizer: CountVectorizer, candidate_k: Sequence[int]) -> list[CandidateResult]:
    feature_names = np.array(vectorizer.get_feature_names_out())
    binary_matrix = (dtm > 0).astype(int).tocsr()
    results: list[CandidateResult] = []

    for k in candidate_k:
        lda_model = LatentDirichletAllocation(
            n_components=k,
            random_state=RANDOM_STATE,
            learning_method="batch",
            max_iter=LDA_MAX_ITER,
        )
        doc_topic_matrix = lda_model.fit_transform(dtm)

        topic_keywords: dict[int, list[str]] = {}
        topic_word_ids: dict[int, list[int]] = {}
        for topic_id, weights in enumerate(lda_model.components_):
            top_ids = np.argsort(weights)[::-1][:TOP_WORD_N]
            topic_word_ids[topic_id] = top_ids.tolist()
            topic_keywords[topic_id] = feature_names[top_ids].tolist()

        coherence_scores = [pairwise_umass(binary_matrix, topic_word_ids[topic_id][:10]) for topic_id in range(k)]
        coherence_umass = float(np.mean(coherence_scores))
        keyword_overlap = mean_keyword_jaccard(topic_keywords)
        topic_summary = build_topic_summary(corpus_df, doc_topic_matrix, topic_keywords)
        satisfaction_topic_id = choose_satisfaction_topic(topic_summary)
        topic_name_map = assign_topic_names(topic_summary, satisfaction_topic_id)
        selection_score = score_candidate(topic_summary, coherence_umass, keyword_overlap, k, satisfaction_topic_id)

        results.append(
            CandidateResult(
                k=k,
                lda_model=lda_model,
                doc_topic_matrix=doc_topic_matrix,
                topic_keywords=topic_keywords,
                topic_summary=topic_summary,
                topic_name_map=topic_name_map,
                satisfaction_topic_id=satisfaction_topic_id,
                coherence_umass=coherence_umass,
                keyword_overlap=keyword_overlap,
                selection_score=selection_score,
            )
        )

    return results


def choose_final_candidate(results: Sequence[CandidateResult]) -> CandidateResult:
    ordered = sorted(results, key=lambda item: (item.selection_score, item.coherence_umass), reverse=True)
    best = ordered[0]
    k5_candidate = next((item for item in results if item.k == 5 and item.satisfaction_topic_id is not None), None)
    if k5_candidate is not None and (best.selection_score - k5_candidate.selection_score) <= 0.25:
        return k5_candidate
    return best


def build_assignment_table(corpus_df: pd.DataFrame, candidate: CandidateResult) -> pd.DataFrame:
    assignment_df = corpus_df.copy()
    dominant_topic_ids = candidate.doc_topic_matrix.argmax(axis=1)
    assignment_df["lda_topic_id"] = dominant_topic_ids
    assignment_df["lda_topic_prob"] = candidate.doc_topic_matrix.max(axis=1)
    assignment_df["lda_topic_name_cn"] = assignment_df["lda_topic_id"].map(candidate.topic_name_map)
    assignment_df["is_satisfaction_topic"] = assignment_df["lda_topic_id"].eq(candidate.satisfaction_topic_id).astype(int)

    for topic_id in range(candidate.doc_topic_matrix.shape[1]):
        assignment_df[f"topic_prob_{topic_id}"] = candidate.doc_topic_matrix[:, topic_id]

    ordered_columns = [
        "slot_rank",
        "category_name",
        "requested_name",
        "selected_name",
        "selected_from",
        "scenic_name",
        "comment_id",
        "review_id",
        "review_time",
        "rating",
        "rating_bucket",
        "review_text",
        "token_count",
        "tokens_text",
        "lda_topic_id",
        "lda_topic_name_cn",
        "lda_topic_prob",
        "is_satisfaction_topic",
    ] + [f"topic_prob_{topic_id}" for topic_id in range(candidate.doc_topic_matrix.shape[1])]

    return assignment_df[ordered_columns]


def build_topic_keyword_table(candidate: CandidateResult) -> pd.DataFrame:
    summary_df = candidate.topic_summary.copy()
    summary_df["topic_name_cn"] = summary_df["lda_topic_id"].map(candidate.topic_name_map)
    summary_df["is_satisfaction_topic"] = summary_df["lda_topic_id"].eq(candidate.satisfaction_topic_id).astype(int)
    summary_df["topic_role"] = np.where(summary_df["is_satisfaction_topic"].eq(1), "satisfaction", "governance")

    return summary_df[
        [
            "lda_topic_id",
            "topic_name_cn",
            "topic_role",
            "is_satisfaction_topic",
            "topic_share",
            "dominant_review_n",
            "dominant_review_share",
            "avg_rating_weighted",
            "high_rating_rate_weighted",
            "low_rating_rate_weighted",
            "positive_keyword_hits",
            "top_keywords",
        ]
    ].sort_values("lda_topic_id").reset_index(drop=True)


def build_top_review_table(assignment_df: pd.DataFrame, candidate: CandidateResult) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for topic_id, topic_name in candidate.topic_name_map.items():
        subset = assignment_df.loc[assignment_df["lda_topic_id"].eq(topic_id)].copy()
        subset["review_length"] = subset["review_text"].fillna("").map(len)
        subset = subset.loc[subset["review_length"] >= MIN_REVIEW_LENGTH_FOR_REPR]
        subset = subset.sort_values(["lda_topic_prob", "review_length"], ascending=[False, False]).head(TOP_REVIEW_N)

        for rank, review_row in enumerate(subset.to_dict("records"), start=1):
            rows.append(
                {
                    "lda_topic_id": topic_id,
                    "topic_name_cn": topic_name,
                    "representative_rank": rank,
                    "scenic_name": review_row["scenic_name"],
                    "comment_id": review_row["comment_id"],
                    "rating": review_row["rating"],
                    "lda_topic_prob": review_row["lda_topic_prob"],
                    "review_text": review_row["review_text"],
                }
            )
    return pd.DataFrame(rows)


def build_scenic_topic_share_table(assignment_df: pd.DataFrame) -> pd.DataFrame:
    scenic_totals = assignment_df.groupby("scenic_name", as_index=False).size().rename(columns={"size": "scenic_review_n"})
    scenic_topic_counts = (
        assignment_df.groupby(["scenic_name", "lda_topic_id", "lda_topic_name_cn"], as_index=False)
        .size()
        .rename(columns={"size": "topic_review_n"})
    )
    merged = scenic_topic_counts.merge(scenic_totals, on="scenic_name", how="left")
    merged["topic_share_within_scenic"] = merged["topic_review_n"] / merged["scenic_review_n"]
    return merged.sort_values(["scenic_name", "topic_share_within_scenic"], ascending=[True, False]).reset_index(drop=True)


def build_candidate_compare_table(results: Sequence[CandidateResult]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for result in results:
        issue_theme_n = result.k - (1 if result.satisfaction_topic_id is not None else 0)
        rows.append(
            {
                "candidate_k": result.k,
                "coherence_umass": result.coherence_umass,
                "keyword_overlap_jaccard": result.keyword_overlap,
                "selection_score": result.selection_score,
                "satisfaction_topic_id": result.satisfaction_topic_id,
                "issue_theme_n": issue_theme_n,
                "topic_names": " | ".join(result.topic_name_map[topic_id] for topic_id in sorted(result.topic_name_map)),
            }
        )
    return pd.DataFrame(rows).sort_values("candidate_k").reset_index(drop=True)


def safe_snippet(text: str, limit: int = 90) -> str:
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def write_report(
    output_path: Path,
    corpus_df: pd.DataFrame,
    candidate_compare_df: pd.DataFrame,
    candidate: CandidateResult,
    topic_keyword_df: pd.DataFrame,
    top_review_df: pd.DataFrame,
) -> None:
    lines: list[str] = [
        "# Experiment 3 LDA 报告",
        "",
        "## 1. 数据说明",
        f"- 输入文件：`{DEFAULT_INPUT_PATH.name}`",
        f"- 进入 LDA 的评论数：{len(corpus_df)}",
        f"- 候选主题数：{', '.join(str(value) for value in CANDIDATE_K)}",
        "",
        "## 2. K 候选比较",
    ]

    for row in candidate_compare_df.to_dict("records"):
        lines.append(
            "- "
            f"K={int(row['candidate_k'])} | "
            f"coherence={float(row['coherence_umass']):.4f} | "
            f"overlap={float(row['keyword_overlap_jaccard']):.4f} | "
            f"score={float(row['selection_score']):.4f} | "
            f"satisfaction_topic_id={row['satisfaction_topic_id']} | "
            f"topic_names={row['topic_names']}"
        )

    lines.extend(
        [
            "",
            "## 3. 最终选用",
            f"- 最终 K：{candidate.k}",
            f"- 独立满意主题：{candidate.topic_name_map.get(candidate.satisfaction_topic_id, '未识别') if candidate.satisfaction_topic_id is not None else '未识别'}",
            "",
            "## 4. 最终主题",
        ]
    )

    for topic_row in topic_keyword_df.to_dict("records"):
        topic_id = int(topic_row["lda_topic_id"])
        topic_name = str(topic_row["topic_name_cn"])
        role = "满意/感知主题" if int(topic_row["is_satisfaction_topic"]) == 1 else "治理主题"
        lines.extend(
            [
                f"### Topic {topic_id}: {topic_name}",
                f"- 主题角色：{role}",
                f"- 核心关键词：{str(topic_row['top_keywords']).replace('|', '、')}",
                f"- 主题占比：{float(topic_row['topic_share']):.3f}",
                f"- 加权平均评分：{float(topic_row['avg_rating_weighted']):.3f}",
                f"- 高评分占比（>=4）：{float(topic_row['high_rating_rate_weighted']):.3f}",
                f"- 低评分占比（<=2）：{float(topic_row['low_rating_rate_weighted']):.3f}",
            ]
        )
        topic_reviews = top_review_df.loc[top_review_df["lda_topic_id"].eq(topic_id)].head(2)
        for review_row in topic_reviews.to_dict("records"):
            lines.append(
                f"- 代表评论（{review_row['scenic_name']}，rating={review_row['rating']}, prob={float(review_row['lda_topic_prob']):.3f}）："
                f"{safe_snippet(str(review_row['review_text']))}"
            )
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = args.input_path if args.input_path.is_absolute() else PROJECT_DIR / args.input_path
    corpus_df = load_corpus(input_path)

    vectorizer = build_vectorizer()
    dtm = vectorizer.fit_transform(corpus_df["tokens_text"])
    results = fit_candidate_models(corpus_df, dtm, vectorizer, args.candidate_k)
    final_candidate = choose_final_candidate(results)

    assignment_df = build_assignment_table(corpus_df, final_candidate)
    topic_keyword_df = build_topic_keyword_table(final_candidate)
    top_review_df = build_top_review_table(assignment_df, final_candidate)
    scenic_topic_share_df = build_scenic_topic_share_table(assignment_df)
    candidate_compare_df = build_candidate_compare_table(results)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidate_compare_df.to_csv(OUTPUT_COMPARE_PATH, index=False, encoding="utf-8-sig")
    topic_keyword_df.to_csv(OUTPUT_KEYWORDS_PATH, index=False, encoding="utf-8-sig")
    top_review_df.to_csv(OUTPUT_TOP_REVIEWS_PATH, index=False, encoding="utf-8-sig")
    assignment_df.to_csv(OUTPUT_ASSIGNMENTS_PATH, index=False, encoding="utf-8-sig")
    scenic_topic_share_df.to_csv(OUTPUT_SCENIC_SHARE_PATH, index=False, encoding="utf-8-sig")
    write_report(
        OUTPUT_REPORT_PATH,
        corpus_df,
        candidate_compare_df,
        final_candidate,
        topic_keyword_df,
        top_review_df,
    )

    print(f"OUTPUT_COMPARE_PATH={OUTPUT_COMPARE_PATH}")
    print(f"OUTPUT_KEYWORDS_PATH={OUTPUT_KEYWORDS_PATH}")
    print(f"OUTPUT_TOP_REVIEWS_PATH={OUTPUT_TOP_REVIEWS_PATH}")
    print(f"OUTPUT_ASSIGNMENTS_PATH={OUTPUT_ASSIGNMENTS_PATH}")
    print(f"OUTPUT_SCENIC_SHARE_PATH={OUTPUT_SCENIC_SHARE_PATH}")
    print(f"OUTPUT_REPORT_PATH={OUTPUT_REPORT_PATH}")
    print(f"FINAL_K={final_candidate.k}")
    print(f"LDA_DOC_N={len(corpus_df)}")


if __name__ == "__main__":
    main()
